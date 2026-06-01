"""
Database query helpers for Spendly profile page.
Contains pure query functions that handle database interactions
without Flask dependencies.
"""

import sqlite3
from datetime import datetime
from database.db import get_db


def get_user_by_id(user_id):
    """
    Fetch a user by their ID.

    Args:
        user_id (int): The user's ID

    Returns:
        dict: User data with keys: id, name, email, member_since (formatted)
              Returns None if user not found
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?",
        (user_id,)
    )

    user = cursor.fetchone()
    conn.close()

    if user is None:
        return None

    # Format member_since as "Month YYYY"
    try:
        date_obj = datetime.strptime(user['created_at'], '%Y-%m-%d %H:%M:%S')
        member_since = date_obj.strftime('%B %Y')
    except ValueError:
        # Fallback if date format is different
        member_since = user['created_at'][:7]  # Just YYYY-MM

    return {
        'id': user['id'],
        'name': user['name'],
        'email': user['email'],
        'member_since': member_since,
        'initials': ''.join([part[0].upper() for part in user['name'].split()[:2]]) or 'U'
    }


def get_summary_stats(user_id, start_date=None, end_date=None):
    """
    Get summary statistics for a user's expenses.

    Args:
        user_id (int): The user's ID
        start_date (str, optional): Start date in YYYY-MM-DD format
        end_date (str, optional): End date in YYYY-MM-DD format

    Returns:
        dict: Statistics with keys:
              - total_spent (float): Sum of all expenses
              - transaction_count (int): Number of expenses
              - top_category (str): Category with highest total spending
    """
    conn = get_db()
    cursor = conn.cursor()

    # Build WHERE clause with optional date filtering
    where_clauses = ["user_id = ?"]
    params = [user_id]

    if start_date:
        where_clauses.append("date >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("date <= ?")
        params.append(end_date)

    where_sql = " AND ".join(where_clauses)

    # Get total spent and transaction count
    cursor.execute(
        f"SELECT COALESCE(SUM(amount), 0) as total_spent, COUNT(*) as transaction_count "
        f"FROM expenses WHERE {where_sql}",
        params
    )

    result = cursor.fetchone()
    total_spent = float(result['total_spent'])
    transaction_count = result['transaction_count']

    # Get top category
    top_category = "—"  # Default when no expenses
    if transaction_count > 0:
        cursor.execute(
            f"""SELECT category, SUM(amount) as category_total
                FROM expenses
                WHERE {where_sql}
                GROUP BY category
                ORDER BY category_total DESC
                LIMIT 1""",
            params
        )
        category_result = cursor.fetchone()
        if category_result:
            top_category = category_result['category']

    conn.close()

    return {
        'total_spent': total_spent,
        'transaction_count': transaction_count,
        'top_category': top_category
    }


def get_recent_transactions(user_id, limit=10, start_date=None, end_date=None):
    """
    Get recent transactions for a user.

    Args:
        user_id (int): The user's ID
        limit (int): Maximum number of transactions to return
        start_date (str, optional): Start date in YYYY-MM-DD format
        end_date (str, optional): End date in YYYY-MM-DD format

    Returns:
        list: List of transaction dicts, each with keys:
              - id (int)
              - date (str)
              - description (str)
              - category (str)
              - amount (float)
              Ordered by date descending (newest first)
    """
    conn = get_db()
    cursor = conn.cursor()

    # Build WHERE clause with optional date filtering
    where_clauses = ["user_id = ?"]
    params = [user_id]

    if start_date:
        where_clauses.append("date >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("date <= ?")
        params.append(end_date)

    where_sql = " AND ".join(where_clauses)
    params.append(limit)  # Add limit as last parameter

    cursor.execute(
        f"""SELECT id, date, description, category, amount
            FROM expenses
            WHERE {where_sql}
            ORDER BY date DESC, created_at DESC
            LIMIT ?""",
        params
    )

    transactions = []
    for row in cursor.fetchall():
        transactions.append({
            'id': row['id'],
            'date': row['date'],
            'description': row['description'] or '',
            'category': row['category'],
            'amount': row['amount']
        })

    conn.close()
    return transactions


def get_category_breakdown(user_id, start_date=None, end_date=None):
    """
    Get spending breakdown by category for a user.

    Args:
        user_id (int): The user's ID
        start_date (str, optional): Start date in YYYY-MM-DD format
        end_date (str, optional): End date in YYYY-MM-DD format

    Returns:
        list: List of category dicts, each with keys:
              - name (str): Category name
              - amount (float): Total spent in category
              - pct (int): Percentage of total spending (0-100)
              - class (str): CSS class name for styling the category bar
    """
    conn = get_db()
    cursor = conn.cursor()

    # Build WHERE clause with optional date filtering
    where_clauses = ["user_id = ?"]
    params = [user_id]

    if start_date:
        where_clauses.append("date >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("date <= ?")
        params.append(end_date)

    where_sql = " AND ".join(where_clauses)

    # Get total spent for percentage calculation
    cursor.execute(
        f"SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE {where_sql}",
        params
    )
    total_result = cursor.fetchone()
    total_spent = total_result['total']

    if total_spent == 0:
        conn.close()
        return []

    # Get spending by category
    cursor.execute(
        f"""SELECT category, SUM(amount) as category_total
            FROM expenses
            WHERE {where_sql}
            GROUP BY category""",
        params
    )

    category_rows = cursor.fetchall()
    conn.close()

    # Calculate percentages and build result
    categories = []
    for row in category_rows:
        category_name = row['category']
        amount = row['category_total']
        # Calculate percentage and round to nearest integer
        pct = round((amount / total_spent) * 100)

        # Determine CSS class based on category name
        category_class = category_name.lower().replace(' ', '-')
        # Handle special cases or default to 'other' if not in predefined classes
        if category_class not in ['food', 'bills', 'transport', 'shopping', 'entertainment', 'health']:
            category_class = 'other'

        categories.append({
            'name': category_name,
            'amount': amount,
            'pct': pct,
            'class': category_class
        })

    # Sort by amount descending
    categories.sort(key=lambda x: x['amount'], reverse=True)

    # Adjust percentages to sum to 100
    if categories:
        current_sum = sum(cat['pct'] for cat in categories)
        if current_sum != 100:
            # Add/subtract the difference from the largest category
            diff = 100 - current_sum
            categories[0]['pct'] += diff
            # Ensure percentage doesn't go below 0
            if categories[0]['pct'] < 0:
                categories[0]['pct'] = 0

    return categories


def insert_expense(user_id, amount, category, date, description):
    """
    Insert a new expense for the given user.

    Args:
        user_id (int): The user's ID
        amount (float): Expense amount
        category (str): Expense category (must be one of fixed categories)
        date (str): Expense date in YYYY-MM-DD format
        description (str, optional): Expense description (can be empty)

    Returns:
        int: The ID of the newly inserted expense
    """
    conn = get_db()
    try:
        cursor = conn.cursor()
        # Store None if description is empty string
        desc_value = description if description else None
        cursor.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, desc_value)
        )
        conn.commit()
        expense_id = cursor.lastrowid
        return expense_id
    finally:
        conn.close()


def get_expense_by_id(expense_id, user_id):
    """
    Fetch a single expense by ID, only if it belongs to the given user.

    Args:
        expense_id (int): The expense ID
        user_id (int): The user's ID

    Returns:
        sqlite3.Row: Expense data with keys: id, user_id, amount, category, date, description
                     Returns None if expense not found or does not belong to user
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, user_id, amount, category, date, description FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id)
    )

    expense = cursor.fetchone()
    conn.close()

    return expense


def update_expense(expense_id, user_id, amount, category, date, description):
    """
    Update an existing expense with ownership verification.

    Args:
        expense_id (int): The expense ID
        user_id (int): The user's ID
        amount (float): New expense amount
        category (str): New expense category
        date (str): New expense date in YYYY-MM-DD format
        description (str, optional): New expense description

    Returns:
        None
    """
    conn = get_db()
    try:
        cursor = conn.cursor()
        # Store None if description is empty string
        desc_value = description if description else None
        cursor.execute(
            """UPDATE expenses
               SET amount = ?, category = ?, date = ?, description = ?
               WHERE id = ? AND user_id = ?""",
            (amount, category, date, desc_value, expense_id, user_id)
        )
        conn.commit()
    finally:
        conn.close()