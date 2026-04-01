"""
文字種・書式バリデーター
マニュアルⅡ章(1)・Ⅲ章の注記に基づき、全角/半角・フォント・サイズを検証する
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional


# ── 文字種判定用正規表現 ────────────────────────────────────────────────────

# 半角英数字（ASCII の 0-9, A-Z, a-z）
_HALFWIDTH_ALNUM = re.compile(r"[0-9A-Za-z]")

# 全角英数大文字（Ａ-Ｚ，０-９）
_FULLWIDTH_UPPER_ALNUM = re.compile(r"^[Ａ-Ｚ０-９\－\ー]+$")

# 半角数字のみ（予算書金額欄）
_HALFWIDTH_DIGITS = re.compile(r"[0-9]")

# ファイル名参照パターン（本文中の大文字英数字の塊、例: 122-011K-0126K）
_FILENAME_REF_PATTERN = re.compile(
    r"[A-Za-z0-9Ａ-Ｚａ-ｚ０-９][A-Za-z0-9Ａ-Ｚａ-ｚ０-９\-－]{3,}"
)

# 除外対象ファイル（フォント・サイズチェック免除）
_YOSAN_FILENAMES = {"yosan.xls", "yosan.htm"}

# 期待フォント名（複数の表記を許容）
_EXPECTED_FONTS = {
    "ms pgothic",
    "ｍｓ ｐゴシック",
    "ms pゴシック",
    "ＭＳ Ｐゴシック".lower(),
}
_EXPECTED_FONTSIZE_PT = "10pt"
_EXPECTED_FONTSIZE_PX = "13px"  # 10pt ≈ 13.3px


@dataclass
class CharResult:
    filename: str
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ── HTML パーサー ──────────────────────────────────────────────────────────

class _HtmlTextExtractor(HTMLParser):
    """HTML本文テキスト・フォント情報・インラインスタイルを抽出する"""

    # タグ内容を無視するブロック
    _SKIP_TAGS = {"script", "style", "head"}

    def __init__(self):
        super().__init__()
        self.text_segments: list[str] = []
        self.font_families: list[str] = []
        self.font_sizes: list[str] = []
        self._skip_depth = 0
        self._current_tag = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        self._current_tag = tag.lower()
        if tag.lower() in self._SKIP_TAGS:
            self._skip_depth += 1
            return

        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        # <font face="..."> タグ
        if tag.lower() == "font":
            if "face" in attr_dict:
                self.font_families.append(attr_dict["face"])
            if "size" in attr_dict:
                self.font_sizes.append(attr_dict["size"])

        # style 属性から font-family・font-size を抽出
        if "style" in attr_dict:
            self._parse_inline_style(attr_dict["style"])

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self.text_segments.append(stripped)

    def _parse_inline_style(self, style: str) -> None:
        for decl in style.split(";"):
            decl = decl.strip()
            if ":" not in decl:
                continue
            prop, _, val = decl.partition(":")
            prop = prop.strip().lower()
            val  = val.strip()
            if prop == "font-family":
                self.font_families.append(val.strip("'\""))
            elif prop == "font-size":
                self.font_sizes.append(val)


def _read_html(path: Path) -> tuple[str, str]:
    """
    HTML ファイルを読み込む（Shift-JIS → UTF-8 フォールバック）
    (raw_bytes, text) を返す
    """
    raw = path.read_bytes()
    for enc in ("shift_jis", "cp932", "utf-8", "utf-8-sig"):
        try:
            return raw, raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw, raw.decode("utf-8", errors="replace")


def _extract_style_block_fonts(html_text: str) -> tuple[list[str], list[str]]:
    """<style> ブロック内の font-family と font-size を抽出する"""
    families: list[str] = []
    sizes: list[str] = []

    style_blocks = re.findall(r"<style[^>]*>(.*?)</style>", html_text, re.DOTALL | re.IGNORECASE)
    for block in style_blocks:
        for m in re.finditer(r"font-family\s*:\s*([^;}{]+)", block, re.IGNORECASE):
            families.append(m.group(1).strip().strip("'\""))
        for m in re.finditer(r"font-size\s*:\s*([^;}{]+)", block, re.IGNORECASE):
            sizes.append(m.group(1).strip())

    return families, sizes


def validate_html_characters(path: Path) -> CharResult:
    """HTM ファイルの文字種・書式を検証する"""
    result = CharResult(filename=path.name)
    is_yosan = path.name.lower() in _YOSAN_FILENAMES

    try:
        _, html_text = _read_html(path)
    except Exception as e:
        result.valid = False
        result.errors.append(f"ERR_READ: ファイル読み込み失敗: {e}")
        return result

    # ── テキスト・フォント情報を抽出 ────────────────────────────────────────
    parser = _HtmlTextExtractor()
    try:
        parser.feed(html_text)
    except Exception:
        result.warnings.append("WRN_CHR_000: HTML解析中に軽微なエラーが発生しました。")

    # スタイルブロックからも取得
    style_families, style_sizes = _extract_style_block_fonts(html_text)
    all_families = [f.lower() for f in parser.font_families + style_families]
    all_sizes    = parser.font_sizes + style_sizes

    full_text = " ".join(parser.text_segments)

    # ── ERR_CHR_001: 本文中の半角英数字チェック ─────────────────────────────
    halfwidth_matches = _HALFWIDTH_ALNUM.findall(full_text)
    if halfwidth_matches:
        sample = "".join(dict.fromkeys(halfwidth_matches))[:20]
        result.errors.append(
            f"ERR_CHR_001: 本文中に半角英数字（例: {sample!r}）が含まれています。"
            "全角に統一してください。 参照: Ⅱ-(1)-① 議案の記載について"
        )
        result.valid = False

    # ── ERR_CHR_002: 本文中ファイル名参照の全角チェック ─────────────────────
    refs = _FILENAME_REF_PATTERN.findall(full_text)
    bad_refs = [r for r in refs if _HALFWIDTH_ALNUM.search(r)]
    if bad_refs:
        sample = bad_refs[0]
        result.errors.append(
            f"ERR_CHR_002: 本文中のファイル名参照 {sample!r} が全角英数大文字ではありません。"
            " 参照: Ⅲ. ファイル名命名規則について（注記）"
        )
        result.valid = False

    # 予算書はフォント・サイズチェックを免除
    if is_yosan:
        result.warnings.append(
            "INFO: yosan ファイルのためフォント・サイズチェックは免除されます。"
        )
        return result

    # ── ERR_FMT_001: フォント名チェック ─────────────────────────────────────
    if all_families:
        bad_fonts = [
            f for f in all_families
            if not any(exp in f for exp in _EXPECTED_FONTS)
        ]
        if bad_fonts:
            sample = bad_fonts[0]
            result.errors.append(
                f"ERR_FMT_001: フォント {sample!r} が規定（ＭＳ Ｐゴシック）と異なります。"
                " 参照: Ⅱ-(1) 議案の記載について"
            )
            result.valid = False
    else:
        result.warnings.append(
            "WRN_FMT_001: フォント指定が検出できませんでした。"
            "インライン指定またはスタイルシートを確認してください。"
        )

    # ── ERR_FMT_002: フォントサイズチェック ─────────────────────────────────
    if all_sizes:
        bad_sizes = [
            s for s in all_sizes
            if _EXPECTED_FONTSIZE_PT not in s.lower()
            and _EXPECTED_FONTSIZE_PX not in s.lower()
            # HTMLの<font size="X">形式は「3」など数値で指定される場合があるため警告のみ
        ]
        # font size 数値指定（<font size="X">）は厳密比較せず警告に留める
        numeric_sizes = [s for s in bad_sizes if re.match(r"^\d+$", s.strip())]
        real_bad = [s for s in bad_sizes if s not in numeric_sizes]

        if real_bad:
            sample = real_bad[0]
            result.errors.append(
                f"ERR_FMT_002: フォントサイズ {sample!r} が規定（１０ｐｔ）と異なります。"
                " 参照: Ⅱ-(1) 議案の記載について"
            )
            result.valid = False
        elif numeric_sizes:
            result.warnings.append(
                f"WRN_FMT_002: フォントサイズ {numeric_sizes[0]!r} の<font>タグ指定を検出。"
                "pt 指定（10pt）への統一を推奨します。"
            )

    return result


def validate_budget_amounts(path: Path) -> CharResult:
    """
    予算書（yosan.htm）の金額欄が半角数字かチェックする
    ※ 全角数字（０-９）が混入していないかを検証
    """
    result = CharResult(filename=path.name)

    try:
        _, html_text = _read_html(path)
    except Exception as e:
        result.valid = False
        result.errors.append(f"ERR_READ: ファイル読み込み失敗: {e}")
        return result

    # <td> セルから数値らしきテキストを抽出
    cell_texts = re.findall(r"<td[^>]*>(.*?)</td>", html_text, re.DOTALL | re.IGNORECASE)
    for cell in cell_texts:
        # タグを除去してテキストのみ取得
        text = re.sub(r"<[^>]+>", "", cell).strip()
        # 全角数字を検出
        if re.search(r"[０-９]", text) and re.search(r"[０-９,，]", text):
            result.errors.append(
                f"ERR_CHR_003: 予算書の金額欄に全角数字が含まれています: {text[:30]!r}"
                " 参照: Ⅱ-(1)-① 議案の記載について"
            )
            result.valid = False
            break

    return result
