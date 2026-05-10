"""
サクミル コネクター
タスク・プロジェクト進捗データを取得する
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests

from ceo_system.config import get_config
from ceo_system.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SakumiruTask:
    task_id: str
    title: str
    assignee: str
    project: str
    status: str        # "todo" | "in_progress" | "done" | "blocked"
    due_date: datetime | None
    updated_at: datetime
    comments: list[str]


@dataclass
class SakumiruProject:
    project_id: str
    name: str
    progress_rate: float   # 0.0 〜 1.0
    tasks: list[SakumiruTask]
    last_activity: datetime


class SakumiruConnector:
    def __init__(self) -> None:
        self._cfg = get_config().sakumiru
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self._cfg.api_key}",
            "Content-Type": "application/json",
        })

    def _get(self, path: str, params: dict | None = None) -> Any:
        url = f"{self._cfg.base_url}{path}"
        resp = self._session.get(url, params=params or {})
        resp.raise_for_status()
        return resp.json()

    def get_all_projects(self) -> list[SakumiruProject]:
        """全プロジェクトの進捗を取得"""
        try:
            data = self._get(f"/companies/{self._cfg.company_id}/projects")
        except requests.RequestException as e:
            logger.error("サクミル プロジェクト取得失敗: %s", e)
            return []

        projects = []
        for p in data.get("projects", []):
            tasks = self._get_project_tasks(p["projectId"])
            done = sum(1 for t in tasks if t.status == "done")
            rate = done / len(tasks) if tasks else 0.0

            projects.append(SakumiruProject(
                project_id=p["projectId"],
                name=p.get("name", "不明"),
                progress_rate=rate,
                tasks=tasks,
                last_activity=datetime.fromisoformat(p.get("updatedAt", datetime.now().isoformat())),
            ))

        logger.info("サクミル プロジェクト取得: %d件", len(projects))
        return projects

    def _get_project_tasks(self, project_id: str) -> list[SakumiruTask]:
        try:
            data = self._get(f"/projects/{project_id}/tasks")
        except requests.RequestException as e:
            logger.warning("タスク取得失敗 project=%s: %s", project_id, e)
            return []

        tasks = []
        for t in data.get("tasks", []):
            due_raw = t.get("dueDate")
            due_date = datetime.fromisoformat(due_raw) if due_raw else None
            updated_raw = t.get("updatedAt", datetime.now().isoformat())

            tasks.append(SakumiruTask(
                task_id=t["taskId"],
                title=t.get("title", "不明"),
                assignee=t.get("assigneeName", "未割当"),
                project=t.get("projectName", "不明"),
                status=t.get("status", "todo"),
                due_date=due_date,
                updated_at=datetime.fromisoformat(updated_raw),
                comments=[c.get("body", "") for c in t.get("comments", [])],
            ))
        return tasks

    def get_overdue_tasks(self) -> list[SakumiruTask]:
        """期限超過タスクを横断的に抽出"""
        from datetime import timezone, timedelta
        now = datetime.now(timezone(timedelta(hours=9)))
        overdue = []
        for project in self.get_all_projects():
            for task in project.tasks:
                if (
                    task.due_date
                    and task.due_date < now
                    and task.status not in ("done",)
                ):
                    overdue.append(task)
        logger.info("期限超過タスク: %d件", len(overdue))
        return overdue

    def get_blocked_tasks(self) -> list[SakumiruTask]:
        """ブロックされているタスクを抽出"""
        blocked = []
        for project in self.get_all_projects():
            for task in project.tasks:
                if task.status == "blocked":
                    blocked.append(task)
        return blocked
