"""
フィードバックループ エージェント
MeetingSkill の結果をスコアと改善コーチングとして配信する
"""
from __future__ import annotations

from ceo_system.mock.factory import get_line_works_connector
from ceo_system.skills.meeting_skill import MeetingSkill
from ceo_system.utils.logger import get_logger

logger = get_logger(__name__)


def _score_bar(score: int) -> str:
    filled = int(score / 10)
    return "█" * filled + "░" * (10 - filled) + f" {score}/100"


class FeedbackAgent:
    def __init__(self) -> None:
        self._skill = MeetingSkill()
        self._lw = get_line_works_connector()

    def execute(self, context: dict) -> dict:
        logger.info("FeedbackAgent 開始")
        result = self._skill.run(context)

        if not result.success:
            logger.error("MeetingSkill 失敗: %s", result.error)
            return {"success": False, "error": result.error}

        output = result.output
        scores = output.get("scores", [])

        if not scores:
            logger.info("採点対象の議事録なし")
            return {"success": True, "scored_count": 0}

        message = self._format_message(output)
        sent = self._lw.send_to_ceo(message)

        return {
            "success": sent,
            "scored_count": len(scores),
            "average_score": output.get("average"),
        }

    def _format_message(self, output: dict) -> str:
        average = output.get("average")
        scores = output.get("scores", [])
        worst = output.get("worst_meeting")
        trend = output.get("trend_comment", "")

        lines = [
            "━━━━━━━━━━━━━━━━━━━━",
            "📋 会議品質フィードバック",
            f"対象会議数: {len(scores)}件",
            "━━━━━━━━━━━━━━━━━━━━",
        ]

        if average is not None:
            lines += [
                "",
                f"📊 平均スコア: {_score_bar(int(average))}",
                f"   {trend}",
            ]

        # 各会議のスコア一覧
        lines += ["", "【 会議別スコア 】"]
        for s in sorted(scores, key=lambda x: -x["score"]):
            lines.append(f"  {_score_bar(s['score'])} {s['title']}")

        # 最も改善が必要な会議の詳細
        if worst:
            lines += [
                "",
                f"【 最重点改善対象: {worst['title']} 】",
                f"スコア: {worst['score']}/100",
            ]
            for imp in worst.get("improvements", [])[:3]:
                lines.append(f"  • {imp}")

            if worst.get("action_items"):
                lines += ["", "アクションアイテム:"]
                for ai in worst["action_items"][:3]:
                    lines.append(
                        f"  □ {ai.get('what','?')} "
                        f"（{ai.get('who','?')} / {ai.get('when','?')}）"
                    )

            if worst.get("ceo_coaching"):
                lines += [
                    "",
                    "💡 CEOへのコーチング:",
                    f"   {worst['ceo_coaching']}",
                ]

        return "\n".join(lines)
