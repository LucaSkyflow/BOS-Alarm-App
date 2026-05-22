import json
import socket
import ssl
import threading
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
    """READ ONLY MQTT client - no publish() exists in this class.

    Reliability model (v1.7.5+):
    - The dashboard goes green only when BOTH CONNACK and SUBACK have been
      confirmed by the broker. paho's own is_connected() is not trusted;
      it's known to lie over silently dropped TLS sockets (paho-mqtt
      issues #840, #525, #891). More importantly, a CONNACK without a
      successful SUBACK is the exact "looks connected, no messages flow"
      zombie we keep hitting — usually a broker-side ACL silently
      denying SUBSCRIBE, or a SUBACK dropped on the wire.
    - check_alive() is the watchdog. It catches:
        a) the paho background loop thread crashed (issue #894)
        b) SUBACK never arrived after CONNACK (SUBSCRIBE_TIMEOUT)
        c) we've been disconnected too long (paho retry stuck, #785)
        d) no traffic for STALE_TIMEOUT (dead socket, #891)
      On any of these it triggers a full teardown + fresh client reinit
      on a dedicated thread — never blocks the caller, never races with
      the paho loop thread (issue #636).
    - We never call client.reconnect() from outside the paho loop
      thread. Soft reconnects are unreliable; only a fresh mqtt.Client
      instance recovers cleanly.
    """

    # MQTT-level keepalive: broker pings every KEEPALIVE seconds.
    KEEPALIVE = 30

    # No PINGRESP/PUBLISH for this long → zombie → reinit.
    # 60s gives ~2 keepalive cycles to recover before we tear down.
    STALE_TIMEOUT = 60

    # After CONNACK, if SUBACK doesn't arrive within this window → reinit.
    # Real SUBACKs come back in <500 ms; 10s is generous.
    SUBSCRIBE_TIMEOUT = 10

    # If _connected has stayed False for this long (paho's auto-reconnect
    # is stuck spinning) → force a fresh client.
    DISCONNECTED_TIMEOUT = 60

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

        # Broker-confirmed state. paho is not trusted for either of these.
        self._connected: bool = False        # CONNACK rc=0
        self._subscribed: bool = False       # SUBACK rc<0x80
        self._subscribe_mid: int | None = None

        # monotonic timestamps
        self._last_activity: float = 0.0
        self._connected_at: float = 0.0
        self._disconnected_at: float = 0.0

        # Reinit serialization. _do_reinit runs on its own thread so the
        # health loop never blocks on TLS handshakes.
        self._reinit_lock = threading.Lock()
        self._reinit_in_progress: bool = False

    @staticmethod
    def _clean_broker(broker: str) -> str:
        b = broker.strip()
        for prefix in ("mqtts://", "mqtt://", "ssl://", "tcp://", "https://", "http://"):
            if b.lower().startswith(prefix):
                b = b[len(prefix):]
                break
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
        self._client.on_subscribe = self._on_subscribe
        self._client.on_socket_open = self._on_socket_open
        self._client.on_log = self._on_log

        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

        if not self._broker:
            log.warning(f"MQTT [{self._label}] broker is empty — skipping connect")
            self._client = None
            return

        log.info(f"MQTT [{self._label}] connecting to {self._broker}:{self._port} "
                 f"(TLS={self._use_tls}, user={self._username!r}, keepalive={self.KEEPALIVE}s)")
        self._disconnected_at = time.monotonic()
        try:
            self._client.connect_async(self._broker, self._port, keepalive=self.KEEPALIVE)
            self._client.loop_start()
        except Exception as e:
            log.error(f"MQTT [{self._label}] connect_async failed: {e}")
            self._client = None

    def disconnect(self):
        self._connected = False
        self._subscribed = False
        self._subscribe_mid = None
        self._last_activity = 0.0
        self._connected_at = 0.0
        self._disconnected_at = time.monotonic()
        if self._client is not None:
            try:
                self._client.loop_stop()
            except Exception:
                pass
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._client = None

    def is_connected(self) -> bool:
        """Truth source for the dashboard. Green ONLY when:
          - broker sent CONNACK with success, AND
          - broker sent SUBACK with success for our topic.
        paho's own is_connected() is intentionally NOT consulted — it
        returns True over silently dead sockets (issues #840, #891)."""
        return self._connected and self._subscribed

    def check_alive(self) -> bool:
        """Watchdog. Returns True if the connection is healthy.
        On any detected fault, schedules a full reinit on a dedicated
        thread (never blocks the caller, never races with paho's loop)."""
        if self._client is None:
            return False
        if not self._broker:
            return False

        # (a) paho's background loop thread crashed?
        # paho doesn't recover from this — auto-reconnect lives in that
        # very thread. See paho issues #894 and #891.
        thread = getattr(self._client, "_thread", None)
        if thread is not None and not thread.is_alive():
            log.error(f"MQTT [{self._label}] paho loop thread is DEAD — forcing reinit")
            self._trigger_reinit("loop thread dead")
            return False

        now = time.monotonic()

        # (b) Stuck disconnected? paho should auto-reconnect, but it can
        # silently give up after long outages (issue #785).
        if not self._connected:
            if self._disconnected_at > 0:
                stuck = now - self._disconnected_at
                if stuck > self.DISCONNECTED_TIMEOUT:
                    log.warning(
                        f"MQTT [{self._label}] disconnected for {stuck:.0f}s "
                        f"(auto-reconnect stuck) — forcing reinit"
                    )
                    self._trigger_reinit("stuck disconnected")
            return False

        # (c) CONNACK arrived but SUBACK never did. Classic "looks
        # connected, no messages flow" zombie — broker accepted the
        # session but the SUBSCRIBE was denied or dropped.
        if not self._subscribed:
            since_connect = now - self._connected_at if self._connected_at > 0 else 0
            if since_connect > self.SUBSCRIBE_TIMEOUT:
                log.error(
                    f"MQTT [{self._label}] no SUBACK after {since_connect:.0f}s — "
                    f"forcing reinit (broker silently denied SUBSCRIBE?)"
                )
                self._trigger_reinit("subscribe timeout")
            return False

        # (d) Fully subscribed. No traffic for too long? paho's KEEPALIVE
        # is 30s, so a healthy quiet feed still sees PINGRESP every 30s
        # (tracked via _on_log). 60s without ANY activity = zombie.
        if self._last_activity == 0:
            return True  # just subscribed, no activity expected yet
        idle = now - self._last_activity
        if idle > self.STALE_TIMEOUT:
            log.warning(
                f"MQTT [{self._label}] no traffic for {idle:.0f}s "
                f"(socket appears dead) — forcing reinit"
            )
            self._trigger_reinit("stale connection")
            return False

        return True

    def _trigger_reinit(self, reason: str):
        """Schedule a full teardown + reinit on a dedicated thread.
        Idempotent: concurrent calls coalesce into one reinit cycle."""
        with self._reinit_lock:
            if self._reinit_in_progress:
                return
            self._reinit_in_progress = True

        # Mark down immediately so is_connected() flips red without
        # waiting for the next health tick.
        was_up = self._connected and self._subscribed
        self._connected = False
        self._subscribed = False
        if was_up and self._on_disconnect_cb:
            try:
                self._on_disconnect_cb(self._label, f"reinit: {reason}")
            except Exception:
                pass

        t = threading.Thread(
            target=self._do_reinit, args=(reason,), daemon=True,
            name=f"mqtt-reinit-{self._label}",
        )
        t.start()

    def _do_reinit(self, reason: str):
        log.info(f"MQTT [{self._label}] reinit START (reason: {reason})")
        try:
            self.connect()
        except Exception as e:
            log.error(f"MQTT [{self._label}] reinit failed: {e}")
        finally:
            with self._reinit_lock:
                self._reinit_in_progress = False
            log.info(f"MQTT [{self._label}] reinit DONE")

    # ── Callbacks (paho thread) ────────────────────────────────────────

    def _on_socket_open(self, client, userdata, sock):
        # OS-level TCP keepalive. Catches half-open sockets (NAT timeout,
        # wake-from-sleep) faster than the MQTT-layer ping.
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            if hasattr(socket, "SIO_KEEPALIVE_VALS"):
                # Windows: (onoff, idle_ms, interval_ms). 20s idle, 5s probes.
                sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 20_000, 5_000))
        except Exception as e:
            log.debug(f"MQTT [{self._label}] socket keepalive setup failed: {e}")

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        rc_failed = False
        try:
            rc_failed = (int(getattr(reason_code, "value", reason_code)) != 0)
        except Exception:
            rc_failed = (reason_code != 0)

        if rc_failed:
            log.error(f"MQTT [{self._label}] CONNECT REJECTED (rc={reason_code})")
            self._connected = False
            self._subscribed = False
            if self._on_disconnect_cb:
                try:
                    self._on_disconnect_cb(self._label, f"rejected: {reason_code}")
                except Exception:
                    pass
            return

        log.info(f"MQTT [{self._label}] CONNACK ok (rc={reason_code}) — subscribing")
        self._connected = True
        self._connected_at = time.monotonic()
        self._last_activity = time.monotonic()
        # NOTE: _disconnected_at is intentionally NOT cleared here. We
        # only clear it after SUBACK confirms the round-trip — so the
        # DISCONNECTED_TIMEOUT watchdog still applies if SUBACK hangs.

        try:
            result, mid = client.subscribe(self._topic)
            self._subscribe_mid = mid
            log.info(
                f"MQTT [{self._label}] SUBSCRIBE queued (mid={mid}, rc={result}) "
                f"topic={self._topic}"
            )
        except Exception as e:
            log.error(f"MQTT [{self._label}] subscribe call raised: {e}")
            # check_alive() will retire this connection via SUBSCRIBE_TIMEOUT

        # Deliberately do NOT fire _on_connect_cb here. The UI goes green
        # only after _on_subscribe confirms the broker accepted the topic.

    def _on_subscribe(self, client, userdata, mid, reason_code_list, properties=None):
        # Validate the SUBACK reason codes. paho-mqtt v2 returns a list
        # of ReasonCode objects; v5 failure codes are >=0x80.
        failures = []
        try:
            for rc in (reason_code_list or []):
                try:
                    rc_value = int(getattr(rc, "value", rc))
                except Exception:
                    rc_value = -1
                if rc_value >= 0x80 or rc_value < 0:
                    failures.append(str(rc))
        except TypeError:
            pass

        if failures:
            log.error(
                f"MQTT [{self._label}] SUBACK FAILURE (mid={mid}, codes={reason_code_list}) — "
                f"watchdog will reinit"
            )
            self._subscribed = False
            # Do NOT trigger reinit from inside a paho callback — set
            # state and let the next health tick (check_alive) handle it.
            return

        log.info(
            f"MQTT [{self._label}] SUBACK ok (mid={mid}, codes={reason_code_list})"
        )
        self._subscribed = True
        self._last_activity = time.monotonic()
        self._disconnected_at = 0.0  # full handshake done — clear stuck-disconnect watchdog

        # Fully up. NOW tell the app to turn the dashboard green.
        if self._on_connect_cb:
            try:
                self._on_connect_cb(self._label)
            except Exception as e:
                log.error(f"MQTT [{self._label}] on_connect_cb raised: {e}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        log.warning(f"MQTT [{self._label}] DISCONNECT (rc={reason_code})")
        was_up = self._connected and self._subscribed
        self._connected = False
        self._subscribed = False
        self._disconnected_at = time.monotonic()
        # Only flash red if we were actually up — avoids spurious flicker
        # during the brief CONNACK→SUBACK window or on graceful reconnect.
        if was_up and self._on_disconnect_cb:
            try:
                self._on_disconnect_cb(self._label, str(reason_code))
            except Exception:
                pass

    def _on_message(self, client, userdata, msg):
        self._last_activity = time.monotonic()
        topic = msg.topic
        try:
            raw = msg.payload.decode("utf-8", errors="replace")
        except Exception as e:
            log.error(f"MQTT [{self._label}] payload decode error: {e}")
            return

        payload = None
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            pass

        if self._on_message_cb:
            # Guard: a raise in the app's callback must not poison paho's
            # loop thread. paho catches exceptions but state can desync.
            try:
                self._on_message_cb(topic, payload, raw, self._label)
            except Exception as e:
                log.exception(f"MQTT [{self._label}] on_message_cb raised: {e}")

    def _on_log(self, client, userdata, level, buf):
        # PINGREQ / PINGRESP traffic counts as liveness on quiet feeds.
        # paho v2 always invokes on_log regardless of its own log level.
        if not buf:
            return
        if "PINGRESP" in buf or "PINGREQ" in buf or "Received CONNACK" in buf:
            self._last_activity = time.monotonic()
