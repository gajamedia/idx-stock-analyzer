import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime


class EmailNotifier:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.email_user = os.getenv("EMAIL_USER", "")
        self.email_pass = os.getenv("EMAIL_PASS", "")
        self.enabled = bool(self.email_user and self.email_pass)

    def send_alert(self, to_email, subject, message):
        if not self.enabled:
            return {"status": "disabled", "reason": "Email not configured"}

        try:
            msg = MIMEMultipart()
            msg["From"] = self.email_user
            msg["To"] = to_email
            msg["Subject"] = f"Stock Alert: {subject}"

            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #e94560;">Stock Alert Triggered</h2>
                <div style="background: #f5f5f5; padding: 15px; border-radius: 8px;">
                    <p>{message}</p>
                </div>
                <p style="color: #888; font-size: 12px; margin-top: 20px;">
                    Sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | IDX Stock Analyzer
                </p>
            </body>
            </html>
            """

            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_pass)
                server.send_message(msg)

            return {"status": "sent", "to": to_email}
        except Exception as e:
            return {"status": "error", "message": str(e)}


class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.enabled = bool(self.bot_token and self.chat_id)

    def send_alert(self, message):
        if not self.enabled:
            return {"status": "disabled", "reason": "Telegram not configured"}

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML",
            }
            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                return {"status": "sent"}
            else:
                return {"status": "error", "message": response.text}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def send_stock_alert(self, symbol, alert_type, target, current_price):
        message = (
            f"<b>Alert Triggered!</b>\n\n"
            f"<b>Saham:</b> {symbol}\n"
            f"<b>Tipe:</b> {alert_type}\n"
            f"<b>Target:</b> Rp {target:,.0f}\n"
            f"<b>Harga Saat Ini:</b> Rp {current_price:,.0f}\n"
            f"<b>Waktu:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return self.send_alert(message)


email_notifier = EmailNotifier()
telegram_notifier = TelegramNotifier()
