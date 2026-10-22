from dataclasses import dataclass
from html import escape

YEAR = "2026"
HEADER_LABELS = (
    "授業科目名",
    "年度",
    "学期",
    "開講曜日・時限",
    "学部・研究科",
    "全担当教員",
    "単位数",
)
SCHEDULE_LABELS = ("授業回数/担当教員（複数担当の場合）", "テーマ", "キーワード・文献・補足情報等")
GRADING_LABELS = ("種別", "割合(%)", "評価基準等")
BOOK_LABELS = ("書名", "著者・出版社")
LISTING_LABELS = (
    "行番号",
    "授業科目名",
    "学部・研究科",
    "学期",
    "開講曜日・時限",
    "キャンパス",
    "全担当教員",
    "授業で利用する言語",
    "単位数",
)
NOTE_ROW = "-"
SIMPLE_CELLS = ("理工学部", "春セメスター", "月1", "BKC", "甲", "日本語", "2")
UNLABELED_FIELD = (
    '<section class="syllabus-section syllabus-section--field"><div class="syllabus-field">'
    '<div class="syllabus-field__value slds-form-element__static">'
    '<span class="syllabus-field__print-text">科目ナンバリングは学科の案内を参照。</span>'
    "</div></div></section>"
)


@dataclass(frozen=True)
class Page:
    code: str
    title: str
    term: str
    slot: str
    faculties: str
    instructors: str
    credits: str
    overview: str
    objectives: str
    schedule_note: str
    sessions: tuple[tuple[str, str, str], ...]
    record_id: str
    aliases: tuple[tuple[str, str], ...] = ()
    campus: str = "BKC"
    language: str = "日本語"
    preparation: str = "なし"
    class_format: str = "対面で実施する。"
    self_study: str = "テキストの予習と復習を各回 2 時間行う。"
    grading_note: str = ""
    advice: str = ""
    remarks: str = ""
    grading: tuple[tuple[str, str, str], ...] = (
        ("定期試験（筆記）", "", ""),
        (
            "上記以外の試験・レポート、平常点評価（日常的な授業における取組状況の評価）",
            "100",
            "発表と課題の提出状況で評価する。",
        ),
    )

    @property
    def heading(self) -> str:
        names = ((self.code, self.title), *self.aliases)
        return " § ".join(f"{code}:{title}" for code, title in names)

    @property
    def text_fields(self) -> tuple[tuple[str, str], ...]:
        return (
            ("キャンパス", self.campus),
            ("授業で利用する言語", self.language),
            ("授業の概要と方法", self.overview),
            ("受講生の到達目標", self.objectives),
            ("事前に履修しておくことが望まれる科目", self.preparation),
            ("授業実施形態", self.class_format),
            ("授業外学習の指示", self.self_study),
            ("成績評価方法(備考)", self.grading_note),
            ("受講および研究に関するアドバイス", self.advice),
            ("備考", self.remarks),
        )

    @property
    def href(self) -> str:
        return f"/syllabus/s/r-syllabus/{self.record_id}/{YEAR}{self.code}"

    @property
    def listing_cells(self) -> tuple[str, ...]:
        return (
            self.faculties,
            self.term,
            self.slot,
            self.campus,
            self.instructors,
            self.language,
            self.credits,
        )


def numbered(themes: tuple[str, ...]) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        (str(number), theme, f"{theme}の要点") for number, theme in enumerate(themes, start=1)
    )


