from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import io
import base64
from decouple import config

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'sssecretkey'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)  # Внешний ключ для связи с категорией
    category = db.relationship('Category', backref=db.backref('expenses', lazy=True))

    def __repr__(self):
        return f"<Expense {self.description}>"

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    expenses = Expense.query.paginate(page=page, per_page=5)
    return render_template('index.html', expenses=expenses)

@app.route('/add', methods=['POST'])
def add_expense():
    try:
        description = request.form['description']
        amount = float(request.form['amount'])
        category_name = request.form['category']

        category = Category.query.filter_by(name=category_name).first()
        if not category:
            category = Category(name=category_name)
            db.session.add(category)
            db.session.commit()

        new_expense = Expense(description=description, amount=amount, category=category)
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
            expense.category = request.form['category']

            db.session.commit()
            flash('Expense updated successfully!', 'success')
        except ValueError:
            flash('Invalid amount. Please enter a valid number.', 'error')

        return redirect(url_for('index'))

    return render_template('edit.html', expense=expense)

@app.route('/delete/<int:expense_id>')
def delete_expense(expense_id):
    expense = Expense.query.get(expense_id)
    db.session.delete(expense)
    db.session.commit()
    flash('Expense deleted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/stats')
def stats():
    total_expenses = db.session.query(db.func.sum(Expense.amount)).scalar() or 0
    average_expense = db.session.query(db.func.avg(Expense.amount)).scalar() or 0

    categories = Category.query.all()
    category_expenses = [db.session.query(db.func.sum(Expense.amount)).filter_by(category=category).scalar() or 0 for category in categories]

    fig, ax = plt.subplots()
    ax.bar([category.name for category in categories], category_expenses)
    ax.set_ylabel('Total Expenses')
    ax.set_title('Expenses by Category')

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)

    img_base64 = base64.b64encode(img.getvalue()).decode('utf-8')

    return render_template('stats.html', total_expenses=total_expenses, average_expense=average_expense, img_base64=img_base64)

if __name__ == '__main__':
    app.run(debug=True)