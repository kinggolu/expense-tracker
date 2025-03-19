import unittest
import json
import os
from app import app, init_db, DATABASE

class ExpenseTrackerTestCase(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        app.config['TESTING'] = True
        self.app = app.test_client()
        
        # Create test database
        if os.path.exists(DATABASE):
            os.remove(DATABASE)
        init_db()
        
    def tearDown(self):
        # Clean up after tests
        if os.path.exists(DATABASE):
            os.remove(DATABASE)
    
    def test_index_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
    
    def test_add_expense(self):
        # Test adding a new expense
        expense_data = {
            'date': '2023-01-01',
            'category': 'Food',
            'amount': 25.50,
            'description': 'Lunch'
        }
        
        response = self.app.post(
            '/api/expenses',
            data=json.dumps(expense_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('id', data)
        
        # Verify expense was added
        response = self.app.get('/api/expenses')
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['category'], 'Food')
        self.assertEqual(float(data[0]['amount']), 25.50)
    
    def test_delete_expense(self):
        # Add an expense first
        expense_data = {
            'date': '2023-01-01',
            'category': 'Food',
            'amount': 25.50,
            'description': 'Lunch'
        }
        
        response = self.app.post(
            '/api/expenses',
            data=json.dumps(expense_data),
            content_type='application/json'
        )
        
        data = json.loads(response.data)
        expense_id = data['id']
        
        # Delete the expense
        response = self.app.delete(f'/api/expenses/{expense_id}')
        self.assertEqual(response.status_code, 200)
        
        # Verify expense was deleted
        response = self.app.get('/api/expenses')
        data = json.loads(response.data)
        self.assertEqual(len(data), 0)
    
    def test_filter_expenses(self):
        # Add multiple expenses
        expenses = [
            {
                'date': '2023-01-01',
                'category': 'Food',
                'amount': 25.50,
                'description': 'Lunch'
            },
            {
                'date': '2023-01-15',
                'category': 'Transportation',
                'amount': 35.00,
                'description': 'Taxi'
            },
            {
                'date': '2023-02-01',
                'category': 'Food',
                'amount': 42.75,
                'description': 'Dinner'
            }
        ]
        
        for expense in expenses:
            self.app.post(
                '/api/expenses',
                data=json.dumps(expense),
                content_type='application/json'
            )
        
        # Test date filter
        response = self.app.get('/api/expenses?start_date=2023-01-10&end_date=2023-01-31')
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['category'], 'Transportation')
        
        # Test category filter
        response = self.app.get('/api/expenses?category=Food')
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)
        
        # Test combined filters
        response = self.app.get('/api/expenses?start_date=2023-01-01&category=Food')
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)
        
        response = self.app.get('/api/expenses?start_date=2023-02-01&category=Food')
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['description'], 'Dinner')

if __name__ == '__main__':
    unittest.main() 