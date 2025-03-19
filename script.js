// Theme handling
document.addEventListener('DOMContentLoaded', function() {
    const theme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', theme);
    
    // Load expenses when the page loads
    loadExpenses();
    
    // Initialize charts
    initializeCharts();

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Theme Toggle Functionality
    const themeToggle = document.getElementById('themeToggle');
    const htmlElement = document.documentElement;
    
    themeToggle.addEventListener('click', function() {
        const currentTheme = htmlElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        
        htmlElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
    });

    // Load expenses if on dashboard page
    if (document.getElementById('expensesList')) {
        loadExpenses();
        loadAnalytics();
        loadBudgetAlerts();
        initializeSmartCategories();
    }

    // Add expense form handler
    const addExpenseForm = document.getElementById('addExpenseForm');
    const saveExpenseBtn = document.getElementById('saveExpense');
    
    if (saveExpenseBtn) {
        saveExpenseBtn.addEventListener('click', addExpense);
    }
});

// Load expenses
async function loadExpenses() {
    try {
        const response = await fetch('/api/expenses', {
            credentials: 'include',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to fetch expenses');
        }
        
        const expenses = await response.json();
        updateDashboardStats(expenses);
        renderExpenseTable(expenses);
        updateCharts(expenses);
    } catch (error) {
        console.error('Error loading expenses:', error);
        const expensesList = document.getElementById('expensesList');
        if (expensesList) {
            expensesList.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-danger">
                        Failed to load expenses. Please try refreshing the page.
                    </td>
                </tr>`;
        }
    }
}

// Update dashboard statistics
function updateDashboardStats(expenses) {
    if (!expenses) return;
    
    const totalExpenses = expenses.reduce((sum, exp) => sum + exp.amount, 0);
    const monthlyAverage = calculateMonthlyAverage(expenses);
    const categories = new Set(expenses.map(exp => exp.category));

    const totalElement = document.getElementById('totalExpenses');
    const averageElement = document.getElementById('monthlyAverage');
    const categoryElement = document.getElementById('categoryCount');

    if (totalElement) totalElement.textContent = `₹${totalExpenses.toFixed(2)}`;
    if (averageElement) averageElement.textContent = `₹${monthlyAverage.toFixed(2)}`;
    if (categoryElement) categoryElement.textContent = categories.size;
}

// Calculate monthly average
function calculateMonthlyAverage(expenses) {
    if (expenses.length === 0) return 0;
    
    const amounts = {};
    expenses.forEach(exp => {
        const month = exp.date.substring(0, 7); // YYYY-MM
        amounts[month] = (amounts[month] || 0) + exp.amount;
    });
    
    const totalMonths = Object.keys(amounts).length;
    const totalAmount = Object.values(amounts).reduce((sum, amount) => sum + amount, 0);
    
    return totalAmount / (totalMonths || 1);
}

// Render expense table
function renderExpenseTable(expenses) {
    const expensesList = document.getElementById('expensesList');
    if (!expensesList) return;

    if (!expenses || expenses.length === 0) {
        expensesList.innerHTML = `
            <tr>
                <td colspan="5" class="text-center">
                    <div class="empty-state">
                        <i class="fas fa-receipt fa-3x mb-3"></i>
                        <p class="empty-text">No expenses found</p>
                        <p class="empty-subtext">Add your first expense using the button above</p>
                    </div>
                </td>
            </tr>`;
        return;
    }

    expensesList.innerHTML = expenses.map(expense => {
        const categoryColor = getCategoryColor(expense.category);
        return `
        <tr>
            <td>${formatDate(expense.date)}</td>
            <td>
                <span class="category-badge" style="background-color: ${categoryColor}; color: white;">
                    ${getCategoryIcon(expense.category)}
                    ${expense.category}
                </span>
            </td>
            <td>${expense.description || '-'}</td>
            <td>₹${expense.amount.toFixed(2)}</td>
            <td>
                <button class="btn btn-sm btn-edit" onclick="editExpense(${expense.id})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-delete" onclick="deleteExpense(${expense.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `}).join('');
}

// Get category icon
function getCategoryIcon(category) {
    const icons = {
        'Food': 'fa-utensils',
        'Transportation': 'fa-car',
        'Housing': 'fa-home',
        'Utilities': 'fa-bolt',
        'Entertainment': 'fa-film',
        'Healthcare': 'fa-heart',
        'Shopping': 'fa-shopping-bag',
        'Education': 'fa-graduation-cap',
        'Travel': 'fa-plane',
        'Other': 'fa-receipt'
    };
    return `<i class="fas ${icons[category] || 'fa-receipt'} me-2"></i>`;
}

// Format date
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Initialize charts
function initializeCharts() {
    // Expense Trends Chart
    const expenseCtx = document.getElementById('expenseChart')?.getContext('2d');
    if (expenseCtx) {
        new Chart(expenseCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Daily Expenses',
                    data: [],
                    borderColor: '#4361ee',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    // Category Chart
    const categoryCtx = document.getElementById('categoryChart')?.getContext('2d');
    if (categoryCtx) {
        new Chart(categoryCtx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: []
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
}

// Update charts with expense data
function updateCharts(expenses) {
    updateExpenseTrendChart(expenses);
    updateCategoryChart(expenses);
}

// Update expense trend chart
function updateExpenseTrendChart(expenses) {
    const chart = Chart.getChart('expenseChart');
    if (!chart) return;

    const dailyTotals = {};
    expenses.forEach(exp => {
        dailyTotals[exp.date] = (dailyTotals[exp.date] || 0) + exp.amount;
    });

    const sortedDates = Object.keys(dailyTotals).sort();
    
    chart.data.labels = sortedDates.map(date => formatDate(date));
    chart.data.datasets[0].data = sortedDates.map(date => dailyTotals[date]);
    chart.update();
}

// Update category chart
function updateCategoryChart(expenses) {
    const chart = Chart.getChart('categoryChart');
    if (!chart) return;

    const categoryTotals = {};
    expenses.forEach(exp => {
        categoryTotals[exp.category] = (categoryTotals[exp.category] || 0) + exp.amount;
    });

    const categories = Object.keys(categoryTotals);
    const colors = categories.map(category => getCategoryColor(category));
    
    chart.data.labels = categories;
    chart.data.datasets[0].data = categories.map(cat => categoryTotals[cat]);
    chart.data.datasets[0].backgroundColor = colors;
    chart.update();
}

// Get category color
function getCategoryColor(category) {
    const colors = {
        'Food': '#ff6b6b',
        'Transportation': '#4d96ff',
        'Housing': '#845ec2',
        'Utilities': '#00c2a8',
        'Entertainment': '#f9c74f',
        'Healthcare': '#4cc9f0',
        'Shopping': '#f472b6',
        'Education': '#4361ee',
        'Travel': '#3a86ff',
        'Other': '#6c757d'
    };
    return colors[category] || colors['Other'];
}

// Show add expense modal
function showAddExpenseModal() {
    const modal = new bootstrap.Modal(document.getElementById('addExpenseModal'));
    modal.show();
}

// Show filter modal
function showFilterModal() {
    const modal = new bootstrap.Modal(document.getElementById('filterModal'));
    modal.show();
}

// Edit expense
async function editExpense(expenseId) {
    try {
        const response = await fetch(`/api/expenses/${expenseId}`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Failed to fetch expense');
        }
        
        const expense = await response.json();
        
        // Fill the form with expense data
        const form = document.getElementById('addExpenseForm');
        form.querySelector('[name="category"]').value = expense.category;
        form.querySelector('[name="amount"]').value = expense.amount;
        form.querySelector('[name="description"]').value = expense.description || '';
        form.querySelector('[name="date"]').value = expense.date;
        
        // Store the expense ID for updating
        form.dataset.expenseId = expenseId;
        
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('addExpenseModal'));
        modal.show();
        
        // Change the modal title and button text
        document.querySelector('#addExpenseModal .modal-title').textContent = 'Edit Expense';
        document.querySelector('#addExpenseModal .btn-primary').textContent = 'Update Expense';
        document.querySelector('#addExpenseModal .btn-primary').onclick = () => updateExpense(expenseId);
    } catch (error) {
        console.error('Error loading expense:', error);
        alert('Failed to load expense details. Please try again.');
    }
}

// Update expense
async function updateExpense(expenseId) {
    const form = document.getElementById('addExpenseForm');
    const formData = new FormData(form);
    
    try {
        const response = await fetch(`/api/expenses/${expenseId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                date: formData.get('date'),
                category: formData.get('category'),
                amount: parseFloat(formData.get('amount')),
                description: formData.get('description')
            })
        });

        if (!response.ok) {
            throw new Error('Failed to update expense');
        }

        // Close modal and reload expenses
        bootstrap.Modal.getInstance(document.getElementById('addExpenseModal')).hide();
        form.reset();
        delete form.dataset.expenseId;
        
        // Reset modal title and button
        document.querySelector('#addExpenseModal .modal-title').textContent = 'Add New Expense';
        document.querySelector('#addExpenseModal .btn-primary').textContent = 'Add Expense';
        document.querySelector('#addExpenseModal .btn-primary').onclick = addExpense;
        
        await loadExpenses();
        await loadAnalytics();
        await loadBudgetAlerts();
    } catch (error) {
        console.error('Error updating expense:', error);
        alert('Failed to update expense. Please try again.');
    }
}

// Delete expense
async function deleteExpense(expenseId) {
    if (!confirm('Are you sure you want to delete this expense?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/expenses/${expenseId}`, {
            method: 'DELETE',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'include'
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to delete expense');
        }
        
        // Reload expenses after successful deletion
        await loadExpenses();
        await loadAnalytics();
        await loadBudgetAlerts();
    } catch (error) {
        console.error('Error deleting expense:', error);
        alert(error.message);
    }
}

// Load analytics
async function loadAnalytics() {
    try {
        const response = await fetch('/api/expenses/analytics', {
            method: 'GET',
            credentials: 'include',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load analytics');
        }

        const data = await response.json();

        // Update summary cards if elements exist
        const totalElement = document.getElementById('totalExpenses');
        const averageElement = document.getElementById('monthlyAverage');
        const categoryElement = document.getElementById('categoryCount');

        if (totalElement) {
            totalElement.textContent = `₹${data.category_totals.reduce((sum, cat) => sum + cat.total, 0).toFixed(2)}`;
        }
        if (averageElement) {
            averageElement.textContent = `₹${data.monthly_average.toFixed(2)}`;
        }
        if (categoryElement) {
            categoryElement.textContent = data.category_totals.length;
        }

        // Update expense trend chart
        const trendCtx = document.getElementById('expenseTrend')?.getContext('2d');
        if (trendCtx) {
            // Destroy existing chart if it exists
            const existingChart = Chart.getChart('expenseTrend');
            if (existingChart) {
                existingChart.destroy();
            }

            new Chart(trendCtx, {
                type: 'line',
                data: {
                    labels: data.daily_totals.map(item => formatDate(item.date)),
                    datasets: [{
                        label: 'Daily Expenses',
                        data: data.daily_totals.map(item => item.total),
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1,
                        fill: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: value => '₹' + value.toFixed(2)
                            }
                        }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: context => '₹' + context.parsed.y.toFixed(2)
                            }
                        }
                    }
                }
            });
        }

        // Update category distribution chart
        const pieCtx = document.getElementById('categoryPie')?.getContext('2d');
        if (pieCtx) {
            // Destroy existing chart if it exists
            const existingChart = Chart.getChart('categoryPie');
            if (existingChart) {
                existingChart.destroy();
            }

            new Chart(pieCtx, {
                type: 'doughnut',
                data: {
                    labels: data.category_totals.map(item => item.category),
                    datasets: [{
                        data: data.category_totals.map(item => item.total),
                        backgroundColor: [
                            '#FF6384',
                            '#36A2EB',
                            '#FFCE56',
                            '#4BC0C0',
                            '#9966FF',
                            '#FF9F40',
                            '#4D5360',
                            '#803690',
                            '#00ADF0',
                            '#FDB45C'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: context => {
                                    const value = context.parsed;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `₹${value.toFixed(2)} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('Error loading analytics:', error);
        // Show error message in the analytics section
        const analyticsError = document.createElement('div');
        analyticsError.className = 'alert alert-danger';
        analyticsError.textContent = 'Failed to load analytics. Please try refreshing the page.';
        
        const analyticsContainer = document.querySelector('.analytics-section');
        if (analyticsContainer) {
            analyticsContainer.innerHTML = '';
            analyticsContainer.appendChild(analyticsError);
        }
    }
}

// Load budget alerts
function loadBudgetAlerts() {
    fetch('/api/budget/alerts')
        .then(response => response.json())
        .then(data => {
            const alertsContainer = document.getElementById('alertsContainer');
            alertsContainer.innerHTML = '';

            // Update budget progress
            const progress = (data.monthly_total / data.monthly_budget) * 100;
            const progressBar = document.getElementById('budgetProgress');
            progressBar.style.width = `${Math.min(progress, 100)}%`;
            progressBar.className = `progress-bar ${progress > 80 ? 'bg-danger' : 'bg-success'}`;

            // Display alerts
            data.alerts.forEach(alert => {
                const alertElement = document.createElement('div');
                alertElement.className = `alert alert-${alert.severity === 'high' ? 'danger' : 'warning'} alert-dismissible fade show`;
                alertElement.innerHTML = `
                    ${alert.message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                `;
                alertsContainer.appendChild(alertElement);
            });
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error loading budget alerts');
        });
}

// Initialize smart categories
function initializeSmartCategories() {
    const descriptionInput = document.getElementById('expenseDescription');
    const categorySelect = document.getElementById('expenseCategory');

    descriptionInput.addEventListener('blur', function() {
        if (this.value) {
            fetch('/api/categories/suggest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ description: this.value })
            })
            .then(response => response.json())
            .then(data => {
                if (data.category) {
                    categorySelect.value = data.category;
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        }
    });
}

// Add expense
async function addExpense(e) {
    e.preventDefault();
    const form = document.getElementById('addExpenseForm');
    const formData = new FormData(form);
    
    // Set today's date if date field is empty
    if (!formData.get('date')) {
        formData.set('date', new Date().toISOString().split('T')[0]);
    }

    const expenseData = {
        amount: parseFloat(formData.get('amount')),
        category: formData.get('category'),
        description: formData.get('description') || '',
        date: formData.get('date')
    };

    // Validate required fields
    if (!expenseData.amount || !expenseData.category || !expenseData.date) {
        alert('Please fill in all required fields');
        return;
    }

    try {
        const response = await fetch('/api/expenses', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'include',
            body: JSON.stringify(expenseData)
        });

        if (!response.ok) {
            throw new Error('Failed to add expense');
        }

        // Close modal and reset form
        const modal = bootstrap.Modal.getInstance(document.getElementById('addExpenseModal'));
        modal.hide();
        form.reset();

        // Reload expenses and analytics
        await loadExpenses();
        await loadAnalytics();
        await loadBudgetAlerts();
    } catch (error) {
        console.error('Error adding expense:', error);
        alert('Failed to add expense. Please try again.');
    }
} 