INTRODUCTION = Page(
    code="10001",
    title="架空工学概論(6A)",
    term="春セメスター",
    slot="月5",
    faculties="理工学部",
    instructors="ALEX EXAMPLE、架空 太郎、仮名 花子",
    credits="2",
    overview=(
        "架空工学科の学びの内容について概説し、計算機の基本的な使い方や大学での学び方など、"
        "今後学科で学ぶための基礎を身につける。\n"
        "(1) 架空工学科に関連するテーマの学習と発表\n"
        "(2) 情報リテラシー（計算機の利用、メール、文献の検索）\n"
        "(3) 計算機の使い方（コマンド、エディタ）"
    ),
    objectives=(
        "(1) 架空工学科での学びの概要を理解している。\n(2) 計算機の基本的な使い方を身につけている。"
    ),
    schedule_note="第 1 回はガイダンスを行う。詳細は LMS を参照。",
    sessions=(
        (
            "1 / 架空 太郎、ALEX EXAMPLE、仮名  花子",
            "架空工学科での学び",
            "カリキュラム、オンラインシラバス、LMS",
        ),
        ("2 / 仮名 花子", "計算機の基本", "ログイン、ファイル、エディタ"),
        ("3 / 仮名 花子", "電子メールと文献の検索", "メール、図書館、データベース"),
        ("4 / 架空 太郎", "テーマの決め方", "調査、資料の読み方"),
        ("5 / 架空 太郎", "資料の作り方", "図表、引用の書き方"),
        ("6 / ALEX EXAMPLE", "発表の準備", "構成、話し方"),
        ("7 / ALEX EXAMPLE", "発表 1", "質疑、振り返り"),
        ("8 / 架空 太郎", "発表 2", "質疑、振り返り"),
        ("9 / 仮名 花子", "学科の研究分野 1", "回路、信号"),
        ("10 / 仮名 花子", "学科の研究分野 2", "情報、通信"),
        ("11 / 架空 太郎", "学科の研究分野 3", "制御、計測"),
        ("12 / ALEX EXAMPLE", "進路と学び", "履修の計画"),
        ("13 / 架空 太郎", "まとめ 1", "レポートの書き方"),
        ("14 / 架空 太郎", "まとめ 2", "レポートの提出"),
    ),
    record_id="a0i000000000001AAA",
)

CIRCUITS_1 = Page(
    code="10002",
    title="架空回路Ⅰ(6T)",
    term="春セメスター",
    slot="水2",
    faculties="理工学部",
    instructors="仮名 一郎",
    credits="2",
    overview=(
        "半導体素子の基本的な動作を学び、増幅回路の原理について理解を深める。\n\n"
        "さまざまな技術分野で使われる回路の基礎として、等価回路を使った解析の方法を身につける。"
    ),
    objectives="(1) 半導体素子の動作を説明できる。\n(2) 増幅回路を等価回路で解析できる。",
    schedule_note="教科書の該当する章を事前に読んでおくこと。",
    sessions=(
        ("1", "半導体の基礎", "半導体、キャリア"),
        ("2", "ダイオード", "整流、順方向と逆方向"),
        ("3", "トランジスタの動作", "電流増幅率"),
        ("4", "バイアス回路", "動作点、安定化"),
        (
            "5～7",
            "小信号の等価回路、増幅の原理、各種の接地回路",
            "小信号の扱いを理解し、トランジスタの等価回路を理解する\n増幅の原理を理解し、各種の接地回路を理解する",
        ),
        ("8", "周波数特性", "低域と高域"),
        ("9", "負帰還", "帰還の効果"),
        ("10", "演算増幅器 1", "理想的な特性"),
        ("11", "演算増幅器 2", "反転と非反転"),
        ("12", "発振回路", "発振の条件"),
        ("13", "電源回路", "整流と平滑"),
        ("14", "まとめ", "総合演習"),
    ),
    record_id="a0i000000000002AAA",
)

CIRCUITS_2 = Page(
    code="10003",
    title="架空回路Ⅱ(6T)",
    term="秋セメスター",
    slot="木3",
    faculties="理工学部",
    instructors="仮名 二郎",
    credits="2",
    overview="ディジタル回路の基礎を学び、論理回路の設計の方法を身につける。",
    objectives="(1) 論理回路を設計できる。\n(2) 順序回路の動作を説明できる。",
    schedule_note="演習には電卓を持参すること。",
    sessions=numbered(
        (
            "ディジタル信号",
            "論理関数",
            "論理の簡単化",
            "組み合わせ回路 1",
            "組み合わせ回路 2",
            "フリップフロップ",
            "順序回路 1",
            "順序回路 2",
            "カウンタ",
            "レジスタ",
            "メモリ",
            "A/D 変換と D/A 変換",
            "設計演習",
            "まとめ",
        )
    ),
    record_id="a0i000000000003AAA",
)

