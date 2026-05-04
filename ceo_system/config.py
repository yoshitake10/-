"""
CEOマネジメントシステム - 設定管理
環境変数からすべての認証情報・パラメータを読み込む
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GoogleConfig:
    credentials_path: str = field(
        default_factory=lambda: os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    )
    token_path: str = field(
        default_factory=lambda: os.environ.get("GOOGLE_TOKEN_PATH", "token.json")
    )
    scopes: list[str] = field(default_factory=lambda: [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/documents.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/gmail.readonly",
    ])
    ceo_calendar_id: str = field(
        default_factory=lambda: os.environ.get("CEO_CALENDAR_ID", "primary")
    )
    strategy_doc_id: str = field(
        default_factory=lambda: os.environ.get("STRATEGY_DOC_ID", "")
    )
    kpi_doc_id: str = field(
        default_factory=lambda: os.environ.get("KPI_DOC_ID", "")
    )


@dataclass
class LineWorksConfig:
    bot_id: str = field(default_factory=lambda: os.environ.get("LINEWORKS_BOT_ID", ""))
    bot_secret: str = field(default_factory=lambda: os.environ.get("LINEWORKS_BOT_SECRET", ""))
    service_account: str = field(
        default_factory=lambda: os.environ.get("LINEWORKS_SERVICE_ACCOUNT", "")
    )
    private_key_path: str = field(
        default_factory=lambda: os.environ.get("LINEWORKS_PRIVATE_KEY_PATH", "lineworks_private.key")
    )
    domain_id: str = field(default_factory=lambda: os.environ.get("LINEWORKS_DOMAIN_ID", ""))
    ceo_user_id: str = field(default_factory=lambda: os.environ.get("LINEWORKS_CEO_USER_ID", ""))
    channel_id: str = field(
        default_factory=lambda: os.environ.get("LINEWORKS_CEO_CHANNEL_ID", "")
    )


@dataclass
class SakumiruConfig:
    api_key: str = field(default_factory=lambda: os.environ.get("SAKUMIRU_API_KEY", ""))
    base_url: str = field(
        default_factory=lambda: os.environ.get("SAKUMIRU_BASE_URL", "https://api.sakumiru.jp/v1")
    )
    company_id: str = field(default_factory=lambda: os.environ.get("SAKUMIRU_COMPANY_ID", ""))


@dataclass
class ClaudeConfig:
    api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    model: str = field(
        default_factory=lambda: os.environ.get("CLAUDE_MODEL", "claude-opus-4-7")
    )
    max_tokens: int = 4096
    cache_enabled: bool = True


@dataclass
class SchedulerConfig:
    # 深夜4時〜早朝6時に自律実行、6:30に配信
    run_hour_start: int = 4
    run_hour_end: int = 6
    briefing_hour: int = 6
    briefing_minute: int = 30
    timezone: str = field(
        default_factory=lambda: os.environ.get("TZ", "Asia/Tokyo")
    )


@dataclass
class AlertConfig:
    # S/A/B/C アラート閾値（戦略への影響度スコア）
    s_threshold: float = 0.9   # 最重要・即時対応
    a_threshold: float = 0.7   # 重要・当日対応
    b_threshold: float = 0.5   # 要注意・今週対応
    c_threshold: float = 0.3   # 参考情報


@dataclass
class SystemConfig:
    google: GoogleConfig = field(default_factory=GoogleConfig)
    line_works: LineWorksConfig = field(default_factory=LineWorksConfig)
    sakumiru: SakumiruConfig = field(default_factory=SakumiruConfig)
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    alert: AlertConfig = field(default_factory=AlertConfig)

    # 分析対象の期間（日数）
    analysis_window_days: int = int(os.environ.get("ANALYSIS_WINDOW_DAYS", "7"))

    # シグナル分類カテゴリー
    signal_categories: list[str] = field(default_factory=lambda: [
        "仮説", "学び", "意思決定", "アイデア", "気づき", "リスク", "機会"
    ])

    def validate(self) -> list[str]:
        """必須設定の欠落をチェックし、問題リストを返す"""
        issues = []
        if not self.claude.api_key:
            issues.append("ANTHROPIC_API_KEY が未設定")
        if not self.line_works.bot_id:
            issues.append("LINEWORKS_BOT_ID が未設定")
        if not self.line_works.ceo_user_id:
            issues.append("LINEWORKS_CEO_USER_ID が未設定")
        if not self.google.strategy_doc_id:
            issues.append("STRATEGY_DOC_ID が未設定（戦略ドキュメントIDを設定してください）")
        if not self.google.kpi_doc_id:
            issues.append("KPI_DOC_ID が未設定（KPIドキュメントIDを設定してください）")
        return issues


# シングルトン
_config: Optional[SystemConfig] = None


def get_config() -> SystemConfig:
    global _config
    if _config is None:
        _config = SystemConfig()
    return _config
