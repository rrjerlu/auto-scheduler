"""Small SQLite persistence layer for the Shiftwise prototype."""

from __future__ import annotations

import json
import hashlib
import secrets
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd


DB_PATH = Path(__file__).with_name("shiftwise.db")
EMPLOYEE_COLUMNS = ["姓名", "可上班日", "可上班班別", "期望休假"]


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with _connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS stores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                available_days TEXT NOT NULL DEFAULT '',
                available_shifts TEXT NOT NULL DEFAULT '',
                preferred_days_off TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(store_id, name),
                FOREIGN KEY(store_id) REFERENCES stores(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS schedule_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id INTEGER NOT NULL,
                week_start TEXT NOT NULL,
                schedule_json TEXT NOT NULL,
                gaps_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(store_id) REFERENCES stores(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'manager', 'staff')),
                store_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(store_id) REFERENCES stores(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS leave_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id INTEGER NOT NULL,
                requester TEXT NOT NULL,
                employee_name TEXT NOT NULL DEFAULT '',
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
                reviewed_by TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(store_id) REFERENCES stores(id) ON DELETE CASCADE
            );
            """
        )
        connection.execute("INSERT OR IGNORE INTO stores (name) VALUES (?)", ("示範門市",))
        store_id = connection.execute("SELECT id FROM stores WHERE name = ?", ("示範門市",)).fetchone()[0]
        for username, password, role in (("admin", "admin123", "admin"), ("manager", "manager123", "manager"), ("staff", "staff123", "staff")):
            connection.execute(
                "INSERT OR IGNORE INTO users (username, password_hash, role, store_id) VALUES (?, ?, ?, ?)",
                (username, hash_password(password), role, store_id),
            )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(leave_requests)")}
        if "employee_name" not in columns:
            connection.execute("ALTER TABLE leave_requests ADD COLUMN employee_name TEXT NOT NULL DEFAULT ''")


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        salt_hex, digest_hex = encoded.split("$", 1)
        expected = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 120_000).hex()
        return secrets.compare_digest(expected, digest_hex)
    except (ValueError, TypeError):
        return False


def authenticate(username: str, password: str) -> dict[str, Any] | None:
    init_db()
    with _connect() as connection:
        row = connection.execute("SELECT id, username, role, store_id, password_hash FROM users WHERE username = ?", (username.strip(),)).fetchone()
    if row is None or not verify_password(password, row["password_hash"]):
        return None
    return {"id": row["id"], "username": row["username"], "role": row["role"], "store_id": row["store_id"]}


def create_leave_request(store_id: int, requester: str, employee_name: str, start_date: str, end_date: str, reason: str) -> None:
    init_db()
    with _connect() as connection:
        connection.execute(
            "INSERT INTO leave_requests (store_id, requester, employee_name, start_date, end_date, reason) VALUES (?, ?, ?, ?, ?, ?)",
            (store_id, requester, employee_name, start_date, end_date, reason),
        )


def list_leave_requests(store_id: int) -> list[dict[str, Any]]:
    init_db()
    with _connect() as connection:
        return [dict(row) for row in connection.execute("SELECT * FROM leave_requests WHERE store_id = ? ORDER BY id DESC", (store_id,))]


def review_leave_request(request_id: int, reviewer: str, status: str) -> None:
    if status not in {"approved", "rejected"}:
        raise ValueError("Invalid leave request status")
    init_db()
    with _connect() as connection:
        connection.execute("UPDATE leave_requests SET status = ?, reviewed_by = ? WHERE id = ?", (status, reviewer, request_id))


def list_stores() -> list[dict[str, Any]]:
    init_db()
    with _connect() as connection:
        return [dict(row) for row in connection.execute("SELECT id, name FROM stores ORDER BY id")]


def create_store(name: str) -> int:
    init_db()
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Store name cannot be empty")
    with _connect() as connection:
        cursor = connection.execute("INSERT INTO stores (name) VALUES (?)", (clean_name,))
        return int(cursor.lastrowid)


def load_employees(store_id: int) -> pd.DataFrame:
    init_db()
    with _connect() as connection:
        rows = connection.execute(
            "SELECT name AS 姓名, available_days AS 可上班日, available_shifts AS 可上班班別, preferred_days_off AS 期望休假 FROM employees WHERE store_id = ? ORDER BY id",
            (store_id,),
        ).fetchall()
    return pd.DataFrame([dict(row) for row in rows], columns=EMPLOYEE_COLUMNS)


def save_employees(store_id: int, employees: pd.DataFrame) -> None:
    init_db()
    with _connect() as connection:
        connection.execute("DELETE FROM employees WHERE store_id = ?", (store_id,))
        for _, row in employees.fillna("").iterrows():
            name = str(row.get("姓名", "")).strip()
            if not name:
                continue
            connection.execute(
                "INSERT OR REPLACE INTO employees (store_id, name, available_days, available_shifts, preferred_days_off) VALUES (?, ?, ?, ?, ?)",
                (store_id, name, str(row.get("可上班日", "")), str(row.get("可上班班別", "")), str(row.get("期望休假", ""))),
            )


def save_schedule(store_id: int, week_start: str, schedule: pd.DataFrame, gaps: list[dict[str, str]]) -> None:
    init_db()
    payload = schedule.to_json(orient="records", force_ascii=False)
    with _connect() as connection:
        connection.execute(
            "INSERT INTO schedule_versions (store_id, week_start, schedule_json, gaps_json) VALUES (?, ?, ?, ?)",
            (store_id, week_start, payload, json.dumps(gaps, ensure_ascii=False)),
        )


def load_latest_schedule(store_id: int, week_start: str) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    init_db()
    with _connect() as connection:
        row = connection.execute(
            "SELECT schedule_json, gaps_json FROM schedule_versions WHERE store_id = ? AND week_start = ? ORDER BY id DESC LIMIT 1",
            (store_id, week_start),
        ).fetchone()
    if row is None:
        return pd.DataFrame(), []
    return pd.DataFrame(json.loads(row["schedule_json"])), json.loads(row["gaps_json"])
