"""
モックコネクター群
USE_MOCK=true のとき、実APIの代わりにこれらが使われる
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from ceo_system.connectors.google_calendar import CalendarEvent
from ceo_system.connectors.gmail import EmailMessage
from ceo_system.connectors.line_works import LineWorksMessage
from ceo_system.connectors.sakumiru import SakumiruProject, SakumiruTask
from ceo_system.mock import fixtures
from ceo_system.utils.logger import get_logger

logger = get_logger(__name__)
JST = timezone(timedelta(hours=9))


# ─── Google Calendar モック ───────────────────────────────────────────────────

class MockGoogleCalendarConnector:
    def get_today_events(self, target_date=None) -> list[CalendarEvent]:
        logger.info("[MOCK] Google Calendar: %d件のイベントを返します", len(fixtures.MOCK_CALENDAR_EVENTS))
        events = []
        for item in fixtures.MOCK_CALENDAR_EVENTS:
            start_raw = item["start"]
            end_raw = item["end"]
            start = datetime.fromisoformat(start_raw["dateTime"])
            end = datetime.fromisoformat(end_raw["dateTime"])
            attendees = [a["email"] for a in item.get("attendees", [])]
            description = item.get("description", "") or ""
            has_doc = bool("http" in description)
            organizer_info = item.get("organizer", {})
            organizer = organizer_info.get("email", "unknown@company.co.jp")
            events.append(CalendarEvent(
                event_id=item["id"],
                title=item["summary"],
                start=start,
                end=end,
                attendees=attendees,
                description=description,
                has_meeting_doc=has_doc,
                organizer=organizer,
            ))
        return events


# ─── Google Docs モック ───────────────────────────────────────────────────────

class MockGoogleDocsConnector:
    def get_strategy_context(self) -> str:
        logger.info("[MOCK] Google Docs: 戦略ドキュメントを返します")
        return fixtures.MOCK_STRATEGY_DOC

    def get_kpi_context(self) -> str:
        logger.info("[MOCK] Google Docs: KPIドキュメントを返します")
        return fixtures.MOCK_KPI_DOC

    def get_meeting_minutes_texts(self, days: int = 7) -> list[dict]:
        logger.info("[MOCK] Google Docs: %d件の議事録を返します", len(fixtures.MOCK_MEETING_MINUTES))
        return fixtures.MOCK_MEETING_MINUTES

    def get_document_text(self, doc_id: str) -> str:
        return f"[MOCK] doc_id={doc_id} のテキスト"


# ─── Gmail モック ─────────────────────────────────────────────────────────────

class MockGmailConnector:
    def get_recent_emails(self, days: int = 1, max_results: int = 30) -> list[EmailMessage]:
        logger.info("[MOCK] Gmail: %d件のメールを返します", len(fixtures.MOCK_EMAILS))
        emails = []
        for i, e in enumerate(fixtures.MOCK_EMAILS):
            emails.append(EmailMessage(
                message_id=f"mock_msg_{i:03d}",
                subject=e["subject"],
                sender=e["sender"],
                received_at=datetime.now(JST) - timedelta(hours=i * 2),
                snippet=e["snippet"],
                body=e["body"],
                labels=["INBOX"],
            ))
        return emails


# ─── LINE WORKS モック ────────────────────────────────────────────────────────

class MockLineWorksConnector:
    def __init__(self) -> None:
        self._sent_messages: list[dict] = []

    def send_to_ceo(self, text: str) -> bool:
        self._sent_messages.append({"to": "CEO", "text": text})
        logger.info("[MOCK] LINE WORKS → CEO へ送信:\n%s\n%s", "─" * 50, text)
        return True

    def send_to_channel(self, channel_id: str, text: str) -> bool:
        self._sent_messages.append({"to": f"channel:{channel_id}", "text": text})
        logger.info("[MOCK] LINE WORKS → channel:%s へ送信", channel_id)
        return True

    def send_dm(self, user_id: str, text: str) -> bool:
        self._sent_messages.append({"to": f"dm:{user_id}", "text": text})
        logger.info("[MOCK] LINE WORKS → DM:%s\n  %s", user_id, text[:80])
        return True

    def send_flex_message(self, user_id: str, flex_content: dict) -> bool:
        logger.info("[MOCK] LINE WORKS → Flex Message to %s", user_id)
        return True

    def get_channel_messages(self, channel_id: str, limit: int = 100) -> list[LineWorksMessage]:
        raw_msgs = fixtures.MOCK_LW_MESSAGES.get(channel_id, [])
        messages = []
        for m in raw_msgs[:limit]:
            messages.append(LineWorksMessage(
                message_id=f"mock_{channel_id}_{m['userId']}",
                channel_id=channel_id,
                sender_id=m["userId"],
                sender_name=m["userName"],
                content=m["content"]["text"],
                created_at=datetime.fromtimestamp(m["createdTime"] / 1000, tz=JST),
            ))
        return messages

    def get_all_channel_ids(self) -> list[str]:
        return [ch["channelId"] for ch in fixtures.MOCK_LW_CHANNELS]

    def get_sent_messages(self) -> list[dict]:
        return self._sent_messages


# ─── サクミル モック ─────────────────────────────────────────────────────────

class MockSakumiruConnector:
    def get_all_projects(self) -> list[SakumiruProject]:
        logger.info("[MOCK] サクミル: %d件のプロジェクトを返します", len(fixtures.MOCK_SAKUMIRU_PROJECTS))
        projects = []
        for p in fixtures.MOCK_SAKUMIRU_PROJECTS:
            tasks = self._build_tasks(p["tasks"])
            done = sum(1 for t in tasks if t.status == "done")
            rate = done / len(tasks) if tasks else 0.0
            projects.append(SakumiruProject(
                project_id=p["projectId"],
                name=p["name"],
                progress_rate=rate,
                tasks=tasks,
                last_activity=datetime.fromisoformat(p["updatedAt"]),
            ))
        return projects

    def get_overdue_tasks(self) -> list[SakumiruTask]:
        now = datetime.now(JST)
        overdue = []
        for project in self.get_all_projects():
            for task in project.tasks:
                if task.due_date and task.due_date < now and task.status != "done":
                    overdue.append(task)
        return overdue

    def get_blocked_tasks(self) -> list[SakumiruTask]:
        blocked = []
        for project in self.get_all_projects():
            for task in project.tasks:
                if task.status == "blocked":
                    blocked.append(task)
        return blocked

    def _build_tasks(self, raw: list) -> list[SakumiruTask]:
        tasks = []
        for t in raw:
            due_raw = t.get("dueDate")
            due_date = datetime.fromisoformat(due_raw) if due_raw else None
            tasks.append(SakumiruTask(
                task_id=t["taskId"],
                title=t["title"],
                assignee=t["assigneeName"],
                project=t["projectName"],
                status=t["status"],
                due_date=due_date,
                updated_at=datetime.fromisoformat(t["updatedAt"]),
                comments=[c["body"] for c in t.get("comments", [])],
            ))
        return tasks