CROSS_LISTED = Page(
    code="10004",
    title="架空平和研究 (GR)",
    term="秋セメスター",
    slot="その他",
    faculties="法学部,理工学部",
    instructors="架空 太郎",
    credits="2",
    overview="学外での研修を通して、平和と交流について考える。",
    objectives="(1) 研修の内容を自分の言葉で説明できる。",
    schedule_note="研修の日程は初回に案内する。",
    sessions=numbered(("ガイダンス", "事前の学習", "研修", "振り返り")),
    record_id="a0i000000000004AAA",
    aliases=(("10005", "架空交流演習(GR)"),),
    class_format="集中で実施する。",
)

PAGES = {page.code: page for page in (INTRODUCTION, CIRCUITS_1, CIRCUITS_2, CROSS_LISTED)}


def screen_text(text: str) -> str:
    return "<br/>".join(escape(line) for line in text.split("\n"))


def table(kind: str, labels: tuple[str, ...], rows: str) -> str:
    heads = "".join(
        f'<th scope="col"><div class="syllabus-table__header-cell" title="{escape(label)}">'
        f"{escape(label)}</div></th>"
        for label in labels
    )
    return (
        f'<table class="syllabus-table syllabus-table--{kind} slds-table slds-table_bordered'
        f' slds-table_col-bordered"><colgroup>{"<col/>" * len(labels)}</colgroup>'
        f'<thead><tr class="slds-line-height_reset">{heads}</tr></thead>'
        f"<tbody><!-- -->{rows}</tbody></table>"
    )


def cell_title(text: str) -> str:
    return f' title="{escape(text)}"' if text else ""


def plain_cell(tag: str, label: str, text: str) -> str:
    scope = ' scope="row"' if tag == "th" else ""
    return (
        f'<{tag} data-label="{escape(label)}"{scope}>'
        f'<div class="syllabus-table__cell slds-cell-wrap"{cell_title(text)}>{escape(text)}'
        f"</div></{tag}>"
    )


def formatted_cell(label: str, text: str) -> str:
    return (
        f'<td data-label="{escape(label)}">'
        f'<div class="syllabus-table__cell slds-cell-wrap"{cell_title(text)}>'
        f"<lightning-formatted-text>{screen_text(text)}</lightning-formatted-text></div></td>"
    )


def row(cells: str) -> str:
    return f'<tr class="slds-hint-parent">{cells}</tr>'


def table_section(kind: str, labels: tuple[str, ...], rows: str, label: str = "") -> str:
    heading = (
        '<div class="syllabus-section__label slds-form-element">'
        f'<span class="syllabus-section__label-text slds-form-element__label">{escape(label)}'
        "</span></div>"
        if label
        else ""
    )
    return (
        f'<section class="syllabus-section syllabus-section--table">{heading}'
        f"{table(kind, labels, rows)}</section>"
    )


def header_section(page: Page) -> str:
    values = (
        page.heading,
        YEAR,
        page.term,
        page.slot,
        page.faculties,
        page.instructors,
        page.credits,
    )
    cells = "".join(
        plain_cell("td", label, value) for label, value in zip(HEADER_LABELS, values, strict=True)
    )
    return table_section("header-info", HEADER_LABELS, row(cells))


def field_section(label: str, text: str) -> str:
    return (
        '<section class="syllabus-section syllabus-section--field">'
        '<div class="syllabus-field"><!-- -->'
        f'<span class="syllabus-field__label">{escape(label)}</span><!-- -->'
        '<div class="syllabus-field__value slds-form-element__static"><!-- -->'
        f'<span class="syllabus-field__print-text">{escape(text)}</span>'
        f'<lightning-formatted-text class="syllabus-screen-only-text">{screen_text(text)}'
        "</lightning-formatted-text><!-- --></div></div></section>"
    )


def schedule_section(page: Page) -> str:
    rows = ((NOTE_ROW, page.schedule_note, ""), *page.sessions)
    html_rows = "".join(
        row(
            "".join(
                formatted_cell(label, text)
                for label, text in zip(SCHEDULE_LABELS, cells, strict=True)
            )
        )
        for cells in rows
    )
    return table_section("schedule", SCHEDULE_LABELS, html_rows, "授業スケジュール")


