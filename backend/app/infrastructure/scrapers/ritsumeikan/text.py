FACULTY_SEPARATOR = ","
NAME_SEPARATOR = "、"
TITLE_SEPARATOR = "§"


def split_list(text: str, separator: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in text.split(separator) if item.strip())


def split_titles(text: str) -> list[tuple[str, str]]:
    titles = []
    for part in text.split(TITLE_SEPARATOR):
        code, _, title = part.strip().partition(":")
        titles.append((code, title.strip()))
    return titles
