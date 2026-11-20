# *** NEW ***
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