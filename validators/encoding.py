"""
エンコードバリデーター
マニュアルⅣ-Ⅲ章に基づき OS 環境とエンコードの整合性を検証する
"""
from __future__ import annotations

import codecs
from dataclasses import dataclass, field
from pathlib import Path


# チェック対象拡張子
_TARGET_EXTENSIONS = {".htm", ".html", ".txt", ".csv"}

# Shift-JIS / CP932 の codecs 名称
_SJIS_NAMES = {"shift_jis", "shift-jis", "sjis", "s_jis", "cp932", "ms932"}
_UTF8_NAMES = {"utf-8", "utf8", "utf_8"}

# BOM 定義
_BOM_UTF8    = b"\xef\xbb\xbf"
_BOM_UTF16LE = b"\xff\xfe"
_BOM_UTF16BE = b"\xfe\xff"


@dataclass
class EncodingResult:
    filename: str
    detected_encoding: str = "unknown"
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _detect_encoding_by_bom(raw: bytes) -> str | None:
    """BOM からエンコードを判定する"""
    if raw.startswith(_BOM_UTF8):
        return "utf-8-sig"
    if raw.startswith(_BOM_UTF16LE):
        return "utf-16-le"
    if raw.startswith(_BOM_UTF16BE):
        return "utf-16-be"
    return None


def _detect_encoding_by_heuristic(raw: bytes) -> str:
    """
    バイト列から Shift-JIS / UTF-8 を簡易判定する。
    chardet が利用可能な場合はそちらを優先する。
    """
    # chardet を試みる
    try:
        import chardet  # type: ignore
        result = chardet.detect(raw)
        enc = (result.get("encoding") or "").lower().replace("-", "_")
        if enc:
            return enc
    except ImportError:
        pass

    # 手動ヒューリスティック
    # UTF-8 チェック
    try:
        raw.decode("utf-8")
        # ASCII の場合は区別がつかないため、日本語バイトが含まれているか確認
        if any(b > 0x7F for b in raw):
            return "utf-8"
        return "ascii"
    except UnicodeDecodeError:
        pass

    # Shift-JIS チェック
    try:
        raw.decode("shift_jis")
        return "shift_jis"
    except UnicodeDecodeError:
        pass

    return "unknown"


def _normalize_encoding_name(enc: str) -> str:
    """エンコード名を正規化する"""
    return enc.lower().replace("-", "_").replace(" ", "_")


def validate_encoding(path: Path, os_hint: str = "windows") -> EncodingResult:
    """
    path:    検証するファイルのパス
    os_hint: 作業 OS の推定（"windows" or "mac"）
    """
    result = EncodingResult(filename=path.name)

    try:
        raw = path.read_bytes()
    except Exception as e:
        result.valid = False
        result.errors.append(f"ERR_READ: ファイル読み込み失敗: {e}")
        return result

    # BOM による判定を優先
    bom_enc = _detect_encoding_by_bom(raw)
    if bom_enc:
        detected = bom_enc
    else:
        detected = _detect_encoding_by_heuristic(raw)

    result.detected_encoding = detected
    norm = _normalize_encoding_name(detected)

    # ── OS 別の期待エンコード照合 ──────────────────────────────────────────
    if os_hint == "windows":
        expected_label = "Shift-JIS (CP932)"
        is_valid_enc = norm in _SJIS_NAMES or norm == "ascii"
    else:  # mac / linux
        expected_label = "UTF-8"
        is_valid_enc = norm in _UTF8_NAMES or norm == "utf_8_sig" or norm == "ascii"

    if not is_valid_enc:
        result.warnings.append(
            f"WRN_ENC_001: {path.name!r} のエンコード（{detected}）が"
            f"OS環境（{os_hint}）の期待値（{expected_label}）と一致しません。"
            "アジェンダシステムで文字化けが発生する恐れがあります。"
            " 参照: Ⅳ-Ⅲ. データの保存"
        )

    return result


def validate_all_encodings(folder_dir: Path, os_hint: str = "windows") -> list[EncodingResult]:
    """フォルダ内の対象ファイル全件のエンコードを検証する"""
    results: list[EncodingResult] = []

    for path in sorted(folder_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in _TARGET_EXTENSIONS:
            results.append(validate_encoding(path, os_hint))

    return results
