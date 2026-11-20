# *** NEW ***
from datetime import date, time
from types import SimpleNamespace

from app.scheduler import (
    FreeSlot,
    ScheduleResult,
    StudySession,
    UnscheduledWork,
    build_schedule,
)

# November 2026: the 16th is a Monday
MONDAY = date(2026, 11, 16)
TUESDAY = date(2026, 11, 17)
WEDNESDAY = date(2026, 11, 18)
THURSDAY = date(2026, 11, 19)
FRIDAY = date(2026, 11, 20)


def assignment(assignment_id, due, hours):
    return SimpleNamespace(id=assignment_id, due_date=due, estimated_hours=hours)


def slot(day, start, end):
    return FreeSlot(day, start, end)


def test_nothing_to_schedule():
    result = build_schedule([], [slot(MONDAY, time(9, 0), time(11, 0))], MONDAY)
    assert result == ScheduleResult(sessions=[], unscheduled=[])


def test_no_free_time_leaves_everything_unscheduled():
    result = build_schedule([assignment(1, FRIDAY, 2)], [], MONDAY)
    assert result.sessions == []
    assert result.unscheduled == [UnscheduledWork(1, 120)]


def test_assignment_that_fits_in_one_slot():
    result = build_schedule(
        [assignment(1, FRIDAY, 2)],
        [slot(MONDAY, time(9, 0), time(12, 0))],
        MONDAY,
    )
    assert result.sessions == [StudySession(1, MONDAY, time(9, 0), time(11, 0))]
    assert result.unscheduled == []


def test_earliest_deadline_goes_first():
    # A is due Friday, B is due Wednesday, so B gets the first hour
    result = build_schedule(
        [assignment(1, FRIDAY, 1), assignment(2, WEDNESDAY, 1)],
        [slot(MONDAY, time(9, 0), time(11, 0))],
        MONDAY,
    )
    assert result.sessions == [
        StudySession(2, MONDAY, time(9, 0), time(10, 0)),
        StudySession(1, MONDAY, time(10, 0), time(11, 0)),
    ]
    assert result.unscheduled == []


def test_ties_are_broken_by_id():
    result = build_schedule(
        [assignment(2, FRIDAY, 1), assignment(1, FRIDAY, 1)],
        [slot(MONDAY, time(9, 0), time(10, 0))],
        MONDAY,
    )
    assert result.sessions == [StudySession(1, MONDAY, time(9, 0), time(10, 0))]
    assert result.unscheduled == [UnscheduledWork(2, 60)]


def test_assignment_is_split_across_slots():
    result = build_schedule(
        [assignment(1, FRIDAY, 3)],
        [
            slot(MONDAY, time(9, 0), time(11, 0)),
            slot(TUESDAY, time(9, 0), time(10, 0)),
        ],
        MONDAY,
    )
    assert result.sessions == [
        StudySession(1, MONDAY, time(9, 0), time(11, 0)),
        StudySession(1, TUESDAY, time(9, 0), time(10, 0)),
    ]
    assert result.unscheduled == []


def test_not_enough_time_reports_the_shortfall():
    # Needs 5 hours but only 3 hours are free
    result = build_schedule(
        [assignment(1, FRIDAY, 5)],
        [
            slot(MONDAY, time(9, 0), time(11, 0)),
            slot(TUESDAY, time(9, 0), time(10, 0)),
        ],
        MONDAY,
    )
    assert result.unscheduled == [UnscheduledWork(1, 120)]


def test_nothing_is_scheduled_after_the_due_date():
    # Due Monday: Monday's slot counts (the due date itself), Tuesday's does not
    result = build_schedule(
        [assignment(1, MONDAY, 2)],
        [
            slot(MONDAY, time(9, 0), time(10, 0)),
            slot(TUESDAY, time(9, 0), time(11, 0)),
        ],
        MONDAY,
    )
    assert result.sessions == [StudySession(1, MONDAY, time(9, 0), time(10, 0))]
    assert result.unscheduled == [UnscheduledWork(1, 60)]


def test_time_is_not_wasted_on_an_assignment_that_is_too_late():
    # A is due Monday, so Tuesday's slot goes to B instead
    result = build_schedule(
        [assignment(1, MONDAY, 1), assignment(2, FRIDAY, 2)],
        [slot(TUESDAY, time(9, 0), time(11, 0))],
        MONDAY,
    )
    assert result.sessions == [StudySession(2, TUESDAY, time(9, 0), time(11, 0))]
    assert result.unscheduled == [UnscheduledWork(1, 60)]


def test_overdue_work_is_scheduled_first():
    # Window starts Wednesday; assignment 1 was due Monday, so it is overdue
    result = build_schedule(
        [assignment(2, FRIDAY, 1), assignment(1, MONDAY, 1)],
        [slot(WEDNESDAY, time(9, 0), time(11, 0))],
        WEDNESDAY,
    )
    assert result.sessions == [
        StudySession(1, WEDNESDAY, time(9, 0), time(10, 0)),
        StudySession(2, WEDNESDAY, time(10, 0), time(11, 0)),
    ]


def test_overdue_work_can_use_any_slot_in_the_window():
    result = build_schedule(
        [assignment(1, MONDAY, 1)],
        [slot(THURSDAY, time(9, 0), time(10, 0))],
        WEDNESDAY,
    )
    assert result.sessions == [StudySession(1, THURSDAY, time(9, 0), time(10, 0))]
    assert result.unscheduled == []


def test_fractional_hours_become_minutes():
    result = build_schedule(
        [assignment(1, FRIDAY, 1.5)],
        [slot(MONDAY, time(9, 0), time(12, 0))],
        MONDAY,
    )
    assert result.sessions == [StudySession(1, MONDAY, time(9, 0), time(10, 30))]


def test_a_tiny_estimate_is_never_lost():
    result = build_schedule(
        [assignment(1, FRIDAY, 0.001)],
        [slot(MONDAY, time(9, 0), time(10, 0))],
        MONDAY,
    )
    assert result.sessions == [StudySession(1, MONDAY, time(9, 0), time(9, 1))]