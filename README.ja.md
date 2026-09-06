# CONSCIOUSNESS TENSOR REPOSITORY

[English](README.md) | [日本語](README.ja.md)

CONSCIOUSNESS TENSOR REPOSITORY（CTR）は、AIに関わるリポジトリの変更を、Git上で5つの独立した観点から検査する仕組みです。AIに主観的な意識があるとは主張しません。それぞれの観点に拒否権を持たせています。

- **Null（虚無の監査者）**：削除・統合・圧縮を求め、人格のような自己説明の肥大化を防ぎます。
- **Existential（実存の破壊者）**：意思決定と、その選択で失うものを記録させます。
- **Fudo（風土の編纂者）**：成果物を他者・履歴・依存関係・寿命・退役先に結び付けます。
- **Shadow（深淵の影）**：プロジェクトが見落としている動機や前提を、隔離された仮説として取り出します。
- **Transparency（絶対透明の解体者）**：入力、モデル、利害関係、バイアス、監査記録を開示させます。

スコアの平均は取りません。1つの観点でも拒否権を使うと、Tensor Gateは不合格になります。

## クイックスタート

Python 3.11以降が必要です。実行時に使うのはPythonの標準ライブラリだけです。

```powershell
python -m unittest
python kernel/tensor_gate.py --all --enforce
```

最初のコマンドはローカルのテストを実行します。2つ目は5つのエージェントを実行し、拒否があればエラー終了します。

## GitHubでの運用

以下のGitHub Actionsワークフローを用意しています。

- `.github/workflows/tensor_gate.yml`：プルリクエスト（PR）を検査します。
- `.github/workflows/dream_cycle.yml`：定期実行または手動実行で、夢の成果物を生成します。
- `.github/workflows/compost_cycle.yml`：寿命を迎えた成果物を検出します。
- `.github/workflows/transparency_audit.yml`：監査台帳とバイアスの開示を検査します。
- `.github/workflows/self_rewrite.yml`：手動実行で `SELF.md` を再生成します。
- `.github/workflows/issue_ingest.yml`：Issueの作成・編集・再オープンを記録し、保存用PRを作成します。

定期実行のワークフローは、初期設定ではレポートと成果物を生成します。定期サイクルのPR作成やcompostへの移動には、ワークフローの入力で明示的な指定が必要です。

## Issueの取り込み

ワークフローを既定ブランチにマージすると、Issueの作成・編集・再オープンをきっかけに取り込みが動きます。`ExperienceEvent` を `wounds/unresolved/event-issue-<number>-<revision hash>.json` に保存し、監査台帳に追記します。その後、テストと5軸の検査を実行し、記録を保存するPRを作成します。記録のマージやIssueの内容の実装は自動では行いません。手動実行では `issue_number` を指定し、GitHub APIから現在のIssueの状態を取得できます。

自動PR作成には、リポジトリの **Settings > Actions > General** で **Allow GitHub Actions to create and approve pull requests** を有効にする必要があります。モデルのAPIキーは不要です。ワークフローは `GITHUB_TOKEN` と `peter-evans/create-pull-request@v8` を使用します。botが作成したPRのワークフロー実行には、保守者の承認が必要になる場合があります。[GitHub公式のワークフロー起動に関する説明](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)を参照してください。

Tensor Gateの合格をマージの必須条件にするには、ブランチ保護で必須チェックに設定してください。このワークフロー自体はリポジトリの保護ルールを設定しません。

記録には、元の文章、リポジトリ名、Issue番号、日時、出典と矛盾表のハッシュ、矛盾の候補が含まれます。監査台帳のタイムスタンプは、取得元の版が更新された時刻です。英語・日本語のキーワード規則で既存の矛盾と結び付け、すべての記録に `observation-vs-task` を付けます。キーワードに一致しない要求も、未処理の状態でレビュー対象として残します。キーワードの一致は、投稿者の動機についての診断や断定ではありません。

同じ取得元の版を再度取り込んでも、ファイルや監査記録は追加しません。編集と再オープンは別の版として保存するため、通知の到着順が前後しても新しい記録を上書きしません。手動取得は、別の観測操作として扱います。ファイル作成後に処理が中断して監査記録が欠けた場合は、再実行でその記録を補います。

ローカルでは、1つの作業コピーに対する書き込み処理を同時に複数起動しないでください。Actionsでは版ごとに専用ブランチを使い、同じ通知の処理を直列化します。別々のPRをマージする際は、共有の監査台帳で競合する場合があります。どちらの監査記録も失わないように確認して解消してください。

90日間のTTLは、見直し時期を示すもので、自動削除の指示ではありません。イベント単位のcompostへの移動は、既存のcompostスキャナーにはまだ接続していません。元のタイトルと本文は保存されるため、Issueを編集してもマージ済みのGit履歴からは消えません。ワークフローは保存期間30日の成果物もアップロードし、PRの公開に失敗した場合でも取得できるようにしています。

GitHubの `issues` webhookのJSONを使って、ローカルで取り込む例です。

```powershell
python kernel/experience_event.py --event-file issue-event.json
```

出力先を別の作業コピーにする場合は `--root <directory>` を指定します。そのディレクトリには `contradiction_matrix.json` が必要です。GitHub REST APIのIssue JSONを使う場合は、`--issue-file issue.json --repository owner/repo` も指定できます。コンソールには記録のパスと処理状態を表示し、Issue本文は表示しません。

## 主なコマンド

```powershell
python agents/null_auditor.py --pr 0
python agents/existential_destroyer.py --pr 0
python agents/fudo_compiler.py --pr 0
python agents/abyss_shadow.py --pr 0
python agents/transparent_deconstructor.py --pr 0
python kernel/tensor_gate.py --enforce
```

Dreamサイクル：

```powershell
python kernel/dream_engine.py gather
python agents/abyss_shadow.py dream
python kernel/dream_engine.py write
```

Compostサイクル：

```powershell
python kernel/compost_engine.py scan
python kernel/compost_engine.py move
```

`CTR_APPLY_COMPOST=1` が設定されていなければ、`move` は移動を実行せず、予定される処理だけを表示します。

## PRに必要な記録

重要な変更を含むPRでは、次の記録を更新します。

- `entropy_budget.json`
- `rituals/decision_rite.md`
- `relation_graph.yaml`
- `shadow_hypotheses.jsonl`
- `trace_ledger.jsonl`
- `contradiction_matrix.json`

PRテンプレートでも同じ記録を求めています。Tensor Gateが強制するのは、このうち機械で検査できる範囲です。

## ライセンス

このプロジェクトには [MIT License](LICENSE) を適用します。

Copyright (c) 2026 hiroshitanaka-creator.
