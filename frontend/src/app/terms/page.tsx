import type { Metadata } from "next";
import Link from "next/link";

import { ContactSection, LegalDocument } from "@/components/legal-document";
import { TEXT_LINK } from "@/components/styles";
import { OPERATOR, SYLLABUS_SITE } from "@/lib/site";

export const metadata: Metadata = { title: "利用規約" };

export default function TermsPage() {
  return (
    <LegalDocument title="利用規約" enactedOn="2026 年 10 月 22 日">
      <section>
        <p>
          この利用規約は、個人({OPERATOR}
          、以下「運営者」)が運営する
          shirube(以下「このアプリ」)の利用の条件を定めます。ログインすると、この規約と
          <Link href="/privacy" className={TEXT_LINK}>
            プライバシーポリシー
          </Link>
          に同意したことになります。
        </p>
      </section>
      <section>
        <h2>1. 非公式のアプリであること</h2>
        <p>
          このアプリは、立命館大学とは関係のない、運営者が個人で作った非公式のアプリです。大学が提供したり認めたりしたものではありません。
        </p>
      </section>
      <section>
        <h2>2. 授業の情報の出典</h2>
        <p>
          授業の情報は、立命館大学が公開している
          <a
            href={SYLLABUS_SITE}
            target="_blank"
            rel="noopener noreferrer"
            className={TEXT_LINK}
          >
            シラバス
          </a>
          と時間割表によります。その内容はこのアプリのものではなく、大学と担当教員のものです。このアプリは、短い引用と原ページへのリンクにとどめます。
        </p>
      </section>
      <section>
        <h2>3. 道標は参考です</h2>
        <p>
          道標は、公開されたシラバスをもとに
          AI(大規模言語モデル)が授業を選び、理由を書いたものです。必修科目、卒業要件、抽選や定員、時間割の変更、来年度以降のカリキュラムの変更は見ていません。誤りや偏りが含まれることがあります。履修の登録は、履修要項など大学の正式な情報で必ず確かめてください。
        </p>
      </section>
      <section>
        <h2>4. アカウント</h2>
        <p>
          Google
          アカウントでログインします。アカウントは本人だけが使い、他人に使わせないでください。
        </p>
      </section>
      <section>
        <h2>5. 利用の制限</h2>
        <p>
          サービスの維持と費用のため、1
          日に作れる道標の数や同時に作れる数に上限を設けます。上限は予告なく変えることがあります。
        </p>
      </section>
      <section>
        <h2>6. 禁止事項</h2>
        <ul>
          <li>他人のアカウントでの利用や、なりすまし</li>
          <li>サーバーに過度な負荷をかける行為や、自動化した大量の要求</li>
          <li>AI に本来の目的と違うことをさせようとする入力</li>
          <li>このアプリやサーバーへの攻撃、脆弱性の悪用</li>
          <li>法令や公序良俗に反する利用</li>
        </ul>
        <p>
          運営者は、これらに当たる利用を止め、そのアカウントのデータを消すことがあります。
        </p>
      </section>
      <section>
        <h2>7. 変更と停止</h2>
        <p>
          運営者は、予告なくこのアプリの内容を変えたり、一時的に止めたりすることがあります。サービスを終えるときは、このアプリのページで知らせたうえで、保存している利用者のデータを消します。
        </p>
      </section>
      <section>
        <h2>8. 免責</h2>
        <p>
          このアプリは現状のまま提供します。運営者は、このアプリの利用や、道標に基づく履修の結果について、法令で許される範囲で責任を負いません。
        </p>
      </section>
      <section>
        <h2>9. 準拠法</h2>
        <p>この規約は、日本法に従って解釈します。</p>
      </section>
      <section>
        <h2>10. 改定</h2>
        <p>
          この規約を変えるときは、このページに改定の日付とともに載せます。改定のあとも使い続けた場合、改定に同意したものとみなします。
        </p>
      </section>
      <ContactSection heading="11. 問い合わせ" />
    </LegalDocument>
  );
}
