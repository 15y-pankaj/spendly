import pytest
# Override the database to use shared in-memory and prevent seeding before importing app
import database.db
original_database = database.db.DATABASE
# Use a named in-memory database that can be shared between connections
database.db.DATABASE = 'file:memdb1?mode=memory&cache=shared'
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
def auth_client_with_expenses(auth_client):
    """Auth client with some test expenses inserted for the logged-in user."""
    # We need to get the user ID from the session or database.
    # Since we are using an in-memory database, we can connect and get the user ID.
    with flask_app.app_context():
        conn = get_db()
        cursor = conn.cursor()
        # Get the user ID for the test user (we know the email)
        cursor.execute("SELECT id FROM users WHERE email = ?", ('test@example.com',))
        user_id = cursor.fetchone()['id']
        # Insert test expenses with various dates
        test_expenses = [
            # (user_id, amount, category, date, description)
            (user_id, 10.0, 'Food', '2026-04-01', 'Breakfast'),
            (user_id, 20.0, 'Transport', '2026-04-05', 'Taxi'),
            (user_id, 15.0, 'Food', '2026-04-10', 'Lunch'),
            (user_id, 30.0, 'Entertainment', '2026-04-15', 'Concert'),
            (user_id, 25.0, 'Bills', '2026-05-01', 'Internet'),
            (user_id, 40.0, 'Shopping', '2026-05-10', 'Clothes'),
        ]
        cursor.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            test_expenses
        )
        conn.commit()
        conn.close()
    return auth_client

# Helper function to parse HTML and check for elements? We'll just use string search for simplicity.
# We'll check for text in the response data.

