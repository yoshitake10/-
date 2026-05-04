"""
CEOマネジメントシステム - メインオーケストレーター
深夜4時〜早朝6時にデータ収集・分析を実行し、6:30にCEOへ配信する
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Google OAuth 共有インスタンス
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from ceo_system.agents.briefing_agent import BriefingAgent
from ceo_system.agents.feedback_agent import FeedbackAgent
from ceo_system.agents.signal_agent import SignalAgent
from ceo_system.agents.strategy_agent import StrategyAgent
from ceo_system.config import get_config
from ceo_system.connectors.gmail import GmailConnector
from ceo_system.connectors.google_docs import GoogleDocsConnector
from ceo_system.utils.logger import get_logger

logger = get_logger(__name__)


class CEOManagementOrchestrator:
    """全エージェントを統括して深夜バッチを実行するオーケストレーター"""

    def __init__(self) -> None:
        self._cfg = get_config()
        self._google_creds: Credentials | None = None

    def run(self) -> dict[str, Any]:
        """メイン実行エントリーポイント"""
        logger.info("=" * 60)
        logger.info("CEOマネジメントシステム 起動 - %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        logger.info("=" * 60)

        issues = self._cfg.validate()
        if issues:
            for issue in issues:
                logger.warning("設定不足: %s", issue)

        context = self._build_context()
        results: dict[str, Any] = {}

        # Phase 1: シグナル検知（データ収集）→ contextに結果を積む
        logger.info("[Phase 1] シグナル検知")
        docs_connector = self._get_docs_connector()
        signal_agent = SignalAgent(docs_connector=docs_connector)
        results["signal"] = signal_agent.execute(context)

        # Phase 2: 戦略・KPI分析（シグナルを活用）
        logger.info("[Phase 2] 戦略・KPI分析")
        strategy_agent = StrategyAgent()
        results["strategy"] = strategy_agent.execute(context)

        # Phase 3: 会議フィードバック
        logger.info("[Phase 3] 会議フィードバック")
        if docs_connector:
            minutes = docs_connector.get_meeting_minutes_texts(
                days=self._cfg.analysis_window_days
            )
            context["meeting_minutes"] = minutes
        feedback_agent = FeedbackAgent()
        results["feedback"] = feedback_agent.execute(context)

        # Phase 4: モーニングブリーフィング（6:30配信）
        logger.info("[Phase 4] モーニングブリーフィング生成・送信")
        briefing_agent = BriefingAgent()
        results["briefing"] = briefing_agent.execute(context)

        self._log_summary(results)
        return results

    def _build_context(self) -> dict[str, Any]:
        """全エージェント共通のコンテキストを構築"""
        context: dict[str, Any] = {}

        # 経営コンテキスト（戦略書・KPI）をキャッシュ対象として読み込む
        docs = self._get_docs_connector()
        if docs:
            strategy_text = docs.get_strategy_context()
            kpi_text = docs.get_kpi_context()
            context["management_context"] = (
                "【中期計画・戦略】\n" + strategy_text + "\n\n"
                "【KPI目標】\n" + kpi_text
            )
        else:
            context["management_context"] = ""

        # Gmail メール収集
        try:
            gmail = GmailConnector(self._get_google_creds())
            emails = gmail.get_recent_emails(days=self._cfg.analysis_window_days)
            context["emails"] = [
                {"subject": e.subject, "sender": e.sender,
                 "snippet": e.snippet, "body": e.body[:300]}
                for e in emails
            ]
            logger.info("Gmail: %d件のメールを収集", len(emails))
        except Exception as e:
            logger.warning("Gmail 収集失敗: %s", e)
            context["emails"] = []

        return context

    def _get_google_creds(self) -> Credentials:
        """Google OAuth 認証情報を取得（キャッシュ済みなら再利用）"""
        if self._google_creds and self._google_creds.valid:
            return self._google_creds

        cfg = self._cfg.google
        creds = None
        token_path = Path(cfg.token_path)

        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), cfg.scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    cfg.credentials_path, cfg.scopes
                )
                creds = flow.run_local_server(port=0)
            token_path.write_text(creds.to_json())

        self._google_creds = creds
        return creds

    def _get_docs_connector(self) -> GoogleDocsConnector | None:
        try:
            return GoogleDocsConnector(self._get_google_creds())
        except Exception as e:
            logger.warning("Docsコネクター初期化失敗: %s", e)
            return None

    def _log_summary(self, results: dict) -> None:
        logger.info("=" * 60)
        logger.info("実行結果サマリー")
        logger.info("  シグナル検知: %d件", results.get("signal", {}).get("signal_count", 0))
        alert_counts = results.get("strategy", {}).get("alert_counts", {})
        logger.info("  戦略アラート: S=%s A=%s B=%s C=%s",
                    alert_counts.get("S", 0), alert_counts.get("A", 0),
                    alert_counts.get("B", 0), alert_counts.get("C", 0))
        logger.info("  会議スコアリング: %d件", results.get("feedback", {}).get("scored_count", 0))
        logger.info("  ブリーフィング送信: %s", results.get("briefing", {}).get("success", False))
        logger.info("=" * 60)


def main() -> None:
    orchestrator = CEOManagementOrchestrator()
    try:
        results = orchestrator.run()
        success_count = sum(1 for v in results.values() if v.get("success"))
        logger.info("完了: %d/4 エージェント成功", success_count)
        sys.exit(0 if success_count > 0 else 1)
    except Exception as e:
        logger.exception("システム致命的エラー: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
