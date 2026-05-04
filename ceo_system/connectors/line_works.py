"""
LINE WORKS コネクター
Bot API v2 を使用してメッセージ送受信・チャンネル操作を行う
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import jwt
import requests

from ceo_system.config import get_config
from ceo_system.utils.logger import get_logger

logger = get_logger(__name__)

LINEWORKS_AUTH_URL = "https://auth.worksmobile.com/oauth2/v2.0/token"
LINEWORKS_API_BASE = "https://www.worksapis.com/v1.0"


@dataclass
class LineWorksMessage:
    message_id: str
    channel_id: str
    sender_id: str
    sender_name: str
    content: str
    created_at: datetime


class LineWorksConnector:
    def __init__(self) -> None:
        self._cfg = get_config().line_works
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    # ── 認証 ──────────────────────────────────────────────────────────────────

    def _get_access_token(self) -> str:
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token

        # JWT assertion を作成
        now = int(time.time())
        payload = {
            "iss": self._cfg.service_account,
            "sub": self._cfg.service_account,
            "iat": now,
            "exp": now + 3600,
        }
        with open(self._cfg.private_key_path, "r") as f:
            private_key = f.read()

        assertion = jwt.encode(payload, private_key, algorithm="RS256")

        resp = requests.post(
            LINEWORKS_AUTH_URL,
            data={
                "assertion": assertion,
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "client_id": self._cfg.bot_id,
                "client_secret": self._cfg.bot_secret,
                "scope": "bot",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._token_expires_at = time.time() + data.get("expires_in", 3600)
        logger.info("LINE WORKS アクセストークン取得完了")
        return self._access_token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
        }

    # ── メッセージ送信 ──────────────────────────────────────────────────────

    def send_to_ceo(self, text: str) -> bool:
        """CEOにダイレクトメッセージを送信"""
        return self._send_dm(self._cfg.ceo_user_id, text)

    def send_to_channel(self, channel_id: str, text: str) -> bool:
        """指定チャンネルにメッセージを送信"""
        url = f"{LINEWORKS_API_BASE}/bots/{self._cfg.bot_id}/channels/{channel_id}/messages"
        body = {"content": {"type": "text", "text": text}}
        try:
            resp = requests.post(url, json=body, headers=self._headers())
            resp.raise_for_status()
            logger.info("チャンネル送信成功: %s", channel_id)
            return True
        except requests.RequestException as e:
            logger.error("チャンネル送信失敗: %s", e)
            return False

    def send_dm(self, user_id: str, text: str) -> bool:
        """任意のユーザーにDMを送信（会議資料不足アラート等）"""
        return self._send_dm(user_id, text)

    def send_flex_message(self, user_id: str, flex_content: dict) -> bool:
        """Flex Message（リッチUI）を送信"""
        url = f"{LINEWORKS_API_BASE}/bots/{self._cfg.bot_id}/users/{user_id}/messages"
        body = {"content": {"type": "flex", "altText": "CEOシステムからのお知らせ", **flex_content}}
        try:
            resp = requests.post(url, json=body, headers=self._headers())
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error("Flex Message 送信失敗: %s", e)
            return False

    def _send_dm(self, user_id: str, text: str) -> bool:
        url = f"{LINEWORKS_API_BASE}/bots/{self._cfg.bot_id}/users/{user_id}/messages"
        body = {"content": {"type": "text", "text": text}}
        try:
            resp = requests.post(url, json=body, headers=self._headers())
            resp.raise_for_status()
            logger.info("DM送信成功: %s", user_id)
            return True
        except requests.RequestException as e:
            logger.error("DM送信失敗 user=%s: %s", user_id, e)
            return False

    # ── メッセージ取得 ─────────────────────────────────────────────────────

    def get_channel_messages(
        self, channel_id: str, limit: int = 100
    ) -> list[LineWorksMessage]:
        """チャンネルの最新メッセージを取得"""
        url = f"{LINEWORKS_API_BASE}/channels/{channel_id}/messages"
        try:
            resp = requests.get(
                url,
                headers=self._headers(),
                params={"limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("チャンネルメッセージ取得失敗: %s", e)
            return []

        messages = []
        for item in data.get("messageList", []):
            content = item.get("content", {})
            text = content.get("text", "")
            if not text:
                continue
            messages.append(LineWorksMessage(
                message_id=item.get("messageId", ""),
                channel_id=channel_id,
                sender_id=item.get("userId", ""),
                sender_name=item.get("userName", "不明"),
                content=text,
                created_at=datetime.fromtimestamp(
                    item.get("createdTime", 0) / 1000
                ),
            ))

        logger.info("LW メッセージ取得: %d件 (channel=%s)", len(messages), channel_id)
        return messages

    def get_all_channel_ids(self) -> list[str]:
        """ドメイン内の全チャンネルIDを取得"""
        url = f"{LINEWORKS_API_BASE}/channels"
        try:
            resp = requests.get(url, headers=self._headers())
            resp.raise_for_status()
            return [c["channelId"] for c in resp.json().get("channelList", [])]
        except requests.RequestException as e:
            logger.error("チャンネル一覧取得失敗: %s", e)
            return []
