"""
Anthropic Claude API クライアント
プロンプトキャッシュを活用して、繰り返し参照する経営コンテキストのコストを削減する
"""
from __future__ import annotations

from typing import Any

import anthropic

from ceo_system.config import get_config
from ceo_system.utils.logger import get_logger

logger = get_logger(__name__)


class ClaudeClient:
    def __init__(self) -> None:
        cfg = get_config().claude
        self._client = anthropic.Anthropic(api_key=cfg.api_key)
        self._model = cfg.model
        self._max_tokens = cfg.max_tokens
        self._cache_enabled = cfg.cache_enabled

    def analyze(
        self,
        system_prompt: str,
        user_message: str,
        cached_context: str | None = None,
    ) -> str:
        """
        Claude に分析を依頼する。
        cached_context は経営コンテキスト等の大容量・繰り返し利用テキストに使う。
        prompt caching により API コストを大幅削減できる。
        """
        messages: list[dict[str, Any]] = []

        if cached_context and self._cache_enabled:
            # 経営コンテキスト（戦略書・KPI等）をキャッシュブロックに入れる
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": cached_context,
                        "cache_control": {"type": "ephemeral"},
                    },
                    {
                        "type": "text",
                        "text": user_message,
                    },
                ],
            })
        else:
            messages.append({"role": "user", "content": user_message})

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_prompt,
                messages=messages,
            )
            usage = response.usage
            logger.info(
                "Claude API 完了 | input=%d cache_read=%d output=%d",
                usage.input_tokens,
                getattr(usage, "cache_read_input_tokens", 0),
                usage.output_tokens,
            )
            return response.content[0].text
        except anthropic.APIError as e:
            logger.error("Claude API エラー: %s", e)
            raise

    def analyze_batch(
        self,
        tasks: list[dict[str, str]],
        system_prompt: str,
        cached_context: str | None = None,
    ) -> list[str]:
        """複数タスクを順次処理（将来のバッチ API 対応を想定）"""
        results = []
        for task in tasks:
            result = self.analyze(
                system_prompt=system_prompt,
                user_message=task["message"],
                cached_context=cached_context,
            )
            results.append(result)
        return results
