import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-prod"

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # Redirect to landing if already logged in
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validate all fields are non-empty
        if not name or not email or not password or not confirm_password:
            flash("All fields are required.", "error")
            return render_template("register.html")

        # Validate password length
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("register.html")

        # Validate passwords match
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        # Try to create the user
        try:
            create_user(name, email, password)
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already registered.", "error")
            return render_template("register.html")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    # Redirect to landing if already logged in
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        user = get_user_by_email(email)

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        session["user_id"] = user["id"]
        flash("Welcome back!", "success")
        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    # Auth guard
    if not session.get("user_id"):
        return redirect(url_for("login"))

    # Hardcoded user data (Step 4 - DB queries in Step 5)
    user = {
        "name": "Demo User",
        "email": "demo@spendly.com",
        "member_since": "April 2026",
        "initials": "DU"
    }

    # Hardcoded summary stats
    stats = {
        "total_spent": 345.49,
        "transaction_count": 8,
        "top_category": "Food"
    }

    # Hardcoded transactions
    transactions = [
        {"date": "2026-04-08", "description": "Dinner with friends", "category": "Food", "amount": 65.00},
        {"date": "2026-04-06", "description": "New shirt", "category": "Shopping", "amount": 89.99},
        {"date": "2026-04-05", "description": "Movie tickets", "category": "Entertainment", "amount": 50.00},
        {"date": "2026-04-03", "description": "Electric bill", "category": "Bills", "amount": 120.00},
        {"date": "2026-04-02", "description": "Bus pass", "category": "Transport", "amount": 25.00},
    ]

    # Hardcoded category breakdown
    categories = [
        {"name": "Shopping", "amount": 89.99, "pct": 26, "class": "shopping"},
        {"name": "Food", "amount": 110.50, "pct": 32, "class": "food"},
        {"name": "Bills", "amount": 120.00, "pct": 35, "class": "bills"},
        {"name": "Transport", "amount": 25.00, "pct": 7, "class": "transport"},
        {"name": "Entertainment", "amount": 50.00, "pct": 14, "class": "entertainment"},
    ]

    return render_template("profile.html",
                          user=user, stats=stats,
                          transactions=transactions, categories=categories)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)

