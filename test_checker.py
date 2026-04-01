"""
単体テスト / 動作確認スクリプト
pytest または python test_checker.py で実行可能
"""
from __future__ import annotations

import io
import os
import sys
import zipfile
import tempfile
from pathlib import Path

# パッケージルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from validators.naming    import validate_name
from validators.structure import validate_structure
from validators.security  import validate_security
from validators.encoding  import validate_encoding
from validators.links     import validate_links
from report import Report, format_report


# ────────────────────────────────────────────────────────────────
# 命名規則テスト
# ────────────────────────────────────────────────────────────────

def test_valid_names():
    valid_cases = [
        "122-011K-0126K",   # 事務局01, 枝番1, K区分, 1月, 26年度, K種
        "122-111K-0625K",   # 未来創造委員会11, 6月, 25年度
        "122-511K-0426S",   # 会員能力向上51, 4月, S種
        "122-021F-0226H",   # 社会開発21, F区分, H種
    ]
    for name in valid_cases:
        result = validate_name(name)
        assert result.valid, f"FAIL (expected valid): {name} → {result.errors}"
        print(f"  OK: {name} → proj={result.parsed.get('project_name','?')[:15]}")


def test_invalid_names():
    invalid_cases = [
        ("122-001K-0126K",  "存在しないプロジェクト番号 00"),
        ("122-011K-0027K",  "年度 27 は無効"),
        ("122-011K-1326K",  "月 13 は無効"),
        ("122-011K-0126X",  "議案種類 X は無効"),
        ("122-011Z-0126K",  "議事区分 Z は無効"),
        ("122-99-0126K",    "形式不正（枝番なし）"),
        ("１２２-011K-0126K", "全角文字混入"),
    ]
    for name, reason in invalid_cases:
        result = validate_name(name)
        assert not result.valid, f"FAIL (expected invalid): {name} ({reason})"
        print(f"  OK: {name!r} → エラー検出（{reason}）")


# ────────────────────────────────────────────────────────────────
# セキュリティテスト
# ────────────────────────────────────────────────────────────────

def test_security_block():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        # マイナンバーキーワードを含むファイルを作成
        (d / "マイナンバー届.htm").write_bytes(b"")
        result = validate_security(d)
        assert result.blocked, "マイナンバー含むファイルでブロックされるべき"
        print(f"  OK: マイナンバーファイル検知 → BLOCKED")


def test_security_clean():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "gian.htm").write_bytes(b"<html><body>test</body></html>")
        result = validate_security(d)
        assert not result.blocked, "クリーンなファイルはブロックされないはず"
        print(f"  OK: クリーンファイル → NOT BLOCKED")


def test_security_content_scan():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        # 内容にマイナンバーキーワードを含む
        content = "この書類には通知カードのコピーが含まれています。".encode("shift_jis")
        (d / "document.htm").write_bytes(content)
        result = validate_security(d)
        assert result.blocked, "内容にキーワード含む場合もブロックされるべき"
        print(f"  OK: 内容中のキーワード検知 → BLOCKED")


# ────────────────────────────────────────────────────────────────
# ディレクトリ構造テスト
# ────────────────────────────────────────────────────────────────

def test_structure_valid():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        folder = d / "122-011K-0126K"
        folder.mkdir()
        (folder / "gian.htm").write_bytes(b"<html></html>")
        result = validate_structure(d, "122-011K-0126K")
        assert result.has_gian
        assert result.valid
        print(f"  OK: 正常構造 → 有効")


def test_structure_missing_gian():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        folder = d / "122-011K-0126K"
        folder.mkdir()
        (folder / "other.htm").write_bytes(b"")
        result = validate_structure(d, "122-011K-0126K")
        assert not result.valid
        assert not result.has_gian
        print(f"  OK: gian.htm 欠落 → エラー検出")


# ────────────────────────────────────────────────────────────────
# リンクテスト
# ────────────────────────────────────────────────────────────────

def test_links_valid():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "annex.pdf").write_bytes(b"%PDF")
        gian = d / "gian.htm"
        gian.write_bytes(
            '<html><body><a href="annex.pdf">添付</a></body></html>'.encode("utf-8")
        )
        result = validate_links(gian, d)
        assert result.valid, f"リンク有効のはず: {result.errors}"
        print(f"  OK: 有効リンク → エラーなし")


def test_links_broken():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        gian = d / "gian.htm"
        gian.write_bytes(
            '<html><body><a href="missing.pdf">資料</a></body></html>'.encode("utf-8")
        )
        result = validate_links(gian, d)
        assert not result.valid
        assert "missing.pdf" in result.broken_links
        print(f"  OK: リンク切れ → エラー検出")


# ────────────────────────────────────────────────────────────────
# レポート出力テスト
# ────────────────────────────────────────────────────────────────

def test_report_pass():
    r = Report(zip_name="122-011K-0126K.zip", parsed_name={
        "project_no": "01", "project_name": "（確認・報告関連）",
        "branch": "1", "category": "K", "month": "01", "year": "26", "doc_type": "K"
    })
    text = format_report(r)
    assert "PASS" in text
    print(f"  OK: PASS レポート生成")


def test_report_fail():
    r = Report(zip_name="bad.zip")
    r.naming_errors = ["ERR_NAME_001: テストエラー"]
    text = format_report(r)
    assert "FAIL" in text
    print(f"  OK: FAIL レポート生成")


# ────────────────────────────────────────────────────────────────
# メイン
# ────────────────────────────────────────────────────────────────

def run_all_tests():
    test_groups = [
        ("命名規則 - 有効ケース",      test_valid_names),
        ("命名規則 - 無効ケース",      test_invalid_names),
        ("セキュリティ - ブロック",    test_security_block),
        ("セキュリティ - クリーン",    test_security_clean),
        ("セキュリティ - 内容スキャン", test_security_content_scan),
        ("構造 - 正常",               test_structure_valid),
        ("構造 - gian.htm欠落",       test_structure_missing_gian),
        ("リンク - 有効",              test_links_valid),
        ("リンク - リンク切れ",        test_links_broken),
        ("レポート - PASS",            test_report_pass),
        ("レポート - FAIL",            test_report_fail),
    ]

    passed = 0
    failed = 0

    for name, fn in test_groups:
        print(f"\n[{name}]")
        try:
            fn()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"結果: {passed} 件合格 / {failed} 件失敗")
    print(f"{'='*50}")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
