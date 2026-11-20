# *** NEW ***
from datetime import date, time
from types import SimpleNamespace

from app.scheduler import FreeSlot, compute_free_slots

# 2026-11-16 is a Monday
MONDAY = date(2026, 11, 16)


def block(day_of_week, start, end):
    return SimpleNamespace(day_of_week=day_of_week, start_time=start, end_time=end)


def test_no_blocks_gives_no_slots():
    assert compute_free_slots([], MONDAY) == []


def test_monday_block_appears_on_the_monday_date():
    slots = compute_free_slots([block(0, time(9, 0), time(11, 0))], MONDAY)
    assert slots == [FreeSlot(date(2026, 11, 16), time(9, 0), time(11, 0))]


def test_window_starting_midweek_finds_next_monday():
    # Window: Wed Nov 18 through Tue Nov 24, so Monday means Nov 23
    wednesday = date(2026, 11, 18)
    slots = compute_free_slots([block(0, time(9, 0), time(11, 0))], wednesday)
    assert [slot.day for slot in slots] == [date(2026, 11, 23)]


def test_slots_are_sorted_by_date_then_start_time():
    blocks = [
        block(2, time(18, 0), time(20, 0)),
        block(0, time(14, 0), time(16, 0)),
        block(0, time(9, 0), time(11, 0)),
    ]
    slots = compute_free_slots(blocks, MONDAY)
    assert [(slot.day, slot.start) for slot in slots] == [
        (date(2026, 11, 16), time(9, 0)),
        (date(2026, 11, 16), time(14, 0)),
        (date(2026, 11, 18), time(18, 0)),
    ]


def test_touching_blocks_are_merged():
    blocks = [
        block(0, time(9, 0), time(11, 0)),
        block(0, time(11, 0), time(12, 30)),
    ]
    slots = compute_free_slots(blocks, MONDAY)
    assert slots == [FreeSlot(date(2026, 11, 16), time(9, 0), time(12, 30))]


def test_separate_blocks_are_not_merged():
    blocks = [
        block(0, time(9, 0), time(11, 0)),
        block(0, time(14, 0), time(16, 0)),
    ]
    assert len(compute_free_slots(blocks, MONDAY)) == 2


def test_blocks_on_different_days_are_not_merged():
    # Monday ends at 23:00 and Tuesday starts at 23:00, but they are different dates
    blocks = [
        block(0, time(21, 0), time(23, 0)),
        block(1, time(23, 0), time(23, 59)),
    ]
    assert len(compute_free_slots(blocks, MONDAY)) == 2


def test_longer_window_repeats_the_weekly_block():
    slots = compute_free_slots([block(0, time(9, 0), time(11, 0))], MONDAY, days=8)
    assert [slot.day for slot in slots] == [date(2026, 11, 16), date(2026, 11, 23)]


def test_slot_minutes():
    slot = FreeSlot(MONDAY, time(9, 0), time(11, 30))
    assert slot.minutes == 150