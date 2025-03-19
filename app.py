from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime, timedelta
import hashlib
import secrets
import functools
from collections import defaultdict

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.secret_key = secrets.token_hex(16)  # Generate a secure secret key for sessions

# Ensure templates and static directories exist
base_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(base_dir, 'templates')
static_dir = os.path.join(base_dir, 'static')

try:
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
except Exception as e:
    print(f"Error creating directories: {str(e)}")
    raise

# Configure Flask app
app.template_folder = templates_dir
app.static_folder = static_dir
app.static_url_path = '/static'  # Add this line to explicitly set the static URL path

# Database setup
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'expenses.db')

def get_db_connection():
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {str(e)}")
        raise

def init_db():
    try:
        if not os.path.exists(DATABASE):
            os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    category TEXT NOT NULL,
                    amount REAL NOT NULL,
                    description TEXT,
                    user_id INTEGER NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
        else:
            # Check if users table exists, if not create it
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if user_id column exists in expenses table
            cursor.execute("PRAGMA table_info(expenses)")
            columns = cursor.fetchall()
            has_user_id = any(column['name'] == 'user_id' for column in columns)
            
            if not has_user_id:
                # Add user_id column to expenses table
                cursor.execute("ALTER TABLE expenses ADD COLUMN user_id INTEGER DEFAULT 1")
            
            # Check if users table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if not cursor.fetchone():
                cursor.execute('''
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                ''')
            
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"Database initialization error: {str(e)}")
        raise

# Initialize the database
init_db()

