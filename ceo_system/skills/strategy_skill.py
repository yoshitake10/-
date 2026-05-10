"""
戦略・KPIアップデート スキル
経営コンテキストと現場の事実を照合し、戦略に影響する事象をアラート（S/A/B/C）で通知する
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ceo_system.config import get_config
from ceo_system.mock.factory import get_sakumiru_connector
from ceo_system.skills.base_skill import BaseSkill, SkillResult
from ceo_system.utils.claude_client import ClaudeClient
from ceo_system.utils.logger import get_logger

logger = get_logger(__name__)


class AlertLevel(str, Enum):
    S = "S"  # 最重要・即時対応（戦略を根本から変える事象）
    A = "A"  # 重要・当日対応
    B = "B"  # 要注意・今週対応
    C = "C"  # 参考情報


@dataclass
class StrategyAlert:
    level: AlertLevel
    title: str
    description: str
    impact_score: float      # 0.0〜1.0
    affected_kpi: str
    recommended_action: str
    evidence: str


SYSTEM_PROMPT = """あなたは経営戦略の専門家AIです。
中期計画・KPI目標と現場の事実データを照合し、
戦略に影響を与える事象を検知してアラートを出します。

アラートレベル定義:
- S: 戦略の根本修正が必要な事象（失注・競合の重大動向・組織クライシス等）
- A: 重要KPIへの直接影響（目標達成に赤信号）
- B: 軽微な影響・要監視（黄色信号）
- C: 参考情報（傾向把握）

出力形式: 必ずJSONで返すこと
{
  "alerts": [
    {
      "level": "S|A|B|C",
      "title": "アラートタイトル",
      "description": "詳細説明（100字以内）",
      "impact_score": 0.0-1.0,
      "affected_kpi": "影響を受けるKPI名",
      "recommended_action": "CEOへの推奨アクション",
      "evidence": "根拠となるデータ"
    }
  ],
  "kpi_status": {
    "kpi名": {"current": "現状値", "target": "目標値", "status": "on_track|at_risk|off_track"}
  }
}"""


class StrategySkill(BaseSkill):
    name = "strategy_kpi"

    def __init__(self) -> None:
        self._sakumiru = get_sakumiru_connector()
        self._claude = ClaudeClient()
        self._cfg = get_config()

    def run(self, context: dict) -> SkillResult:
        try:
            management_context = context.get("management_context", "")
            field_data = self._collect_field_data(context)
            result = self._analyze_strategy_gap(management_context, field_data)
            alerts = result.get("alerts", [])
            kpi_status = result.get("kpi_status", {})

            # アラートレベル別に分類
            classified = self._classify_alerts(alerts)

            return self._ok({
                "alerts": alerts,
                "classified": classified,
                "kpi_status": kpi_status,
                "s_alerts": classified.get("S", []),
                "a_alerts": classified.get("A", []),
            })
        except Exception as e:
            logger.error("StrategySkill エラー: %s", e)
            return self._err(str(e))

    def _collect_field_data(self, context: dict) -> str:
        """現場データをテキストに集約"""
        sections = []

        # サクミル プロジェクト進捗
        projects = self._sakumiru.get_all_projects()
        if projects:
            import datetime as _dt
            _now = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=9)))
            proj_lines = []
            for p in projects:
                rate = f"{p.progress_rate * 100:.0f}%"
                overdue_count = sum(
                    1 for t in p.tasks
                    if t.due_date and t.status != "done"
                    and t.due_date < _now
                )
                proj_lines.append(
                    f"- {p.name}: 進捗{rate} | 期限超過タスク{overdue_count}件"
                )
            sections.append("【プロジェクト進捗】\n" + "\n".join(proj_lines))

        # シグナルスキルの結果があれば活用
        if "signals" in context:
            top_signals = context["signals"][:10]
            sig_lines = [f"- [{s['category']}] {s['content']}" for s in top_signals]
            sections.append("【検知済みシグナル】\n" + "\n".join(sig_lines))

        # メールから失注・競合情報を抽出
        if "emails" in context:
            loss_keywords = ["失注", "辞退", "見送り", "競合", "他社に", "今回は"]
            relevant = [
                e for e in context["emails"]
                if any(kw in str(e) for kw in loss_keywords)
            ]
            if relevant:
                sections.append(
                    f"【失注・競合関連メール: {len(relevant)}件】\n"
                    + "\n".join(str(e)[:100] for e in relevant[:5])
                )

        return "\n\n".join(sections) if sections else "現場データなし"

    def _analyze_strategy_gap(self, management_context: str, field_data: str) -> dict:
        """Claudeで戦略ギャップを分析"""
        prompt = f"""以下の現場データと経営コンテキストを照合し、戦略への影響を分析してください。

【現場データ】
{field_data}

上記を踏まえてアラートとKPIステータスを出力してください。"""

        response = self._claude.analyze(
            system_prompt=SYSTEM_PROMPT,
            user_message=prompt,
            cached_context=management_context,
        )

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            return json.loads(response[start:end])
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("戦略分析パース失敗: %s", e)
            return {"alerts": [], "kpi_status": {}}

    def _classify_alerts(self, alerts: list[dict]) -> dict[str, list[dict]]:
        result: dict[str, list] = {"S": [], "A": [], "B": [], "C": []}
        for a in alerts:
            level = a.get("level", "C")
            if level in result:
                result[level].append(a)
        return result
