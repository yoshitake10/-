"""Google Docs / Drive コネクター"""
from __future__ import annotations

from typing import Any

from googleapiclient.discovery import build

from ceo_system.config import get_config
from ceo_system.utils.logger import get_logger

logger = get_logger(__name__)


class GoogleDocsConnector:
    """Google Docs からドキュメントテキストを取得する"""

    def __init__(self, credentials: Any) -> None:
        self._docs_svc = build("docs", "v1", credentials=credentials)
        self._drive_svc = build("drive", "v3", credentials=credentials)
        self._cfg = get_config().google

    def get_document_text(self, doc_id: str) -> str:
        """ドキュメントの全テキストを結合して返す"""
        doc = self._docs_svc.documents().get(documentId=doc_id).execute()
        content = doc.get("body", {}).get("content", [])
        return self._extract_text(content)

    def get_strategy_context(self) -> str:
        """中期計画・戦略ドキュメントのテキストを取得"""
        if not self._cfg.strategy_doc_id:
            logger.warning("STRATEGY_DOC_ID が未設定")
            return ""
        text = self.get_document_text(self._cfg.strategy_doc_id)
        logger.info("戦略ドキュメント取得: %d文字", len(text))
        return text

    def get_kpi_context(self) -> str:
        """KPIドキュメントのテキストを取得"""
        if not self._cfg.kpi_doc_id:
            logger.warning("KPI_DOC_ID が未設定")
            return ""
        text = self.get_document_text(self._cfg.kpi_doc_id)
        logger.info("KPIドキュメント取得: %d文字", len(text))
        return text

    def list_recent_docs(self, days: int = 7) -> list[dict]:
        """過去N日間に更新されたドキュメント一覧を取得"""
        from datetime import datetime, timedelta, timezone
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        results = self._drive_svc.files().list(
            q=(
                f"mimeType='application/vnd.google-apps.document' "
                f"and modifiedTime > '{cutoff}'"
            ),
            fields="files(id,name,modifiedTime,lastModifyingUser)",
            orderBy="modifiedTime desc",
            pageSize=50,
        ).execute()

        files = results.get("files", [])
        logger.info("最近更新されたドキュメント: %d件", len(files))
        return files

    def get_meeting_minutes_texts(self, days: int = 7) -> list[dict]:
        """'議事録'を含むドキュメントのテキストを収集"""
        results = self._drive_svc.files().list(
            q=(
                "mimeType='application/vnd.google-apps.document' "
                "and name contains '議事録'"
            ),
            fields="files(id,name,modifiedTime)",
            orderBy="modifiedTime desc",
            pageSize=20,
        ).execute()

        minutes = []
        for f in results.get("files", []):
            try:
                text = self.get_document_text(f["id"])
                minutes.append({
                    "title": f["name"],
                    "modified": f["modifiedTime"],
                    "text": text,
                })
            except Exception as e:
                logger.warning("議事録取得失敗 %s: %s", f["name"], e)

        logger.info("議事録取得: %d件", len(minutes))
        return minutes

    def _extract_text(self, content: list) -> str:
        texts = []
        for elem in content:
            paragraph = elem.get("paragraph")
            if not paragraph:
                continue
            for pe in paragraph.get("elements", []):
                run = pe.get("textRun")
                if run:
                    texts.append(run.get("content", ""))
        return "".join(texts)
