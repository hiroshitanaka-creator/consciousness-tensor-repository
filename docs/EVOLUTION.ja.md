# 進化機能とコンテキストグラフ

5つの進化案とコンテキストグラフを、同じ記録と出典を共有する機能として実装しています。
公開CTRは処理と架空の検証素材を持ち、個人の記録は別の非公開リポジトリに保存します。
既存のルート直下のIssue取込やDreamは、公開CTR自身の開発用として残しています。

## 6つの機能

| 機能 | 実際に行うこと |
| --- | --- |
| 傷の成長・再発 | Issueの版を傷に結び付け、未対処・調査中・対処済み・再発を追跡します。対処済みには、その傷に対応する成功した実験と採用判断が必要です。 |
| 選ばなかった未来の比較 | 指定したGitコミットやデータの違いを、独立した作業コピーで同じテストにかけます。結果とコード・テスト・入力のハッシュを保存します。 |
| 実験できるDream | 出典と乱数種を持つテンプレート仮説、または外部AIの提案を保存します。採用には、その仮説の検証種別に対応する実験と採用判断が必要です。 |
| 忘却実験 | 作業コピーで指定した記憶を除き、同じコードとテストで結果を比較します。元の記録や監査履歴を削除しません。 |
| 5軸の審査能力の検証 | 正例・反例を既存の5エージェントに実際に審査させ、見逃しと過剰拒否を軸ごとに計測します。基準の自動変更や平均化はしません。 |
| コンテキストグラフ | 層別の目次、個別記録、意味付きの関係、自己状態を生成します。日本語・英語の検索で関連証拠をたどり、読んだIDと版を記録します。 |

## 最初の操作

Python 3.11以降で、CTRの作業コピーから実行します。--contextは非公開データの保存先です。

```powershell
python -m kernel.ctr --context D:/private-context/context init --owner your-account
python -m kernel.ctr --context D:/private-context/context ingest --file issue-event.json
python -m kernel.ctr --context D:/private-context/context search "記憶の保存期間" --budget 6000
python -m kernel.ctr --context D:/private-context/context index
```

context/INDEX.mdが入口です。graph.jsonで参照先・反証・置き換え・依存を探し、
records/の個別記録を読みます。SELF.mdとSELF.jsonには実際の未解決の傷と採用判断が出ます。

正本はcontext/state.jsonです。記録と監査の更新をまとめて確定し、目次などはそこから生成します。
生成途中で停止した場合はindexを再実行できます。強制終了で.writer-lockが残ったときは、
動作中の書き込み処理がないことを確認してからロックを回復する必要があります。

検索はキーワードと2段階の関係探索です。埋め込み検索や意図の推論は行いません。
--budgetは文字数の上限で、トークン数ではありません。記録を途中で切らず、入らなかったIDを返します。
通常は却下・退役・旧版を除外します。--include-inactiveで明示的に含められます。
期限切れは見直し対象として表示し、自動で消しません。

## 判断と実験

```powershell
python -m kernel.ctr --context D:/private-context/context transition wound:minimality-vs-ecology investigating
python -m kernel.ctr --context D:/private-context/context experiment --repo D:/reviewed-project --file plan.json --trust-code
python -m kernel.ctr --context D:/private-context/context decide --file decision.json --accept
python -m kernel.ctr --context D:/private-context/context transition wound:minimality-vs-ecology scarred --decision decision:retention --evidence experiment:REPLACE_WITH_ID
```

実験計画にはkind、title、acceptance、wounds、context_ids、variantsを指定します。
kindはcounterfactualまたはforgettingです。variantsは2〜4案で、最初をbaselineとします。
各案にnameとrefを付け、忘却案には除く記憶のIDをomitに指定します。
テストは環境変数CTR_EXPERIMENT_CONTEXTが示すJSONから選択された記憶を読みます。

