"""
シグナル検知エージェント
SignalSkill の結果を重要度順に整形してCEOに配信する
"""
from __future__ import annotations

from ceo_system.mock.factory import get_line_works_connector
from ceo_system.skills.signal_skill import SignalSkill
from ceo_system.utils.logger import get_logger

logger = get_logger(__name__)

IMPORTANCE_ICONS = {5: "🔴", 4: "🟠", 3: "🟡", 2: "🟢", 1: "⚪"}


class SignalAgent:
    def __init__(self, docs_connector=None) -> None:
        self._skill = SignalSkill(docs_connector=docs_connector)
        self._lw = get_line_works_connector()

    def execute(self, context: dict) -> dict:
        logger.info("SignalAgent 開始")
        result = self._skill.run(context)

        if not result.success:
            logger.error("SignalSkill 失敗: %s", result.error)
            return {"success": False, "error": result.error}

        output = result.output
        top_signals = output.get("top_signals", [])

        if not top_signals:
            logger.info("検知シグナルなし")
            return {"success": True, "signal_count": 0}

        message = self._format_message(output)
        sent = self._lw.send_to_ceo(message)

        # シグナルデータを後続エージェントのコンテキストに渡す
        context["signals"] = output.get("signals", [])

        return {
            "success": sent,
            "signal_count": len(output.get("signals", [])),
            "top_signals": top_signals,
        }

    def _format_message(self, output: dict) -> str:
        top = output.get("top_signals", [])
        by_cat = output.get("by_category", {})

        lines = [
            "━━━━━━━━━━━━━━━━━━━━",
            "📡 シグナル検知レポート",
            f"検知件数: {len(output.get('signals', []))}件",
            "━━━━━━━━━━━━━━━━━━━━",
            "",
            "【 重要シグナル TOP5 】",
        ]

        for i, s in enumerate(top[:5], 1):
            icon = IMPORTANCE_ICONS.get(s["importance"], "⚪")
            lines.append(f"{i}. {icon} [{s['category']}] {s['content']}")
            if s.get("recommended_action"):
                lines.append(f"   → {s['recommended_action']}")

        if by_cat:
            lines += ["", "【 カテゴリー別サマリー 】"]
            for cat, signals in by_cat.items():
                if signals:
                    lines.append(f"■ {cat}: {len(signals)}件")

        return "\n".join(lines)
