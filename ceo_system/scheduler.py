"""
スケジューラー
深夜4時〜早朝6時に処理、6:30にCEOへ配信するジョブをスケジューリングする
"""
from __future__ import annotations

import time
from datetime import datetime

import schedule

from ceo_system.config import get_config
from ceo_system.main import CEOManagementOrchestrator
from ceo_system.utils.logger import get_logger

logger = get_logger(__name__)


def run_daily_job() -> None:
    """毎朝4:00に実行される日次バッチ"""
    logger.info("日次バッチ開始")
    orchestrator = CEOManagementOrchestrator()
    try:
        results = orchestrator.run()
        logger.info("日次バッチ完了: %s", results)
    except Exception as e:
        logger.exception("日次バッチエラー: %s", e)


def start_scheduler() -> None:
    """スケジューラーを起動してループを開始する"""
    cfg = get_config().scheduler
    run_time = f"{cfg.briefing_hour - 2:02d}:{cfg.briefing_minute:02d}"  # 6:30配信の2時間前 = 4:30
    run_time = "04:00"  # 固定: 深夜4時に開始

    logger.info("スケジューラー起動 - 実行時刻: %s (JST)", run_time)
    schedule.every().day.at(run_time).do(run_daily_job)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "now":
        # 即時実行モード（テスト用）
        run_daily_job()
    else:
        start_scheduler()
