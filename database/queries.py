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


def get_summary_stats(user_id):
    """
    Get summary statistics for a user's expenses.

    Args:
        user_id (int): The user's ID

    Returns:
        dict: Statistics with keys:
              - total_spent (float): Sum of all expenses
              - transaction_count (int): Number of expenses
              - top_category (str): Category with highest total spending
    """
    conn = get_db()
    cursor = conn.cursor()

    # Get total spent and transaction count
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0) as total_spent, COUNT(*) as transaction_count "
        "FROM expenses WHERE user_id = ?",
        (user_id,)
    )

    result = cursor.fetchone()
    total_spent = float(result['total_spent'])
    transaction_count = result['transaction_count']

    # Get top category
    top_category = "—"  # Default when no expenses
    if transaction_count > 0:
        cursor.execute(
            """SELECT category, SUM(amount) as category_total
               FROM expenses
               WHERE user_id = ?
               GROUP BY category
               ORDER BY category_total DESC
               LIMIT 1""",
            (user_id,)
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


def get_recent_transactions(user_id, limit=10):
    """
    Get recent transactions for a user.

    Args:
        user_id (int): The user's ID
        limit (int): Maximum number of transactions to return

    Returns:
        list: List of transaction dicts, each with keys:
              - date (str)
              - description (str)
              - category (str)
              - amount (float)
              Ordered by date descending (newest first)
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT date, description, category, amount
           FROM expenses
           WHERE user_id = ?
           ORDER BY date DESC, created_at DESC
           LIMIT ?""",
        (user_id, limit)
    )

    transactions = []
    for row in cursor.fetchall():
        transactions.append({
            'date': row['date'],
            'description': row['description'] or '',
            'category': row['category'],
            'amount': row['amount']
        })

    conn.close()
    return transactions


def get_category_breakdown(user_id):
    """
    Get spending breakdown by category for a user.

    Args:
        user_id (int): The user's ID

    Returns:
        list: List of category dicts, each with keys:
              - name (str): Category name
              - amount (float): Total spent in category
              - pct (int): Percentage of total spending (0-100)
    """
    conn = get_db()
    cursor = conn.cursor()

    # Get total spent for percentage calculation
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE user_id = ?",
        (user_id,)
    )
    total_result = cursor.fetchone()
    total_spent = total_result['total']

    if total_spent == 0:
        conn.close()
        return []

    # Get spending by category
    cursor.execute(
        """SELECT category, SUM(amount) as category_total
           FROM expenses
           WHERE user_id = ?
           GROUP BY category""",
        (user_id,)
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

        categories.append({
            'name': category_name,
            'amount': amount,
            'pct': pct
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