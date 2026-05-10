"""Google Calendar コネクター"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from ceo_system.config import get_config
from ceo_system.utils.logger import get_logger

logger = get_logger(__name__)
JST = timezone(timedelta(hours=9))


@dataclass
class CalendarEvent:
    event_id: str
    title: str
    start: datetime
    end: datetime
    attendees: list[str]
    description: str
    has_meeting_doc: bool  # 会議資料が添付/リンクされているか
    organizer: str


class GoogleCalendarConnector:
    def __init__(self) -> None:
        self._cfg = get_config().google
        self._service: Any = None

    def _auth(self) -> Any:
        if self._service:
            return self._service

        from pathlib import Path
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds = None
        token_path = Path(self._cfg.token_path)
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), self._cfg.scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self._cfg.credentials_path, self._cfg.scopes
                )
                creds = flow.run_local_server(port=0)
            token_path.write_text(creds.to_json())

        self._service = build("calendar", "v3", credentials=creds)
        return self._service

    def get_today_events(self, target_date: date | None = None) -> list[CalendarEvent]:
        """指定日（デフォルト今日）のCEOカレンダーイベントを取得"""
        svc = self._auth()
        d = target_date or date.today()
        start = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=JST)
        end = start + timedelta(days=1)

        result = svc.events().list(
            calendarId=self._cfg.ceo_calendar_id,
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = []
        for item in result.get("items", []):
            start_raw = item.get("start", {})
            end_raw = item.get("end", {})
            ev_start = self._parse_dt(start_raw)
            ev_end = self._parse_dt(end_raw)

            attendees = [
                a.get("email", "") for a in item.get("attendees", [])
            ]
            description = item.get("description", "") or ""
            # 会議資料の存在チェック: 説明文にURLまたは添付ファイルがあるか
            has_doc = bool(
                item.get("attachments")
                or "http" in description
                or "docs.google" in description
            )

            organizer_info = item.get("organizer", {})
            organizer = organizer_info.get("displayName") or organizer_info.get("email", "不明")

            events.append(CalendarEvent(
                event_id=item["id"],
                title=item.get("summary", "（タイトルなし）"),
                start=ev_start,
                end=ev_end,
                attendees=attendees,
                description=description,
                has_meeting_doc=has_doc,
                organizer=organizer,
            ))

        logger.info("カレンダー取得: %d件 (%s)", len(events), d.isoformat())
        return events

    def _parse_dt(self, raw: dict) -> datetime:
        if "dateTime" in raw:
            return datetime.fromisoformat(raw["dateTime"])
        elif "date" in raw:
            d = date.fromisoformat(raw["date"])
            return datetime(d.year, d.month, d.day, tzinfo=JST)
        return datetime.now(JST)
