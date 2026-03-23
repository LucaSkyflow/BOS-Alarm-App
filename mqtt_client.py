import json
import ssl
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

    def __init__(self, broker, port, username, password, use_tls, topic, label,
                 on_message_callback=None, on_connect_callback=None, on_disconnect_callback=None):
        self._broker = broker
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

        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

        if not self._broker:
            log.warning(f"MQTT [{self._label}] broker is empty — skipping connect")
            return

        log.info(f"MQTT [{self._label}] connecting to {self._broker}:{self._port} "
                 f"(TLS={self._use_tls}, user={self._username!r})")
        try:
            self._client.connect_async(self._broker, self._port)
            self._client.loop_start()
        except Exception as e:
            log.error(f"MQTT [{self._label}] connect_async failed: {e}")
            self._client = None

    def disconnect(self):
        if self._client is not None:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:
                pass
            self._client = None

    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected()

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        log.info(f"MQTT [{self._label}] connected (rc={reason_code})")
        client.subscribe(self._topic)
        log.info(f"MQTT [{self._label}] subscribed to {self._topic}")
        if self._on_connect_cb:
            self._on_connect_cb(self._label)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        log.warning(f"MQTT [{self._label}] disconnected (rc={reason_code})")
        if self._on_disconnect_cb:
            self._on_disconnect_cb(self._label)

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        raw = msg.payload.decode("utf-8", errors="replace")

        payload = None
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            pass

        if self._on_message_cb:
            self._on_message_cb(topic, payload, raw, self._label)
