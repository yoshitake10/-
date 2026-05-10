"""スキル基底クラス"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillResult:
    skill_name: str
    success: bool
    output: Any
    error: str | None = None
    metadata: dict = field(default_factory=dict)


class BaseSkill(ABC):
    """全スキルの共通インターフェース"""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def run(self, context: dict) -> SkillResult: ...

    def _ok(self, output: Any, **meta) -> SkillResult:
        return SkillResult(skill_name=self.name, success=True, output=output, metadata=meta)

    def _err(self, error: str) -> SkillResult:
        return SkillResult(skill_name=self.name, success=False, output=None, error=error)
