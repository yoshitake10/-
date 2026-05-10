"""
仮想モード用のリアルなダミーデータ定義
実際の会社をイメージした現実的なシナリオを設定
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
TODAY = datetime.now(JST).replace(hour=0, minute=0, second=0, microsecond=0)


# ─── Google Calendar ──────────────────────────────────────────────────────────

MOCK_CALENDAR_EVENTS = [
    {
        "id": "evt001",
        "summary": "週次経営会議",
        "start": {"dateTime": (TODAY.replace(hour=9, minute=0)).isoformat()},
        "end":   {"dateTime": (TODAY.replace(hour=10, minute=30)).isoformat()},
        "attendees": [
            {"email": "ceo@company.co.jp"},
            {"email": "cfo@company.co.jp"},
            {"email": "cto@company.co.jp"},
            {"email": "cmo@company.co.jp"},
        ],
        "description": "https://docs.google.com/document/d/agenda001/edit",
        "organizer": {"email": "ceo@company.co.jp", "displayName": "田中 社長"},
    },
    {
        "id": "evt002",
        "summary": "A社 商談（新規受注5000万）",
        "start": {"dateTime": (TODAY.replace(hour=13, minute=0)).isoformat()},
        "end":   {"dateTime": (TODAY.replace(hour=14, minute=0)).isoformat()},
        "attendees": [
            {"email": "ceo@company.co.jp"},
            {"email": "sales01@company.co.jp"},
            {"email": "tanaka@a-corp.co.jp"},
        ],
        "description": "",  # ← 資料なし（アラート対象）
        "organizer": {"email": "sales01@company.co.jp", "displayName": "鈴木 営業部長"},
    },
    {
        "id": "evt003",
        "summary": "新プロダクト開発 進捗レビュー",
        "start": {"dateTime": (TODAY.replace(hour=15, minute=0)).isoformat()},
        "end":   {"dateTime": (TODAY.replace(hour=16, minute=0)).isoformat()},
        "attendees": [
            {"email": "ceo@company.co.jp"},
            {"email": "cto@company.co.jp"},
            {"email": "dev01@company.co.jp"},
            {"email": "dev02@company.co.jp"},
        ],
        "description": "",  # ← 資料なし（アラート対象）
        "organizer": {"email": "cto@company.co.jp", "displayName": "山田 CTO"},
    },
    {
        "id": "evt004",
        "summary": "採用面接（エンジニア候補）",
        "start": {"dateTime": (TODAY.replace(hour=17, minute=0)).isoformat()},
        "end":   {"dateTime": (TODAY.replace(hour=18, minute=0)).isoformat()},
        "attendees": [
            {"email": "ceo@company.co.jp"},
            {"email": "hr01@company.co.jp"},
        ],
        "description": "https://drive.google.com/file/d/resume001",
        "organizer": {"email": "hr01@company.co.jp", "displayName": "佐藤 HR"},
    },
]


# ─── Google Docs ──────────────────────────────────────────────────────────────

MOCK_STRATEGY_DOC = """
# 中期計画 2024-2026

## ミッション
テクノロジーで中小企業の業務効率を10倍にする

## 3年数値目標
- 売上: 5億円 → 15億円（3年でトリプル）
- 顧客数: 200社 → 800社
- 従業員: 30名 → 80名
- 経常利益率: 8% → 15%

## 2026年最重点戦略
1. SaaSプロダクト「TaskFlow」のARR 3億円達成
2. 大手企業パートナー経由のチャネル拡大（代理店10社）
3. エンジニア採用強化（年間10名）

## 最重要KPI（2026年Q2目標）
- MRR: 2,500万円（現状: 1,800万円）
- 解約率（チャーン）: 月次2%以下（現状: 3.2%）
- NPS: 40以上（現状: 28）
- 新規受注: 月15件（現状: 9件）
"""

MOCK_KPI_DOC = """
# KPI ダッシュボード（2026年5月 最終更新）

| KPI | 目標 | 先月実績 | 今月見込 | 状況 |
|-----|------|---------|---------|------|
| MRR | 2,500万 | 1,780万 | 1,820万 | 要注意 |
| 新規受注 | 15件 | 9件 | 10件 | 危険 |
| チャーン率 | 2.0% | 3.2% | 3.0% | 危険 |
| NPS | 40 | 28 | 30 | 要注意 |
| 採用数（累計） | 10名 | 3名 | 5名 | 要注意 |

## 特記事項
- 大手B社との代理店契約交渉が難航中（5月末期限）
- チャーンの主因: オンボーディング体制の不備（3件中2件）
- A社商談（5000万）が今月のキーアカウント
"""


# ─── 議事録 ─────────────────────────────────────────────────────────────────

MOCK_MEETING_MINUTES = [
    {
        "title": "2026年5月 週次経営会議（先週）議事録",
        "modified": (TODAY - timedelta(days=7)).isoformat(),
        "text": """
日時: 2026年5月7日 9:00〜10:30
参加者: 田中CEO、山本CFO、山田CTO、鈴木営業部長、佐藤HR

