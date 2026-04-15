"""
Persistent State Manager — SQLite Backend
==========================================
Replaces in-memory _state dict with SQLite-backed storage.
Supports per-user sessions, server restart survival, and scenario management.
"""
import sqlite3
import json
import os
import time
import numpy as np
import pandas as pd
from typing import Dict, Optional, Any
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("YIELD_DB_PATH", "yield_intelligence.db")


class NumpyEncoder(json.JSONEncoder):
    """Handle numpy types in JSON serialization."""
    def default(self, obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, (np.bool_,)): return bool(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, pd.Timestamp): return str(obj)
        return super().default(obj)


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'analyst',
            created_at REAL DEFAULT (strftime('%s','now'))
        );
        
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            state_json TEXT,
            updated_at REAL DEFAULT (strftime('%s','now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        
        CREATE TABLE IF NOT EXISTS scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_id TEXT,
            name TEXT NOT NULL,
            description TEXT,
            parameters TEXT,
            results TEXT,
            created_at REAL DEFAULT (strftime('%s','now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        
        CREATE TABLE IF NOT EXISTS external_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            data_type TEXT NOT NULL,
            filename TEXT,
            data_json TEXT,
            uploaded_at REAL DEFAULT (strftime('%s','now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {DB_PATH}")


def save_session(session_id: str, state: Dict, user_id: int = None):
    """Save session state to database. Strips DataFrames (stored as JSON-safe dicts)."""
    # Convert state to JSON-safe format (strip DataFrames, numpy)
    safe_state = {}
    skip_keys = {"campaign_data", "journey_data", "reporting_data", "training_data",
                 "attribution", "attribution_roi", "_attr_dicts",
                 "external_competitive", "external_events", "external_trends"}
    
    for k, v in state.items():
        if k in skip_keys:
            # Store metadata only (not full DataFrames)
            if v is not None and hasattr(v, 'shape'):
                safe_state[f"_meta_{k}"] = {"rows": len(v), "columns": list(v.columns)}
            elif v is not None and isinstance(v, dict) and any(hasattr(vv, 'shape') for vv in v.values()):
                safe_state[f"_meta_{k}"] = {"keys": list(v.keys())}
            continue
        try:
            json.dumps(v, cls=NumpyEncoder)
            safe_state[k] = v
        except (TypeError, ValueError):
            logger.debug(f"Skipping non-serializable key: {k}")
    
    conn = _get_conn()
    state_json = json.dumps(safe_state, cls=NumpyEncoder)
    conn.execute(
        "INSERT OR REPLACE INTO sessions (id, user_id, state_json, updated_at) VALUES (?, ?, ?, ?)",
        (session_id, user_id, state_json, time.time())
    )
    conn.commit()
    conn.close()


def load_session(session_id: str) -> Optional[Dict]:
    """Load session state from database."""
    conn = _get_conn()
    row = conn.execute("SELECT state_json FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    if row and row["state_json"]:
        return json.loads(row["state_json"])
    return None


def save_scenario(user_id: int, session_id: str, name: str, description: str,
                  parameters: Dict, results: Dict) -> int:
    """Save an optimizer scenario."""
    conn = _get_conn()
    cursor = conn.execute(
        "INSERT INTO scenarios (user_id, session_id, name, description, parameters, results) VALUES (?,?,?,?,?,?)",
        (user_id, session_id, name, description,
         json.dumps(parameters, cls=NumpyEncoder),
         json.dumps(results, cls=NumpyEncoder))
    )
    conn.commit()
    scenario_id = cursor.lastrowid
    conn.close()
    return scenario_id


def list_scenarios(user_id: int = None, session_id: str = None) -> list:
    """List saved scenarios."""
    conn = _get_conn()
    if user_id:
        rows = conn.execute(
            "SELECT id, name, description, parameters, created_at FROM scenarios WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
    elif session_id:
        rows = conn.execute(
            "SELECT id, name, description, parameters, created_at FROM scenarios WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, name, description, parameters, created_at FROM scenarios ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
    conn.close()
    return [{"id": r["id"], "name": r["name"], "description": r["description"],
             "parameters": json.loads(r["parameters"]) if r["parameters"] else {},
             "created_at": r["created_at"]} for r in rows]


def load_scenario(scenario_id: int) -> Optional[Dict]:
    """Load a saved scenario."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM scenarios WHERE id = ?", (scenario_id,)
    ).fetchone()
    conn.close()
    if row:
        return {
            "id": row["id"], "name": row["name"], "description": row["description"],
            "parameters": json.loads(row["parameters"]) if row["parameters"] else {},
            "results": json.loads(row["results"]) if row["results"] else {},
            "created_at": row["created_at"],
        }
    return None


def compare_scenarios(ids: list) -> list:
    """Load multiple scenarios for comparison."""
    conn = _get_conn()
    placeholders = ",".join(["?"] * len(ids))
    rows = conn.execute(
        f"SELECT * FROM scenarios WHERE id IN ({placeholders})", ids
    ).fetchall()
    conn.close()
    return [{
        "id": r["id"], "name": r["name"],
        "parameters": json.loads(r["parameters"]) if r["parameters"] else {},
        "results": json.loads(r["results"]) if r["results"] else {},
    } for r in rows]


# ── Auth helpers ──

def create_user(username: str, password_hash: str, role: str = "analyst") -> int:
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, password_hash, role)
        )
        conn.commit()
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError(f"Username '{username}' already exists")
    conn.close()
    return user_id


def get_user(username: str) -> Optional[Dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if row:
        return {"id": row["id"], "username": row["username"],
                "password_hash": row["password_hash"], "role": row["role"]}
    return None


def get_user_by_id(user_id: int) -> Optional[Dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if row:
        return {"id": row["id"], "username": row["username"], "role": row["role"]}
    return None


# Initialize on import
init_db()
