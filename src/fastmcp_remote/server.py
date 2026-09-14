import sqlite3
from pathlib import Path

from fastmcp import FastMCP

# =========================================================
# FastMCP SERVER
# =========================================================

mcp = FastMCP("Expense Tracker")


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

# Project structure:
#
# fastmcp remote/
# ├── data/
# │   └── expenses.db
# ├── src/
# │   └── fastmcp_remote/
# │       └── server.py
# ├── pyproject.toml
# └── .venv/
#
# server.py is:
# project/src/fastmcp_remote/server.py
#
# parents[0] = fastmcp_remote
# parents[1] = src
# parents[2] = project root

PROJECT_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_DIR / "data"

# Make sure the data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_NAME = DATA_DIR / "expenses.db"


# =========================================================
# DATABASE CONNECTION
# =========================================================


def get_db_connection():
    """Create a SQLite database connection."""

    conn = sqlite3.connect(
        str(DB_NAME),
        timeout=10,
    )

    conn.row_factory = sqlite3.Row

    return conn


# =========================================================
# DATABASE INITIALIZATION
# =========================================================


def init_db():
    """Create the expenses table if it doesn't exist."""

    conn = get_db_connection()

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

        conn.commit()

    finally:
        conn.close()


# Initialize database when the server starts
init_db()


# =========================================================
# ADD EXPENSE
# =========================================================


@mcp.tool
def add_expense(
    description: str,
    amount: float,
    category: str,
) -> str:
    """Add a new expense to the expense tracker."""

    if amount <= 0:
        return "Error: amount must be greater than 0."

    conn = get_db_connection()

    try:
        cursor = conn.execute(
            """
            INSERT INTO expenses (
                description,
                amount,
                category
            )
            VALUES (?, ?, ?)
            """,
            (
                description,
                amount,
                category,
            ),
        )

        expense_id = cursor.lastrowid

        conn.commit()

        return (
            f"Expense added successfully. "
            f"ID: {expense_id}, "
            f"{description} - ₹{amount:.2f} ({category})"
        )

    finally:
        conn.close()


# =========================================================
# LIST EXPENSES
# =========================================================


@mcp.tool
def list_expenses() -> list[dict]:
    """List all expenses."""

    conn = get_db_connection()

    try:
        rows = conn.execute("""
            SELECT
                id,
                description,
                amount,
                category,
                created_at
            FROM expenses
            ORDER BY created_at DESC
            """).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


# =========================================================
# SUMMARIZE EXPENSES
# =========================================================


@mcp.tool
def summarize_expenses() -> dict:
    """Return total expenses and spending grouped by category."""

    conn = get_db_connection()

    try:
        # Total amount
        total_row = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM expenses
            """).fetchone()

        # Number of expenses
        count_row = conn.execute("""
            SELECT COUNT(*) AS count
            FROM expenses
            """).fetchone()

        # Group by category
        category_rows = conn.execute("""
            SELECT
                category,
                SUM(amount) AS total
            FROM expenses
            GROUP BY category
            ORDER BY total DESC
            """).fetchall()

        return {
            "total_expenses": round(
                total_row["total"],
                2,
            ),
            "number_of_expenses": count_row["count"],
            "by_category": {
                row["category"]: round(
                    row["total"],
                    2,
                )
                for row in category_rows
            },
        }

    finally:
        conn.close()


# =========================================================
# DELETE EXPENSE
# =========================================================


@mcp.tool
def delete_expense(expense_id: int) -> str:
    """Delete an expense using its ID."""

    conn = get_db_connection()

    try:
        cursor = conn.execute(
            """
            DELETE FROM expenses
            WHERE id = ?
            """,
            (expense_id,),
        )

        deleted = cursor.rowcount

        conn.commit()

        if deleted == 0:
            return f"No expense found with ID {expense_id}."

        return f"Expense {expense_id} deleted successfully."

    finally:
        conn.close()


# =========================================================
# DATABASE DIAGNOSTIC
# =========================================================


@mcp.tool
def database_status() -> dict:
    """
    Check the database path and verify that the database is writable.
    Useful for diagnosing remote MCP connector issues.
    """

    conn = None

    try:
        conn = get_db_connection()

        # Test SQLite write access inside a temporary table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _write_test (
                id INTEGER
            )
            """)

        conn.execute("""
            INSERT INTO _write_test (id)
            VALUES (1)
            """)

        conn.execute("""
            DELETE FROM _write_test
            """)

        conn.commit()

        return {
            "status": "ok",
            "database_path": str(DB_NAME),
            "database_exists": DB_NAME.exists(),
            "database_writable": True,
            "data_directory": str(DATA_DIR),
            "data_directory_exists": DATA_DIR.exists(),
        }

    except Exception as e:
        return {
            "status": "error",
            "database_path": str(DB_NAME),
            "database_exists": DB_NAME.exists(),
            "database_writable": False,
            "error": str(e),
        }

    finally:
        if conn is not None:
            conn.close()


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8000,
    )
