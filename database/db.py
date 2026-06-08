import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash


DATABASE = "spendly.db"

# Valid expense categories
VALID_CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


def is_valid_date(date_str):
    """Validate date string in YYYY-MM-DD format.

    Args:
        date_str (str): Date string to validate

    Returns:
        bool: True if valid YYYY-MM-DD date or empty string, False otherwise
    """
    if not date_str or date_str == '':
        return True  # Empty string means no filter
    try:
        # Try to parse as YYYY-MM-DD
        parts = date_str.split('-')
        if len(parts) != 3:
            return False
        year, month, day = parts
        # Check that we have exactly 4 digits, 2 digits, 2 digits
        if len(year) != 4 or len(month) != 2 or len(day) != 2:
            return False
        # Try to convert to integers
        year_int = int(year)
        month_int = int(month)
        day_int = int(day)
        # Basic range checking
        if month_int < 1 or month_int > 12:
            return False
        if day_int < 1 or day_int > 31:
            return False
        # Additional check for days in month (simplified)
        return True
    except ValueError:
        return False


def validate_expense_form(amount_str, category, date_str):
    """Validate expense form data and return list of error messages.

    Args:
        amount_str (str): Amount as string from form
        category (str): Category as string from form
        date_str (str): Date as string from form

    Returns:
        list: List of error messages (empty if no errors)
    """
    errors = []

    # Validate amount
    if not amount_str:
        errors.append("Amount is required.")
    else:
        try:
            amount = float(amount_str)
            if amount <= 0:
                errors.append("Amount must be greater than 0.")
        except ValueError:
            errors.append("Amount must be a valid number.")

    # Validate category
    if not category:
        errors.append("Category is required.")
    elif category not in VALID_CATEGORIES:
        errors.append("Please select a valid category.")

    # Validate date
    if not date_str:
        errors.append("Date is required.")
    else:
        # Basic YYYY-MM-DD validation
        try:
            parts = date_str.split('-')
            if len(parts) != 3:
                raise ValueError
            year, month, day = parts
            if len(year) != 4 or len(month) != 2 or len(day) != 2:
                raise ValueError
            year_int = int(year)
            month_int = int(month)
            day_int = int(day)
            if month_int < 1 or month_int > 12:
                raise ValueError
            if day_int < 1 or day_int > 31:
                raise ValueError
            # Additional check for days in month (simplified)
        except ValueError:
            errors.append("Date must be in YYYY-MM-DD format.")

    return errors


def create_user(name, email, password):
    """
    Create a new user with the given name, email, and password.
    Hashes the password before storing.
    Returns the new user's id.
    Raises sqlite3.IntegrityError if email already exists.
    """
    conn = get_db()
    cursor = conn.cursor()

    password_hash = generate_password_hash(password)

    cursor.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash)
    )

    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return user_id


def get_user_by_email(email):
    """
    Fetch a user by email address.
    Returns the user row as a dict-like object, or None if not found.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    )

    user = cursor.fetchone()
    conn.close()

    return user


def get_db():
    """
    Open a connection to the SQLite database.
    Sets row_factory for dict-like row access and enables foreign key enforcement.
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """
    Create the users and expenses tables if they don't exist.
    Safe to call multiple times.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Create expenses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


def seed_db():
    """
    Insert demo user and sample expenses if they don't already exist.
    Safe to call multiple times - checks for existing data before inserting.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Check if users table already has data
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    # Create demo user
    demo_password_hash = generate_password_hash("demo123")
    cursor.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", demo_password_hash)
    )

    # Get the demo user's ID
    cursor.execute("SELECT id FROM users WHERE email = ?", ("demo@spendly.com",))
    demo_user_id = cursor.fetchone()[0]

    # Insert 8 sample expenses across different categories
    sample_expenses = [
        (demo_user_id, 45.50, "Food", "2026-04-01", "Lunch at cafe"),
        (demo_user_id, 25.00, "Transport", "2026-04-02", "Bus pass"),
        (demo_user_id, 120.00, "Bills", "2026-04-03", "Electric bill"),
        (demo_user_id, 35.00, "Health", "2026-04-04", "Pharmacy"),
        (demo_user_id, 50.00, "Entertainment", "2026-04-05", "Movie tickets"),
        (demo_user_id, 89.99, "Shopping", "2026-04-06", "New shirt"),
        (demo_user_id, 15.00, "Other", "2026-04-07", "Miscellaneous"),
        (demo_user_id, 65.00, "Food", "2026-04-08", "Dinner with friends"),
    ]

    cursor.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        sample_expenses
    )

    conn.commit()
    conn.close()