def grading_section(page: Page) -> str:
    html_rows = "".join(
        row(
            plain_cell("th", GRADING_LABELS[0], kind)
            + plain_cell("td", GRADING_LABELS[1], percentage)
            + plain_cell("td", GRADING_LABELS[2], criteria)
        )
        for kind, percentage, criteria in page.grading
    )
    return table_section("evaluation", GRADING_LABELS, html_rows, "成績評価方法")


def book_section(label: str, title: str, publisher: str) -> str:
    cells = plain_cell("th", BOOK_LABELS[0], title) + plain_cell("td", BOOK_LABELS[1], publisher)
    return table_section("book", BOOK_LABELS, row(cells), label)


def detail_page(page: Page, omit: str = "") -> str:
    fields = "".join(
        field_section(label, text) for label, text in page.text_fields if label != omit
    )
    return (
        '<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">'
        f"<title>シラバス情報: {YEAR}{page.code}</title></head>"
        '<body class="comm-page-detail-a0i"><div class="themeLayoutStarterWrapper">'
        '<div class="syllabus-detail">'
        f"{header_section(page)}{UNLABELED_FIELD}{fields}"
        f"{schedule_section(page)}{grading_section(page)}"
        f"{book_section('教科書', '架空工学の教科書', '架空 太郎（架空出版）')}"
        f"{book_section('参考書', '架空工学の演習', '仮名 花子（仮名書房）')}"
        "</div></div></body></html>"
    )


def listing_row(heading: str, href: str, cells: tuple[str, ...]) -> str:
    link = escape(href)
    record_id = escape(href.rsplit("/", 2)[-2])
    values = "".join(
        f'<td role="gridcell" data-label="{escape(label)}" data-cell-value="{escape(text)}">'
        f'<lightning-primitive-cell-factory class="slds-cell-wrap" data-label="{escape(label)}">'
        '<span class="slds-grid slds-grid_align-spread"><div class="slds-hyphenate">'
        f"<lightning-base-formatted-text>{escape(text)}</lightning-base-formatted-text>"
        "</div></span></lightning-primitive-cell-factory></td>"
        for label, text in zip(LISTING_LABELS[2:], cells, strict=True)
    )
    return (
        f'<tr class="slds-hint-parent" role="row" data-row-key-value="{record_id}">'
        '<td role="gridcell" data-col-key-value="0-rowNumber-0"><lightning-primitive-cell-factory>'
        '<span class="slds-grid slds-grid_align-spread"><div class="slds-truncate">'
        '<span class="slds-row-number slds-text-body_small slds-text-color_weak"></span>'
        "</div></span></lightning-primitive-cell-factory></td>"
        f'<th role="rowheader" scope="row" data-label="授業科目名" data-cell-value="{link}">'
        '<lightning-primitive-cell-factory class="slds-cell-wrap" data-label="授業科目名">'
        '<span class="slds-grid slds-grid_align-spread"><div class="slds-hyphenate">'
        f'<lightning-formatted-url><a href="{link}" target="_blank" title="{link}">'
        f"{escape(heading)}</a></lightning-formatted-url></div></span>"
        f"</lightning-primitive-cell-factory></th>{values}</tr>"
    )


def listing_page(*rows: Page | tuple[str, str]) -> str:
    built = tuple(
        listing_row(entry.heading, entry.href, entry.listing_cells)
        if isinstance(entry, Page)
        else listing_row(entry[0], entry[1], SIMPLE_CELLS)
        for entry in rows
    )
    heads = "".join(
        f'<th role="columnheader" scope="col" aria-label="{escape(label)}">'
        f'<span class="slds-truncate" title="{escape(label)}">{escape(label)}</span></th>'
        for label in LISTING_LABELS
    )
    return (
        '<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><title>ホーム</title></head>'
        '<body class="comm-page-home"><div class="themeLayoutStarterWrapper">'
        '<div class="slds-card"><p class="slds-m-vertical_medium content">'
        f"全 {len(built)} 件（1 / 1 ページ）</p>"
        '<table class="slds-table slds-table_header-fixed slds-table_bordered" role="grid"'
        f' data-num-rows="{len(built)}"><thead><tr class="slds-line-height_reset" role="row">'
        f'{heads}</tr></thead><tbody data-rowgroup-body="">{"".join(built)}</tbody></table></div>'
        "</div></body></html>"
    )
