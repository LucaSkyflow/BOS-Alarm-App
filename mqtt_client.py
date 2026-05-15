import json
import socket
import ssl
import time
import logging
import paho.mqtt.client as mqtt

log = logging.getLogger(__name__)

try:
    import certifi
    _CA_CERTS = certifi.where()
except Exception:
    _CA_CERTS = None


class MQTTManager:
    """READ ONLY MQTT client - no publish() exists in this class."""

    # MQTT-level keepalive. Broker pings every KEEPALIVE seconds; paho marks
    # the connection dead after ~1.5x without a PINGRESP. Lower = faster
    # detection of zombie sockets, at the cost of slightly more traffic.
    KEEPALIVE = 30

    # Safety net: if paho still claims connected but no PINGRESP / message
    # was seen for this long, the socket is almost certainly a zombie —
    # force a reconnect. Must be well above KEEPALIVE * 2.
    STALE_TIMEOUT = 120

    def __init__(self, broker, port, username, password, use_tls, topic, label,
                 on_message_callback=None, on_connect_callback=None, on_disconnect_callback=None):
        self._broker = self._clean_broker(broker)
        self._port = int(port)
        self._username = username
        self._password = password
        self._use_tls = use_tls
        self._topic = topic
        self._label = label
        self._on_message_cb = on_message_callback
        self._on_connect_cb = on_connect_callback
        self._on_disconnect_cb = on_disconnect_callback
        self._client: mqtt.Client | None = None
        # Broker-confirmed connection (set on CONNACK rc=0, cleared on DISCONNECT).
        # paho's own is_connected() can stay True over a dead socket — this
        # flag plus PINGRESP-based liveness is what we actually trust.
        self._connected: bool = False
        # monotonic timestamp of last sign of life (CONNACK, message, PINGRESP)
        self._last_activity: float = 0.0

    @staticmethod
    def _clean_broker(broker: str) -> str:
        """Strip protocol prefixes and port from broker address.

        Handles inputs like:
          mqtts://mqtt.example.com:8883  →  mqtt.example.com
          mqtt://mqtt.example.com        →  mqtt.example.com
          tcp://mqtt.example.com:1883    →  mqtt.example.com
          mqtt.example.com:8883          →  mqtt.example.com
          mqtt.example.com               →  mqtt.example.com
        """
        b = broker.strip()
        # Remove protocol prefix
        for prefix in ("mqtts://", "mqtt://", "ssl://", "tcp://", "https://", "http://"):
            if b.lower().startswith(prefix):
                b = b[len(prefix):]
                break
        # Remove port suffix
        if ":" in b:
            b = b.split(":")[0]
        return b.strip()

    def connect(self):
        self.disconnect()

        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        if self._use_tls:
            if _CA_CERTS:
                log.info(f"MQTT [{self._label}] TLS with certifi: {_CA_CERTS}")
                self._client.tls_set(
                    ca_certs=_CA_CERTS,
                    cert_reqs=ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLS_CLIENT,
                )
            else:
                log.info(f"MQTT [{self._label}] TLS with system defaults")
                self._client.tls_set(
                    cert_reqs=ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLS_CLIENT,
                )

        if self._username:
            self._client.username_pw_set(self._username, self._password)

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.on_socket_open = self._on_socket_open
        # on_log lets us notice PINGRESP traffic so STALE_TIMEOUT doesn't
        # trip on a perfectly healthy but quiet connection.
        self._client.on_log = self._on_log

        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

        if not self._broker:
            log.warning(f"MQTT [{self._label}] broker is empty — skipping connect")
            return

        log.info(f"MQTT [{self._label}] connecting to {self._broker}:{self._port} "
                 f"(TLS={self._use_tls}, user={self._username!r}, keepalive={self.KEEPALIVE}s)")
        try:
            self._client.connect_async(self._broker, self._port, keepalive=self.KEEPALIVE)
            self._client.loop_start()
        except Exception as e:
            log.error(f"MQTT [{self._label}] connect_async failed: {e}")
            self._client = None

    def disconnect(self):
        self._connected = False
        self._last_activity = 0.0
        if self._client is not None:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:
                pass
            self._client = None

    def is_connected(self) -> bool:
        """True only if the broker confirmed CONNACK AND paho still considers
        the socket connected. paho's own ``is_connected()`` can lie after a
        silently dropped TCP connection — the ``_connected`` flag, cleared
        on the DISCONNECT callback, keeps the UI honest."""
        return (
            self._client is not None
            and self._connected
            and self._client.is_connected()
        )

    def check_alive(self) -> bool:
        """Verify the connection is actually alive; force a reconnect if it
        looks like a zombie. Returns True if connection appears healthy.

        Call this periodically (e.g. from the health loop). Combined with
        the shorter KEEPALIVE and OS-level TCP keepalive, this catches the
        rare cases where paho still claims connected over a dead socket."""
        if self._client is None:
            return False
        if not self._connected:
            # not connected (or never was); paho's loop_start handles reconnect
            return False
        if self._last_activity == 0:
            return True  # just connected, no activity expected yet
        idle = time.monotonic() - self._last_activity
        if idle > self.STALE_TIMEOUT:
            log.warning(
                f"MQTT [{self._label}] no PINGRESP/traffic for {idle:.0f}s "
                f"while still 'connected' — forcing reconnect"
            )
            self._connected = False
            if self._on_disconnect_cb:
                try:
                    self._on_disconnect_cb(self._label, "stale connection")
                except Exception:
                    pass
            try:
                self._client.reconnect()
            except Exception as e:
                log.error(f"MQTT [{self._label}] reconnect() failed: {e} — full reinit")
                try:
                    self.connect()
                except Exception as e2:
                    log.error(f"MQTT [{self._label}] full reinit failed: {e2}")
            return False
        return True

    # ── Callbacks ──────────────────────────────────────────────────────────

    def _on_socket_open(self, client, userdata, sock):
        # OS-level TCP keepalive. Detects half-open sockets (NAT timeout,
        # Windows wake-from-sleep) faster than the MQTT-layer ping.
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            if hasattr(socket, "SIO_KEEPALIVE_VALS"):
                # Windows: (onoff, idle_ms, interval_ms). After 20s idle, probe
                # every 5s; OS drops the socket after ~10 missed probes.
                sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 20_000, 5_000))
        except Exception as e:
            log.debug(f"MQTT [{self._label}] socket keepalive setup failed: {e}")

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        # paho v2 ReasonCode compares cleanly to ints
        rc_failed = False
        try:
            rc_failed = (int(getattr(reason_code, "value", reason_code)) != 0)
        except Exception:
            rc_failed = (reason_code != 0)

        if rc_failed:
            log.error(f"MQTT [{self._label}] connect REJECTED (rc={reason_code})")
            self._connected = False
            if self._on_disconnect_cb:
                self._on_disconnect_cb(self._label, f"rejected: {reason_code}")
            return

        log.info(f"MQTT [{self._label}] connected (rc={reason_code})")
        self._connected = True
        self._last_activity = time.monotonic()

        try:
            client.subscribe(self._topic)
            log.info(f"MQTT [{self._label}] subscribed to {self._topic}")
        except Exception as e:
            log.error(f"MQTT [{self._label}] subscribe failed: {e}")

        if self._on_connect_cb:
            self._on_connect_cb(self._label)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        log.warning(f"MQTT [{self._label}] disconnected (rc={reason_code})")
        self._connected = False
        if self._on_disconnect_cb:
            self._on_disconnect_cb(self._label, str(reason_code))

    def _on_message(self, client, userdata, msg):
        self._last_activity = time.monotonic()
        topic = msg.topic
        raw = msg.payload.decode("utf-8", errors="replace")

        payload = None
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            pass

        if self._on_message_cb:
            self._on_message_cb(topic, payload, raw, self._label)

    def _on_log(self, client, userdata, level, buf):
        # paho emits "Received PINGRESP" each successful keepalive round-trip.
        # Counting that as activity prevents check_alive() from tripping on
        # a healthy-but-quiet production feed.
        if buf and ("PINGRESP" in buf or "Received CONNACK" in buf):
            self._last_activity = time.monotonic()
