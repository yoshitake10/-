"""
戦略・KPIアップデート エージェント
StrategySkill の結果をアラートレベル別に整形して配信する
S/Aレベルは即時通知、B/Cは朝のブリーフィングに統合
"""
from __future__ import annotations

from ceo_system.connectors.line_works import LineWorksConnector
from ceo_system.skills.strategy_skill import AlertLevel, StrategySkill
from ceo_system.utils.logger import get_logger

logger = get_logger(__name__)

ALERT_ICONS = {
    AlertLevel.S: "🚨",
    AlertLevel.A: "⚠️",
    AlertLevel.B: "📌",
    AlertLevel.C: "ℹ️",
}


class StrategyAgent:
    def __init__(self) -> None:
        self._skill = StrategySkill()
        self._lw = LineWorksConnector()

    def execute(self, context: dict) -> dict:
        logger.info("StrategyAgent 開始")
        result = self._skill.run(context)

        if not result.success:
            logger.error("StrategySkill 失敗: %s", result.error)
            return {"success": False, "error": result.error}

        output = result.output
        classified = output.get("classified", {})

        # S/Aレベルは即時通知
        urgent_sent = False
        s_alerts = classified.get("S", [])
        a_alerts = classified.get("A", [])

        if s_alerts or a_alerts:
            urgent_message = self._format_urgent_alerts(s_alerts, a_alerts)
            urgent_sent = self._lw.send_to_ceo(urgent_message)
            logger.info("緊急アラート送信: S=%d件, A=%d件", len(s_alerts), len(a_alerts))

        # 全体レポートも送信
        full_message = self._format_full_report(output)
        self._lw.send_to_ceo(full_message)

        return {
            "success": True,
            "urgent_sent": urgent_sent,
            "alert_counts": {
                "S": len(s_alerts),
                "A": len(a_alerts),
                "B": len(classified.get("B", [])),
                "C": len(classified.get("C", [])),
            },
            "kpi_status": output.get("kpi_status", {}),
        }

    def _format_urgent_alerts(self, s_alerts: list, a_alerts: list) -> str:
        lines = [
            "━━━━━━━━━━━━━━━━━━━━",
            "🚨 【緊急】戦略アラート",
            "━━━━━━━━━━━━━━━━━━━━",
        ]

        for a in s_alerts:
            lines += [
                f"",
                f"🚨 [S] {a['title']}",
                f"   {a['description']}",
                f"   影響KPI: {a['affected_kpi']}",
                f"   → {a['recommended_action']}",
            ]

        for a in a_alerts:
            lines += [
                f"",
                f"⚠️ [A] {a['title']}",
                f"   {a['description']}",
                f"   → {a['recommended_action']}",
            ]

        return "\n".join(lines)

    def _format_full_report(self, output: dict) -> str:
        classified = output.get("classified", {})
        kpi_status = output.get("kpi_status", {})

        lines = [
            "━━━━━━━━━━━━━━━━━━━━",
            "📊 戦略・KPI アップデート",
            "━━━━━━━━━━━━━━━━━━━━",
        ]

        # KPI ステータス
        if kpi_status:
            lines += ["", "【 KPI 状況 】"]
            status_icons = {"on_track": "✅", "at_risk": "⚠️", "off_track": "❌"}
            for kpi_name, kpi_data in kpi_status.items():
                icon = status_icons.get(kpi_data.get("status", ""), "❓")
                lines.append(
                    f"{icon} {kpi_name}: {kpi_data.get('current','?')} / 目標 {kpi_data.get('target','?')}"
                )

        # B/C アラート（情報提供）
        b_alerts = classified.get("B", [])
        c_alerts = classified.get("C", [])
        if b_alerts or c_alerts:
            lines += ["", "【 モニタリング事項 】"]
            for a in b_alerts:
                lines.append(f"📌 [B] {a['title']}: {a['description']}")
            for a in c_alerts:
                lines.append(f"ℹ️ [C] {a['title']}: {a['description']}")

        return "\n".join(lines)
