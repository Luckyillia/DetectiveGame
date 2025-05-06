import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.services.log_services import LogService


class EmailService:
    def __init__(self):
        self.log_service = LogService()

        # Настройки почтового сервера (лучше хранить в переменных окружения)
        self.smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", 587))
        self.sender_email = os.environ.get("SENDER_EMAIL", "your-email@gmail.com")
        self.sender_password = os.environ.get("SENDER_PASSWORD", "your-password-or-app-password")

    def send_email(self, recipient_email, subject, message, html_message=None):
        """Отправляет электронное письмо указанному получателю"""
        try:
            # Создаем сообщение
            email = MIMEMultipart("alternative")
            email["Subject"] = subject
            email["From"] = self.sender_email
            email["To"] = recipient_email

            # Добавляем текстовую версию
            email.attach(MIMEText(message, "plain"))

            # Добавляем HTML версию, если она есть
            if html_message:
                email.attach(MIMEText(html_message, "html"))

            # Подключаемся к серверу и отправляем письмо
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Включаем шифрование
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient_email, email.as_string())

            self.log_service.add_system_log(
                message=f"Отправлено письмо на адрес {recipient_email}",
                metadata={"subject": subject}
            )
            return True

        except Exception as e:
            self.log_service.add_error_log(
                error_message=f"Ошибка отправки письма: {str(e)}",
                metadata={"recipient": recipient_email, "subject": subject}
            )
            return False

    def send_password_reset_code(self, recipient_email, username, reset_code):
        subject = "Код восстановления пароля для Detective Chronicles"

        # Текстовая версия
        text_message = f"""
    Здравствуйте, {username}!

    Вы запросили восстановление пароля в приложении Detective Chronicles.
    Ваш код для восстановления пароля: {reset_code}

    Код действителен в течение 15 минут.
    Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо.

    С уважением,
    Команда Detective Chronicles
    https://europe.on-air.io/luckyillia/detective
    """

        # HTML версия - более профессионально оформленная
        html_message = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #f9f9f9; border: 1px solid #ddd; border-radius: 5px; padding: 20px;">
            <div style="text-align: center; margin-bottom: 20px;">
                <h2 style="color: #2a5885; margin: 0;">Восстановление пароля</h2>
            </div>

            <p>Здравствуйте, <strong>{username}</strong>!</p>
            <p>Вы запросили восстановление пароля в приложении Detective Chronicles.</p>
            <p>Ваш код для восстановления пароля:</p>

            <div style="background-color: #f5f5f5; padding: 15px; margin: 15px 0; text-align: center; font-size: 24px; letter-spacing: 5px; font-weight: bold; border-radius: 4px;">
                {reset_code}
            </div>

            <p>Код действителен в течение <strong>15 минут</strong>.</p>
            <p><em>Если вы не запрашивали восстановление пароля, пожалуйста, проигнорируйте это письмо.</em></p>

            <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">

            <p style="font-size: 12px; color: #777; text-align: center;">
                © Detective Chronicles 2023<br>
                <a href="https://europe.on-air.io/luckyillia/detective" style="color: #2a5885; text-decoration: none;">Detective Game</a>
            </p>
        </div>
    </body>
    </html>
    """

        return self.send_email(recipient_email, subject, text_message, html_message)