"""
Claude API モック
ANTHROPIC_API_KEY なしで動作確認できる仮想レスポンスを返す
"""
from __future__ import annotations

import json
import random
from datetime import datetime


class MockClaudeClient:
    """実際のClaude APIを呼ばず、リアルな仮想レスポンスを返す"""

    def analyze(
        self,
        system_prompt: str,
        user_message: str,
        cached_context: str | None = None,
    ) -> str:
        prompt_lower = user_message.lower() + system_prompt.lower()

        if "モーニングブリーフィング" in user_message or "スケジュール" in user_message:
            return self._mock_briefing()
        if "シグナル" in user_message or "抽出" in user_message:
            return self._mock_signals()
        if "戦略" in user_message or "kpi" in prompt_lower or "アラート" in user_message:
            return self._mock_strategy()
        if "議事録" in user_message or "採点" in user_message or "スコア" in user_message:
            return self._mock_meeting_score()
        return "[MOCK Claude] 仮想レスポンス"

    def analyze_batch(self, tasks, system_prompt, cached_context=None):
        return [self.analyze(system_prompt, t["message"], cached_context) for t in tasks]

    # ─── 仮想レスポンス ───────────────────────────────────────────────────────

    def _mock_briefing(self) -> str:
        today = datetime.now().strftime("%Y年%m月%d日")
        return f"""【{today} CEO モーニングブリーフィング】

▼ 本日の最重要ミーティング

1. 【最優先】A社 商談（13:00〜14:00）
   → 5,000万円の大型案件。競合も入っている可能性あり。
   → 準備ポイント: ROI試算・導入事例3社・オンボーディング体制の説明を準備すること。
   → 資料が未登録なため、鈴木部長に確認済みDMを送信しました。

2. 週次経営会議（09:00〜10:30）
   → MRR未達（1,820万/目標2,500万）への打ち手を決定する必要あり。
   → 事前に「新規受注加速策」の腹案を3つ持って臨むこと。

3. 開発進捗レビュー（15:00〜16:00）
   → OAuth遅延によるv2.3リリース2週間延期の影響を確認。
   → 営業への影響範囲とリカバリー策をCTOに問い直すこと。

▼ 本日の優先度と時間配分
- 09:00〜10:30: 経営会議（MRR対策の意思決定に集中）
- 11:00〜12:00: A社商談の個人準備（提案書最終確認）
- 13:00〜14:00: A社商談（クロージングを目指す）
- 14:00〜15:00: B社代理店交渉の回答方針を固める
- 15:00〜16:00: 開発レビュー
- 17:00〜18:00: 採用面接

▼ 本日CEOが事前決断すべき事項
□ B社代理店交渉: レベニューシェア30%要求をどこまで受け入れるか
□ エンジニア採用: 山口候補に競合オファー対抗できる条件上限を決める
□ MRR未達対策: 既存顧客のアップセル vs 新規獲得、どちらに舵を切るか

▼ 本日のリスク
⚠ 本番サーバー負荷上昇中（87%）→ A社商談中のデモ環境に影響する可能性あり。インフラチームの状況確認を。"""

    def _mock_signals(self) -> str:
        return json.dumps({
            "signals": [
                {
                    "category": "リスク",
                    "content": "競合X社が当社比30%安で提案、失注リスク増大",
                    "importance": 5,
                    "source": "営業チーム LINE WORKS",
                    "recommended_action": "価格戦略の緊急見直し、または差別化提案の強化"
                },
                {
                    "category": "意思決定",
                    "content": "B社代理店交渉でレベニューシェア30%要求、5月末期限",
                    "importance": 5,
                    "source": "Gmail（B社田中氏）",
                    "recommended_action": "本日中に経営判断・回答を確定させる"
                },
                {
                    "category": "リスク",
                    "content": "エンジニア採用候補が競合オファー受領、逸失リスク高",
                    "importance": 4,
                    "source": "HR LINE WORKS",
                    "recommended_action": "採用条件の上限を本日決定してHRに通達"
                },
                {
                    "category": "気づき",
                    "content": "本番CPU87%超過、A社商談デモ環境に影響の可能性",
                    "importance": 4,
                    "source": "インフラチームメール",
                    "recommended_action": "商談前にインフラチームの復旧状況を確認"
                },
                {
                    "category": "アイデア",
                    "content": "AI機能追加で競合との差別化が可能（競合未着手）",
                    "importance": 3,
                    "source": "開発チーム LINE WORKS",
                    "recommended_action": "次のロードマップ会議でAI機能をアジェンダに追加"
                },
                {
                    "category": "学び",
                    "content": "失注理由トップ2: 価格（3件）・UI改善遅れ（2件）",
                    "importance": 3,
                    "source": "営業週次報告",
                    "recommended_action": "提案書改訂時にUI改善ロードマップを明示する"
                },
                {
                    "category": "リスク",
                    "content": "チャーン率3.2%、目標2%を1.2pt超過（オンボーディング不備が主因）",
                    "importance": 4,
                    "source": "KPI文書",
                    "recommended_action": "CSチームとオンボーディング改善を来週アジェンダに"
                },
            ]
        }, ensure_ascii=False)

    def _mock_strategy(self) -> str:
        return json.dumps({
            "alerts": [
                {
                    "level": "S",
                    "title": "新規受注が目標の67%に留まり、MRR目標達成が危機的状況",
                    "description": "月次新規受注9件（目標15件）、MRR1,820万（目標2,500万）。このまま推移すると期末目標の達成は不可能。",
                    "impact_score": 0.92,
                    "affected_kpi": "MRR / 新規受注件数",
                    "recommended_action": "本日の経営会議でMRR加速策を意思決定。既存顧客アップセルと新規獲得の優先度を確定する。",
                    "evidence": "KPI文書: MRR 1,820万/目標2,500万、新規受注 9件/目標15件"
                },
                {
                    "level": "A",
                    "title": "チャーン率3.2%が目標2%を大幅超過",
                    "description": "チャーンの主因はオンボーディング不備（3件中2件）。解約が増えると既存売上基盤が崩れる。",
                    "impact_score": 0.78,
                    "affected_kpi": "チャーン率 / MRR",
                    "recommended_action": "CSチームにオンボーディング改善タスクを最優先で割り当て。今週中に改善計画を提出させる。",
                    "evidence": "CSレポート: NPS 24（目標40）、批判者コメント上位はオンボーディング"
                },
                {
                    "level": "A",
                    "title": "B社代理店交渉が今月末で期限切れ、失注なら戦略的損失大",
                    "description": "B社はチャネル拡大戦略の重要パートナー候補。条件不一致で破談になれば代替確保が困難。",
                    "impact_score": 0.75,
                    "affected_kpi": "代理店チャネル数 / 間接売上",
                    "recommended_action": "レベニューシェア25%（中間案）での再提案を検討。本日中に意思決定。",
                    "evidence": "Gmail: B社田中氏よりRS30%要求・5月末期限"
                },
                {
                    "level": "B",
                    "title": "TaskFlow v2.3リリースが2週間遅延、商談機会損失の恐れ",
                    "description": "OAuth連携の設計変更によりリリース遅延。機能訴求できない商談が積み上がっている。",
                    "impact_score": 0.55,
                    "affected_kpi": "新規受注 / 顧客満足度",
                    "recommended_action": "CTO・営業部長のアラインメント会を今週実施し、代替のセールストークを準備する。",
                    "evidence": "開発議事録: OAuth遅延、v2.3リリース延期"
                },
                {
                    "level": "C",
                    "title": "競合X社が低価格戦略で市場浸食の可能性",
                    "description": "営業から複数の価格競合報告。X社は当社比30%安で提案している模様。",
                    "impact_score": 0.35,
                    "affected_kpi": "新規受注",
                    "recommended_action": "来月の戦略会議で競合分析を実施。当面は価値提案の強化で対応。",
                    "evidence": "営業チームLINE WORKSメッセージ"
                },
            ],
            "kpi_status": {
                "MRR": {"current": "1,820万円", "target": "2,500万円", "status": "off_track"},
                "新規受注": {"current": "9件/月", "target": "15件/月", "status": "off_track"},
                "チャーン率": {"current": "3.2%", "target": "2.0%以下", "status": "off_track"},
                "NPS": {"current": "24", "target": "40以上", "status": "at_risk"},
                "採用数": {"current": "3名", "target": "10名/年", "status": "at_risk"},
            }
        }, ensure_ascii=False)

    def _mock_meeting_score(self) -> str:
        score = random.randint(52, 78)
        return json.dumps({
            "score": score,
            "breakdown": {
                "目的明確性": {"score": int(score * 0.18), "comment": "会議の目的は冒頭に述べられたが、ゴールが曖昧なまま議論が進んだ"},
                "意思決定": {"score": int(score * 0.22), "comment": "いくつかの決定がなされたが、根拠が弱く覆る可能性がある"},
                "アクションアイテム": {"score": int(score * 0.20), "comment": "担当者は明確。ただし期限が「来週」と曖昧なものが複数"},
                "参加者貢献": {"score": int(score * 0.15), "comment": "CTOの発言が多く、他メンバーの意見が引き出せていない"},
                "時間効率": {"score": int(score * 0.13), "comment": "予定の10分オーバー。採用議題が予想より長引いた"},
                "次回への連続性": {"score": int(score * 0.12), "comment": "次回アジェンダが未設定。参加者が何を準備すべきか不明確"},
            },
            "strengths": [
                "売上数字を具体的な根拠とともに共有できている",
                "失注分析が詳細で再現性のある振り返りができている",
            ],
            "improvements": [
                "会議冒頭30秒でゴールを宣言する（例:「本日は価格戦略について3つの選択肢から決定する」）",
                "アクションアイテムの期限を「来週」ではなく「◯月◯日」と明示する",
                "発言の少ないメンバーに意図的に意見を求める（「CFOはどう思いますか？」）",
            ],
            "action_items": [
                {"what": "提案書テンプレートリニューアル", "who": "鈴木営業部長", "when": "5月14日"},
                {"what": "CTOと営業部長のアラインメント会設定", "who": "山田CTO", "when": "5月9日"},
                {"what": "エンジニア採用条件の再提案", "who": "佐藤HR", "when": "5月8日"},
            ],
            "ceo_coaching": (
                "中期計画でMRR3倍を掲げているにもかかわらず、会議では数値未達の「報告」に終始しています。"
                "次回からは必ず「どうすれば目標を達成できるか」の仮説を参加者に事前提出させ、"
                "会議を『選択肢を選ぶ場』に変えてください。"
                "意思決定の質がMRR達成に直結します。"
            ),
        }, ensure_ascii=False)
