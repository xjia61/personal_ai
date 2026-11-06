from datetime import date, timedelta

import pytest

from app.services.job_service import get_freshness, time_range_for_days, valid_url
from app.services.job_service import search_queries
from app.schemas import JobSearchRequest


@pytest.mark.parametrize("days,expected", [(1, "day"), (2, "week"), (7, "week"),
                                            (8, "month"), (31, "month"), (32, "year")])
def test_search_time_ranges(days, expected):
    assert time_range_for_days(days) == expected


@pytest.mark.parametrize("age,expected", [(-1, 0), (0, 100), (3, 100), (4, 85),
                                         (7, 85), (8, 65), (14, 65), (15, 0)])
def test_job_freshness(age, expected):
    posted = (date.today() - timedelta(days=age)).isoformat()
    assert get_freshness(posted, 14) == expected


@pytest.mark.parametrize("posted", [None, "", "unknown"])
def test_unknown_date_is_not_invented(posted):
    assert get_freshness(posted, 14) is None


@pytest.mark.parametrize("url,expected", [("https://example.invalid/job", True),
    ("javascript:alert(1)", False), ("file:///tmp/job", False), ("/jobs/1", False)])
def test_search_url_format(url, expected):
    assert valid_url(url) is expected


def test_queries_preserve_city_state_and_search_remote_separately():
    queries = search_queries(["Python Engineer"], ["Houston, TX"], True)
    assert queries == ['"Python Engineer" Houston, TX jobs', '"Python Engineer" remote jobs']
    assert len(search_queries(["A", "B", "C", "D"], ["1", "2", "3", "4"], True)) == 8


@pytest.mark.parametrize("overrides", [dict(keywords=[]), dict(keywords=[" "]),
    dict(posted_within_days=0), dict(posted_within_days=91), dict(min_relevance_score=101),
    dict(keywords=["x"] * 5), dict(locations=["x"] * 5), dict(keywords=["x" * 101])])
def test_search_request_limits(overrides):
    with pytest.raises(ValueError):
        JobSearchRequest.model_validate({"keywords": ["Python"], **overrides})
