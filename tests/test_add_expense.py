import pytest
from app import app as flask_app
from database.db import init_db, get_db
from database.queries import insert_expense, get_recent_transactions

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

from app import app as flask_app
from database.db import init_db, get_db

@pytest.fixture
def app():
    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret',
        'WTF_CSRF_ENABLED': False,
    })
    with flask_app.app_context():
        init_db()
        yield flask_app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client):
    """A test client that is already logged in."""
    # Register a user
    client.post('/register', data={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'testpass123',
        'confirm_password': 'testpass123'
    })
    # Login
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'testpass123'
    })
    return client

@pytest.fixture
def auth_client_with_user(auth_client):
    """Auth client and return the user ID for use in direct DB calls."""
    with flask_app.app_context():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", ('test@example.com',))
        user_id = cursor.fetchone()['id']
        conn.close()
    return auth_client, user_id

# Unit tests for insert_expense function
def test_insert_expense_valid_data(auth_client_with_user):
    """Test inserting a valid expense."""
    auth_client, user_id = auth_client_with_user

    expense_id = insert_expense(
        user_id=user_id,
        amount=50.0,
        category="Food",
        date="2026-03-20",
        description="Lunch"
    )

    # Verify the expense was inserted and returned an ID
    assert expense_id is not None
    assert isinstance(expense_id, int)
    assert expense_id > 0

    # Verify we can retrieve the expense
    with flask_app.app_context():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM expenses WHERE id = ?",
            (expense_id,)
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row['user_id'] == user_id
        assert float(row['amount']) == 50.0
        assert row['category'] == "Food"
        assert row['date'] == "2026-03-20"
        assert row['description'] == "Lunch"

def test_insert_expense_with_none_description(auth_client_with_user):
    """Test inserting an expense with None/empty description."""
    auth_client, user_id = auth_client_with_user

    expense_id = insert_expense(
        user_id=user_id,
        amount=25.5,
        category="Transport",
        date="2026-03-21",
        description=""  # Empty string
    )

    # Verify the expense was inserted
    assert expense_id is not None
    assert isinstance(expense_id, int)
    assert expense_id > 0

    # Verify description is stored as NULL
    with flask_app.app_context():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT description FROM expenses WHERE id = ?",
            (expense_id,)
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row['description'] is None

# Route tests for GET /expenses/add
def test_get_add_expense_unauthenticated_redirects(client):
    """Unauthenticated access to GET /expenses/add should redirect to login."""
    response = client.get('/expenses/add')
    assert response.status_code == 302
    assert '/login' in response.location

def test_get_add_expense_authenticated_shows_form(auth_client):
    """Authenticated access to GET /expenses/add should show the form."""
    response = auth_client.get('/expenses/add')
    assert response.status_code == 200
    # Check that the form is present
    assert b'<form' in response.data
    assert b'method="POST"' in response.data
    # Check for category select with all 7 options
    assert b'<select' in response.data
    assert b'Food' in response.data
    assert b'Transport' in response.data
    assert b'Bills' in response.data
    assert b'Health' in response.data
    assert b'Entertainment' in response.data
    assert b'Shopping' in response.data
    assert b'Other' in response.data

# Route tests for POST /expenses/add
def test_post_add_expense_unauthenticated_redirects(client):
    """Unauthenticated access to POST /expenses/add should redirect to login."""
    response = client.post('/expenses/add', data={
        'amount': '50.0',
        'category': 'Food',
        'date': '2026-03-20',
        'description': 'Lunch'
    })
    assert response.status_code == 302
    assert '/login' in response.location

