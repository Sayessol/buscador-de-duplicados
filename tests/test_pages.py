"""Splitting of the "Similar photos" groups into pages.

Windows does not draw windows taller than 32,767 px: if the gallery goes
past that it gets cut off and the scrollbar disappears.
"""

import pytest

from ui.similar_photos_tab import (
    HEADER_HEIGHT, ROW_HEIGHT, PAGE_MAX_HEIGHT, COLUMNS, MAX_GROUPS_PER_PAGE,
    split_into_pages,
)

WINDOWS_LIMIT = 32767


def _height(n):
    return HEADER_HEIGHT + ROW_HEIGHT * -(-n // COLUMNS)


def test_no_groups_means_no_pages():
    assert split_into_pages([]) == []


def test_few_groups_fit_in_one_page():
    assert split_into_pages([3, 2, 5]) == [(0, 3)]


@pytest.mark.parametrize("counts", [
    [2] * 500,                  # many small groups
    [12] * 200,                 # groups of several rows
    [3, 40, 2, 90, 2, 2, 7],    # mix
    [900, 2, 2],                # a huge group and others
])
def test_pages_cover_all_groups_without_gaps(counts):
    pages = split_into_pages(counts)
    assert pages[0][0] == 0 and pages[-1][1] == len(counts)
    for (_, end), (start, _) in zip(pages, pages[1:]):
        assert end == start
    assert all(start < end for start, end in pages)


@pytest.mark.parametrize("counts", [[2] * 500, [12] * 200, [3, 40, 2, 90, 2, 2, 7]])
def test_no_page_approaches_the_windows_limit(counts):
    for start, end in split_into_pages(counts):
        assert end - start <= MAX_GROUPS_PER_PAGE
        assert sum(_height(n) for n in counts[start:end]) <= PAGE_MAX_HEIGHT < WINDOWS_LIMIT


def test_a_huge_group_gets_its_own_page():
    assert split_into_pages([900, 2, 2]) == [(0, 1), (1, 3)]


def test_the_case_that_used_to_fail_is_now_split():
    """69 groups of ~9 photos measured about 52,000 px all at once."""
    assert sum(_height(9) for _ in range(69)) > WINDOWS_LIMIT
    assert len(split_into_pages([9] * 69)) > 1
