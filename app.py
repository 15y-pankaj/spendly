import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from werkzeug.security import check_password_hash
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email, VALID_CATEGORIES, is_valid_date, validate_expense_form
from database.queries import get_user_by_id, get_summary_stats, get_recent_transactions, get_category_breakdown, insert_expense, get_expense_by_id, update_expense, delete_expense as delete_expense_db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')

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

    # Get user ID from session
    user_id = session["user_id"]

    # Get date filter parameters from query string
    start_date = request.args.get('start_date', type=str)
    end_date = request.args.get('end_date', type=str)

    # Convert invalid dates to None (no filter)
    if not is_valid_date(start_date):
        start_date = None
    if not is_valid_date(end_date):
        end_date = None

    # If both dates are valid, check that start_date <= end_date
    if start_date and end_date and start_date > end_date:
        flash("Start date must be before end date.", "error")
        # Invalid range: ignore both dates (treat as no filter)
        start_date = None
        end_date = None

    # Fetch real user data from database
    user = get_user_by_id(user_id)
    if user is None:
        # User not found (shouldn't happen if session is valid)
        session.clear()
        return redirect(url_for("login"))

    # Fetch real summary stats from database with date filtering
    stats = get_summary_stats(user_id, start_date=start_date, end_date=end_date)

    # Fetch real transactions from database with date filtering
    transactions = get_recent_transactions(user_id, start_date=start_date, end_date=end_date)

    # Fetch real category breakdown from database with date filtering
    categories = get_category_breakdown(user_id, start_date=start_date, end_date=end_date)

    return render_template("profile.html",
                          user=user, stats=stats,
                          transactions=transactions, categories=categories,
                          start_date=start_date, end_date=end_date)


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    # Auth guard
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "GET":
        # Render the add expense form
        return render_template("add_expense.html")

    # POST request - process form submission
    user_id = session["user_id"]

    # Get form data
    amount_str = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date_str = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    # Validate form data using utility function
    errors = validate_expense_form(amount_str, category, date_str)

    # If there are validation errors, re-render the form with errors and pre-filled values
    if errors:
        for error in errors:
            flash(error, "error")
        return render_template("add_expense.html",
                             amount=amount_str,
                             category=category,
                             date=date_str,
                             description=description)

    # All validation passed - insert the expense
    try:
        amount_float = float(amount_str)
        # For description, store None if empty string
        desc_value = description if description else None
        insert_expense(user_id, amount_float, category, date_str, desc_value)
        flash("Expense added successfully!", "success")
        return redirect(url_for("profile"))
    except Exception as e:
        flash("An error occurred while saving the expense. Please try again.", "error")
        return render_template("add_expense.html",
                             amount=amount_str,
                             category=category,
                             date=date_str,
                             description=description)


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    # Auth guard
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]

    if request.method == "GET":
        # GET: show the edit form pre-filled with current expense data
        expense = get_expense_by_id(id, user_id)
        if expense is None:
            # Expense not found or not owned by user
            abort(404)

        # Get categories for the dropdown (same as add_expense)
        categories = VALID_CATEGORIES

        return render_template("edit_expense.html",
                             expense=expense,
                             categories=categories)

    # POST request - process form submission
    # Get form data
    amount_str = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date_str = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    # Validate form data using utility function
    errors = validate_expense_form(amount_str, category, date_str)

    # If there are validation errors, re-render the form with errors and pre-filled values
    if errors:
        for error in errors:
            flash(error, "error")
        # Get the expense again to pass to template (for pre-filled values in case we want to show original)
        # But we'll use submitted values for the form as per spec
        expense = get_expense_by_id(id, user_id)
        if expense is None:
            abort(404)
        categories = VALID_CATEGORIES
        return render_template("edit_expense.html",
                             expense=expense,
                             categories=categories,
                             amount=amount_str,
                             category=category,
                             date=date_str,
                             description=description)

    # All validation passed - update the expense
    try:
        amount_float = float(amount_str)
        # For description, store None if empty string
        desc_value = description if description else None
        update_expense(id, user_id, amount_float, category, date_str, desc_value)
        flash("Expense updated successfully!", "success")
        return redirect(url_for("profile"))
    except Exception as e:
        flash("An error occurred while updating the expense. Please try again.", "error")
        # Get the expense again to pass to template
        expense = get_expense_by_id(id, user_id)
        if expense is None:
            abort(404)
        categories = VALID_CATEGORIES
        return render_template("edit_expense.html",
                             expense=expense,
                             categories=categories,
                             amount=amount_str,
                             category=category,
                             date=date_str,
                             description=description)


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    # Auth guard: only allow logged-in users
    if not session.get("user_id"):
        return redirect(url_for("login"))
    user_id = session["user_id"]

    # Ownership check — same pattern as edit_expense
    expense = get_expense_by_id(id, user_id)
    if expense is None:
        abort(404)

    delete_expense_db(id, user_id)
    flash("Expense deleted.", "success")
    return redirect(url_for("profile"))


# Analytics route (coming soon)
@app.route("/analytics")
def analytics():
    # Auth guard: only allow logged-in users
    if not session.get("user_id"):
        flash("Please log in to access analytics.", "info")
        return redirect(url_for("login"))
    return render_template("analytics.html")


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5008))
    app.run(debug=True, host='0.0.0.0', port=port)

