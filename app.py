"""
議案書自動チェックシステム - Streamlit Web UI
"""
from __future__ import annotations

import hmac
import sys
import tempfile
from pathlib import Path

import streamlit as st

# パッケージパスを追加
sys.path.insert(0, str(Path(__file__).parent))

from checker import run_checks
from report import Report, format_report

# ── ページ設定 ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="議案書チェッカー | 尾道JC",
    page_icon="📋",
    layout="centered",
)


# ── パスワード保護 ──────────────────────────────────────────────────────────
def _check_password() -> bool:
    """secrets.toml にパスワードが設定されている場合のみ認証を要求する"""
    try:
        expected = st.secrets["password"]
    except (KeyError, FileNotFoundError):
        # secrets未設定 = ローカル開発モード（認証スキップ）
        return True

    def _on_submit():
        entered = st.session_state.get("pw_input", "")
        if hmac.compare_digest(entered, expected):
            st.session_state["auth_ok"] = True
        else:
            st.session_state["auth_ok"] = False
            st.session_state["auth_failed"] = True

    if st.session_state.get("auth_ok"):
        return True

    st.title("📋 議案書 自動チェックシステム")
    st.caption("一般社団法人 尾道青年会議所")
    st.markdown("---")
    st.subheader("🔐 ログイン")
    st.text_input(
        "パスワードを入力してください",
        type="password",
        key="pw_input",
        on_change=_on_submit,
    )
    if st.session_state.get("auth_failed"):
        st.error("パスワードが正しくありません。")
    st.caption("パスワードは担当者にお問い合わせください。")
    return False


if not _check_password():
    st.stop()

# ── カスタムCSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ステータスバッジ */
.badge-pass {
    background: #d4edda; color: #155724;
    padding: 8px 20px; border-radius: 8px;
    font-size: 1.3rem; font-weight: bold;
    border-left: 6px solid #28a745;
    display: inline-block; margin: 8px 0;
}
.badge-warn {
    background: #fff3cd; color: #856404;
    padding: 8px 20px; border-radius: 8px;
    font-size: 1.3rem; font-weight: bold;
    border-left: 6px solid #ffc107;
    display: inline-block; margin: 8px 0;
}
.badge-fail {
    background: #f8d7da; color: #721c24;
    padding: 8px 20px; border-radius: 8px;
    font-size: 1.3rem; font-weight: bold;
    border-left: 6px solid #dc3545;
    display: inline-block; margin: 8px 0;
}
/* エラー行 */
.err-item {
    background: #fff5f5; border-left: 4px solid #dc3545;
    padding: 6px 12px; margin: 4px 0;
    border-radius: 0 4px 4px 0; font-size: 0.88rem;
    font-family: monospace; word-break: break-all;
}
/* 警告行 */
.warn-item {
    background: #fffdf0; border-left: 4px solid #ffc107;
    padding: 6px 12px; margin: 4px 0;
    border-radius: 0 4px 4px 0; font-size: 0.88rem;
    font-family: monospace; word-break: break-all;
}
/* メタ情報ボックス */
.meta-box {
    background: #f0f4ff; border: 1px solid #c8d8ff;
    border-radius: 8px; padding: 14px 18px; margin: 12px 0;
    font-size: 0.92rem;
}
.meta-box table { width: 100%; border-collapse: collapse; }
.meta-box td { padding: 3px 8px; }
.meta-box td:first-child { font-weight: bold; color: #555; width: 140px; }
/* blocked バナー */
.blocked-banner {
    background: #dc3545; color: white;
    padding: 14px 18px; border-radius: 8px;
    font-weight: bold; font-size: 1.05rem; margin: 12px 0;
}
</style>
""", unsafe_allow_html=True)


# ── ヘッダー ────────────────────────────────────────────────────────────────
st.title("📋 議案書 自動チェックシステム")
st.caption("一般社団法人 尾道青年会議所 ｜ 議案書作成マニュアル2026年度版 準拠")
st.markdown("---")


# ── サイドバー: 設定 ────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 設定")
    os_hint = st.radio(
        "作業OS（エンコードチェック用）",
        options=["windows", "mac"],
        format_func=lambda x: "Windows" if x == "windows" else "Mac",
        index=0,
    )
    st.markdown("---")
    st.markdown("""
**チェック項目一覧**
- ✅ ファイル命名規則
- ✅ ディレクトリ構造
- ✅ 文字種・フォント
- ✅ ハイパーリンク有効性
- ✅ マイナンバー検知
- ✅ エンコード整合性
- ✅ （案）付与確認
""")
    st.markdown("---")
    st.caption(
        "🔒 アップロードされたファイルはチェック処理後に自動削除されます。"
        "外部に保存・送信されることはありません。"
    )


# ── ファイルアップロード ────────────────────────────────────────────────────
st.subheader("① ZIPファイルをアップロード")
st.markdown(
    "議案フォルダを ZIP に圧縮したファイルを選択してください。\n\n"
    "例: `122-011K-0126K.zip`"
)

uploaded = st.file_uploader(
    "ZIPファイルを選択",
    type=["zip"],
    label_visibility="collapsed",
)

if uploaded is None:
    st.info("👆 ZIPファイルをアップロードしてチェックを開始してください。")
    st.stop()


# ── チェック実行 ────────────────────────────────────────────────────────────
st.subheader("② チェック結果")

with st.spinner("検証中..."):
    # 一時ファイルに保存してから run_checks へ渡す
    with tempfile.NamedTemporaryFile(
        suffix=".zip", delete=False, prefix="gian_upload_"
    ) as tmp:
        tmp.write(uploaded.read())
        tmp_path = Path(tmp.name)

    try:
        # ファイル名を元のアップロード名で上書き（命名規則チェックに使用）
        named_path = tmp_path.parent / uploaded.name
        tmp_path.rename(named_path)
        report: Report = run_checks(named_path, os_hint=os_hint)
    finally:
        # 一時ファイルを削除
        try:
            named_path.unlink(missing_ok=True)
        except Exception:
            tmp_path.unlink(missing_ok=True)


# ── ステータスバッジ ────────────────────────────────────────────────────────
badge_map = {
    "PASS": ('<div class="badge-pass">✓ 合格（PASS）</div>', st.success),
    "WARN": ('<div class="badge-warn">△ 警告（WARN）</div>', st.warning),
    "FAIL": ('<div class="badge-fail">✗ 不合格（FAIL）</div>', st.error),
}
badge_html, _ = badge_map[report.status]
st.markdown(badge_html, unsafe_allow_html=True)

# マイナンバー検知時の強調バナー
if report.blocked:
    st.markdown(
        '<div class="blocked-banner">🚨 重大エラー: マイナンバー関連書類の混入を検知しました。'
        'アップロードは中断されています。直ちに該当ファイルを除去してください。</div>',
        unsafe_allow_html=True,
    )


# ── 解析情報 ────────────────────────────────────────────────────────────────
if report.parsed_name:
    p = report.parsed_name
    st.markdown(f"""
<div class="meta-box">
<table>
<tr><td>ファイル名</td><td>{report.zip_name}</td></tr>
<tr><td>プロジェクト番号</td><td>{p.get('project_no','?')} &nbsp;–&nbsp; {p.get('project_name','不明')}</td></tr>
<tr><td>枝番 / 議事区分</td><td>{p.get('branch','?')} / {p.get('category','?')}</td></tr>
<tr><td>上程月 / 年度</td><td>{p.get('month','?')} 月 &nbsp;/&nbsp; 20{p.get('year','?')} 年度</td></tr>
<tr><td>議案種類</td><td>{p.get('doc_type','?')}</td></tr>
</table>
</div>
""", unsafe_allow_html=True)


# ── エラー数サマリー ────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
col1.metric("エラー数", len(report.all_errors), delta=None)
col2.metric("警告数",   len(report.all_warnings), delta=None)

st.markdown("---")


# ── カテゴリ別詳細 ──────────────────────────────────────────────────────────
def render_issues(errors: list[str], warnings: list[str]) -> None:
    for e in errors:
        st.markdown(f'<div class="err-item">🔴 {e}</div>', unsafe_allow_html=True)
    for w in warnings:
        st.markdown(f'<div class="warn-item">🟡 {w}</div>', unsafe_allow_html=True)


categories = [
    ("🏷️ 命名規則",       report.naming_errors,    report.naming_warnings),
    ("📁 ディレクトリ構造", report.structure_errors, report.structure_warnings),
    ("🔤 文字種・書式",    report.character_errors, report.character_warnings),
    ("🔗 ハイパーリンク",  report.link_errors,      report.link_warnings),
    ("🔒 セキュリティ",    report.security_errors,  report.security_warnings),
    ("💾 エンコード",      [],                      report.encoding_warnings),
    ("📎 （案）付与",      [],                      report.suffix_warnings),
]

has_any = False
for title, errs, warns in categories:
    if not errs and not warns:
        continue
    has_any = True
    total = len(errs) + len(warns)
    label = f"{title} （{total}件）"
    # エラーがあれば展開した状態で表示
    with st.expander(label, expanded=bool(errs)):
        render_issues(errs, warns)

if not has_any:
    st.success("🎉 全ての検査項目をクリアしました！そのままアップロードできます。")


# ── レポートダウンロード ────────────────────────────────────────────────────
st.markdown("---")
st.subheader("③ レポートのダウンロード")

report_text = format_report(report)
st.download_button(
    label="📥 テキストレポートをダウンロード",
    data=report_text.encode("utf-8"),
    file_name=f"check_{report.zip_name.replace('.zip','')}.txt",
    mime="text/plain",
)

# テキストプレビュー
with st.expander("レポート全文を表示"):
    st.code(report_text, language=None)