■ 議題1: 売上進捗
鈴木: 4月の新規受注は9件で目標15件を大きく下回った。
主な失注要因は価格競合（3件）とプロダクトのUI改善遅れ（2件）。
田中: 価格で負けるのは機能が十分伝わっていないからでは？
提案書の見直しをお願いしたい。期限は来週金曜。→（担当:鈴木）

■ 議題2: 開発進捗
山田: TaskFlowのv2.3リリースが2週間遅延。
原因はAPIの設計変更対応。来月15日リリース見込み。
田中: 遅延の影響で商談が取りにくくなっている。
優先度の整理が必要。来週CTO・営業部長でアラインメント会を設定してください。

■ 議題3: 採用
佐藤: エンジニア候補3名が最終面接フェーズ。うち1名は競合オファーあり。
田中: 競合オファーを受けている候補は条件見直しを検討。詳細をHRから提出してほしい。

■ 決定事項
- 提案書リニューアル（担当:鈴木、期限:5/14）
- CTOと営業部長のアラインメント会設定（担当:山田、期限:5/9）
- エンジニア採用条件の再提案（担当:佐藤、期限:5/8）

■ 次回
5月14日 同メンバー
""",
    },
    {
        "title": "TaskFlow開発 スプリントレビュー 議事録",
        "modified": (TODAY - timedelta(days=3)).isoformat(),
        "text": """
日時: 2026年5月11日 14:00〜15:00
参加者: 山田CTO、開発チーム5名

■ 完了タスク（7件）
- ダッシュボード高速化（50%改善）
- CSV出力機能
- 多言語対応（英語）

■ 未完了タスク（3件）
- OAuth連携（API設計見直し中）→ 5/22完了予定
- 通知設定UI → 5/25完了予定
- データエクスポート改善 → 未着手（優先度整理中）

■ 課題
OAuth連携の遅延がv2.3全体リリースに影響している。
認証ライブラリの選定を再検討したい。

■ アクション
- OAuth設計書を5/13までに山田がレビュー
- 優先度整理のために営業フィードバックを収集（担当:山田）

