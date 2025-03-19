# Expense Tracking System

A simple web-based expense tracking system built with Flask and SQLite.

## Features

- Add expenses with date, category, amount, and description
- View all expenses in a table format
- Delete expenses
- Filter expenses by date range and category
- RESTful API for expense management

## Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

## Installation

1. Clone this repository or download the source code.

2. Navigate to the project directory:
   ```
   cd expense-tracking-system
   ```

3. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   ```

4. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```
     source venv/bin/activate
     ```

5. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the Application

1. Start the Flask application:
   ```
   python app.py
   ```

2. Open your web browser and navigate to:
   ```
   http://127.0.0.1:5000/
   ```

## API Endpoints

The application provides the following RESTful API endpoints:

- `GET /api/expenses` - Get all expenses (with optional filtering)
  - Query parameters:
    - `start_date` - Filter expenses from this date (YYYY-MM-DD)
    - `end_date` - Filter expenses until this date (YYYY-MM-DD)
    - `category` - Filter expenses by category

- `POST /api/expenses` - Add a new expense
  - Request body:
    ```json
    {
      "date": "YYYY-MM-DD",
      "category": "Category",
      "amount": 100.00,
      "description": "Description"
    }
    ```

- `DELETE /api/expenses/<id>` - Delete an expense by ID

## Database

The application uses SQLite as the database. The database file (`expenses.db`) will be created automatically when you run the application for the first time.

## License

This project is open source and available under the [MIT License](LICENSE). 