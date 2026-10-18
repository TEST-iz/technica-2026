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

_CREATE_SCORES_TABLE = """
CREATE TABLE IF NOT EXISTS scores (
    score_id INTEGER PRIMARY KEY AUTOINCREMENT,
    input_id INTEGER,
    candidate_name TEXT,
    similarity_score REAL,
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
            c.execute(_CREATE_SCORES_TABLE)
    except Exception as exc:
        logger.error("DB init failed %s", exc)
        raise


def save_input(payload: str) -> int:
    try:
        with conn() as c:
            cursor = c.cursor()
            cursor.execute("INSERT INTO input (raw_assembly) VALUES (?);", (payload,))
            input_id = cursor.lastrowid
            c.commit()
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
            c.commit()
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

def save_scores(input_id: int, matches: list[tuple[str, float]]):
    try:
        with conn() as c:
            for candidate_name, score in matches:
                c.execute("INSERT INTO scores (input_id, candidate_name, similarity_score) VALUES (?, ?, ?);", (input_id, candidate_name, score))
            c.commit()    
    except Exception as exc:
        logger.error("Failed to save similarity scores: %s", exc)
        raise

def get_scores(input_id: int) -> list:
    try:
        with conn() as c:
            rows = c.execute(
                "SELECT candidate_name, similarity_score FROM scores WHERE input_id = ? ORDER BY similarity_score DESC;",
                (input_id,)
            ).fetchall()
            return [dict(row) for row in rows]
    except Exception as exc:
        logger.error("Failed to retrieve scores: %s", exc)
        raise

def main():
    init_db()
if __name__ == "__main__":
    main()
