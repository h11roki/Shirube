from pathlib import Path

from playwright.sync_api import sync_playwright

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
        "スポーツ方法実習Ⅰ(A)【バスケットボー<br>ル】",
        "2",
        "1",
        "櫻木 規美子",
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
        "川畑 良尚、峯元 高<br>志、福水 洋平",
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
        "坂田 隆介",
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
        "瀧口 浩一",
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
        "鄭 雅英",
        "-",
        "選考",
    ],
]
STYLE = "table{border-collapse:collapse;font-size:9px}td,th{border:1px solid #000;padding:2px}"


def table(heading: str, rows: list[list[str]]) -> str:
    head = "".join(f"<th>{cell}</th>" for cell in HEADER)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f"<table><tr><td colspan='13'>{heading}</td></tr><tr>{head}</tr>{body}</table>"


def main() -> None:
    html = f"<html><head><style>{STYLE}</style></head><body>"
    html += (
        table("【春学期】月曜日", SPRING_ROWS)
        + "<br>"
        + table("【その他】", OTHER_ROWS)
        + "</body></html>"
    )
    output = Path(__file__).with_name("sample.pdf")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.pdf(path=str(output), format="A4")
        browser.close()


if __name__ == "__main__":
    main()
