"""
議案書自動チェックシステム - メインエントリポイント
Usage:
    python checker.py <path/to/gian.zip> [--os windows|mac] [--out report.txt]
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from report import Report, print_report, format_report
from validators.naming    import validate_name
from validators.structure import validate_structure
from validators.character import validate_html_characters, validate_budget_amounts
from validators.links     import validate_links, validate_suffix_notation
from validators.security  import validate_security
from validators.encoding  import validate_all_encodings


def run_checks(zip_path: Path, os_hint: str = "windows") -> Report:
    """ZIP ファイルに対して全バリデーションを実行し Report を返す"""

    report = Report(zip_name=zip_path.name)
    zip_stem = zip_path.stem  # 拡張子なしのファイル名

    # ── 1. 命名規則チェック ────────────────────────────────────────────────
    naming = validate_name(zip_stem)
    report.naming_errors   = naming.errors
    report.naming_warnings = naming.warnings
    report.parsed_name     = naming.parsed

    # ── 2. ZIP 展開 ────────────────────────────────────────────────────────
    tmp_dir = Path(tempfile.mkdtemp(prefix="gian_checker_"))
    try:
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # ZIP 内のファイル名エンコードを CP932 (Shift-JIS) で処理
                for zi in zf.infolist():
                    try:
                        zi.filename = zi.filename.encode("cp437").decode("cp932")
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        pass
                zf.extractall(tmp_dir)
        except zipfile.BadZipFile as e:
            report.structure_errors.append(f"ERR_ZIP_001: ZIPファイルが破損しています: {e}")
            return report

        # ── 3. ディレクトリ構造チェック ─────────────────────────────────────
        structure = validate_structure(tmp_dir, zip_stem)
        report.structure_errors   = structure.errors
        report.structure_warnings = structure.warnings

        # 以降の処理で使うフォルダ確定
        if structure.root_folder:
            folder_dir = tmp_dir / structure.root_folder
        else:
            folder_dir = tmp_dir

        gian_path = folder_dir / "gian.htm"
        # 大文字小文字を柔軟に検索
        if not gian_path.exists():
            for p in folder_dir.iterdir():
                if p.name.lower() == "gian.htm":
                    gian_path = p
                    break

        # ── 4. セキュリティチェック（最優先: ブロック時は以降をスキップ）────
        security = validate_security(folder_dir)
        report.security_errors   = security.errors
        report.security_warnings = security.warnings
        report.blocked           = security.blocked

        if report.blocked:
            # 機密情報検知時は以降の処理を中断して即返す
            return report

        # ── 5. エンコードチェック ────────────────────────────────────────────
        enc_results = validate_all_encodings(folder_dir, os_hint)
        for enc in enc_results:
            report.encoding_warnings.extend(enc.warnings)

        # ── 6. 文字種・書式チェック ─────────────────────────────────────────
        for path in sorted(folder_dir.iterdir()):
            if not path.is_file():
                continue
            if path.suffix.lower() in (".htm", ".html"):
                char_result = validate_html_characters(path)
                report.character_errors.extend(char_result.errors)
                report.character_warnings.extend(char_result.warnings)

                # 予算書（yosan.htm）の金額チェック
                if path.name.lower().startswith("yosan"):
                    budget_result = validate_budget_amounts(path)
                    report.character_errors.extend(budget_result.errors)
                    report.character_warnings.extend(budget_result.warnings)

        # ── 7. ハイパーリンクチェック ─────────────────────────────────────
        link_result = validate_links(gian_path, folder_dir)
        report.link_errors   = link_result.errors
        report.link_warnings = link_result.warnings

        # ── 8. （案）・（参考資料）付与チェック ──────────────────────────
        _, suffix_warns = validate_suffix_notation(folder_dir)
        report.suffix_warnings = suffix_warns

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="議案書作成マニュアル準拠 自動チェックシステム",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python checker.py 122-011K-0126K.zip
  python checker.py 122-011K-0126K.zip --os mac
  python checker.py 122-011K-0126K.zip --out result.txt
        """,
    )
    parser.add_argument(
        "zip_file",
        type=Path,
        help="チェック対象の ZIP ファイルパス",
    )
    parser.add_argument(
        "--os",
        choices=["windows", "mac"],
        default="windows",
        dest="os_hint",
        help="作業 OS（エンコードチェック用）。デフォルト: windows",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        dest="output",
        help="レポートをテキストファイルに出力するパス（省略時はコンソールのみ）",
    )

    args = parser.parse_args()
    zip_path: Path = args.zip_file.resolve()

    if not zip_path.exists():
        print(f"エラー: ファイルが見つかりません: {zip_path}", file=sys.stderr)
        sys.exit(1)

    if zip_path.suffix.lower() != ".zip":
        print(f"エラー: ZIP ファイルを指定してください: {zip_path}", file=sys.stderr)
        sys.exit(1)

    print(f"\n検証開始: {zip_path.name} ...")
    report = run_checks(zip_path, os_hint=args.os_hint)

    print_report(report)

    if args.output:
        report_text = format_report(report)
        args.output.write_text(report_text, encoding="utf-8")
        print(f"レポートを保存しました: {args.output}")

    # 終了コード: FAIL=1, WARN=2, PASS=0
    exit_codes = {"PASS": 0, "WARN": 2, "FAIL": 1}
    sys.exit(exit_codes.get(report.status, 1))


if __name__ == "__main__":
    main()
