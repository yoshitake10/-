#!/usr/bin/env python3
"""
CEOマネジメントシステム 仮想デモ実行スクリプト
API認証情報なしで全機能を動作確認できる

使い方:
  python demo.py            # 全フェーズ実行
  python demo.py briefing   # ブリーフィングのみ
  python demo.py signal     # シグナル検知のみ
  python demo.py strategy   # 戦略・KPIのみ
  python demo.py feedback   # 会議フィードバックのみ
"""
from __future__ import annotations

import os
import sys

# 仮想モードを有効化（APIキー不要）
os.environ["USE_MOCK"] = "true"
os.environ["ANTHROPIC_API_KEY"] = "mock-key-not-used"

# ─── 以降は通常のシステムコードを呼び出す ─────────────────────────────────────

from ceo_system.main import CEOManagementOrchestrator
from ceo_system.mock.factory import get_docs_connector, get_gmail_connector
from ceo_system.agents.briefing_agent import BriefingAgent
from ceo_system.agents.signal_agent import SignalAgent
from ceo_system.agents.strategy_agent import StrategyAgent
from ceo_system.agents.feedback_agent import FeedbackAgent
from ceo_system.mock.connectors import MockLineWorksConnector
from ceo_system.utils.logger import get_logger

logger = get_logger("demo")

DIVIDER = "=" * 60


def _build_mock_context() -> dict:
    docs = get_docs_connector()
    gmail = get_gmail_connector()

    strategy_text = docs.get_strategy_context()
    kpi_text = docs.get_kpi_context()

    emails_raw = gmail.get_recent_emails()
    emails = [
        {"subject": e.subject, "sender": e.sender,
         "snippet": e.snippet, "body": e.body[:300]}
        for e in emails_raw
    ]

    minutes = docs.get_meeting_minutes_texts()

    return {
        "management_context": (
            "【中期計画・戦略】\n" + strategy_text + "\n\n"
            "【KPI目標】\n" + kpi_text
        ),
        "emails": emails,
        "meeting_minutes": minutes,
    }


def run_briefing(context: dict) -> None:
    print(f"\n{DIVIDER}")
    print("  Phase 1: モーニングブリーフィング")
    print(DIVIDER)
    agent = BriefingAgent()
    result = agent.execute(context)
    print(f"\n実行結果:")
    print(f"  送信成功: {result.get('success')}")
    print(f"  本日の予定: {result.get('events_count')}件")
    print(f"  資料不足で通知送付: {result.get('missing_docs', [])}")
    print(f"  DM送信数: {result.get('dm_notifications', 0)}件")


def run_signal(context: dict) -> None:
    print(f"\n{DIVIDER}")
    print("  Phase 2: シグナル検知")
    print(DIVIDER)
    docs = get_docs_connector()
    agent = SignalAgent(docs_connector=docs)
    result = agent.execute(context)
    print(f"\n実行結果:")
    print(f"  送信成功: {result.get('success')}")
    print(f"  検知シグナル数: {result.get('signal_count', 0)}件")
    tops = result.get("top_signals", [])
    if tops:
        print(f"  重要シグナルTOP:")
        for s in tops[:3]:
            print(f"    ★{s['importance']} [{s['category']}] {s['content']}")


def run_strategy(context: dict) -> None:
    print(f"\n{DIVIDER}")
    print("  Phase 3: 戦略・KPIアップデート")
    print(DIVIDER)
    agent = StrategyAgent()
    result = agent.execute(context)
    print(f"\n実行結果:")
    print(f"  送信成功: {result.get('success')}")
    counts = result.get("alert_counts", {})
    print(f"  アラート: S={counts.get('S',0)} A={counts.get('A',0)} B={counts.get('B',0)} C={counts.get('C',0)}")
    kpi = result.get("kpi_status", {})
    if kpi:
        print(f"  KPI状況:")
        status_map = {"on_track": "✅", "at_risk": "⚠️", "off_track": "❌"}
        for name, data in kpi.items():
            icon = status_map.get(data.get("status", ""), "❓")
            print(f"    {icon} {name}: {data.get('current','?')} / 目標 {data.get('target','?')}")


def run_feedback(context: dict) -> None:
    print(f"\n{DIVIDER}")
    print("  Phase 4: 会議品質フィードバック")
    print(DIVIDER)
    agent = FeedbackAgent()
    result = agent.execute(context)
    print(f"\n実行結果:")
    print(f"  送信成功: {result.get('success')}")
    print(f"  採点した会議数: {result.get('scored_count', 0)}件")
    avg = result.get("average_score")
    if avg:
        print(f"  平均スコア: {avg}/100")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    print(f"\n{'='*60}")
    print("  CEO マネジメントシステム - 仮想デモ実行")
    print(f"  モード: {mode}")
    print(f"{'='*60}")
    print("\nモックデータを読み込み中...")

    context = _build_mock_context()

    print(f"  ✓ 経営コンテキスト読み込み: {len(context['management_context'])}文字")
    print(f"  ✓ メール: {len(context['emails'])}件")
    print(f"  ✓ 議事録: {len(context['meeting_minutes'])}件")

    if mode in ("all", "briefing"):
        run_briefing(context)

    if mode in ("all", "signal"):
        run_signal(context)

    if mode in ("all", "strategy"):
        run_strategy(context)

    if mode in ("all", "feedback"):
        run_feedback(context)

    print(f"\n{DIVIDER}")
    print("  デモ完了")
    print(f"  ※ LINE WORKS への実際の送信はモックです（ログに出力済み）")
    print(f"  ※ 本番化には .env.example を参考に環境変数を設定してください")
    print(DIVIDER)


if __name__ == "__main__":
    main()
