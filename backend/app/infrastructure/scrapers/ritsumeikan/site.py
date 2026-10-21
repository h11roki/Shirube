BASE_URL = "https://syllabus.ritsumei.ac.jp"


def detail_url(href: str) -> str:
    return f"{BASE_URL}{href}?language=ja"
