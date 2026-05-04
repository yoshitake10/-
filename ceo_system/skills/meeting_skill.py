"""
会議品質スコアリング スキル
議事録を分析し、会議の品質を100点満点でスコアリングして改善案を提示する
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ceo_system.skills.base_skill import BaseSkill, SkillResult
from ceo_system.utils.claude_client import ClaudeClient
from ceo_system.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """あなたは会議ファシリテーションの専門家AIです。
議事録を分析し、会議の品質を客観的にスコアリングします。

採点基準（合計100点）:
- 目的明確性（20点）: 会議の目的・ゴールが明確だったか
- 意思決定（25点）: 明確な意思決定がなされたか
- アクションアイテム（20点）: 担当者・期限付きのアクションが定義されたか
- 参加者貢献（15点）: 適切な参加者が適切に発言したか
- 時間効率（10点）: 時間内に議題を消化できたか
- 次回への連続性（10点）: 次回会議へのインプットが明確か

出力形式: 必ずJSONで返すこと
{
  "score": 0-100,
  "breakdown": {
    "目的明確性": {"score": 0-20, "comment": "評価コメント"},
    "意思決定": {"score": 0-25, "comment": "評価コメント"},
    "アクションアイテム": {"score": 0-20, "comment": "評価コメント"},
    "参加者貢献": {"score": 0-15, "comment": "評価コメント"},
    "時間効率": {"score": 0-10, "comment": "評価コメント"},
    "次回への連続性": {"score": 0-10, "comment": "評価コメント"}
  },
  "strengths": ["良かった点1", "良かった点2"],
  "improvements": ["改善案1", "改善案2", "改善案3"],
  "action_items": [{"what": "アクション", "who": "担当者", "when": "期限"}],
  "ceo_coaching": "CEOへの具体的な改善コーチング（過去のコンテキストを踏まえた提言）"
}"""


@dataclass
class MeetingScore:
    meeting_title: str
    score: int
    breakdown: dict[str, dict]
    strengths: list[str]
    improvements: list[str]
    action_items: list[dict]
    ceo_coaching: str


class MeetingSkill(BaseSkill):
    name = "meeting_quality"

    def __init__(self) -> None:
        self._claude = ClaudeClient()

    def run(self, context: dict) -> SkillResult:
        try:
            minutes_list = context.get("meeting_minutes", [])
            if not minutes_list:
                return self._ok({"scores": [], "average": None, "message": "議事録なし"})

            scores = []
            past_context = context.get("management_context", "")

            for minutes in minutes_list:
                score = self._score_meeting(minutes, past_context)
                if score:
                    scores.append(score)

            if not scores:
                return self._ok({"scores": [], "average": None})

            average = sum(s.score for s in scores) / len(scores)
            worst = min(scores, key=lambda s: s.score)
            best = max(scores, key=lambda s: s.score)

            return self._ok({
                "scores": [self._score_to_dict(s) for s in scores],
                "average": round(average, 1),
                "worst_meeting": self._score_to_dict(worst),
                "best_meeting": self._score_to_dict(best),
                "trend_comment": self._generate_trend_comment(scores, average),
            })
        except Exception as e:
            logger.error("MeetingSkill エラー: %s", e)
            return self._err(str(e))

    def _score_meeting(self, minutes: dict, past_context: str) -> MeetingScore | None:
        title = minutes.get("title", "不明な会議")
        text = minutes.get("text", "")

        if len(text) < 100:
            logger.info("議事録が短すぎてスキップ: %s", title)
            return None

        prompt = f"""以下の議事録を採点してください。

【会議名】{title}
【議事録】
{text[:3000]}

過去のコンテキストや経営方針を踏まえて、CEOへの具体的なコーチングも含めてください。"""

        response = self._claude.analyze(
            system_prompt=SYSTEM_PROMPT,
            user_message=prompt,
            cached_context=past_context if past_context else None,
        )

        return self._parse_score(title, response)

    def _parse_score(self, title: str, response: str) -> MeetingScore | None:
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            data = json.loads(response[start:end])
            return MeetingScore(
                meeting_title=title,
                score=int(data.get("score", 0)),
                breakdown=data.get("breakdown", {}),
                strengths=data.get("strengths", []),
                improvements=data.get("improvements", []),
                action_items=data.get("action_items", []),
                ceo_coaching=data.get("ceo_coaching", ""),
            )
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("会議スコアパース失敗 %s: %s", title, e)
            return None

    def _generate_trend_comment(self, scores: list[MeetingScore], average: float) -> str:
        if average >= 80:
            return f"会議品質は良好です（平均{average:.1f}点）。引き続き高水準を維持してください。"
        elif average >= 60:
            return f"会議品質は改善余地あり（平均{average:.1f}点）。アクションアイテムの明確化が鍵です。"
        else:
            return f"会議品質が低下しています（平均{average:.1f}点）。ファシリテーション方法の見直しを推奨します。"

    @staticmethod
    def _score_to_dict(s: MeetingScore) -> dict:
        return {
            "title": s.meeting_title,
            "score": s.score,
            "breakdown": s.breakdown,
            "strengths": s.strengths,
            "improvements": s.improvements,
            "action_items": s.action_items,
            "ceo_coaching": s.ceo_coaching,
        }