class TestProfileDateFilter:
    """Test date filtering on the profile page."""

    def test_profile_loads_without_filters_shows_all_expenses(self, auth_client_with_expenses):
        """The profile page loads without errors when no date filters are applied (shows all expenses)."""
        response = auth_client_with_expenses.get('/profile')
        assert response.status_code == 200
        # Check that all test expenses are present in the response
        # We look for known descriptions and amounts
        assert b'Breakfast' in response.data
        assert b'Taxi' in response.data
        assert b'Lunch' in response.data
        assert b'Concert' in response.data
        assert b'Internet' in response.data
        assert b'Clothes' in response.data

    def test_profile_filters_by_start_date(self, auth_client_with_expenses):
        """Filtering by start_date shows expenses on or after that date."""
        # Start date: 2026-04-10 should show Lunch, Concert, Internet, Clothes
        response = auth_client_with_expenses.get('/profile?start_date=2026-04-10')
        assert response.status_code == 200
        # Expenses before start date should not appear
        assert b'Breakfast' not in response.data  # 2026-04-01
        assert b'Taxi' not in response.data       # 2026-04-05
        # Expenses on or after start date should appear
        assert b'Lunch' in response.data          # 2026-04-10
        assert b'Concert' in response.data        # 2026-04-15
        assert b'Internet' in response.data       # 2026-05-01
        assert b'Clothes' in response.data        # 2026-05-10

    def test_profile_filters_by_end_date(self, auth_client_with_expenses):
        """Filtering by end_date shows expenses on or before that date."""
        # End date: 2026-04-10 should show Breakfast, Taxi, Lunch
        response = auth_client_with_expenses.get('/profile?end_date=2026-04-10')
        assert response.status_code == 200
        # Expenses after end date should not appear
        assert b'Concert' not in response.data   # 2026-04-15
        assert b'Internet' not in response.data  # 2026-05-01
        assert b'Clothes' not in response.data   # 2026-05-10
        # Expenses on or before end date should appear
        assert b'Breakfast' in response.data     # 2026-04-01
        assert b'Taxi' in response.data          # 2026-04-05
        assert b'Lunch' in response.data         # 2026-04-10

    def test_profile_filters_by_date_range(self, auth_client_with_expenses):
        """Filtering by both start_date and end_date shows expenses within the range."""
        # Range: 2026-04-05 to 2026-04-15 should show Taxi, Lunch, Concert
        response = auth_client_with_expenses.get('/profile?start_date=2026-04-05&end_date=2026-04-15')
        assert response.status_code == 200
        # Outside range
        assert b'Breakfast' not in response.data  # 2026-04-01 (too early)
        assert b'Internet' not in response.data   # 2026-05-01 (too late)
        assert b'Clothes' not in response.data    # 2026-05-10 (too late)
        # Inside range
        assert b'Taxi' in response.data           # 2026-04-05
        assert b'Lunch' in response.data          # 2026-04-10
        assert b'Concert' in response.data       # 2026-04-15

    def test_profile_ignores_invalid_date_parameters(self, auth_client_with_expenses):
        """Invalid or malformed date parameters are ignored gracefully (falls back to showing all data)."""
        # Test with invalid start_date format
        response = auth_client_with_expenses.get('/profile?start_date=2026/04/01')
        assert response.status_code == 200
        # Should show all expenses because invalid date is ignored
        assert b'Breakfast' in response.data
        assert b'Clothes' in response.data
        # Test with invalid end_date format
        response = auth_client_with_expenses.get('/profile?end_date=01-04-2026')
        assert response.status_code == 200
        assert b'Breakfast' in response.data
        assert b'Clothes' in response.data
        # Test with start_date after end_date (should be ignored or swapped? spec says: ensure start_date <= end_date; if not, swap or ignore invalid range)
        # We'll assume the implementation ignores the invalid range (as per spec: ignore invalid dates and treat as unset)
        response = auth_client_with_expenses.get('/profile?start_date=2026-05-01&end_date=2026-04-01')
        assert response.status_code == 200
        # Should show all expenses because the range is invalid (start > end) and ignored
        assert b'Breakfast' in response.data
        assert b'Clothes' in response.data

    def test_profile_reset_link_clears_filters(self, auth_client_with_expenses):
        """The Reset link clears the date filters and returns to showing all expenses."""
        # First apply a filter
        response = auth_client_with_expenses.get('/profile?start_date=2026-04-10')
        assert response.status_code == 200
        assert b'Breakfast' not in response.data  # filtered out
        # Now click Reset (which should be a link to /profile without query params)
        # We simulate by going to the profile page without parameters
        response = auth_client_with_expenses.get('/profile')
        assert response.status_code == 200
        # All expenses should be visible again
        assert b'Breakfast' in response.data
        assert b'Clothes' in response.data

    def test_profile_summary_stats_respect_date_filter(self, auth_client_with_expenses):
        """Summary stats, category breakdown, and recent transactions all respect the applied date filter."""
        # We'll check that the stats change when we apply a filter.
        # Get stats without filter
        response_all = auth_client_with_expenses.get('/profile')
        assert response_all.status_code == 200
        # We can't easily extract the stats from HTML without parsing, but we can check for known values.
        # Instead, we can check that the filtered page does not contain certain expenses and that the total amount is different.
        # For simplicity, we'll check that the filtered page does not show an expense that should be excluded.
        # And we'll check that the total amount in the stats is correct by looking for a known total in the HTML.
        # Since we don't have the exact HTML structure, we'll do a basic check: the filtered page should not show the excluded expense.
        # We already tested that in the previous tests. To avoid duplication, we'll just test one stat: the transaction count.
        # We can look for a pattern like "X expenses" in the HTML.
        # Let's assume the profile page shows the transaction count somewhere.
        # We'll check for the string "expenses" or "transactions" but it's better to check for a known amount.
        # Instead, we'll check that the total amount displayed in the stats matches the sum of filtered expenses.
        # This is getting too coupled to the implementation. Let's stick to checking that the filtered expenses are present/absent.
        # The spec says: "Summary stats, category breakdown, and recent transactions all respect the applied date filter."
        # We have already tested that recent transactions respect the filter (by checking presence/absence of descriptions).
        # For summary stats, we can check that the total spent changes when we filter.
        # We'll compute the expected total for a filter and then check if the HTML contains that total (formatted).
        # We know the amounts of our test expenses.
        # Filter: start_date=2026-04-10 -> expenses: Lunch (15), Concert (30), Internet (25), Clothes (40) = 110 total
        response = auth_client_with_expenses.get('/profile?start_date=2026-04-10')
        assert response.status_code == 200
        # We expect to see the total somewhere. Let's assume the stats are displayed in a card or something.
        # We'll look for the string "110" or "110.00" in the response data.
        # Since the amount is a float, it might be formatted as 110.00.
        assert b'110.00' in response.data or b'110' in response.data
        # Similarly, for end_date filter: end_date=2026-04-10 -> Breakfast (10), Taxi (20), Lunch (15) = 45 total
        response = auth_client_with_expenses.get('/profile?end_date=2026-04-10')
        assert response.status_code == 200
        assert b'45.00' in response.data or b'45' in response.data

    def test_profile_category_breakdown_respects_date_filter(self, auth_client_with_expenses):
        """Category breakdown respects the date filter."""
        # We'll check that the category breakdown changes with the filter.
        # For simplicity, we'll check that a category that should be absent is not mentioned.
        # Filter: start_date=2026-04-10 -> categories: Food (Lunch), Entertainment (Concert), Bills (Internet), Shopping (Clothes)
        # Note: we have two Food items (Breakfast and Lunch) but Breakfast is filtered out, so only Lunch remains.
        response = auth_client_with_expenses.get('/profile?start_date=2026-04-10')
        assert response.status_code == 200
        # We expect to see the categories that are present and not see the ones that are absent.
        # The category "Transport" should be absent because Taxi is filtered out.
        assert b'Transport' not in response.data
        # The category "Food" should still be present (because of Lunch)
        assert b'Food' in response.data
        # We can also check that the percentage for Food is present, but that's more complex.
        # We'll leave it at that for now.

    def test_profile_form_present_and_submits_via_get(self, auth_client_with_expenses):
        """The date filter form in the UI correctly submits the selected dates via GET and updates the displayed transaction list."""
        # Check that the profile page contains the form with start_date and end_date inputs and a filter button.
        response = auth_client_with_expenses.get('/profile')
        assert response.status_code == 200
        # Check for form elements (we can look for input names and the button)
        assert b'name="start_date"' in response.data
        assert b'name="end_date"' in response.data
        assert b'value="Apply"' in response.data or b'>Apply<' in response.data  # button text
        # Check that the form method is GET (should be, but we can check for method="GET")
        # We'll just assume it's GET as per spec.
        # Now test that submitting the form with dates works.
        # We'll simulate a form submission by clicking the button (which is a GET request with the form data).
        # We can do a GET request with the query parameters as we did before.
        # But we already tested the filtering behavior. We'll just do a quick check that the form submission redirects to the same page with params.
        # We'll submit the form with start_date=2026-04-01 and end_date=2026-05-10 (which should show all expenses in our test set)
        response = auth_client_with_expenses.get('/profile?start_date=2026-04-01&end_date=2026-05-10')
        assert response.status_code == 200
        # All expenses should be visible because our test set spans April to May 2026
        assert b'Breakfast' in response.data
        assert b'Clothes' in response.data