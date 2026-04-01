"""
セキュリティバリデーター（個人情報・マイナンバー検知）
マニュアルⅡ-(3) に基づき機密情報の混入を検知する
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── 検知キーワード定義 ──────────────────────────────────────────────────────

# 致命的（FAIL）: アップロードを強制遮断
BLOCK_KEYWORDS: list[str] = [
    "個人番号届出書",
    "マイナンバー",
    "通知カード",
    "住民票",
]

# 警告（WARN）: 財務書類と混在時に警告
WARN_KEYWORDS: list[str] = [
    "身分証",
    "免許証",
    "パスポート",
]

# 財務書類キーワード（WARN_KEYWORDS との混在チェック用）
FINANCIAL_KEYWORDS: list[str] = [
    "予算", "見積", "請求", "領収", "振込", "収支",
]

# マイナンバーの数字パターン（12桁の数字列）
_MYNUMBER_DIGIT_PATTERN = re.compile(r"\b\d{12}\b")

# テキストを読み込める拡張子
_TEXT_EXTENSIONS = {".htm", ".html", ".txt", ".csv"}


@dataclass
class SecurityResult:
    """セキュリティ検査結果"""
    blocked: bool = False          # True なら処理を強制中断
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blocked_files: list[str] = field(default_factory=list)


def _read_text(path: Path) -> Optional[str]:
    """テキストファイルを読み込む。失敗した場合は None を返す"""
    raw = path.read_bytes()
    for enc in ("shift_jis", "cp932", "utf-8", "utf-8-sig"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def _scan_text_for_keywords(text: str, keywords: list[str]) -> list[str]:
    """テキスト内に含まれるキーワードのリストを返す"""
    return [kw for kw in keywords if kw in text]


def validate_security(folder_dir: Path) -> SecurityResult:
    """
    フォルダ内の全ファイルに対してセキュリティスキャンを実行する。
    ファイル名スキャン + テキストファイルの内容スキャン。
    """
    result = SecurityResult()

    # 財務書類が存在するか（WARN_KEYWORDS との混在チェック用）
    has_financial = False
    for path in folder_dir.iterdir():
        if any(kw in path.stem for kw in FINANCIAL_KEYWORDS):
            has_financial = True
            break

    for path in folder_dir.iterdir():
        if not path.is_file():
            continue

        filename = path.name

        # ── ファイル名スキャン ───────────────────────────────────────────────

        # BLOCK キーワード（ファイル名）
        for kw in BLOCK_KEYWORDS:
            if kw in filename:
                result.blocked = True
                result.valid = False
                result.blocked_files.append(filename)
                result.errors.append(
                    f"SEC_ERR_001: 【重要】{filename!r} にマイナンバー関連キーワード"
                    f"（{kw!r}）を検知しました。処理を中断します。"
                    " 参照: Ⅱ-(3) 注意！マイナンバーの扱い"
                )
                break

        # WARN キーワード（ファイル名）
        for kw in WARN_KEYWORDS:
            if kw in filename:
                if has_financial:
                    result.warnings.append(
                        f"WRN_SEC_001: {filename!r} に身分証関連キーワード（{kw!r}）を検知。"
                        "財務書類との混在が疑われます。内容を確認してください。"
                    )
                else:
                    result.warnings.append(
                        f"WRN_SEC_002: {filename!r} に身分証関連キーワード（{kw!r}）を検知。"
                        "個人情報の取り扱いに注意してください。"
                    )

        # ── テキスト内容スキャン（テキスト系ファイルのみ） ─────────────────
        if path.suffix.lower() not in _TEXT_EXTENSIONS:
            continue

        try:
            text = _read_text(path)
        except Exception:
            result.warnings.append(f"WRN_SEC_003: {filename!r} の内容スキャンに失敗しました。")
            continue

        if text is None:
            continue

        # BLOCK キーワード（内容）
        found_block = _scan_text_for_keywords(text, BLOCK_KEYWORDS)
        if found_block:
            result.blocked = True
            result.valid = False
            if filename not in result.blocked_files:
                result.blocked_files.append(filename)
            for kw in found_block:
                result.errors.append(
                    f"SEC_ERR_001: 【重要】{filename!r} の内容にマイナンバー関連キーワード"
                    f"（{kw!r}）を検知しました。処理を中断します。"
                    " 参照: Ⅱ-(3) 注意！マイナンバーの扱い"
                )

        # 12桁数字パターン検知（マイナンバー候補）
        digit_matches = _MYNUMBER_DIGIT_PATTERN.findall(text)
        if digit_matches:
            result.warnings.append(
                f"WRN_SEC_004: {filename!r} に12桁の数字列（マイナンバー候補: "
                f"{digit_matches[0]}...）が含まれています。確認してください。"
            )

        # WARN キーワード（内容）
        found_warn = _scan_text_for_keywords(text, WARN_KEYWORDS)
        if found_warn and has_financial:
            for kw in found_warn:
                if not any(kw in w for w in result.warnings):
                    result.warnings.append(
                        f"WRN_SEC_001: {filename!r} 内に身分証関連キーワード（{kw!r}）を検知。"
                        "財務書類との混在を確認してください。"
                    )

    return result
