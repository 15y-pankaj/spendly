#!/usr/bin/env python3
"""
Seed script to add a realistic Indian user to the database.
Generates random name, email, and hashes password before inserting.
"""

import random
from datetime import datetime
from werkzeug.security import generate_password_hash
from database.db import get_db


# Common Indian first names across regions
FIRST_NAMES = [
    "Aarav", "Vihaan", "Aditya", "Sai", "Arjun", "Reyansh", "Ayaan", "Krishna",
    "Ishaan", "Dhruv", "Karan", "Rohan", "Aryan", "Dev", "Rahul", "Priya",
    "Ananya", "Diya", "Sara", "Aisha", "Zara", "Meera", "Kavya", "Neha",
    "Riya", "Pooja", "Sneha", "Divya", "Aditi", "Shruti", "Lakshmi", "Radha"
]

# Common Indian surnames across regions
LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Kumar", "Singh", "Gupta", "Reddy", "Rao",
    "Nair", "Menon", "Iyer", "Shankar", "Das", "Bose", "Chatterjee", "Banerjee",
    "Ghosh", "Joshi", "Desai", "Joshi", "Kulkarni", "Patil", "Deshmukh",
    "Kapoor", "Malhotra", "Chopra", "Bhatt", "Mehta", "Parekh", "Shah"
]


def generate_unique_email():
    """Generate a unique email that doesn't already exist in the database."""
    conn = get_db()
    cursor = conn.cursor()

    max_attempts = 100
    for _ in range(max_attempts):
        first_name = random.choice(FIRST_NAMES).lower()
        last_name = random.choice(LAST_NAMES).lower()
        number = random.randint(10, 999)

        email = f"{first_name}.{last_name}{number}@gmail.com"

        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone() is None:
            conn.close()
            return email

    conn.close()
    raise Exception("Could not generate unique email after multiple attempts")


def generate_indian_name():
    """Generate a realistic Indian name."""
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    return f"{first_name} {last_name}"


def seed_user():
    """Generate and insert a new Indian user into the database."""
    # Generate unique user details
    name = generate_indian_name()
    email = generate_unique_email()
    password_hash = generate_password_hash("password123")

    # Insert into database
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash)
    )

    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Print confirmation
    print(f"id: {user_id}")
    print(f"name: {name}")
    print(f"email: {email}")


if __name__ == "__main__":
    seed_user()
