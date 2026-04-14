#!/usr/bin/env python3
"""
Seed script to add realistic Indian expenses for a specific user.
Generates random expenses across categories with appropriate amounts.
"""

import random
import sys
from datetime import datetime, timedelta
from database.db import get_db


# Category definitions with Indian rupee ranges and distribution weights
CATEGORIES = {
    "Food": {"min": 50, "max": 800, "weight": 30},
    "Transport": {"min": 20, "max": 500, "weight": 20},
    "Bills": {"min": 200, "max": 3000, "weight": 15},
    "Health": {"min": 100, "max": 2000, "weight": 8},
    "Entertainment": {"min": 100, "max": 1500, "weight": 10},
    "Shopping": {"min": 200, "max": 5000, "weight": 12},
    "Other": {"min": 50, "max": 1000, "weight": 5},
}

# Realistic Indian expense descriptions by category
DESCRIPTIONS = {
    "Food": [
        "Lunch at office cafeteria", "Dinner at local restaurant", "Street food",
        "Groceries from Big Bazaar", "Coffee at Cafe Coffee Day", "Biryani order",
        "Breakfast at Udupi", "Pizza delivery", "Thali meal", "Snacks from kirana store",
        "Family dinner outing", "Tiffin service", "Ice cream parlour", "Juice corner"
    ],
    "Transport": [
        "Metro card recharge", "Auto fare", "Uber ride", "Bus pass", "Fuel at IOCL",
        "Ola cab", "Train ticket", "Airport taxi", "Bike parking", "Toll charge",
        "Car wash", "Monthly bus pass", "Rapido bike taxi"
    ],
    "Bills": [
        "Electricity bill - BESCOM", "Mobile recharge Airtel", "Jio fiber broadband",
        "DTH recharge", "Water bill", "Gas cylinder booking", "House rent",
        "Maintenance charges", "Internet bill ACT", "LIC premium", "Credit card bill"
    ],
    "Health": [
        "Doctor consultation", "Medicines at Apollo Pharmacy", "Gym membership",
        "Health checkup", "Dental clinic", "Eye test and glasses", "Physiotherapy",
        "Yoga class fee", "Diagnostic lab tests", "Vitamin supplements"
    ],
    "Entertainment": [
        "Movie tickets PVR", "Netflix subscription", "Amazon Prime video",
        "Hotstar subscription", "Amusement park entry", "Concert tickets",
        "Gaming zone", "Bowling alley", "Escape room experience"
    ],
    "Shopping": [
        "Clothes at Reliance Trends", "Shoes from Bata", "Electronics at Croma",
        "Home decor HomeCentre", "Gifts for wedding", "Kitchen appliances",
        "Furniture IKEA", "Cosmetics Nykaa", "Books at Crossword", "Jewellery Tanishq"
    ],
    "Other": [
        "Kirana store purchase", "Stationery items", "Pet supplies", "Donation",
        "Tips and tips", "Emergency cash withdrawal", "ATM charges", "Bank charges",
        "Photocopy and print", "Tailoring charges", "Salon visit"
    ],
}


def parse_arguments(args):
    """Parse command line arguments: user_id, count, months."""
    if len(args) != 3:
        return None

    try:
        user_id = int(args[0])
        count = int(args[1])
        months = int(args[2])
        return {"user_id": user_id, "count": count, "months": months}
    except ValueError:
        return None


def verify_user_exists(user_id):
    """Check if user exists in database. Returns True if exists, False otherwise."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def select_category():
    """Select a category based on distribution weights."""
    categories = list(CATEGORIES.keys())
    weights = [CATEGORIES[cat]["weight"] for cat in categories]
    return random.choices(categories, weights=weights, k=1)[0]


def generate_expense(user_id, start_date, end_date):
    """Generate a single realistic expense."""
    category = select_category()
    cat_config = CATEGORIES[category]

    # Random amount in range
    amount = round(random.uniform(cat_config["min"], cat_config["max"]), 2)

    # Random date in range
    days_range = (end_date - start_date).days
    random_date = start_date + timedelta(days=random.randint(0, days_range))

    # Random description
    description = random.choice(DESCRIPTIONS[category])

    return (user_id, amount, category, random_date.strftime("%Y-%m-%d"), description)


def seed_expenses(user_id, count, months):
    """Generate and insert expenses for the given user."""
    # Calculate date range (approximate months as 30 days each)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)

    # Generate all expenses
    expenses = []
    for _ in range(count):
        expenses.append(generate_expense(user_id, start_date, end_date))

    # Insert in single transaction
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            expenses
        )
        conn.commit()

        # Get inserted records for confirmation
        cursor.execute(
            "SELECT id, user_id, amount, category, date, description FROM expenses WHERE user_id = ? ORDER BY date DESC LIMIT 5",
            (user_id,)
        )
        sample = cursor.fetchall()

        # Get date range of inserted expenses
        cursor.execute(
            "SELECT MIN(date), MAX(date) FROM expenses WHERE user_id = ?",
            (user_id,)
        )
        date_range = cursor.fetchone()

        conn.close()

        return {
            "inserted_count": count,
            "min_date": date_range[0],
            "max_date": date_range[1],
            "sample": sample
        }

    except Exception as e:
        conn.rollback()
        conn.close()
        raise e


def main():
    # Step 1: Parse arguments
    args = sys.argv[1:]
    parsed = parse_arguments(args)

    if parsed is None:
        print("Usage: /seed-expenses <user_id> <count> <months>")
        print("Example: /seed-expenses 1 50 6")
        sys.exit(1)

    user_id = parsed["user_id"]
    count = parsed["count"]
    months = parsed["months"]

    # Step 2: Verify user exists
    if not verify_user_exists(user_id):
        print(f"No user found with id {user_id}.")
        sys.exit(1)

    # Step 3 & 4: Generate, insert, and confirm
    try:
        result = seed_expenses(user_id, count, months)

        print(f"\nSuccessfully inserted {result['inserted_count']} expenses.")
        print(f"Date range: {result['min_date']} to {result['max_date']}")
        print("\nSample of 5 inserted records:")
        print("-" * 80)
        print(f"{'ID':<6} {'User':<6} {'Amount':>10} {'Category':<15} {'Date':<12} {'Description'}")
        print("-" * 80)
        for row in result["sample"]:
            print(f"{row[0]:<6} {row[1]:<6} {row[2]:>10.2f} {row[3]:<15} {row[4]:<12} {row[5]}")
        print("-" * 80)

    except Exception as e:
        print(f"Error inserting expenses: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
