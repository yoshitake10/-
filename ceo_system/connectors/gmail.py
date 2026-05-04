"""Gmail コネクター"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from googleapiclient.discovery import build

from ceo_system.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EmailMessage:
    message_id: str
    subject: str
    sender: str
    received_at: datetime
    snippet: str
    body: str
    labels: list[str]


class GmailConnector:
    def __init__(self, credentials: Any) -> None:
        self._svc = build("gmail", "v1", credentials=credentials)

    def get_recent_emails(self, days: int = 1, max_results: int = 30) -> list[EmailMessage]:
        """CEOの受信メールを取得（重要・未読優先）"""
        cutoff = int(
            (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()
        )
        query = f"after:{cutoff} -category:promotions -category:social"

        result = self._svc.users().messages().list(
            userId="me",
            q=query,
            maxResults=max_results,
        ).execute()

        messages = []
        for msg_ref in result.get("messages", []):
            try:
                msg = self._fetch_message(msg_ref["id"])
                if msg:
                    messages.append(msg)
            except Exception as e:
                logger.warning("メール取得失敗 %s: %s", msg_ref["id"], e)

        logger.info("Gmail 取得: %d件", len(messages))
        return messages

    def _fetch_message(self, message_id: str) -> EmailMessage | None:
        raw = self._svc.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()

        headers = {
            h["name"].lower(): h["value"]
            for h in raw.get("payload", {}).get("headers", [])
        }

        subject = headers.get("subject", "（件名なし）")
        sender = headers.get("from", "不明")
        date_str = headers.get("date", "")

        try:
            from email.utils import parsedate_to_datetime
            received_at = parsedate_to_datetime(date_str)
        except Exception:
            received_at = datetime.now(timezone.utc)

        body = self._extract_body(raw.get("payload", {}))

        return EmailMessage(
            message_id=message_id,
            subject=subject,
            sender=sender,
            received_at=received_at,
            snippet=raw.get("snippet", ""),
            body=body[:2000],  # 最大2000文字
            labels=raw.get("labelIds", []),
        )

    def _extract_body(self, payload: dict) -> str:
        """メール本文をプレーンテキストで取得"""
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    data = part.get("body", {}).get("data", "")
                    if data:
                        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        else:
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        return ""
