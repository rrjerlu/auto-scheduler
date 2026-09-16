"""Optional Email and LINE notification adapters.

All credentials are read from environment variables or Streamlit secrets.
The app remains usable when notifications are not configured.
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

import requests


def _setting(name: str) -> str:
    try:
        import streamlit as st

        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return str(value or os.getenv(name, ""))


def send_email(recipient: str, subject: str, body: str) -> tuple[bool, str]:
    host = _setting("SMTP_HOST")
    port = int(_setting("SMTP_PORT") or "587")
    username = _setting("SMTP_USERNAME")
    password = _setting("SMTP_PASSWORD")
    sender = _setting("SMTP_FROM") or username
    if not all((host, username, password, sender, recipient)):
        return False, "Email 尚未設定 SMTP Secrets"
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(message)
    except Exception as error:
        return False, f"Email 發送失敗：{error}"
    return True, "Email 已發送"


def send_line(user_id: str, message: str) -> tuple[bool, str]:
    token = _setting("LINE_CHANNEL_ACCESS_TOKEN")
    if not token or not user_id:
        return False, "LINE 尚未設定 Channel Access Token 或使用者 ID"
    response = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"to": user_id, "messages": [{"type": "text", "text": message}]},
        timeout=15,
    )
    if response.ok:
        return True, "LINE 通知已發送"
    return False, f"LINE 發送失敗：HTTP {response.status_code}"


def notify(recipient_email: str = "", line_user_id: str = "", subject: str = "Shiftwise 通知", message: str = "") -> list[str]:
    results = []
    if recipient_email:
        results.append(send_email(recipient_email, subject, message)[1])
    if line_user_id:
        results.append(send_line(line_user_id, message)[1])
    return results or ["尚未設定通知對象"]