# Hash password function
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Login required decorator
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            # Clear any partial session data
            session.clear()
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and user['password'] == hash_password(password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid username or password'
    
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            error = 'Passwords do not match'
        else:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if username already exists
            cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
            if cursor.fetchone():
                error = 'Username already exists'
            else:
                # Check if email already exists
                cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
                if cursor.fetchone():
                    error = 'Email already exists'
                else:
                    # Create new user
                    hashed_password = hash_password(password)
                    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    cursor.execute(
                        'INSERT INTO users (username, email, password, created_at) VALUES (?, ?, ?, ?)',
                        (username, email, hashed_password, created_at)
                    )
                    conn.commit()
                    flash('Account created successfully! Please login.', 'success')
                    return redirect(url_for('login'))
            
            conn.close()
    
    return render_template('register.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/expenses', methods=['GET'])
@login_required
def get_expenses():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        category = request.args.get('category')
        
        query = "SELECT * FROM expenses WHERE user_id = ?"
        params = [session['user_id']]
        where_clauses = ["user_id = ?"]
        
        if start_date:
            where_clauses.append("date >= ?")
            params.append(start_date)
        
        if end_date:
            where_clauses.append("date <= ?")
            params.append(end_date)
            
        if category:
            where_clauses.append("category = ?")
            params.append(category)
        
        query = "SELECT * FROM expenses WHERE " + " AND ".join(where_clauses)
        query += " ORDER BY date DESC"
        
        cursor.execute(query, params)
        expenses = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Convert decimal amounts to float for JSON serialization
        for expense in expenses:
            expense['amount'] = float(expense['amount'])
        
        return jsonify(expenses)
    
    except Exception as e:
        app.logger.error(f"Error fetching expenses: {str(e)}")
        return jsonify({'error': 'Failed to fetch expenses'}), 500

@app.route('/api/expenses', methods=['POST'])
@login_required
def add_expense():
    try:
        data = request.get_json()
        
        if not data or not all(key in data for key in ['date', 'category', 'amount']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO expenses (date, category, amount, description, user_id) VALUES (?, ?, ?, ?, ?)',
            (data['date'], data['category'], data['amount'], data.get('description', ''), session['user_id'])
        )
        
        conn.commit()
        expense_id = cursor.lastrowid
        
        # Fetch the newly created expense
        cursor.execute('SELECT * FROM expenses WHERE id = ?', (expense_id,))
        expense = dict(cursor.fetchone())
        conn.close()
        
        return jsonify({
            'message': 'Expense added successfully',
            'expense': expense
        }), 201
        
    except Exception as e:
        app.logger.error(f"Error adding expense: {str(e)}")
        return jsonify({'error': 'Failed to add expense'}), 500

@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
@login_required
def delete_expense(expense_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify that the expense belongs to the current user
        cursor.execute('SELECT user_id FROM expenses WHERE id = ?', (expense_id,))
        expense = cursor.fetchone()
        
        if not expense:
            return jsonify({'error': 'Expense not found'}), 404
            
        if expense['user_id'] != session['user_id']:
            return jsonify({'error': 'Access denied'}), 403
        
        cursor.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Expense deleted successfully'}), 200
        
    except Exception as e:
        app.logger.error(f"Error deleting expense: {str(e)}")
        return jsonify({'error': 'Failed to delete expense'}), 500

@app.route('/api/expenses/<int:expense_id>', methods=['GET'])
@login_required
def get_expense(expense_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get expense and verify ownership
    cursor.execute('SELECT * FROM expenses WHERE id = ? AND user_id = ?', (expense_id, session['user_id']))
    expense = cursor.fetchone()
    conn.close()
    
    if not expense:
        return jsonify({'error': 'Expense not found'}), 404
    
    # Convert to dictionary and handle decimal
    expense_dict = dict(expense)
    expense_dict['amount'] = float(expense_dict['amount'])
    
    return jsonify(expense_dict)

@app.route('/api/expenses/<int:expense_id>', methods=['PUT'])
@login_required
def update_expense(expense_id):
    data = request.get_json()
    
    if not data or not all(key in data for key in ['date', 'category', 'amount']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify ownership
    cursor.execute('SELECT user_id FROM expenses WHERE id = ?', (expense_id,))
    expense = cursor.fetchone()
    
    if not expense or expense['user_id'] != session['user_id']:
        conn.close()
        return jsonify({'error': 'Expense not found or access denied'}), 403
    
    # Update expense
    cursor.execute('''
        UPDATE expenses 
        SET date = ?, category = ?, amount = ?, description = ?
        WHERE id = ?
    ''', (data['date'], data['category'], data['amount'], data.get('description', ''), expense_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Expense updated successfully'})

@app.route('/api/user/profile')
@login_required
def user_profile():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, username, email, created_at FROM users WHERE id = ?', (session['user_id'],))
    user = dict(cursor.fetchone())
    
    # Get total expenses
    cursor.execute('SELECT COUNT(*) as count, SUM(amount) as total FROM expenses WHERE user_id = ?', (session['user_id'],))
    stats = dict(cursor.fetchone())
    
    conn.close()
    
    return jsonify({
        'user': user,
        'stats': {
            'total_expenses': stats['count'] or 0,
            'total_amount': stats['total'] or 0
        }
    })

@app.route('/profile')
@login_required
def profile():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user information
    cursor.execute('SELECT id, username, email, created_at FROM users WHERE id = ?', (session['user_id'],))
    user_data = cursor.fetchone()
    
    # Check if user exists
    if user_data is None:
        # Create a default user object if user not found
        user = {
            'id': session['user_id'],
            'username': session.get('username', 'User'),
            'email': 'No email provided',
            'created_at': datetime.now().strftime('%B %d, %Y')
        }
    else:
        user = dict(user_data)
        # Format created_at date with error handling
        try:
            created_at = datetime.strptime(user['created_at'], '%Y-%m-%d %H:%M:%S')
            user['created_at'] = created_at.strftime('%B %d, %Y')
        except (ValueError, TypeError):
            # If date parsing fails, use current date
            user['created_at'] = datetime.now().strftime('%B %d, %Y')
    
    # Get user statistics
    cursor.execute('SELECT COUNT(*) as count, SUM(amount) as total FROM expenses WHERE user_id = ?', (session['user_id'],))
    stats = dict(cursor.fetchone())
    
    if stats['total'] is None:
        stats['total'] = 0
    
    # Get recent expenses
    cursor.execute('''
        SELECT * FROM expenses 
        WHERE user_id = ? 
        ORDER BY date DESC 
        LIMIT 5
    ''', (session['user_id'],))
    recent_expenses = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    # Helper function for Jinja template
    def get_category_icon(category):
        icons = {
            'Food': 'fas fa-utensils',
            'Transportation': 'fas fa-car',
            'Housing': 'fas fa-home',
            'Utilities': 'fas fa-bolt',
            'Entertainment': 'fas fa-film',
            'Healthcare': 'fas fa-heartbeat',
            'Shopping': 'fas fa-shopping-bag',
            'Education': 'fas fa-graduation-cap',
            'Travel': 'fas fa-plane',
            'Other': 'fas fa-tag'
        }
        return icons.get(category, 'fas fa-tag')
    
    return render_template('profile.html', 
                          user=user, 
                          stats=stats, 
                          recent_expenses=recent_expenses,
                          get_category_icon=get_category_icon)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user information
    cursor.execute('SELECT id, username, email FROM users WHERE id = ?', (session['user_id'],))
    user_data = cursor.fetchone()
    
    if user_data is None:
        conn.close()
        flash('User not found', 'error')
        return redirect(url_for('profile'))
    
    user = dict(user_data)
    error = None
    success = None
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        current_password = request.form['current_password']
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Verify current password
        cursor.execute('SELECT password FROM users WHERE id = ?', (session['user_id'],))
        stored_password = cursor.fetchone()['password']
        
        if hash_password(current_password) != stored_password:
            error = 'Current password is incorrect'
        elif username != user['username']:
            # Check if username already exists
            cursor.execute('SELECT id FROM users WHERE username = ? AND id != ?', (username, session['user_id']))
            if cursor.fetchone():
                error = 'Username already exists'
        elif email != user['email']:
            # Check if email already exists
            cursor.execute('SELECT id FROM users WHERE email = ? AND id != ?', (email, session['user_id']))
            if cursor.fetchone():
                error = 'Email already exists'
        elif new_password and new_password != confirm_password:
            error = 'New passwords do not match'
        else:
            # Update user information
            if new_password:
                # Update with new password
                cursor.execute(
                    'UPDATE users SET username = ?, email = ?, password = ? WHERE id = ?',
                    (username, email, hash_password(new_password), session['user_id'])
                )
            else:
                # Update without changing password
                cursor.execute(
                    'UPDATE users SET username = ?, email = ? WHERE id = ?',
                    (username, email, session['user_id'])
                )
            
            conn.commit()
            success = 'Profile updated successfully'
            
            # Update session username
            session['username'] = username
            
            # Refresh user data
            user['username'] = username
            user['email'] = email
    
    conn.close()
    
    return render_template('edit_profile.html', user=user, error=error, success=success)

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/api/expenses/analytics', methods=['GET'])
@login_required
def get_expense_analytics():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Get expenses by category
        cursor.execute("""
            SELECT category, SUM(amount) as total
            FROM expenses 
            WHERE user_id = ? AND date >= ? AND date <= ?
            GROUP BY category
            ORDER BY total DESC
        """, (session['user_id'], start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        
        category_totals = [dict(row) for row in cursor.fetchall()]
        
        # Get daily totals
        cursor.execute("""
            SELECT date, SUM(amount) as total
            FROM expenses 
            WHERE user_id = ? AND date >= ? AND date <= ?
            GROUP BY date
            ORDER BY date
        """, (session['user_id'], start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        
        daily_totals = [dict(row) for row in cursor.fetchall()]
        
        # Calculate monthly average
        cursor.execute("""
            SELECT AVG(daily_total) as monthly_average
            FROM (
                SELECT date, SUM(amount) as daily_total
                FROM expenses 
                WHERE user_id = ?
                GROUP BY date
            )
        """, (session['user_id'],))
        
        monthly_average = cursor.fetchone()['monthly_average'] or 0
        
        conn.close()
        
        return jsonify({
            'category_totals': category_totals,
            'daily_totals': daily_totals,
            'monthly_average': round(monthly_average, 2)
        })
    
    except Exception as e:
        app.logger.error(f"Error getting analytics: {str(e)}")
        return jsonify({'error': 'Failed to get analytics'}), 500

@app.route('/api/categories/suggest', methods=['POST'])
@login_required
def suggest_category():
    try:
        data = request.get_json()
        description = data.get('description', '').lower()
        
        # Define category keywords
        category_keywords = {
            'Food': ['restaurant', 'food', 'grocery', 'meal', 'lunch', 'dinner', 'breakfast'],
            'Transport': ['fuel', 'gas', 'uber', 'taxi', 'bus', 'train', 'metro'],
            'Shopping': ['mall', 'clothes', 'shoes', 'amazon', 'store'],
            'Bills': ['electricity', 'water', 'internet', 'phone', 'rent'],
            'Entertainment': ['movie', 'game', 'netflix', 'spotify', 'concert'],
            'Healthcare': ['doctor', 'medicine', 'hospital', 'clinic', 'medical']
        }
        
        # Find matching category
        for category, keywords in category_keywords.items():
            if any(keyword in description for keyword in keywords):
                return jsonify({'category': category})
        
        return jsonify({'category': 'Other'})
    
    except Exception as e:
        app.logger.error(f"Error suggesting category: {str(e)}")
        return jsonify({'error': 'Failed to suggest category'}), 500

@app.route('/api/budget/alerts', methods=['GET'])
@login_required
def get_budget_alerts():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get current month's total
        current_month = datetime.now().strftime('%Y-%m')
        cursor.execute("""
            SELECT SUM(amount) as monthly_total
            FROM expenses 
            WHERE user_id = ? AND strftime('%Y-%m', date) = ?
        """, (session['user_id'], current_month))
        
        monthly_total = cursor.fetchone()['monthly_total'] or 0
        
        # Get category totals for current month
        cursor.execute("""
            SELECT category, SUM(amount) as total
            FROM expenses 
            WHERE user_id = ? AND strftime('%Y-%m', date) = ?
            GROUP BY category
        """, (session['user_id'], current_month))
        
        category_totals = {row['category']: row['total'] for row in cursor.fetchall()}
        
        # Define budget limits (you can make these user-configurable)
        monthly_budget = 50000  # ₹50,000
        category_budgets = {
            'Food': 15000,
            'Transport': 5000,
            'Shopping': 10000,
            'Bills': 10000,
            'Entertainment': 5000,
            'Healthcare': 5000,
            'Other': 5000
        }
        
        # Generate alerts
        alerts = []
        
        # Check monthly budget
        if monthly_total > monthly_budget * 0.8:
            alerts.append({
                'type': 'monthly',
                'severity': 'high' if monthly_total > monthly_budget else 'warning',
                'message': f'Monthly expenses (₹{monthly_total:,.2f}) are {int((monthly_total/monthly_budget)*100)}% of budget'
            })
        
        # Check category budgets
        for category, budget in category_budgets.items():
            if category in category_totals and category_totals[category] > budget * 0.8:
                alerts.append({
                    'type': 'category',
                    'category': category,
                    'severity': 'high' if category_totals[category] > budget else 'warning',
                    'message': f'{category} expenses (₹{category_totals[category]:,.2f}) are {int((category_totals[category]/budget)*100)}% of budget'
                })
        
        conn.close()
        
        return jsonify({
            'alerts': alerts,
            'monthly_total': monthly_total,
            'monthly_budget': monthly_budget,
            'category_totals': category_totals,
            'category_budgets': category_budgets
        })
    
    except Exception as e:
        app.logger.error(f"Error getting budget alerts: {str(e)}")
        return jsonify({'error': 'Failed to get budget alerts'}), 500

@app.route('/api/expenses/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_expense(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if request.method == 'GET':
            cursor.execute('SELECT * FROM expenses WHERE id = ? AND user_id = ?', (id, session['user_id']))
            expense = cursor.fetchone()
            
            if expense:
                return jsonify(dict(expense))
            return jsonify({'error': 'Expense not found'}), 404
        
        elif request.method == 'PUT':
            data = request.get_json()
            
            cursor.execute('''
                UPDATE expenses 
                SET amount = ?, category = ?, description = ?, date = ?
                WHERE id = ? AND user_id = ?
            ''', (
                data['amount'],
                data['category'],
                data.get('description', ''),
                data['date'],
                id,
                session['user_id']
            ))
            
            conn.commit()
            return jsonify({'success': True})
        
        elif request.method == 'DELETE':
            cursor.execute('DELETE FROM expenses WHERE id = ? AND user_id = ?', (id, session['user_id']))
            conn.commit()
            return jsonify({'success': True})
        
    except Exception as e:
        app.logger.error(f"Error managing expense: {str(e)}")
        return jsonify({'error': f'Failed to {request.method.lower()} expense'}), 500
    
    finally:
        conn.close()

if __name__ == '__main__':
    try:
        # Allow connections from any device on the network
        host = '0.0.0.0'  # Listen on all available network interfaces
        port = 5000
        
        print(f" * Starting Flask server on {host}:{port}")
        print(" * You can access the application from other devices using your computer's IP address")
        print(" * For example: http://192.168.168.76:5000")
        print(" * Or using IPv6: http://[2401:4900:5f23:7a1d:5055:e95b:9fcb:b90e]:5000")
        
        app.run(
            host=host,
            port=port,
            debug=True,
            use_reloader=True,
            threaded=True
        )
    except Exception as e:
        print(f"Error starting the server: {str(e)}")
        input("Press Enter to exit...") 