"""
Tests for date filter functionality in Spendly profile page.
"""
import tempfile
import os
import sys

# Add the parent directory to the path so we can import database modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import init_db, get_db
from database.queries import get_summary_stats, get_recent_transactions, get_category_breakdown


def test_query_functions_with_date_params():
    """Test that query functions accept date parameters without errors."""
    # Create a temporary database for testing
    test_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    test_db.close()

    # Temporarily override the DATABASE constant
    import database.db
    original_db = database.db.DATABASE
    database.db.DATABASE = test_db.name

    try:
        # Initialize database
        init_db()

        # Test that functions work with date parameters (should return empty data since no expenses added)
        # These should not raise exceptions
        stats = get_summary_stats(1, start_date='2026-01-01', end_date='2026-12-31')
        assert isinstance(stats, dict)
        assert 'total_spent' in stats
        assert 'transaction_count' in stats
        assert 'top_category' in stats

        transactions = get_recent_transactions(1, start_date='2026-01-01', end_date='2026-12-31')
        assert isinstance(transactions, list)

        categories = get_category_breakdown(1, start_date='2026-01-01', end_date='2026-12-31')
        assert isinstance(categories, list)

        # Test with only start date
        stats_start = get_summary_stats(1, start_date='2026-01-01')
        assert isinstance(stats_start, dict)

        # Test with only end date
        stats_end = get_summary_stats(1, end_date='2026-12-31')
        assert isinstance(stats_end, dict)

        # Test with no date parameters (backward compatibility)
        stats_none = get_summary_stats(1)
        assert isinstance(stats_none, dict)

    finally:
        # Restore original database
        database.db.DATABASE = original_db
        # Clean up temp file
        os.unlink(test_db.name)


def test_date_parameter_validation():
    """Test that invalid date parameters are handled gracefully."""
    # Create a temporary database for testing
    test_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    test_db.close()

    # Temporarily override the DATABASE constant
    import database.db
    original_db = database.db.DATABASE
    database.db.DATABASE = test_db.name

    try:
        # Initialize database
        init_db()

        # Test with invalid date format - should be treated as no filter (not crash)
        stats = get_summary_stats(1, start_date='invalid-date', end_date='also-invalid')
        assert isinstance(stats, dict)

        # Test with empty string dates
        stats_empty = get_summary_stats(1, start_date='', end_date='')
        assert isinstance(stats_empty, dict)

    finally:
        # Restore original database
        database.db.DATABASE = original_db
        # Clean up temp file
        os.unlink(test_db.name)


if __name__ == "__main__":
    test_query_functions_with_date_params()
    test_date_parameter_validation()
    print("All tests passed!")