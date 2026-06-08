import pytest
from app import app as flask_app
from database.db import init_db, get_db
from database.queries import insert_expense, get_expense_by_id, delete_expense
from werkzeug.security import generate_password_hash

# Override the database to use shared in-memory and prevent seeding before importing app
import database.db
original_database = database.db.DATABASE
# Use a named in-memory database that can be shared between connections
database.db.DATABASE = 'file:memdb2?mode=memory&cache=shared'
# Prevent seeding by replacing seed_db with a no-op
database.db.seed_db = lambda: None

# Fixture to clean database between tests
@pytest.fixture(autouse=True)
def clean_db():
    """Clean all data from tables between tests."""
    with flask_app.app_context():
        conn = get_db()
        try:
            cursor = conn.cursor()
            # Delete all expenses first (due to foreign key constraint)
            cursor.execute("DELETE FROM expenses")
            # Delete all users
            cursor.execute("DELETE FROM users")
            conn.commit()
        finally:
            conn.close()

# Fixture to create the app client
@pytest.fixture
def client():
    return flask_app.test_client()

# Fixture to create an authenticated client for a regular user
@pytest.fixture
def auth_client(client):
    # Create a user
    with flask_app.app_context():
        conn = get_db()
        try:
            cursor = conn.cursor()
            password_hash = generate_password_hash("password")
            cursor.execute(
                "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                ("testuser", "test@example.com", password_hash, "2026-01-01 00:00:00")
            )
            conn.commit()
            user_id = cursor.lastrowid
        finally:
            conn.close()
    # Log in
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'password'
    }, follow_redirects=True)
    return client

# Fixture to create a second user (to test ownership)
@pytest.fixture
def other_user_id(client):
    # Create a second user
    with flask_app.app_context():
        conn = get_db()
        try:
            cursor = conn.cursor()
            password_hash = generate_password_hash("password")
            cursor.execute(
                "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                ("otheruser", "other@example.com", password_hash, "2026-01-01 00:00:00")
            )
            conn.commit()
            other_user_id = cursor.lastrowid
        finally:
            conn.close()
    return other_user_id

# Unit tests for delete_expense
def test_delete_expense_own_row_removed():
    """delete_expense removes the row when given correct user_id."""
    with flask_app.app_context():
        conn = get_db()
        try:
            cursor = conn.cursor()
            # Insert an expense for user 1
            cursor.execute(
                "INSERT INTO users (id, name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (1, "user1", "user1@example.com", "hash1", "2026-01-01 00:00:00")
            )
            cursor.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (1, 10.0, "Food", "2026-01-01", "Lunch")
            )
            conn.commit()
            expense_id = cursor.lastrowid
        finally:
            conn.close()

        # Call delete_expense
        delete_expense(expense_id, 1)

        # Verify the expense is gone
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM expenses WHERE id = ?", (expense_id,))
            count = cursor.fetchone()[0]
            assert count == 0
        finally:
            conn.close()

def test_delete_expense_wrong_user_no_effect():
    """delete_expense does nothing when given wrong user_id."""
    with flask_app.app_context():
        conn = get_db()
        try:
            cursor = conn.cursor()
            # Insert an expense for user 1
            cursor.execute(
                "INSERT INTO users (id, name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (1, "user1", "user1@example.com", "hash1", "2026-01-01 00:00:00")
            )
            cursor.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (1, 10.0, "Food", "2026-01-01", "Lunch")
            )
            conn.commit()
            expense_id = cursor.lastrowid
        finally:
            conn.close()

        # Call delete_expense with wrong user_id (2)
        delete_expense(expense_id, 2)  # Should not delete

        # Verify the expense still exists
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM expenses WHERE id = ?", (expense_id,))
            count = cursor.fetchone()[0]
            assert count == 1
        finally:
            conn.close()

def test_delete_expense_nonexistent_id():
    """delete_expense does nothing when given nonexistent id."""
    with flask_app.app_context():
        conn = get_db()
        try:
            cursor = conn.cursor()
            # Insert a user
            cursor.execute(
                "INSERT INTO users (id, name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (1, "user1", "user1@example.com", "hash1", "2026-01-01 00:00:00")
            )
            conn.commit()
        finally:
            conn.close()

        # Call delete_expense with nonexistent id
        delete_expense(99999, 1)  # Should not raise

        # Verify no expenses exist (still)
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM expenses")
            count = cursor.fetchone()[0]
            assert count == 0
        finally:
            conn.close()

# Route tests
def test_delete_post_unauthenticated_redirects_to_login(client):
    """POST to /expenses/<id>/delete when logged out redirects to /login."""
    response = client.post('/expenses/1/delete', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.location

def test_delete_post_own_expense_redirects_to_profile_and_removes_row(auth_client):
    """POST to /expenses/<id>/delete for own expense redirects to /profile and removes row."""
    # First, create an expense for the logged-in user
    with flask_app.app_context():
        conn = get_db()
        try:
            cursor = conn.cursor()
            # Get the user id from the session? We know we created a user with email test@example.com in auth_client fixture
            # But we can also insert directly knowing the user id from the fixture setup.
            # However, the auth_client fixture logs in a user we created. Let's get that user's id.
            # Alternatively, we can create the expense in the same app context as the fixture.
            # We'll do: in the app context, insert a user and expense, then use the auth_client to make the request.
            # But note: the auth_client fixture already created a user and logged in.
            # We'll need to get the user id from that fixture. Instead, let's create the expense in the auth_client fixture?
            # We'll adjust: we'll create the expense in the test itself using the same user id as in the fixture.
            # Since we know the fixture creates a user with email test@example.com, we can look up the id.
            cursor.execute("SELECT id FROM users WHERE email = ?", ( "test@example.com", ))
            user = cursor.fetchone()
            user_id = user['id']
            cursor.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_id, 10.0, "Food", "2026-01-01", "Lunch")
            )
            conn.commit()
            expense_id = cursor.lastrowid
        finally:
            conn.close()

    # Now make the delete request
    response = auth_client.post(f'/expenses/{expense_id}/delete', follow_redirects=False)
    assert response.status_code == 302
    assert '/profile' in response.location

    # Verify the expense is removed
    with flask_app.app_context():
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM expenses WHERE id = ?", (expense_id,))
            count = cursor.fetchone()[0]
            assert count == 0
        finally:
            conn.close()

def test_delete_post_other_users_expense_returns_404(auth_client, other_user_id):
    """POST to /expenses/<id>/delete for other user's expense returns 404."""
    # Create an expense for the other user
    with flask_app.app_context():
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (other_user_id, 10.0, "Food", "2026-01-01", "Lunch")
            )
            conn.commit()
            expense_id = cursor.lastrowid
        finally:
            conn.close()

    # Try to delete it with the regular auth_client (which is a different user)
    response = auth_client.post(f'/expenses/{expense_id}/delete', follow_redirects=False)
    assert response.status_code == 404

    # Verify the expense still exists
    with flask_app.app_context():
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM expenses WHERE id = ?", (expense_id,))
            count = cursor.fetchone()[0]
            assert count == 1
        finally:
            conn.close()

def test_delete_post_nonexistent_id_returns_404(auth_client):
    """POST to /expenses/<id>/delete for nonexistent id returns 404."""
    response = auth_client.post('/expenses/99999/delete', follow_redirects=False)
    assert response.status_code == 404

def test_delete_get_returns_405(auth_client):
    """GET to /expenses/<id>/delete returns 405."""
    response = auth_client.get('/expenses/1/delete')
    assert response.status_code == 405