import sqlite3
from pathlib import Path
from fastmcp import FastMCP

mcp = FastMCP("Expense Tracker")

BASE_DIR = Path(__file__).resolve().parent
DB_NAME = BASE_DIR / "expenses.db"


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

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
    conn.close()


# Initialize database as soon as server starts/imports
init_db()


@mcp.tool
def add_expense(description: str, amount: float, category: str) -> str:
    """Add a new expense."""

    if amount <= 0:
        return "Error: amount must be greater than 0."

    conn = get_db_connection()

    cursor = conn.execute(
        """
        INSERT INTO expenses (description, amount, category)
        VALUES (?, ?, ?)
        """,
        (description, amount, category),
    )

    expense_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return (
        f"Expense added successfully. "
        f"ID: {expense_id}, "
        f"{description} - ₹{amount:.2f} ({category})"
    )


@mcp.tool
def list_expenses() -> list[dict]:
    """List all expenses."""

    conn = get_db_connection()

    rows = conn.execute("""
        SELECT id, description, amount, category, created_at
        FROM expenses
        ORDER BY created_at DESC
    """).fetchall()

    conn.close()

    return [dict(row) for row in rows]


@mcp.tool
def summarize_expenses() -> dict:
    """Return total expenses and spending grouped by category."""

    conn = get_db_connection()

    total_row = conn.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM expenses
    """).fetchone()

    category_rows = conn.execute("""
        SELECT category, SUM(amount) AS total
        FROM expenses
        GROUP BY category
        ORDER BY total DESC
    """).fetchall()

    count_row = conn.execute("""
        SELECT COUNT(*) AS count
        FROM expenses
    """).fetchone()

    conn.close()

    return {
        "total_expenses": round(total_row["total"], 2),
        "number_of_expenses": count_row["count"],
        "by_category": {
            row["category"]: round(row["total"], 2) for row in category_rows
        },
    }


@mcp.tool
def delete_expense(expense_id: int) -> str:
    """Delete an expense using its ID."""

    conn = get_db_connection()

    cursor = conn.execute(
        """
        DELETE FROM expenses
        WHERE id = ?
        """,
        (expense_id,),
    )

    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if deleted == 0:
        return f"No expense found with ID {expense_id}."

    return f"Expense {expense_id} deleted successfully."


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
