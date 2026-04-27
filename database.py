import sqlite3
from pathlib import Path

DB_PATH = Path("data/enterprise.db")


def get_connection():
    """Create and return database connection."""
    return sqlite3.connect(DB_PATH)


def create_tables():
    """Create all required tables for the project."""
    conn = get_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        department TEXT,
        email TEXT
    )
    """)

    # Leave balance table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leave_balance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        casual_leave INTEGER DEFAULT 12,
        sick_leave INTEGER DEFAULT 10,
        earned_leave INTEGER DEFAULT 15,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    # Leave requests table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leave_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        leave_type TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'Pending Manager Approval',
        approver_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    # IT tickets table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS it_tickets (
        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        issue_type TEXT NOT NULL,
        description TEXT,
        priority TEXT DEFAULT 'Medium',
        status TEXT DEFAULT 'Open',
        assigned_engineer TEXT DEFAULT 'IT Team',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    # Asset requests table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS asset_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        asset_type TEXT NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'Pending Manager Approval',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    # Chat memory table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_memory (
        memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        user_message TEXT NOT NULL,
        bot_response TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    # Logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        query TEXT,
        intent TEXT,
        agent_used TEXT,
        tool_used TEXT,
        status TEXT,
        response_time REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def insert_sample_users():
    """Insert sample users and leave balances."""
    conn = get_connection()
    cursor = conn.cursor()

    users = [
        ("EMP001", "Rifa", "Employee", "Engineering", "rifa@example.com"),
        ("MGR001", "Ayesha", "Manager", "Engineering", "ayesha@example.com"),
        ("IT001", "John", "IT Team", "IT", "john@example.com"),
        ("HR001", "Sara", "HR Team", "HR", "sara@example.com"),
        ("ADMIN001", "Admin", "Admin", "Administration", "admin@example.com"),
    ]

    cursor.executemany("""
    INSERT OR IGNORE INTO users (user_id, name, role, department, email)
    VALUES (?, ?, ?, ?, ?)
    """, users)

    for user in users:
        user_id = user[0]
        cursor.execute("""
        INSERT OR IGNORE INTO leave_balance (user_id, casual_leave, sick_leave, earned_leave)
        VALUES (?, 12, 10, 15)
        """, (user_id,))

    conn.commit()
    conn.close()


def show_users():
    """Display inserted users for testing."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT user_id, name, role, department, email FROM users")
    users = cursor.fetchall()

    conn.close()

    print("\nSample Users:")
    print("-" * 60)
    for user in users:
        print(user)


def main():
    DB_PATH.parent.mkdir(exist_ok=True)

    create_tables()
    insert_sample_users()
    show_users()

    print("\nDatabase created successfully!")
    print(f"Database path: {DB_PATH}")


if __name__ == "__main__":
    main()