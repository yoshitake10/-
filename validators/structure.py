"""
ディレクトリ構造バリデーター
マニュアルⅣ章に基づき ZIP 展開後の構成を検証する
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


_HALFWIDTH_UPPER_ALNUM = re.compile(r"^[A-Z0-9\-]+$")


@dataclass
class StructureResult:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    root_folder: Optional[str] = None
    has_gian: bool = False
    files: list[str] = field(default_factory=list)


def validate_structure(extracted_dir: Path, zip_stem: str) -> StructureResult:
    """
    extracted_dir: ZIPを展開したディレクトリ
    zip_stem:      ZIPファイル名（拡張子なし）
    """
    result = StructureResult()

    # ── ルートフォルダの確認 ─────────────────────────────────────────────────
    top_level = [p for p in extracted_dir.iterdir()]
    folders   = [p for p in top_level if p.is_dir()]
    loose_files = [p for p in top_level if p.is_file()]

    if len(folders) == 1 and not loose_files:
        root = folders[0]
        result.root_folder = root.name

        # ルートフォルダ名が半角英数大文字かチェック
        if not _HALFWIDTH_UPPER_ALNUM.match(root.name):
            result.valid = False
            result.errors.append(
                f"ERR_NAME_001: ルートフォルダ名 {root.name!r} が半角英数大文字ではありません。"
            )

        # ルートフォルダ名と ZIP ファイル名の一致チェック
        if root.name != zip_stem:
            result.valid = False
            result.errors.append(
                f"ERR_STR_001: ルートフォルダ名 {root.name!r} が"
                f"ZIPファイル名 {zip_stem!r} と一致しません。"
            )

        scan_dir = root
    elif loose_files and not folders:
        # フラット展開（ルートフォルダなし）
        result.warnings.append(
            "WRN_STR_001: ZIPがフォルダを含まずファイルが直置きされています。"
            "ルートフォルダを作成して再パッケージすることを推奨します。"
        )
        scan_dir = extracted_dir
    else:
        result.valid = False
        result.errors.append(
            "ERR_STR_002: ZIP内のディレクトリ構造が不正です。"
            "ルートフォルダが1つのみ存在する構成にしてください。"
        )
        scan_dir = extracted_dir

    # ── gian.htm の存在確認 ─────────────────────────────────────────────────
    gian_path = scan_dir / "gian.htm"
    if gian_path.exists():
        result.has_gian = True
    else:
        # 大文字小文字を無視して検索
        gian_candidates = [
            p for p in scan_dir.iterdir()
            if p.is_file() and p.name.lower() == "gian.htm"
        ]
        if gian_candidates:
            result.has_gian = True
            result.warnings.append(
                f"WRN_STR_002: gian.htm のファイル名の大文字小文字が"
                f"規定と異なります: {gian_candidates[0].name!r}"
            )
        else:
            result.valid = False
            result.errors.append(
                "ERR_STR_003: 必須ファイル gian.htm がフォルダ直下に見つかりません。"
            )

    # ── ファイル一覧を収集 ──────────────────────────────────────────────────
    if scan_dir.exists():
        result.files = [p.name for p in scan_dir.iterdir() if p.is_file()]

    return result
