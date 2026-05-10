"""
モーニングブリーフィング エージェント
BriefingSkill の結果をLINE WORKSのリッチメッセージに変換して配信する
"""
from __future__ import annotations

from datetime import datetime

from ceo_system.config import get_config
from ceo_system.mock.factory import get_line_works_connector
from ceo_system.skills.briefing_skill import BriefingSkill
from ceo_system.utils.logger import get_logger

logger = get_logger(__name__)


class BriefingAgent:
    def __init__(self) -> None:
        self._skill = BriefingSkill()
        self._lw = get_line_works_connector()
        self._cfg = get_config()

    def execute(self, context: dict) -> dict:
        logger.info("BriefingAgent 開始")
        result = self._skill.run(context)

        if not result.success:
            logger.error("BriefingSkill 失敗: %s", result.error)
            return {"success": False, "error": result.error}

        output = result.output
        message = self._format_message(output)

        sent = self._lw.send_to_ceo(message)
        logger.info("ブリーフィング送信: %s", "成功" if sent else "失敗")

        return {
            "success": sent,
            "events_count": output.get("events_count", 0),
            "missing_docs": output.get("missing_doc_events", []),
            "dm_notifications": len(output.get("dm_sent", [])),
        }

    def _format_message(self, output: dict) -> str:
        now = datetime.now()
        date_str = now.strftime("%Y年%m月%d日 (%a)")

        lines = [
            f"━━━━━━━━━━━━━━━━━━━━",
            f"🌅 CEO モーニングブリーフィング",
            f"📅 {date_str}",
            f"━━━━━━━━━━━━━━━━━━━━",
            "",
            output.get("briefing", ""),
        ]

        missing = output.get("missing_doc_events", [])
        if missing:
            lines += [
                "",
                "⚠️ 【会議資料 未添付】",
            ]
            for title in missing:
                lines.append(f"  • {title}")
            lines.append("→ 担当者にDMで通知済みです")

        lines += [
            "",
            f"━━━━━━━━━━━━━━━━━━━━",
            f"本日も最高の判断を。",
        ]

        return "\n".join(lines)
