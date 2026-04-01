"""
ハイパーリンク有効性バリデーター
マニュアルⅣ-Ⅱ章に基づき gian.htm 内のリンクを検証する
"""
from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional


# 許可する拡張子
_ALLOWED_EXTENSIONS = {".htm", ".html", ".pdf", ".jpeg", ".jpg", ".png"}


@dataclass
class LinkIssue:
    href: str
    error_code: str
    message: str
    is_fatal: bool = True


@dataclass
class LinkResult:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked_links: list[str] = field(default_factory=list)
    broken_links: list[str] = field(default_factory=list)


class _HrefExtractor(HTMLParser):
    """<a href="..."> から href 属性を抽出する"""

    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag.lower() == "a":
            for k, v in attrs:
                if k.lower() == "href" and v:
                    self.hrefs.append(v)


def _read_html(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("shift_jis", "cp932", "utf-8", "utf-8-sig"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def _normalize_href(href: str) -> Optional[str]:
    """
    href を正規化してファイル名を返す。
    外部 URL・アンカーのみのリンクは None を返す（検証対象外）
    """
    href = href.strip()

    # 外部 URL を除外
    if href.lower().startswith(("http://", "https://", "mailto:", "ftp://")):
        return None

    # アンカーのみ（例: #section1）を除外
    if href.startswith("#"):
        return None

    # URL デコード
    try:
        href = urllib.parse.unquote(href)
    except Exception:
        pass

    # パス区切りを正規化（バックスラッシュ→スラッシュ）
    href = href.replace("\\", "/")

    # アンカー部分を除去
    href = href.split("#")[0]

    return href or None


def validate_links(gian_path: Path, folder_dir: Path) -> LinkResult:
    """
    gian_path: gian.htm のパス
    folder_dir: 議案フォルダのルート（リンク先ファイルを検索するディレクトリ）
    """
    result = LinkResult()

    if not gian_path.exists():
        result.valid = False
        result.errors.append("ERR_LNK_000: gian.htm が存在しないためリンク検証をスキップしました。")
        return result

    # ── href 抽出 ──────────────────────────────────────────────────────────
    try:
        html_text = _read_html(gian_path)
    except Exception as e:
        result.valid = False
        result.errors.append(f"ERR_READ: gian.htm 読み込み失敗: {e}")
        return result

    extractor = _HrefExtractor()
    try:
        extractor.feed(html_text)
    except Exception:
        result.warnings.append("WRN_LNK_000: gian.htm のHTML解析中に軽微なエラーが発生しました。")

    # フォルダ内の実ファイル一覧（大文字小文字を正規化して比較）
    existing_files: dict[str, Path] = {
        p.name.lower(): p for p in folder_dir.iterdir() if p.is_file()
    }

    seen: set[str] = set()

    for raw_href in extractor.hrefs:
        normalized = _normalize_href(raw_href)
        if normalized is None:
            continue

        # サブパスの場合はファイル名部分のみ取得
        filename = Path(normalized).name
        if not filename:
            continue

        if filename.lower() in seen:
            continue
        seen.add(filename.lower())

        result.checked_links.append(filename)

        # ── 実在性チェック ──────────────────────────────────────────────────
        if filename.lower() not in existing_files:
            result.valid = False
            result.broken_links.append(filename)
            result.errors.append(
                f"ERR_LNK_001: ハイパーリンク先 {filename!r} がフォルダ内に見つかりません。"
                " 参照: Ⅳ-Ⅱ. ハイパーリンクの作成"
            )
            continue

        # ── 形式チェック ────────────────────────────────────────────────────
        ext = Path(filename).suffix.lower()
        if ext not in _ALLOWED_EXTENSIONS:
            result.warnings.append(
                f"WRN_LNK_002: リンク先 {filename!r} の形式（{ext}）が"
                f"規定（htm/pdf/jpeg）以外です。"
            )

    # ── gian.htm 内に1件もリンクがない場合の警告 ─────────────────────────
    if not result.checked_links:
        result.warnings.append(
            "WRN_LNK_003: gian.htm 内にハイパーリンクが1件も見つかりませんでした。"
        )

    return result


def validate_suffix_notation(folder_dir: Path) -> tuple[list[str], list[str]]:
    """
    議案フォルダ内の各ファイルについて（案）・（参考資料）付与の基本チェックを行う。
    マニュアルⅡ章(2)に基づく簡易判定。
    返値: (errors, warnings)
    """
    errors: list[str] = []
    warnings: list[str] = []

    # （案）必須キーワード（ファイル名に含まれる場合、末尾に（案）が必要）
    REQUIRED_AN_KEYWORDS = [
        "事業収支予算書", "見積書", "事業概要", "タイムスケジュール",
        "講師プロフィール", "会場レイアウト", "検証資料",
    ]

    # （参考資料）が付くべきキーワード
    SANKO_KEYWORDS = [
        "ルールブック", "デザイン案", "ポスター", "チラシ",
    ]

    for path in folder_dir.iterdir():
        if not path.is_file():
            continue

        name_no_ext = path.stem  # 拡張子なし

        for kw in REQUIRED_AN_KEYWORDS:
            if kw in name_no_ext:
                if "（案）" not in name_no_ext and "案" not in name_no_ext:
                    warnings.append(
                        f"WRN_SUFFIX_001: {path.name!r} には（案）の付与が推奨されます。"
                        " 参照: Ⅱ-(2) 資料の性質表示"
                    )
                break

    return errors, warnings
