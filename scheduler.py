"""Constraint-aware scheduling engine for service businesses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class Shift:
    name: str
    start: str
    end: str
    hours: float


@dataclass
class Employee:
    name: str
    available_days: set[str]
    available_shifts: set[str]
    preferred_days_off: set[str]


DAY_KEYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAY_LABELS = {
    "Mon": "週一",
    "Tue": "週二",
    "Wed": "週三",
    "Thu": "週四",
    "Fri": "週五",
    "Sat": "週六",
    "Sun": "週日",
}


def _consecutive_days(worked: set[int], day_index: int) -> int:
    """Return the consecutive run that would exist if day_index were worked."""
    run = 1
    previous = day_index - 1
    while previous in worked:
        run += 1
        previous -= 1
    following = day_index + 1
    while following in worked:
        run += 1
        following += 1
    return run


def build_week(start: date) -> list[date]:
    """Return a Monday-to-Sunday week containing start."""
    monday = start - timedelta(days=start.weekday())
    return [monday + timedelta(days=offset) for offset in range(7)]


def generate_schedule(
    employees: Iterable[Employee],
    shifts: Iterable[Shift],
    week_dates: list[date],
    demand: dict[str, dict[str, int]],
    max_weekly_hours: float = 40,
    max_consecutive_days: int = 6,
    absences: dict[str, set[str]] | None = None,
) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    """Generate a practical greedy schedule and report uncovered demand slots.

    The engine intentionally favours explainability: every assignment is made
    from the currently eligible employees and scored for fairness and preference.
    """
    employees = list(employees)
    shifts = list(shifts)
    absences = absences or {}
    hours_by_employee = {employee.name: 0.0 for employee in employees}
    worked_by_employee: dict[str, set[int]] = {employee.name: set() for employee in employees}
    assignments: list[dict[str, object]] = []
    gaps: list[dict[str, str]] = []

    for day_index, work_date in enumerate(week_dates):
        day_key = DAY_KEYS[work_date.weekday()]
        date_key = work_date.isoformat()
        day_demand = demand.get(date_key, {})
        for shift in shifts:
            required = max(0, int(day_demand.get(shift.name, 0)))
            for slot_number in range(required):
                eligible: list[tuple[tuple[float, ...], Employee]] = []
                for employee in employees:
                    if employee.name in absences.get(date_key, set()):
                        continue
                    if day_key not in employee.available_days:
                        continue
                    if shift.name not in employee.available_shifts:
                        continue
                    if employee.name in {
                        row["employee"]
                        for row in assignments
                        if row["date"] == date_key
                    }:
                        continue
                    if hours_by_employee[employee.name] + shift.hours > max_weekly_hours:
                        continue
                    if _consecutive_days(worked_by_employee[employee.name], day_index) > max_consecutive_days:
                        continue

                    preference_penalty = 1.0 if day_key in employee.preferred_days_off else 0.0
                    consecutive_score = float(_consecutive_days(worked_by_employee[employee.name], day_index))
                    fairness_score = hours_by_employee[employee.name]
                    eligible.append(((preference_penalty, consecutive_score, fairness_score), employee))

                if not eligible:
                    gaps.append(
                        {
                            "date": date_key,
                            "day": DAY_LABELS[day_key],
                            "shift": shift.name,
                            "slot": str(slot_number + 1),
                            "reason": "沒有符合目前限制的員工（可能包含臨時請假）",
                        }
                    )
                    continue

                _, selected = min(eligible, key=lambda item: item[0])
                hours_by_employee[selected.name] += shift.hours
                worked_by_employee[selected.name].add(day_index)
                assignments.append(
                    {
                        "date": date_key,
                        "day": DAY_LABELS[day_key],
                        "employee": selected.name,
                        "shift": shift.name,
                        "time": f"{shift.start} - {shift.end}",
                        "hours": shift.hours,
                        "preference": "休假偏好" if day_key in selected.preferred_days_off else "符合條件",
                    }
                )

    columns = ["date", "day", "employee", "shift", "time", "hours", "preference"]
    return pd.DataFrame(assignments, columns=columns), gaps


def audit_schedule(schedule: pd.DataFrame, max_weekly_hours: float = 40, min_rest_hours: float = 11) -> list[dict[str, str]]:
    """Return explainable labor-rule warnings for an existing schedule."""
    if schedule.empty:
        return []
    violations: list[dict[str, str]] = []
    hours = schedule.groupby("employee")["hours"].sum()
    for employee, total_hours in hours.items():
        if total_hours > max_weekly_hours:
            violations.append({"type": "工時", "employee": str(employee), "message": f"本週 {total_hours:.1f} 小時，超過上限 {max_weekly_hours:.1f} 小時"})

    working = schedule.copy()
    working["start_at"] = pd.to_datetime(working["date"] + " " + working["time"].str.split(" - ").str[0])
    working["end_at"] = pd.to_datetime(working["date"] + " " + working["time"].str.split(" - ").str[1])
    for employee, rows in working.sort_values("start_at").groupby("employee"):
        rows = rows.sort_values("start_at")
        previous = None
        for _, row in rows.iterrows():
            if previous is not None:
                rest_hours = (row["start_at"] - previous["end_at"]).total_seconds() / 3600
                if rest_hours < min_rest_hours:
                    violations.append({"type": "休息", "employee": str(employee), "message": f"{previous['date']} 後僅休息 {rest_hours:.1f} 小時，低於 {min_rest_hours:.0f} 小時"})
            previous = row
    return violations
