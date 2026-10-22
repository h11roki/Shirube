from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle

FONT = "HeiseiKakuGo-W5"
HEADER = [
    "曜日",
    "時限",
    "区分",
    "学科",
    "入学年度",
    "回生",
    "授業ＣＤ",
    "科目名",
    "クラス",
    "単位",
    "担当教員",
    "教室",
    "登録方法",
]
SPRING_ROWS = [
    [
        "月",
        "1-2",
        "教養D",
        "全",
        "26-16",
        "1",
        "34982",
        "スポーツ方法実習Ⅰ(A)【バスケットボー\nル】",
        "2",
        "1",
        "架空 規子",
        "１アリーナ",
        "抽選",
    ],
    [
        "月",
        "1-2",
        "専門",
        "電",
        "24-20",
        "3",
        "32453",
        "電動移動機械システム",
        "B8",
        "2",
        "仮名 一郎、架空 太\n郎、仮名 花子",
        "Ｃ３０５",
        "本",
    ],
    [
        "月",
        "3-4",
        "立命館/教養A",
        "全",
        "26-20/19-16",
        "1",
        "34793",
        "日本国憲法",
        "G2",
        "2",
        "仮名 二郎",
        "C101",
        "抽選",
    ],
    [
        "月",
        "7-10",
        "専門",
        "電・情",
        "24-16",
        "3",
        "32423",
        "電気電子工学実験Ⅲ",
        "A8",
        "2",
        "架空 三郎",
        "EX1",
        "本",
    ],
]
OTHER_ROWS = [
    [
        "@",
        "@",
        "立命館",
        "全",
        "25-20",
        "2",
        "16806",
        "平和人権フィールドワーク",
        "GR",
        "2",
        "仮名 四郎",
        "-",
        "選考",
    ],
]
COLUMN_WIDTHS = [30, 30, 55, 40, 55, 40, 45, 150, 35, 30, 110, 60, 45]


def table(heading: str, rows: list[list[str]]) -> Table:
    data = [[heading] + [""] * (len(HEADER) - 1), HEADER, *rows]
    built = Table(data, colWidths=COLUMN_WIDTHS)
    built.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("SPAN", (0, 0), (-1, 0)),
            ]
        )
    )
    return built


def main() -> None:
    pdfmetrics.registerFont(UnicodeCIDFont(FONT))
    output = Path(__file__).with_name("sample.pdf")
    document = SimpleDocTemplate(str(output), pagesize=landscape(A4))
    document.build(
        [table("【春学期】月曜日", SPRING_ROWS), Spacer(1, 12), table("【その他】", OTHER_ROWS)]
    )


if __name__ == "__main__":
    main()
