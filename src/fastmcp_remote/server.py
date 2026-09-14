import sqlite3
from pathlib import Path
from fastmcp import FastMCP

# ---------------------------------------------------------
# FastMCP Server
# ---------------------------------------------------------

mcp = FastMCP("Expense Tracker")


# ---------------------------------------------------------
# Database Configuration
# ---------------------------------------------------------

# Project root:
# fastmcp remote/
# ├── src/
# │   └── fastmcp_remote/
# │       └── server.py
# └── data/
#     └── expenses.db

PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_DIR / "data"

# Create the data directory if it doesn't exist
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_NAME = DATA_DIR / "expenses.db"


# ---------------------------------------------------------
# Database Connection
# ---------------------------------------------------------


def get_db_connection():
    """Create and return a SQLite database connection."""

    conn = sqlite3.connect(
        DB_NAME,
        timeout=10,
    )

    conn.row_factory = sqlite3.Row

    return conn


# ---------------------------------------------------------
# Database Initialization
# ---------------------------------------------------------


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


# Initialize database when server starts
init_db()


# ---------------------------------------------------------
# Add Expense
# ---------------------------------------------------------


@mcp.tool
def add_expense(
    description: str,
    amount: float,
    category: str,
) -> str:
    """Add a new expense."""

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


# ---------------------------------------------------------
# List Expenses
# ---------------------------------------------------------


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


# ---------------------------------------------------------
# Summarize Expenses
# ---------------------------------------------------------


@mcp.tool
def summarize_expenses() -> dict:
    """Return total expenses and spending grouped by category."""

    conn = get_db_connection()

    try:
        # Total expenses
        total_row = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM expenses
            """).fetchone()

        # Expenses grouped by category
        category_rows = conn.execute("""
            SELECT
                category,
                SUM(amount) AS total
            FROM expenses
            GROUP BY category
            ORDER BY total DESC
            """).fetchall()

        # Number of expenses
        count_row = conn.execute("""
            SELECT COUNT(*) AS count
            FROM expenses
            """).fetchone()

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


# ---------------------------------------------------------
# Delete Expense
# ---------------------------------------------------------


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


# ---------------------------------------------------------
# Start MCP Server
# ---------------------------------------------------------

if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8000,
    )
