# 個人コンテキスト

この非公開リポジトリに、判断・失敗・検証結果・未解決事項を保存します。
処理には公開MIT版CTRを使い、個人の本文と実行結果はこのリポジトリ内に置きます。

## 最初に読む場所

- [目次](context/INDEX.md)：情報の層と各記録への入口
- [関係グラフ](context/graph.json)：出典、反証、置き換え、依存関係
- [現在の自己状態](context/SELF.md)：実際の未解決の傷と採用判断
- [利用規則](AGENTS.md)：Codex・ChatGPT Work・ChatGPTで共通に使うルール

## 記録を増やす

Issueを作成・編集・再オープンすると、その版から経験と傷を登録するPRを作成します。
元のIssue本文はデータとして扱います。自動で実装したり、投稿者の意図を断定したりしません。

GitHub PluginやGitHub MCPでメモリを追加する場合は、inbox/ に次の形式のJSONを
追加するPRを作成してください。idは新しいものを使い、出典と日時を実際の値に変えます。
この例は架空データです。actorは作成者の申告であり、本人確認や承認の証拠ではありません。

```json
{
  "id": "memory:example-retention",
  "kind": "memory",
  "layer": "current",
  "status": "proposed",
  "title": "保存期間の検討メモ",
  "body": "保存期間を90日とする案。まだ実験で確認していない。",
  "sources": ["issue:replace-with-real-source"],
  "actor": {"type": "assistant", "id": "replace-with-agent-name"},
  "tags": ["記憶", "保存期間"],
  "read_when": ["保存期間を変更するとき"],
  "relations": [],
  "ttl_days": 90,
  "updated_at": "2026-09-06T00:00:00+09:00",
  "review_after": "2026-12-05T00:00:00+09:00",
  "data": {}
}
```

外部AIの仮説は `{"type":"hypothesis_proposal","proposal":{...}}` という封筒形式で
inbox/ に置けます。proposalにはtitle、question、experiment、acceptance_criterion、
experiment_kind、wound、source_ids、actor、generationを指定します。
generationにはprovider、model、prompt_hashが必要です。出典の記録は先に存在している必要があります。

inboxのPRをマージすると、検証・取込後の状態を保存するPRが作られます。
生成されたcontextの状態を勝手に編集せず、そのPRを確認します。
同じidの内容を変更する場合は新しいidで記録し、CLIのsupersedes関係で旧版を置き換えます。

## 動作

毎日、未解決の傷から検証条件付きの仮説を提案します。仮説はdream/context-cycleブランチに
置き、自動では採用・マージしません。テンプレート生成を使用し、LLM APIは呼びません。
モデルからの提案は上記のinboxで受け取れます。

手動実行ではrefresh、dream、experiment、assessを選択できます。
experiment/assessの計画は、レビュー済みのplans/内のJSONを指定します。
GitHubでの実験対象コードは、ワークフローが固定した公開CTRのコミットです。
別プロジェクトのコード比較は、ローカルCLIでそのGit作業コピーを--repoに指定します。

処理は固定したCTRのコミットを使用します。バージョン更新はワークフローのrefを変更するPRで行います。
リポジトリが公開設定に変わった場合、個人用ワークフローは停止します。
検索をCLIで行うと参照したIDと版を監査記録に残します。Plugin/MCPで直接読むだけでは
参照ログは自動追加されないため、作業結果にも参照したIDとハッシュを記載してください。

詳しいCLIと実験計画の形式は、公開CTRのdocs/EVOLUTION.mdとdocs/EVOLUTION.ja.mdを参照してください。
