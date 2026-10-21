import type { Metadata } from "next";
import Link from "next/link";

import { ISSUES_URL, OPERATOR } from "@/lib/site";

export const metadata: Metadata = { title: "プライバシーポリシー" };

export default function PrivacyPage() {
  return (
    <>
      <header className="grid gap-2">
        <h1>プライバシーポリシー</h1>
        <p className="text-sm text-sub">2026 年 10 月 22 日 制定</p>
      </header>
      <section>
        <p>
          shirube(以下「このアプリ」)は、個人({OPERATOR}
          )が運営する非公式のアプリです。このページでは、このアプリが利用者のどの情報を扱い、どこへ送り、どう消せるかを説明します。
        </p>
      </section>
      <section>
        <h2>保存する情報</h2>
        <ul>
          <li>
            Google
            アカウントの利用者の番号(sub)。ログインした人を見分けるためだけに使います
          </li>
          <li>
            入力した内容: なりたい職業、回生、学科、学科で分かれたクラスの選択
          </li>
          <li>
            作った道標(選んだ授業と理由、学期ごとの時間割)と、その状態や作った日時
          </li>
          <li>「もう取った」と答えた授業の科目名</li>
        </ul>
        <p>
          Google
          から受け取る名前、メールアドレス、プロフィール画像はサーバーに保存しません。ログイン状態を保つために暗号化したクッキーの中に置き、画面に名前を出すためにだけ使います。
        </p>
      </section>
      <section>
        <h2>外部へ送る情報</h2>
        <ul>
          <li>
            Google: ログインに Google の認証を使います。Google に送られる情報と
            Google での扱いは、Google のプライバシーポリシーによります
          </li>
          <li>
            OpenAI:
            道標を作るとき、入力した職業名と、そこから読み取った職業とスキル、授業のシラバスの抜粋を
            OpenAI の API に送ります。利用者を特定する情報(Google
            の番号など)は送りません。OpenAI での扱いは OpenAI の API
            のデータの方針によります
          </li>
        </ul>
        <p>
          これ以外の第三者に利用者の情報を渡しません。広告やアクセス解析のサービスは使っていません。
        </p>
      </section>
      <section>
        <h2>クッキーと端末への保存</h2>
        <ul>
          <li>
            ログイン状態を保つためのクッキー(Auth.js の authjs.session-token
            など)。ログアウトか退会で消えます
          </li>
          <li>
            見た目(明るい・暗い)の設定を端末の localStorage
            に保存します。利用者の情報は含みません
          </li>
        </ul>
      </section>
      <section>
        <h2>サーバーのログ</h2>
        <p>
          障害の調査と不正な利用の防止のために、アクセスログ(IP
          アドレス、時刻、要求した
          URL、状態コード)と、アプリのログ(道標の番号、状態、失敗の原因。失敗の原因には入力した職業名が含まれることがあります)を残し、30
          日で消します。Google の番号はログに書きません。
        </p>
      </section>
      <section>
        <h2>消し方</h2>
        <ul>
          <li>道標は、結果の画面か一覧の「消す」でいつでも消せます</li>
          <li>
            退会(一覧の下)で、利用者の番号、道標、もう取ったと答えた授業を全て消します
          </li>
          <li>
            道標を消したり退会したりしても、その日に作った道標の「作った日時」だけは、1
            日に作れる数を数えるために、誰のものか分からない形で翌日の 0
            時まで残ります。日時のほかは残りません
          </li>
          <li>サーバーのログは上のとおり 30 日で消えます</li>
        </ul>
      </section>
      <section>
        <h2>問い合わせ</h2>
        <p>
          GitHub の Issue(
          <a href={ISSUES_URL} target="_blank" rel="noreferrer">
            {ISSUES_URL}
          </a>
          )で受け付けます。
        </p>
      </section>
      <section>
        <h2>改定</h2>
        <p>
          このポリシーを変えるときは、このページに改定の日付とともに載せます。
        </p>
        <p>
          <Link href="/terms">利用規約</Link>もあわせてお読みください。
        </p>
      </section>
    </>
  );
}
