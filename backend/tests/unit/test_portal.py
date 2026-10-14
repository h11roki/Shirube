from app.infrastructure.scrapers.ritsumeikan.portal import SyllabusPortal


def test_listing_queries_cover_every_term_weekday_and_period() -> None:
    queries = SyllabusPortal(2026).listing_queries()

    assert len(queries) == 3 * 7 * 7 + 2
    assert len({query.key for query in queries}) == len(queries)
    assert queries[0].key == "春学期_月_1"
    assert queries[-1].weekday is None
