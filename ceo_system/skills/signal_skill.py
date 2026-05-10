"""
シグナル検知スキル
全社員の行動ログからCEOが知るべき重要情報をカテゴリー別に抽出する
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ceo_system.config import get_config
from ceo_system.mock.factory import get_line_works_connector, get_sakumiru_connector
from ceo_system.skills.base_skill import BaseSkill, SkillResult
from ceo_system.utils.claude_client import ClaudeClient
from ceo_system.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """あなたはCEOの情報フィルタリングAIです。
膨大な社内情報から「CEOが知るべき重要シグナル」だけを抽出します。

抽出ルール:
- CEOの意思決定に影響する情報のみ
- 現場レベルの詳細は不要、本質だけ
- 各シグナルは50字以内で簡潔に
- 重要度を★（1-5）で評価

出力形式: 必ずJSONで返すこと
{
  "signals": [
    {
      "category": "カテゴリー名",
      "content": "シグナル内容（50字以内）",
      "importance": 5,
      "source": "情報源",
      "recommended_action": "CEOへの推奨アクション"
    }
  ]
}"""


@dataclass
class Signal:
    category: str
    content: str
    importance: int  # 1-5
    source: str
    recommended_action: str


class SignalSkill(BaseSkill):
    name = "signal_detection"

    def __init__(self, docs_connector=None) -> None:
        self._lw = get_line_works_connector()
        self._sakumiru = get_sakumiru_connector()
        self._docs = docs_connector
        self._claude = ClaudeClient()
        self._cfg = get_config()

    def run(self, context: dict) -> SkillResult:
        try:
            raw_data = self._collect_all_data(context)
            signals = self._detect_signals(raw_data, context.get("management_context", ""))
            categorized = self._categorize(signals)
            return self._ok({
                "signals": [self._signal_to_dict(s) for s in signals],
                "by_category": categorized,
                "top_signals": [self._signal_to_dict(s) for s in sorted(signals, key=lambda x: -x.importance)[:5]],
            })
        except Exception as e:
            logger.error("SignalSkill エラー: %s", e)
            return self._err(str(e))

    def _collect_all_data(self, context: dict) -> dict[str, Any]:
        """全データソースから情報を収集"""
        data: dict[str, Any] = {}

        # LINE WORKS メッセージ
        channel_ids = self._lw.get_all_channel_ids()
        lw_messages = []
        for ch_id in channel_ids[:10]:  # 最大10チャンネル
            msgs = self._lw.get_channel_messages(ch_id, limit=50)
            lw_messages.extend(msgs)
        data["line_works_messages"] = [
            f"[{m.sender_name}] {m.content}" for m in lw_messages
        ]

        # サクミル タスク動向
        overdue = self._sakumiru.get_overdue_tasks()
        blocked = self._sakumiru.get_blocked_tasks()
        data["overdue_tasks"] = [f"{t.assignee}: {t.title}" for t in overdue]
        data["blocked_tasks"] = [f"{t.assignee}: {t.title}" for t in blocked]

        # 議事録（Docsコネクターが使える場合）
        if self._docs:
            minutes = self._docs.get_meeting_minutes_texts(
                days=self._cfg.analysis_window_days
            )
            data["meeting_minutes"] = [
                {"title": m["title"], "excerpt": m["text"][:500]} for m in minutes
            ]

        # Gmailは context から受け取る（オーケストレーターが収集済み）
        if "emails" in context:
            data["emails"] = context["emails"]

        return data

    def _detect_signals(self, raw_data: dict, management_context: str) -> list[Signal]:
        """Claudeを使ってシグナルを抽出"""
        categories = self._cfg.signal_categories
        data_summary = self._summarize_raw_data(raw_data)

        prompt = f"""以下の社内データからシグナルを抽出してください。

抽出カテゴリー: {', '.join(categories)}

【社内データ】
{data_summary}

各カテゴリーで重要なシグナルを最大3件ずつ抽出してください。"""

        response = self._claude.analyze(
            system_prompt=SYSTEM_PROMPT,
            user_message=prompt,
            cached_context=management_context if management_context else None,
        )

        return self._parse_signals(response)

    def _summarize_raw_data(self, data: dict) -> str:
        sections = []

        if data.get("line_works_messages"):
            msgs = data["line_works_messages"][:30]
            sections.append(f"■ LINE WORKS（直近{len(msgs)}件）\n" + "\n".join(msgs))

        if data.get("overdue_tasks"):
            sections.append(f"■ 期限超過タスク\n" + "\n".join(data["overdue_tasks"]))

        if data.get("blocked_tasks"):
            sections.append(f"■ ブロック中タスク\n" + "\n".join(data["blocked_tasks"]))

        if data.get("meeting_minutes"):
            for m in data["meeting_minutes"][:5]:
                sections.append(f"■ 議事録「{m['title']}」\n{m['excerpt']}")

        if data.get("emails"):
            sections.append(f"■ メール（直近）\n" + "\n".join(
                f"[{e.get('subject','')}] {e.get('snippet','')}" for e in data["emails"][:10]
            ))

        return "\n\n".join(sections)

    def _parse_signals(self, response: str) -> list[Signal]:
        try:
            # JSON部分を抽出
            start = response.find("{")
            end = response.rfind("}") + 1
            if start == -1:
                return []
            data = json.loads(response[start:end])
            signals = []
            for s in data.get("signals", []):
                signals.append(Signal(
                    category=s.get("category", "その他"),
                    content=s.get("content", ""),
                    importance=int(s.get("importance", 3)),
                    source=s.get("source", "不明"),
                    recommended_action=s.get("recommended_action", ""),
                ))
            return signals
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("シグナルパース失敗: %s\nresponse: %s", e, response[:200])
            return []

    def _categorize(self, signals: list[Signal]) -> dict[str, list[dict]]:
        result: dict[str, list] = {}
        for s in signals:
            result.setdefault(s.category, []).append(self._signal_to_dict(s))
        return result

    @staticmethod
    def _signal_to_dict(s: Signal) -> dict:
        return {
            "category": s.category,
            "content": s.content,
            "importance": s.importance,
            "source": s.source,
            "recommended_action": s.recommended_action,
        }
