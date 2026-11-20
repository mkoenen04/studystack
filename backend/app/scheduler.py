from dataclasses import dataclass
from datetime import date, time, timedelta


@dataclass(frozen=True)
class FreeSlot:
    """A stretch of time on one calendar date when the student can study."""

    day: date
    start: time
    end: time

    @property
    def minutes(self) -> int:
        start_minutes = self.start.hour * 60 + self.start.minute
        end_minutes = self.end.hour * 60 + self.end.minute
        return end_minutes - start_minutes


def compute_free_slots(blocks, start_date: date, days: int = 7) -> list[FreeSlot]:
    """Turns weekly availability blocks into free slots on real dates.

    blocks: anything with day_of_week (0 = Monday ... 6 = Sunday), start_time, end_time.
    start_date: the first day of the planning window.
    days: how many days the window covers, including start_date.

    Blocks that touch (one ends exactly when the next starts) are merged into one slot.
    The result is sorted by date and then start time.
    """
    slots: list[FreeSlot] = []

    for offset in range(days):
        current_day = start_date + timedelta(days=offset)

        # date.weekday() uses the same numbering as the database: 0 = Monday ... 6 = Sunday
        todays_blocks = sorted(
            (block for block in blocks if block.day_of_week == current_day.weekday()),
            key=lambda block: block.start_time,
        )

        for block in todays_blocks:
            previous = slots[-1] if slots else None
            if previous is not None and previous.day == current_day and previous.end == block.start_time:
                # Touching blocks form one continuous slot
                slots[-1] = FreeSlot(current_day, previous.start, block.end_time)
            else:
                slots.append(FreeSlot(current_day, block.start_time, block.end_time))

    return slots


# *** NEW ***
@dataclass(frozen=True)
class StudySession:
    """One planned stretch of work on one assignment."""

    assignment_id: int
    day: date
    start: time
    end: time


# *** NEW ***
@dataclass(frozen=True)
class UnscheduledWork:
    """Time an assignment still needs that did not fit into the free slots."""

    assignment_id: int
    minutes: int


# *** NEW ***
@dataclass(frozen=True)
class ScheduleResult:
    sessions: list[StudySession]
    unscheduled: list[UnscheduledWork]


# *** NEW ***
def _to_minutes(value: time) -> int:
    return value.hour * 60 + value.minute


# *** NEW ***
def _to_time(minutes: int) -> time:
    return time(minutes // 60, minutes % 60)


# *** NEW ***
def build_schedule(assignments, slots, start_date: date) -> ScheduleResult:
    """Plans study sessions using earliest-deadline-first.

    assignments: anything with id, due_date, and estimated_hours (only incomplete ones should be passed in).
    slots: free slots from compute_free_slots.
    start_date: the first day of the planning window. Assignments due before it are overdue.

    Slots are filled in time order. In each slot, the assignment with the earliest due date that
    still needs time and can still be done by its due date gets the time first. Overdue assignments
    are scheduled first and may use any slot. Work that does not fit is returned as unscheduled.
    """
    # Minutes each assignment still needs (at least 1, so a tiny estimate is never lost)
    remaining = {
        assignment.id: max(1, round(assignment.estimated_hours * 60))
        for assignment in assignments
    }
    ordered = sorted(assignments, key=lambda assignment: (assignment.due_date, assignment.id))

    sessions: list[StudySession] = []

    for slot in sorted(slots, key=lambda slot: (slot.day, slot.start)):
        cursor = _to_minutes(slot.start)
        slot_end = _to_minutes(slot.end)

        for assignment in ordered:
            if cursor >= slot_end:
                break
            if remaining[assignment.id] <= 0:
                continue

            is_overdue = assignment.due_date < start_date
            if not is_overdue and slot.day > assignment.due_date:
                # Too late for this assignment; leave the time for the next one
                continue

            used = min(remaining[assignment.id], slot_end - cursor)
            sessions.append(
                StudySession(
                    assignment_id=assignment.id,
                    day=slot.day,
                    start=_to_time(cursor),
                    end=_to_time(cursor + used),
                )
            )
            remaining[assignment.id] -= used
            cursor += used

    unscheduled = [
        UnscheduledWork(assignment_id=assignment.id, minutes=remaining[assignment.id])
        for assignment in ordered
        if remaining[assignment.id] > 0
    ]
    return ScheduleResult(sessions=sessions, unscheduled=unscheduled)