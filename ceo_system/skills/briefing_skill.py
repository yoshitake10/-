"""
モーニングブリーフィング スキル
今日のスケジュール整理 + 会議資料不足チェック + LINE WORKS DM送付
"""
from __future__ import annotations

from datetime import datetime

from ceo_system.connectors.google_calendar import CalendarEvent
from ceo_system.mock.factory import get_calendar_connector, get_line_works_connector
from ceo_system.skills.base_skill import BaseSkill, SkillResult
from ceo_system.utils.claude_client import ClaudeClient
from ceo_system.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """あなたはCEOの優秀なエグゼクティブアシスタントです。
CEOの時間を最大限に活かすため、今日のスケジュールを戦略的な視点で整理し、
何に集中すべきかを明確に示してください。
- 出力は日本語
- 箇条書きで簡潔に
- 最重要事項を先頭に
- 推奨アクションを必ず含める"""


class BriefingSkill(BaseSkill):
    name = "briefing"

    def __init__(self) -> None:
        self._calendar = get_calendar_connector()
        self._lw = get_line_works_connector()
        self._claude = ClaudeClient()

    def run(self, context: dict) -> SkillResult:
        try:
            events = self._calendar.get_today_events()
            briefing_text = self._generate_briefing(events)
            missing_doc_events = [e for e in events if not e.has_meeting_doc and len(e.attendees) > 1]
            dm_results = self._notify_missing_docs(missing_doc_events)
            return self._ok({
                "briefing": briefing_text,
                "events_count": len(events),
                "missing_doc_events": [e.title for e in missing_doc_events],
                "dm_sent": dm_results,
            })
        except Exception as e:
            logger.error("BriefingSkill エラー: %s", e)
            return self._err(str(e))

    def _generate_briefing(self, events: list[CalendarEvent]) -> str:
        if not events:
            return "本日の予定はありません。戦略タスクに集中できる一日です。"

        events_text = self._format_events(events)
        prompt = f"""本日（{datetime.now().strftime('%Y年%m月%d日 %A')}）のCEOスケジュールです：

{events_text}

以下を含むモーニングブリーフィングを作成してください：
1. 本日の最重要ミーティングTOP3とその準備ポイント
2. スケジュール全体の優先順位と時間配分の推奨
3. CEOが事前に決断・確認すべき事項
4. 本日のリスク・注意点"""

        return self._claude.analyze(system_prompt=SYSTEM_PROMPT, user_message=prompt)

    def _format_events(self, events: list[CalendarEvent]) -> str:
        lines = []
        for e in events:
            start = e.start.strftime("%H:%M")
            end = e.end.strftime("%H:%M")
            doc_status = "✓ 資料あり" if e.has_meeting_doc else "⚠ 資料なし"
            attendees_count = len(e.attendees)
            lines.append(
                f"[{start}〜{end}] {e.title} | 参加者:{attendees_count}名 | {doc_status}"
            )
        return "\n".join(lines)

    def _notify_missing_docs(self, events: list[CalendarEvent]) -> list[dict]:
        """会議資料が不足している会議の主催者にDMを送付"""
        results = []
        for e in events:
            message = (
                f"【会議資料の確認依頼】\n"
                f"本日 {e.start.strftime('%H:%M')} からの「{e.title}」について、"
                f"会議資料がカレンダーに登録されていません。\n"
                f"開始30分前までにGoogle Driveへのリンクをカレンダーに追加いただけますか？"
            )
            # 主催者のLINE WORKSアカウントへDM（メールアドレス→アカウントID変換が必要）
            # ここでは主催者名を記録し、実際の送信はuser_id解決後に行う
            sent = self._lw.send_dm(e.organizer, message)
            results.append({"event": e.title, "organizer": e.organizer, "sent": sent})
            logger.info("資料不足通知: %s -> %s (sent=%s)", e.title, e.organizer, sent)
        return results
