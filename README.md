# Spendly - Personal Expense Tracker

A lightweight, secure personal expense tracker built with Flask and SQLite. Track your expenses, understand your spending patterns, and take control of your finances.

![Spendly Landing Page](<Screenshot 2026-06-08 165257.png>)

## ✨ Features

- **User Authentication**: Secure registration and login system with password hashing
- **Expense Management**: Add, edit, and delete expenses with categorization
- **Spending Analytics**: View summary statistics, category breakdowns, and recent transactions
- **Date Filtering**: Filter expenses by custom date ranges
- **Responsive Design**: Clean, modern UI that works on mobile and desktop
- **Data Validation**: Comprehensive form validation for all inputs
- **Flash Messaging**: User feedback through success/error notifications
- **Protected Routes**: Authentication guards on all user-specific pages

## 🛠️ Technology Stack

- **Backend**: Flask 3.1.3 (Python web framework)
- **Database**: SQLite 3 (lightweight, file-based database)
- **Frontend**: 
  - HTML5 with Jinja2 templating
  - CSS3 (custom styles)
  - Vanilla JavaScript (no frameworks)
- **Security**: 
  - Werkzeug for password hashing
  - Parameterized SQL queries to prevent injection
  - Session-based authentication
- **Testing**: pytest 8.3.5 with pytest-flask plugin

## 📋 Prerequisites

- Python 3.10+
- pip (Python package manager)
- Git (for version control)

## 🚀 Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/spendly.git
   cd spendly
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database**
   The database is automatically initialized when you run the application for the first time.

5. **Run the development server**
   ```bash
   python app.py
   ```
   
   The application will be available at [http://localhost:5008](http://localhost:5008)

6. **Create your first account**
   - Navigate to [http://localhost:5008/register](http://localhost:5008/register)
   - Fill in the registration form
   - Log in and start tracking your expenses!

## 🧪 Running Tests

To run the test suite:
```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run a specific test file
pytest tests/test_foo.py

# Run tests matching a keyword
pytest -k "test_name"
```

## 📁 Project Structure

```
spendly/
├── app.py                 # Main Flask application - all routes
├── requirements.txt       # Python dependencies
├── README.md              # This file
├── .gitignore             # Git ignore rules
├── database/              # Database layer
│   ├── __init__.py        # Package initializer
│   ├── db.py              # SQLite connection helpers & schema
│   └── queries.py         # Database query functions
├── templates/             # HTML templates (Jinja2)
│   ├── base.html          # Base layout template
│   ├── landing.html       # Landing page
│   ├── login.html         # Login page
│   ├── register.html      # Registration page
│   ├── profile.html       # User dashboard
│   ├── add_expense.html   # Add expense form
│   ├── edit_expense.html  # Edit expense form
│   ├── analytics.html     # Analytics placeholder
│   ├── terms.html         # Terms and conditions
│   └── privacy.html       # Privacy policy
└── static/                # Static assets
    ├── css/               # Stylesheets
    │   ├── style.css      # Global styles
    │   └── landing.css    # Landing page specific styles
    └── js/                # JavaScript
        └── main.js        # Client-side functionality
```

## 🛤️ Routes

| Route | Method | Description | Status |
|-------|--------|-------------|--------|
| `GET /` | GET | Landing page | Implemented |
| `GET /register` | GET/POST | User registration | Implemented |
| `GET /login` | GET/POST | User login | Implemented |
| `GET /logout` | GET | User logout | Implemented |
| `GET /profile` | GET | User dashboard with expense summary | Implemented |
| `GET /expenses/add` | GET/POST | Add new expense | Implemented |
| `GET /expenses/<id>/edit` | GET/POST | Edit existing expense | Implemented |
| `GET /expenses/<id>/delete` | POST | Delete expense | Implemented |
| `GET /analytics` | GET | Analytics placeholder | Stub |
| `GET /terms` | GET | Terms and conditions | Implemented |
| `GET /privacy` | GET | Privacy policy | Implemented |

## 🗄️ Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
```

### Expenses Table
```sql
CREATE TABLE expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    date TEXT NOT NULL,
    description TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Valid Categories
- Food
- Transport
- Bills
- Health
- Entertainment
- Shopping
- Other

## 🔒 Security Features

1. **Password Hashing**: All passwords are hashed using Werkzeug's `generate_password_hash()` with salt
2. **SQL Injection Prevention**: All database queries use parameterized queries (`?` placeholders)
3. **Input Validation**: Comprehensive validation for all form inputs
4. **Authentication Guards**: Protected routes check for valid user sessions
5. **Authorization Checks**: Users can only access their own expenses
6. **Session Security**: Flask sessions with secret key configuration
7. **Foreign Key Enforcement**: SQLite foreign key constraints enabled on every connection

## 📱 Responsive Design

The application features a responsive design that adapts to different screen sizes:
- Mobile-first approach
- Flexible layouts using CSS
- Touch-friendly controls
- Optimized for both desktop and mobile browsers

## 🧩 Key Components

### Authentication System
- Secure user registration with email verification
- Password strength validation (minimum 8 characters)
- Remember me functionality via Flask sessions
- Automatic redirect after login/logout

### Expense Management
- Form validation for amount, category, and date
- Client-side and server-side validation
- Support for optional descriptions
- Category-based expense tracking
- Date filtering capabilities

### Dashboard Features
- Total spending summary
- Transaction count
- Top spending category
- Recent transactions list
- Category breakdown with percentages
- Custom date range filtering

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### To contribute:
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

Please make sure to:
- Follow the existing code style (PEP 8 for Python)
- Write clear, descriptive commit messages
- Update documentation as needed
- Add tests for new functionality

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Flask](https://flask.palletsprojects.com/)
- Inspired by personal finance management tools
- Thanks to all contributors and users

## 📞 Support

If you have any questions or need support, please open an issue in the repository.

---

Made with ❤️ for better financial awareness