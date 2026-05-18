# Spec: Date Filter For Profile Page

## Overview
Add date range filtering to the profile page to allow users to view their expenses within a specific time period. This feature enhances the profile page by letting users analyze spending patterns over custom intervals, building upon the existing transaction display implemented in previous steps.

## Depends on
- 04-profile-page-design (profile page structure and styling)
- 05-backend-routes-for-profile-page (backend data fetching for profile)
- 01-database-setup (expenses table with date column)

## Routes
No new routes. The existing GET /profile route will be modified to accept optional query parameters `start_date` and `end_date` (YYYY-MM-DD format) for filtering transactions.

## Database changes
No database changes. Filtering will be applied to the existing `date` column in the expenses table using parameterized queries.

## Templates
- Modify: templates/profile.html
  - Add a date range filter form above the transaction list with two date inputs (Start Date, End Date) and a Filter button.
  - The form should submit via GET to the same profile page.
  - Display currently selected date range (if any) and provide a Reset link to clear filters.

## Files to change
- app.py: Modify the profile route to read start_date and end_date from request.args, validate format, and pass to query functions.
- database/queries.py: 
  - Update get_recent_transactions(user_id, limit=10, start_date=None, end_date=None) to include date range filtering.
  - Update get_summary_stats(user_id, start_date=None, end_date=None) to calculate stats within date range.
  - Update get_category_breakdown(user_id, start_date=None, end_date=None) to calculate category breakdown within date range.
- templates/profile.html: Add date filter form and adjust transaction list heading to show active filter.

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use only sqlite3 module via existing database/db.py helpers.
- Parameterised queries only — never use f-string or string concatenation for SQL.
- All templates must extend base.html.
- Use CSS variables from existing style.css for styling; do not hardcode hex values.
- Validate date parameters: ignore invalid dates and treat as unset (show all data).
- If both start_date and end_date are provided, ensure start_date <= end_date; if not, swap or ignore invalid range.
- Maintain existing functionality when no dates are provided (show all expenses).
- Update query functions to optionally accept start_date and end_date strings in YYYY-MM-DD format.
- Adjust SQL queries to filter on date column using BETWEEN or >= AND <= conditions with placeholders.
- Ensure backward compatibility: existing calls to query functions without date parameters should continue to work.

## Definition of done
- [ ] The profile page loads without errors when no date filters are applied (shows all expenses).
- [ ] The profile page accepts start_date and end_date query parameters (e.g., /profile?start_date=2026-04-01&end_date=2026-04-30) and filters transactions accordingly.
- [ ] The date filter form in the UI correctly submits the selected dates via GET and updates the displayed transaction list.
- [ ] Invalid or malformed date parameters are ignored gracefully (falls back to showing all data).
- [ ] Summary stats, category breakdown, and recent transactions all respect the applied date filter.
- [ ] The Reset link clears the date filters and returns to showing all expenses.
- [ ] All database queries use parameterized placeholders (?), with no string formatting of user input into SQL.
- [ ] The page continues to extend base.html and uses existing CSS variables for styling.
- [ ] Manual testing confirms that filtering works for various date ranges, including edge cases like single day, open-ended ranges (only start or only end date), and cross-month ranges.