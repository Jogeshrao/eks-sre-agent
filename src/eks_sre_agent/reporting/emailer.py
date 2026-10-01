from __future__ import annotations
import os, smtplib, ssl
from email.message import EmailMessage

def send_email(subject: str, body: str, recipients: list[str]):
    if not recipients:
        return
    host = os.environ["SMTP_HOST"]
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.environ["SMTP_FROM"]

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(host, port, timeout=30) as s:
        s.starttls(context=ssl.create_default_context())
        if user:
            s.login(user, password or "")
        s.send_message(msg)