required_passで、結果を見る前に合格が必要な案を決めます。忘却実験では全案の合格と
読み込む情報量の減少が必要です。コードとテストも同一でなければなりません。
実験の合計設定時間は最大300秒です。--trust-codeは対象のコードを確認して実行する指定です。
Gitの作業コピーはファイル変更の分離であり、OSやネットワークのサンドボックスではありません。
信頼できないテストを実行するには、別途隔離された実行環境が必要です。

採用判断には、選択、2つ以上の却下案、代償、失敗条件、出典、作成者、実験・評価のID、
5軸それぞれのveto値を記録します。1軸でもtrueなら採用できません。
veto値は審査者の申告であり、それ自体が独立した審査結果を証明するものではありません。
actorも作成者の申告です。AIの提案を人間の選択として記録しないでください。

## Dreamと審査の評価

```powershell
python -m kernel.ctr --context D:/private-context/context dream wound:minimality-vs-ecology --seed 42
python -m kernel.ctr --context D:/private-context/context propose-dream --file model-proposal.json
python -m kernel.ctr --context D:/private-context/context assess --repo D:/ctr --file examples/evolution/judge_corpus.json --trust-code
python -m kernel.ctr --context D:/private-context/context review-dream hypothesis:REPLACE_WITH_ID accepted --decision decision:retention
```

内蔵Dream生成はテンプレート方式で、LLM APIや課金は不要です。Codexなどが作った仮説は
propose-dreamで取り込めます。title、question、experiment、acceptance_criterion、
experiment_kind、wound、source_ids、actor、generationを指定し、
generationにはprovider、model、prompt_hashを付けます。モデル情報は外部からの申告です。

実験計画のhypothesisに仮説IDを指定すると、結果がその仮説に結び付きます。
異なる仮説や異なる検証種別の成功を、その仮説の採用根拠にすることはできません。
審査評価型の仮説には、評価用コーパスにもhypothesisとwoundsを指定します。

評価用コーパスは2〜8件の正例・反例を持ち、各ケースに5軸の正解ラベルを指定します。
実際のエージェントの結果と照合し、見逃し率と過剰拒否率を別々に計算します。
これは指定した事例に対する評価であり、一般的な判断能力や意識の証明ではありません。

## 個人用GitHubリポジトリ

[非公開リポジトリ用テンプレート](../templates/personal-context)を用意しています。
ワークフローのCTR_ENGINE_REVISIONを、レビュー済みのCTRコミットSHAに置き換えて使います。
個人のIssue本文、索引、実験結果、PR、Actionsの成果物は非公開側に保存します。
公開設定になった場合は処理を止めます。

GitHub Plugin/MCPでは、README、AGENTS、context/INDEXから読み始めます。
新しい記憶や外部AIの仮説はinbox/にPRで追加します。詳細な形式はテンプレートのREADMEにあります。
読み取り専用の接続では参照ログを自動追加できないため、作業結果に参照IDとハッシュを示してください。
このテンプレートの設置だけで、各製品の接続や権限が自動で有効になるわけではありません。

毎日のDreamは、未解決の傷のうち直近の検討が古いものを最大3件選び、
dream/context-cycleブランチに提案します。それ以外の更新はcodex/context-cycleに置きます。
自動マージは行いません。実験・評価は手動実行またはローカルCLIで開始します。

実行待ちは最大100件をキューに保持し、未マージの候補PRがあれば、その監査履歴を検証して
状態を引き継ぎます。mainと候補で履歴が分岐した場合は、片方を上書きせず停止します。
その候補をマージするか、出典を確認して整合させてから再開します。
キュー上限を超えた通知や失敗した実行は、別途確認が必要です。

## 一周分の実証

```powershell
python -m unittest
python -m kernel.evolution_demo --output D:/fresh-ctr-demo
```

架空のGitリポジトリで、却下案の失敗、不要な記憶の除外成功、必要な記憶の除外失敗、
仮説の検証と採用、傷の対処と再発、5軸の実評価、グラフ検索まで実行します。
summary.jsonに結果を保存します。毎回、新しい出力先を指定してください。

完全な入力契約と制限は[英語版](EVOLUTION.md)と[スキーマ](../schemas/context_record.schema.json)を参照してください。
