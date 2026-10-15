def listing_page(*rows: tuple[str, str]) -> str:
    body = "".join(
        f"<tr><th><a href='{href}'>{title}</a></th>"
        "<td>理工学部</td><td>春セメスター</td><td>月1</td><td>BKC</td>"
        "<td>甲</td><td>日本語</td><td>2</td></tr>"
        for title, href in rows
    )
    return f"<table><tbody>{body}</tbody></table>"
