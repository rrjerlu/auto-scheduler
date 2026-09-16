"""Minimal LINE webhook for Shiftwise service operations support.

Run locally with: uvicorn line_bot:app --host 0.0.0.0 --port 8000
Configure LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET in deployment secrets.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Any

import requests
from fastapi import FastAPI, Header, HTTPException, Request

app = FastAPI(title="Shiftwise LINE Support")


def setting(name: str) -> str:
    return os.getenv(name, "")


def valid_signature(body: bytes, signature: str) -> bool:
    secret = setting("LINE_CHANNEL_SECRET")
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(digest).decode(), signature)


def reply(token: str, text: str) -> None:
    access_token = setting("LINE_CHANNEL_ACCESS_TOKEN")
    if not access_token:
        raise RuntimeError("LINE_CHANNEL_ACCESS_TOKEN is not configured")
    response = requests.post(
        "https://api.line.me/v2/bot/message/reply",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={"replyToken": token, "messages": [{"type": "text", "text": text}]},
        timeout=15,
    )
    response.raise_for_status()


def answer(text: str) -> str:
    normalized = text.strip().lower()
    if normalized in {"help", "幫助", "選單", "menu"}:
        return "Shiftwise 服務選單\n1. 我的班表\n2. 我要請假\n3. 我要換班\n4. 轉接主管"
    if "班表" in normalized:
        return "請登入 Shiftwise 網站查看完整週班表；若無法登入，請回覆「轉接主管」。"
    if "請假" in normalized:
        return "請登入 Shiftwise，在總覽頁提交請假申請，送出後由店長審核。"
    if "換班" in normalized:
        return "請登入 Shiftwise，在總覽頁提交換班申請，店長核准後才會生效。"
    if "主管" in normalized or "真人" in normalized:
        return "已記錄你的需求，請稍候由店長或管理者回覆。"
    return "我可以協助：查詢班表、提交請假、提交換班，或轉接主管。回覆「選單」查看功能。"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "shiftwise-line-support"}


@app.post("/line/webhook")
async def webhook(request: Request, x_line_signature: str = Header(default="")) -> dict[str, Any]:
    body = await request.body()
    if not valid_signature(body, x_line_signature):
        raise HTTPException(status_code=401, detail="Invalid LINE signature")
    payload = await request.json()
    for event in payload.get("events", []):
        if event.get("type") != "message" or event.get("message", {}).get("type") != "text":
            continue
        reply(event["replyToken"], answer(event["message"]["text"]))
    return {"ok": True}