def test_post_add_expense_authenticated_valid_data_redirects(auth_client):
    """Authenticated POST with valid data should redirect to profile."""
    response = auth_client.post('/expenses/add', data={
        'amount': '50.0',
        'category': 'Food',
        'date': '2026-03-20',
        'description': 'Lunch'
    }, follow_redirects=False)

    assert response.status_code == 302
    assert '/profile' in response.location

    # Verify the expense was actually inserted
    with flask_app.app_context():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", ('test@example.com',))
        user_id = cursor.fetchone()['id']
        cursor.execute(
            "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,)
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert float(row['amount']) == 50.0
        assert row['category'] == "Food"
        assert row['date'] == "2026-03-20"
        assert row['description'] == "Lunch"

def test_post_add_expense_authenticated_no_description_redirects(auth_client):
    """Authenticated POST with no description should redirect and store NULL."""
    response = auth_client.post('/expenses/add', data={
        'amount': '30.0',
        'category': 'Shopping',
        'date': '2026-03-21',
        'description': ''  # Empty description
    }, follow_redirects=False)

    assert response.status_code == 302
    assert '/profile' in response.location

    # Verify the expense was inserted with NULL description
    with flask_app.app_context():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", ('test@example.com',))
        user_id = cursor.fetchone()['id']
        cursor.execute(
            "SELECT description FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,)
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row['description'] is None

# Validation tests for POST /expenses/add
def test_post_add_expense_missing_amount_shows_error(auth_client):
    """Missing amount should show error and re-render form."""
    response = auth_client.post('/expenses/add', data={
        'amount': '',  # Missing amount
        'category': 'Food',
        'date': '2026-03-20',
        'description': 'Lunch'
    })

    assert response.status_code == 200  # Should re-render form, not redirect
    assert b'Amount is required.' in response.data
    # Check that previously entered values are preserved
    assert b'Food' in response.data  # category preserved
    assert b'2026-03-20' in response.data  # date preserved
    assert b'Lunch' in response.data  # description preserved

def test_post_add_expense_zero_amount_shows_error(auth_client):
    """Amount = 0 should show error."""
    response = auth_client.post('/expenses/add', data={
        'amount': '0',
        'category': 'Food',
        'date': '2026-03-20',
        'description': 'Lunch'
    })

    assert response.status_code == 200
    assert b'Amount must be greater than 0.' in response.data

def test_post_add_expense_negative_amount_shows_error(auth_client):
    """Negative amount should show error."""
    response = auth_client.post('/expenses/add', data={
        'amount': '-10.0',
        'category': 'Food',
        'date': '2026-03-20',
        'description': 'Lunch'
    })

    assert response.status_code == 200
    assert b'Amount must be greater than 0.' in response.data

def test_post_add_expense_non_numeric_amount_shows_error(auth_client):
    """Non-numeric amount should show error."""
    response = auth_client.post('/expenses/add', data={
        'amount': 'abc',
        'category': 'Food',
        'date': '2026-03-20',
        'description': 'Lunch'
    })

    assert response.status_code == 200
    assert b'Amount must be a valid number.' in response.data

def test_post_add_expense_missing_category_shows_error(auth_client):
    """Missing category should show error."""
    response = auth_client.post('/expenses/add', data={
        'amount': '50.0',
        'category': '',  # Missing category
        'date': '2026-03-20',
        'description': 'Lunch'
    })

    assert response.status_code == 200
    assert b'Category is required.' in response.data

def test_post_add_expense_invalid_category_shows_error(auth_client):
    """Invalid category should show error."""
    response = auth_client.post('/expenses/add', data={
        'amount': '50.0',
        'category': 'InvalidCategory',
        'date': '2026-03-20',
        'description': 'Lunch'
    })

    assert response.status_code == 200
    assert b'Please select a valid category.' in response.data

def test_post_add_expense_missing_date_shows_error(auth_client):
    """Missing date should show error."""
    response = auth_client.post('/expenses/add', data={
        'amount': '50.0',
        'category': 'Food',
        'date': '',  # Missing date
        'description': 'Lunch'
    })

    assert response.status_code == 200
    assert b'Date is required.' in response.data

def test_post_add_expense_invalid_date_format_shows_error(auth_client):
    """Invalid date format should show error."""
    response = auth_client.post('/expenses/add', data={
        'amount': '50.0',
        'category': 'Food',
        'date': '2026/03/20',  # Wrong format
        'description': 'Lunch'
    })

    assert response.status_code == 200
    assert b'Date must be in YYYY-MM-DD format.' in response.data

def test_post_add_expense_invalid_date_month_shows_error(auth_client):
    """Invalid date month should show error."""
    response = auth_client.post('/expenses/add', data={
        'amount': '50.0',
        'category': 'Food',
        'date': '2026-13-20',  # Invalid month
        'description': 'Lunch'
    })

    assert response.status_code == 200
    assert b'Date must be in YYYY-MM-DD format.' in response.data

def test_post_add_expense_invalid_date_day_shows_error(auth_client):
    """Invalid date day should show error."""
    response = auth_client.post('/expenses/add', data={
        'amount': '50.0',
        'category': 'Food',
        'date': '2026-03-32',  # Invalid day
        'description': 'Lunch'
    })

    assert response.status_code == 200
    assert b'Date must be in YYYY-MM-DD format.' in response.data

# Test successful submission without description
def test_post_add_expense_no_description_saves_as_null(auth_client):
    """Submitting without description should save with NULL description."""
    response = auth_client.post('/expenses/add', data={
        'amount': '50.0',
        'category': 'Food',
        'date': '2026-03-20',
        'description': ''  # Empty description
    }, follow_redirects=False)

    assert response.status_code == 302
    assert '/profile' in response.location

    # Verify NULL description in database
    with flask_app.app_context():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", ('test@example.com',))
        user_id = cursor.fetchone()['id']
        cursor.execute(
            "SELECT description FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,)
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row['description'] is None

# Test that successful submission redirects to profile and expense appears in transaction list
def test_post_add_expense_appears_in_profile(auth_client):
    """Successful expense submission should appear in profile transaction list."""
    # Submit an expense
    response = auth_client.post('/expenses/add', data={
        'amount': '25.50',
        'category': 'Entertainment',
        'date': '2026-03-15',
        'description': 'Concert tickets'
    }, follow_redirects=False)

    assert response.status_code == 302
    assert '/profile' in response.location

    # Follow redirect to profile page
    response = auth_client.get('/profile')
    assert response.status_code == 200

    # Check that the expense appears in the transaction list
    assert b'Concert tickets' in response.data
    assert b'25.50' in response.data
    assert b'Entertainment' in response.data
    assert b'2026-03-15' in response.data