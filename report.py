"""
検証結果レポート生成モジュール
判定ステータス（PASS / WARN / FAIL）と詳細メッセージを整形して出力する
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import textwrap


@dataclass
class Report:
    zip_name: str
    naming_errors:    list[str] = field(default_factory=list)
    naming_warnings:  list[str] = field(default_factory=list)
    structure_errors: list[str] = field(default_factory=list)
    structure_warnings: list[str] = field(default_factory=list)
    character_errors: list[str] = field(default_factory=list)
    character_warnings: list[str] = field(default_factory=list)
    link_errors:      list[str] = field(default_factory=list)
    link_warnings:    list[str] = field(default_factory=list)
    security_errors:  list[str] = field(default_factory=list)
    security_warnings: list[str] = field(default_factory=list)
    encoding_warnings: list[str] = field(default_factory=list)
    suffix_warnings:  list[str] = field(default_factory=list)
    blocked: bool = False
    parsed_name: Optional[dict] = None

    @property
    def all_errors(self) -> list[str]:
        return (
            self.naming_errors
            + self.structure_errors
            + self.character_errors
            + self.link_errors
            + self.security_errors
        )

    @property
    def all_warnings(self) -> list[str]:
        return (
            self.naming_warnings
            + self.structure_warnings
            + self.character_warnings
            + self.link_warnings
            + self.security_warnings
            + self.encoding_warnings
            + self.suffix_warnings
        )

    @property
    def status(self) -> str:
        if self.blocked or self.all_errors:
            return "FAIL"
        if self.all_warnings:
            return "WARN"
        return "PASS"

    @property
    def status_label(self) -> str:
        labels = {
            "PASS": "✓ 合格 (PASS)",
            "WARN": "△ 警告 (WARN)",
            "FAIL": "✗ 不合格 (FAIL)",
        }
        return labels[self.status]


def _section(title: str, items: list[str], indent: int = 2) -> str:
    if not items:
        return ""
    pad = " " * indent
    lines = [f"  【{title}】"]
    for item in items:
        # 長い行を折り返す
        wrapped = textwrap.wrap(item, width=90, subsequent_indent=pad + "  ")
        lines.append(pad + wrapped[0])
        lines.extend(pad + "  " + w for w in wrapped[1:])
    return "\n".join(lines)


def format_report(report: Report) -> str:
    """レポートを読みやすいテキスト形式に整形して返す"""
    sep_major = "=" * 70
    sep_minor = "-" * 70

    lines: list[str] = [
        "",
        sep_major,
        f"  議案書 自動チェック結果レポート",
        sep_major,
        f"  対象ファイル : {report.zip_name}",
    ]

    # 命名規則解析結果
    if report.parsed_name:
        p = report.parsed_name
        lines += [
            f"  プロジェクト番号 : {p.get('project_no', '?')} "
            f"（{p.get('project_name', '不明')}）",
            f"  枝番 / 議事区分 : {p.get('branch', '?')} / {p.get('category', '?')}",
            f"  上程月 / 年度   : {p.get('month', '?')} / 20{p.get('year', '?')}",
            f"  議案種類       : {p.get('doc_type', '?')}",
        ]

    lines += [
        sep_minor,
        f"  判定ステータス : {report.status_label}",
        sep_minor,
    ]

    # FAIL の場合は強調
    if report.blocked:
        lines += [
            "  !! 重大エラーが検出されました。アップロードは中断されています !!",
            "",
        ]

    # エラー詳細
    categories = [
        ("命名規則",    report.naming_errors,    report.naming_warnings),
        ("ディレクトリ構造", report.structure_errors, report.structure_warnings),
        ("文字種・書式",  report.character_errors, report.character_warnings),
        ("ハイパーリンク", report.link_errors,    report.link_warnings),
        ("セキュリティ",  report.security_errors,  report.security_warnings),
        ("エンコード",   [],                      report.encoding_warnings),
        ("（案）付与",   [],                      report.suffix_warnings),
    ]

    has_detail = False
    for title, errs, warns in categories:
        block_lines = []
        err_sec  = _section("エラー",   errs)
        warn_sec = _section("警告・推奨", warns)
        if err_sec:
            block_lines.append(err_sec)
        if warn_sec:
            block_lines.append(warn_sec)

        if block_lines:
            has_detail = True
            lines.append(f"\n▼ {title}")
            lines.extend(block_lines)

    if not has_detail:
        lines.append("\n  全ての検査項目をクリアしました。")

    lines += [
        "",
        sep_major,
        f"  エラー数: {len(report.all_errors)}  /  警告数: {len(report.all_warnings)}",
        sep_major,
        "",
    ]

    return "\n".join(lines)


def print_report(report: Report) -> None:
    """レポートをコンソールに出力する"""
    print(format_report(report))
