FACULTY_SEPARATOR = ","
NAME_SEPARATOR = "、"


def split_list(text: str, separator: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in text.split(separator) if item.strip())
