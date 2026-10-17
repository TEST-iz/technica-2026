import sqlite3
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)
DB_PATH = "winners.db"

_CREATE_INPUT_TABLE = """
CREATE TABLE IF NOT EXISTS input (
    input_id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_assembly TEXT
);
"""

_CREATE_OUTPUT_TABLE = """
CREATE TABLE IF NOT EXISTS output (
    output_id INTEGER PRIMARY KEY AUTOINCREMENT,
    input_id INTEGER,
    llm_output TEXT,
    FOREIGN KEY (input_id) REFERENCES input(input_id)
);
"""

@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL;")
    try:
        yield c
    finally:
        c.close()

def init_db():
    try:
        with conn() as c:
            c.execute(_CREATE_INPUT_TABLE)
            c.execute(_CREATE_OUTPUT_TABLE)
    except Exception as exc:
        logger.error("DB init failed %s", exc)
        raise


def save_input(payload: str) -> int:
    try:
        with conn() as c:
            c.execute("INSERT INTO input (raw_assembly) VALUES (?);", (payload,))
            input_id = c.lastrowid
            return input_id
    except Exception as exc:
        logger.error("Failed to save input payload: %s", exc)
        raise

def get_input(id: int) -> str:
    try:
        with conn() as c:
            row = c.execute("SELECT raw_assembly FROM input WHERE input_id = (?);", (id,)).fetchone()
            if row is None:
                raise ValueError(f"No input found with ID {id}")
            return row["raw_assembly"]
    except Exception as exc:
        logger.error("Failed to retrieve data")
        raise

def save_output(payload: str, input_id: int) -> None:
    try:
        with conn() as c:
            c.execute("INSERT INTO output (input_id, llm_output) VALUES (?, ?);", (input_id, payload))
            return None
    except Exception as exc:
        logger.error("Failed to save output payload: %s", exc)
        raise

def get_output(input_id: int) -> str:
    try:
        with conn() as c:
            row = c.execute("SELECT llm_output FROM output WHERE input_id = (?);", (input_id,)).fetchone()
            if row is None:
                raise ValueError(f"No output found with ID {input_id}")
            return row["llm_output"]
    except Exception as exc:
        logger.error("Failed to retrieve data")
        raise
