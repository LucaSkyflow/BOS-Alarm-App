import threading
import logging

log = logging.getLogger(__name__)


class NotificationManager:
    def send_alarm_notification(self, record):
        threading.Thread(target=self._send, args=(record,), daemon=True).start()

    @staticmethod
    def _send(record):
        try:
            from plyer import notification

            if record.incoming_helicopter:
                title = "!! HELIKOPTER ALARM !!"
            else:
                title = "BOS Alarm"

            body = f"{record.organization}\n{record.address}\n{record.local_time}"

            notification.notify(
                title=title,
                message=body,
                app_name="BOS Alarm",
                timeout=10,
            )
        except Exception as e:
            log.error(f"Toast notification error: {e}")
