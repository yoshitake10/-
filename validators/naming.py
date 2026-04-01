"""
命名規則バリデーター
マニュアルⅢ章・Ⅳ章に基づき ZIPファイル・フォルダ名を検証する
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# ── マスターデータ: プロジェクト番号対応表 ──────────────────────────────────
PROJECT_MASTER: dict[str, str] = {
    "01": "（確認・報告関連）",
    "02": "（協議・審議関連）",
    "03": "１１月例会行事",
    "04": "会員拡大の調査・研究・実践",
    "05": "新入会員ガイダンス",
    "06": "仮入会員ガイダンス",
    "07": "新入会員ガイダンス",
    "08": "その他、尾道青年会議所における目的達成のための事業の実施",
    "11": "まちの未来創造事業の調査・研究・実践",
    "12": "家族会",
    "13": "６月例会行事",
    "14": "１０月例会行事",
    "15": "その他、尾道青年会議所における目的達成のための事業の実施",
    "21": "災害に強いまちづくり事業の調査・研究・実践",
    "22": "２月例会行事",
    "23": "９月例会行事",
    "24": "クリスマス会",
    "25": "尾道の伝統文化の調査・研究・実践",
    "26": "その他、尾道青年会議所における目的達成のための事業の実施",
    "31": "ブロック野球大会の企画・運営",
    "32": "地域と灯す繋がりの燈火創造事業の調査・研究・実践",
    "33": "３月例会行事",
    "34": "７月会員交流例会行事",
    "35": "しまなみ３JCへの参画",
    "36": "その他、尾道青年会議所における目的達成のための事業の実施",
    "41": "例会・総会の設営及び運営",
    "42": "全般的な庶務の遂行",
    "43": "地域に根付く組織づくり事業の調査・研究・実践",
    "44": "１月例会行事",
    "45": "５月例会行事",
    "46": "卒業例会",
    "47": "活動記録の整理・保存及び広報活動の実踐",
    "48": "その他、尾道青年会議所における目的達成のための事業の実施",
    "51": "まちの燈となる人財育成事業の調査・研究・実践",
    "52": "新年宴会",
    "53": "４月例会行事",
    "54": "夏期講習",
    "55": "新理事研修",
    "56": "その他、尾道青年会議所における目的達成のための事業の実施",
}

VALID_YEARS = {"26", "25"}

# メインパターン: 122-{proj2}{branch1}{cat1}-{month2}{year2}{type1}
_NAMING_RE = re.compile(
    r"^122-(?P<proj>\d{2})(?P<branch>\d)(?P<cat>[KSCFH])-(?P<month>0[1-9]|1[0-2])(?P<year>\d{2})(?P<dtype>[KSH])$"
)

# ファイル名は半角英数大文字のみ許可（拡張子なしで検証）
_HALFWIDTH_UPPER_ALNUM = re.compile(r"^[A-Z0-9\-]+$")


@dataclass
class NamingResult:
    name: str
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    parsed: Optional[dict] = None


def validate_name(name: str) -> NamingResult:
    """ZIPファイル名またはルートフォルダ名（拡張子なし）を検証する"""
    result = NamingResult(name=name, valid=True)

    # 半角英数大文字チェック
    if not _HALFWIDTH_UPPER_ALNUM.match(name):
        result.valid = False
        result.errors.append(
            "ERR_NAME_001: ファイル命名規則が正しくありません。"
            "半角英数大文字（A-Z, 0-9, ハイフン）で入力してください。"
            f" 実際の値: {name!r}"
        )
        return result

    # 正規表現パターンマッチ
    m = _NAMING_RE.match(name)
    if not m:
        result.valid = False
        result.errors.append(
            "ERR_NAME_001: 命名規則パターン（122-PPBNCC-MMYYTT）に一致しません。"
            f" 実際の値: {name!r}"
        )
        return result

    proj   = m.group("proj")
    branch = m.group("branch")
    cat    = m.group("cat")
    month  = m.group("month")
    year   = m.group("year")
    dtype  = m.group("dtype")

    result.parsed = {
        "project_no": proj,
        "branch": branch,
        "category": cat,
        "month": month,
        "year": year,
        "doc_type": dtype,
    }

    # プロジェクト番号の存在確認
    if proj not in PROJECT_MASTER:
        result.valid = False
        result.errors.append(
            f"ERR_NAME_002: プロジェクト番号 {proj!r} はマスターデータに存在しません。"
        )
    else:
        result.parsed["project_name"] = PROJECT_MASTER[proj]

    # 年度チェック
    if year not in VALID_YEARS:
        result.valid = False
        result.errors.append(
            f"ERR_NAME_003: 年度 {year!r} は有効範囲外です。"
            f"使用可能な値: {sorted(VALID_YEARS)}"
        )

    return result