※ 来週のスプリントプランニングは5/18 10:00
""",
    },
]


# ─── Gmail ────────────────────────────────────────────────────────────────────

MOCK_EMAILS = [
    {
        "subject": "【失注報告】C社 システム導入案件",
        "sender": "suzuki@company.co.jp",
        "snippet": "C社より他社に決定した旨の連絡がありました。理由は初期費用の高さとのことです。",
        "body": (
            "田中社長\n\n"
            "先日ご商談いただいたC社（予算800万）について、"
            "本日先方より「他社製品を選定した」との連絡がありました。\n"
            "失注理由：初期費用が高い、UI学習コストが懸念。\n"
            "競合はX社製品でした。価格は当社比30%安。\n\n"
            "鈴木"
        ),
    },
    {
        "subject": "Re: 代理店契約について（B社）",
        "sender": "tanaka@b-corp.co.jp",
        "snippet": "契約条件の一部について再協議をお願いしたいと思います。特にレベニューシェアの割合について...",
        "body": (
            "田中様\n\n"
            "先日ご提示いただいた契約書を社内で検討した結果、"
            "レベニューシェア率（現在20%）を30%に変更いただければ"
            "前向きに検討できます。また、最低売上保証条項も削除をご検討いただけますか。\n\n"
            "期限は5月末を想定しています。ご判断をよろしくお願いします。\n\n"
            "B社 田中"
        ),
    },
    {
        "subject": "【緊急】本番サーバー負荷上昇のお知らせ",
        "sender": "infra@company.co.jp",
        "snippet": "本日13:00頃より本番環境のCPU負荷が85%を超えています。現在調査中です。",
        "body": (
            "本番環境CPU負荷: 87%（閾値: 80%）\n"
            "発生時刻: 13:02\n"
            "影響範囲: TaskFlow APIレスポンスタイム増加（平均2.3秒→6.1秒）\n"
            "現在対応中: インフラチーム\n"
            "次回報告: 1時間後"
        ),
    },
    {
        "subject": "5月度 顧客満足度アンケート結果",
        "sender": "cs@company.co.jp",
        "snippet": "NPS調査の結果をお送りします。今月のNPSスコアは+24でした。",
        "body": (
            "5月NPSスコア: +24（目標+40）\n"
            "回答数: 45社\n"
            "推奨者: 18社、中立: 18社、批判者: 9社\n\n"
            "批判者の主なコメント:\n"
            "・オンボーディングサポートが不足（5件）\n"
            "・UIが直感的でない（3件）\n"
            "・API連携の安定性（1件）"
        ),
    },
]


# ─── LINE WORKS メッセージ ────────────────────────────────────────────────────

MOCK_LW_CHANNELS = [
    {"channelId": "ch_sales", "name": "営業チーム"},
    {"channelId": "ch_dev",   "name": "開発チーム"},
    {"channelId": "ch_mgmt",  "name": "経営メンバー"},
]

MOCK_LW_MESSAGES = {
    "ch_sales": [
        {"userId": "u001", "userName": "鈴木（営業部長）",
         "content": {"text": "A社商談の提案書、今日中に仕上げます。CEOに確認いただけますか？"},
         "createdTime": int((TODAY - timedelta(hours=2)).timestamp() * 1000)},
        {"userId": "u002", "userName": "田中（営業）",
         "content": {"text": "X社がうちより30%安い価格で提案してきているらしい。差別化ポイントを整理したい"},
         "createdTime": int((TODAY - timedelta(hours=5)).timestamp() * 1000)},
        {"userId": "u003", "userName": "伊藤（営業）",
         "content": {"text": "D社が来月中に意思決定するとのこと。競合3社が入っているが当社が本命とのこと"},
         "createdTime": int((TODAY - timedelta(hours=8)).timestamp() * 1000)},
    ],
    "ch_dev": [
        {"userId": "u010", "userName": "山田（CTO）",
         "content": {"text": "OAuth APIの設計やり直しが必要。2週間追加でかかる見込みです"},
         "createdTime": int((TODAY - timedelta(hours=1)).timestamp() * 1000)},
        {"userId": "u011", "userName": "加藤（エンジニア）",
         "content": {"text": "本番のCPU使用率がまた上がってきた。N+1クエリが原因っぽい、今日修正します"},
         "createdTime": int((TODAY - timedelta(hours=3)).timestamp() * 1000)},
        {"userId": "u012", "userName": "中村（エンジニア）",
         "content": {"text": "アイデアなんですが、AI機能を追加したら差別化できると思う。競合もまだやってない"},
         "createdTime": int((TODAY - timedelta(hours=6)).timestamp() * 1000)},
    ],
    "ch_mgmt": [
        {"userId": "u020", "userName": "山本（CFO）",
         "content": {"text": "今月の売上見込み1820万。目標2500万に対して大幅未達。資金繰りは問題なし"},
         "createdTime": int((TODAY - timedelta(hours=4)).timestamp() * 1000)},
        {"userId": "u021", "userName": "佐藤（HR）",
         "content": {"text": "エンジニア候補の山口さん、他社からオファーが来てる。条件改善しないと逃げるかも"},
         "createdTime": int((TODAY - timedelta(hours=7)).timestamp() * 1000)},
    ],
}


# ─── サクミル ────────────────────────────────────────────────────────────────

MOCK_SAKUMIRU_PROJECTS = [
    {
        "projectId": "proj001",
        "name": "TaskFlow v2.3 開発",
        "updatedAt": (TODAY - timedelta(days=1)).isoformat(),
        "tasks": [
            {"taskId": "t001", "title": "OAuth連携実装", "assigneeName": "加藤",
             "projectName": "TaskFlow v2.3", "status": "blocked",
             "dueDate": (TODAY - timedelta(days=3)).isoformat(),
             "updatedAt": TODAY.isoformat(), "comments": [{"body": "APIの設計変更が必要"}]},
            {"taskId": "t002", "title": "通知設定UI実装", "assigneeName": "中村",
             "projectName": "TaskFlow v2.3", "status": "in_progress",
             "dueDate": (TODAY + timedelta(days=10)).isoformat(),
             "updatedAt": TODAY.isoformat(), "comments": []},
            {"taskId": "t003", "title": "データエクスポート改善", "assigneeName": "未割当",
             "projectName": "TaskFlow v2.3", "status": "todo",
             "dueDate": (TODAY - timedelta(days=1)).isoformat(),  # 期限超過
             "updatedAt": TODAY.isoformat(), "comments": []},
        ],
    },
    {
        "projectId": "proj002",
        "name": "営業プロセス改善",
        "updatedAt": (TODAY - timedelta(days=2)).isoformat(),
        "tasks": [
            {"taskId": "t010", "title": "提案書テンプレートリニューアル", "assigneeName": "鈴木",
             "projectName": "営業プロセス改善", "status": "in_progress",
             "dueDate": (TODAY + timedelta(days=3)).isoformat(),
             "updatedAt": TODAY.isoformat(), "comments": []},
            {"taskId": "t011", "title": "競合分析レポート作成", "assigneeName": "田中（営業）",
             "projectName": "営業プロセス改善", "status": "todo",
             "dueDate": (TODAY - timedelta(days=5)).isoformat(),  # 大幅期限超過
             "updatedAt": TODAY.isoformat(), "comments": [{"body": "X社の価格情報収集中"}]},
        ],
    },
    {
        "projectId": "proj003",
        "name": "採用強化2026",
        "updatedAt": TODAY.isoformat(),
        "tasks": [
            {"taskId": "t020", "title": "エンジニア採用条件見直し", "assigneeName": "佐藤（HR）",
             "projectName": "採用強化2026", "status": "in_progress",
             "dueDate": (TODAY + timedelta(days=1)).isoformat(),
             "updatedAt": TODAY.isoformat(), "comments": [{"body": "競合オファーあり、急ぎ"}]},
            {"taskId": "t021", "title": "採用説明会資料作成", "assigneeName": "佐藤（HR）",
             "projectName": "採用強化2026", "status": "done",
             "dueDate": (TODAY - timedelta(days=7)).isoformat(),
             "updatedAt": (TODAY - timedelta(days=2)).isoformat(), "comments": []},
        ],
    },
]
