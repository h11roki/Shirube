# 0106. サーバーへは SSM Session Manager を通した SSH で入り、セキュリティグループの 22 番を閉じる

- ステータス: 承認
- 日付: 2026-11-15

## 文脈

- ADR 0105 で本番の資源を Terraform に取り込んだとき、セキュリティグループが SSH(22 番)を 0.0.0.0/0 から受けていると分かった。手順書と ADR 0094 は「自分の IP だけ」と書いていた。入るには鍵が要るが、誰でも sshd に繋いで試せる
- 高橋さんは、取り込みでは今の形のまま残し、次の変更で SSM Session Manager に移して 22 番を閉じると選んだ(2026-11-15)
- サーバーに入るのは高橋さん(と手元の Claude Code)だけで、デプロイ(ADR 0094)、監視(ADR 0095)、バックアップと戻しの演習(ADR 0097)はどれもサーバーの中の cron か外からの HTTPS で、SSH を使わない。SSH を使うのは、手で入れ替えるとき、科目のデータを `scp` で送るとき、`report` などをサーバーで流すとき
- サーバーの AMI は Canonical の Ubuntu 26.04 で、SSM のエージェント(snap の amazon-ssm-agent 3.3)が入って動いている。EC2 に IAM のロールが付いていないので、Systems Manager には登録されていない
- アカウントは新しい登録の無料プランで、Systems Manager と IAM は無料プランで使える(高度な機能は要らない)。Session Manager は EC2 のインスタンスに使う分には料金がかからない
- サーバーは外向きの通信を全て許していて、公開の IP があるので、エージェントは SSM の公開のエンドポイントに届く

## 検討した選択肢

1. SSM Session Manager を通して SSH する(`AWS-StartSSHSession` を手元の ssh の ProxyCommand にする)。22 番を閉じる
2. SSM Session Manager のシェルだけを使い、SSH の鍵と sshd をやめる
3. 22 番を自宅の IP だけに開ける
4. EC2 Instance Connect Endpoint を通す

## 決定

1 を採る。

- Terraform で IAM のロール(EC2 が引き受ける)に AWS 管理の `AmazonSSMManagedInstanceCore` だけを付け、インスタンスプロファイルにして EC2 に付ける。付け替えは EC2 を止めずにできる
- エージェントが Systems Manager に登録され、手元から SSM を通して SSH で入れることを確かめてから、セキュリティグループから 22 番の規則を消す。2 つは別の apply にし、どちらも保存した plan を高橋さんに見せてから流す
- 手元は `~/.ssh/config` に、インスタンスの ID へ `aws ssm start-session --document-name AWS-StartSSHSession` で繋ぐ `ProxyCommand` を書き、`ssh shirube` と `scp ... shirube:~/` をそのまま使う。AWS CLI の Session Manager のプラグインが要る(Homebrew の `session-manager-plugin`)。鍵は `aws login --profile shirube` の鍵を使う
- EC2 のメタデータの応答の届く段数(`http_put_response_hop_limit`)を 2 から 1 にし、Docker のコンテナからロールの鍵を取れないようにする(ロールを使うのはサーバーの上のエージェントだけで、アプリは AWS の API を使わない)
- ロール、ポリシーの付け、インスタンスプロファイルにも `prevent_destroy` を付ける(22 番を閉じたので、消えるとサーバーに入る道が無くなる)
- SSH の鍵の組と sshd はそのまま残す。SSM は通り道だけを替え、入るにはこれまでどおり SSH の鍵が要る
- セッションの記録(S3 や CloudWatch Logs への出力)は付けない

## 理由

- 1 は、外から sshd に届く口を無くしつつ、`scp` や手元の ssh の設定、手順書のコマンドを替えずに使える。入るには AWS の鍵(12 時間で切れ、GitHub の Builder ID の許可が要る)と SSH の鍵の両方が要る
- 2 はシェルの利用者が `ssm-user` になり、`scp` も使えないので、手順書(科目のデータの送り方など)を全て書き直すことになる
- 3 は自宅の IP が変わるたびに書き換えて apply する手間があり、出先からは入れない。口も残る
- 4 は Instance Connect Endpoint を VPC に作る必要があり、EC2 にも Instance Connect の設定が要る。費用はかからないが、Session Manager より資源が増える
- セッションの記録は、入るのが本人だけで、S3 や CloudWatch Logs の費用と管理が増えるので今は付けない

## 受け入れたトレードオフ

- 手元に Session Manager のプラグインと `~/.ssh/config` の設定が要り、`aws login` の鍵が切れていると入れない(90 日を過ぎるとブラウザで許可し直す)
- SSM が使えない(エージェントが止まる、AWS 側の障害)と、サーバーに入れない。そのときは、コンソールかこの Terraform でセキュリティグループに自分の IP の 22 番を一時的に足して入る
- EC2 のロールは、Systems Manager のための管理ポリシーの権限を持つ(サーバーの上で直に動くプロセスはその鍵を使える。コンテナからは段数で届かない)。アプリは AWS の API を使わないので、ほかの権限は足さない

## 再検討する条件

- サーバーに入る人が増えたとき。セッションの記録と、人ごとの権限を考える
- 無料プランを有料プランに上げるとき(ADR 0076)。Session Manager の料金とセッションの記録を見直す
