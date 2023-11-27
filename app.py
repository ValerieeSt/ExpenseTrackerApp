from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import io
import base64
from decouple import config
from models import db, Category, Expense
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'sssecretkey'
db.init_app(app)
migrate = Migrate(app, db)

from models import Category, Expense

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    category_filter = request.args.get('category', type=str)
    sort_by = request.args.get('sort_by', 'date', type=str)
    sort_order = request.args.get('sort_order', 'desc', type=str)

    expenses_query = Expense.query

    if category_filter:
        expenses_query = expenses_query.filter(Expense.category.has(name=category_filter))

    if sort_by == 'amount':
        if sort_order == 'asc':
            expenses_query = expenses_query.order_by(Expense.amount)
        else:
            expenses_query = expenses_query.order_by(Expense.amount.desc())
    elif sort_by == 'description':
        if sort_order == 'asc':
            expenses_query = expenses_query.order_by(Expense.description)
        else:
            expenses_query = expenses_query.order_by(Expense.description.desc())
    else:
        expenses_query = expenses_query.order_by(Expense.date.desc())

    expenses = expenses_query.paginate(page=page, per_page=20)

    categories = Category.query.all()

    return render_template('index.html', expenses=expenses, categories=categories, category_filter=category_filter, sort_by=sort_by, sort_order=sort_order)

@app.route('/add', methods=['POST'])
def add_expense():
    try:
        description = request.form['description']
        amount = float(request.form['amount'])
        category_name = request.form['category']
        date_str = request.form['date']
        date = datetime.strptime(date_str, '%Y-%m-%d')

        category = Category.query.filter_by(name=category_name).first()
        if not category:
            category = Category(name=category_name)
            db.session.add(category)
            db.session.commit()

        new_expense = Expense(description=description, amount=amount, category=category, date=date)
        db.session.add(new_expense)
        db.session.commit()

        flash('Expense added successfully!', 'success')
    except ValueError:
        flash('Invalid amount. Please enter a valid number.', 'error')

    return redirect(url_for('index'))


@app.route('/edit/<int:expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    expense = Expense.query.get(expense_id)

    if request.method == 'POST':
        try:
            expense.description = request.form['description']
            expense.amount = float(request.form['amount'])
            category_name = request.form['category']

            category = Category.query.filter_by(name=category_name).first()
            if not category:
                category = Category(name=category_name)
                db.session.add(category)
                db.session.commit()

            expense.category = category

            db.session.commit()
            flash('Expense updated successfully!', 'success')
        except ValueError:
            flash('Invalid amount. Please enter a valid number.', 'error')

        return redirect(url_for('index'))

    return render_template('edit.html', expense=expense)



@app.route('/stats')
def stats():
    selected_month = request.args.get('month', type=int, default=datetime.now().month)
    selected_year = request.args.get('year', type=int, default=datetime.now().year)

    total_expenses = db.session.query(db.func.sum(Expense.amount)).filter(db.func.extract('month', Expense.date) == selected_month, db.func.extract('year', Expense.date) == selected_year).scalar() or 0

    average_expense = db.session.query(db.func.avg(Expense.amount)).filter(db.func.extract('month', Expense.date) == selected_month, db.func.extract('year', Expense.date) == selected_year).scalar() or 0

    categories = Category.query.all()
    category_expenses = [db.session.query(db.func.sum(Expense.amount)).filter(db.func.extract('month', Expense.date) == selected_month, db.func.extract('year', Expense.date) == selected_year, Expense.category == category).scalar() or 0 for category in categories]

    fig, ax = plt.subplots(figsize=(16, 6))
    ax.barh([category.name for category in categories], category_expenses)
    ax.set_xlabel('Total Expenses')
    ax.set_title(f'Expenses by Category - {selected_month}/{selected_year}')

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)

    img_base64 = base64.b64encode(img.getvalue()).decode('utf-8')

    return render_template('stats.html', total_expenses=total_expenses, average_expense=average_expense, img_base64=img_base64, selected_month=selected_month, selected_year=selected_year, datetime=datetime)

@app.route('/categories')
def get_categories():
    categories = Category.query.all()
    category_names = [category.name for category in categories]
    return {'categories': category_names}

@app.route('/delete/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    expense = Expense.query.get(expense_id)

    if not expense:
        return jsonify({'status': 'error', 'message': 'Expense not found!'}), 404

    if request.form.get('confirm_delete') == 'yes':
        try:
            db.session.delete(expense)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Expense deleted successfully!'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': f'An error occurred while deleting the expense: {str(e)}'}), 500
    else:
        return jsonify({'status': 'info', 'message': 'Deletion canceled.'})


if __name__ == '__main__':
    app.run(debug=True)