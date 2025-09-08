# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import csv
from io import StringIO

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'dev-secret-change-this'  # change for production

db = SQLAlchemy(app)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    payment_method = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'amount': self.amount,
            'category': self.category,
            'description': self.description,
            'date': self.date.isoformat(),
            'payment_method': self.payment_method,
        }

with app.app_context():
    db.create_all()


@app.route('/')
def index():
    # optional filters via query params: start, end, category
    from datetime import datetime as dt
    q = Expense.query.order_by(Expense.date.desc())
    start = request.args.get('start')
    end = request.args.get('end')
    category = request.args.get('category')
    if start:
        try:
            s = dt.strptime(start, '%Y-%m-%d').date()
            q = q.filter(Expense.date >= s)
        except:
            pass
    if end:
        try:
            e = dt.strptime(end, '%Y-%m-%d').date()
            q = q.filter(Expense.date <= e)
        except:
            pass
    if category:
        q = q.filter(Expense.category == category)
    expenses = q.all()
    total = sum(e.amount for e in expenses)
    categories = [r[0] for r in db.session.query(Expense.category).distinct().all()]
    return render_template('index.html', expenses=expenses, total=total, categories=categories)

@app.route('/add', methods=['POST'])
def add():
    amount = request.form.get('amount')
    category = request.form.get('category') or 'Other'
    description = request.form.get('description')
    date_str = request.form.get('date')
    payment_method = request.form.get('payment_method')
    try:
        amt = float(amount)
    except:
        flash('Please enter a valid amount.', 'danger')
        return redirect(url_for('index'))
    try:
        exp_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.utcnow().date()
    except:
        exp_date = datetime.utcnow().date()
    e = Expense(amount=amt, category=category, description=description, date=exp_date, payment_method=payment_method)
    db.session.add(e)
    db.session.commit()
    flash('Expense added.', 'success')
    return redirect(url_for('index'))

@app.route('/edit/<int:expense_id>', methods=['GET', 'POST'])
def edit(expense_id):
    e = Expense.query.get_or_404(expense_id)
    if request.method == 'POST':
        try:
            e.amount = float(request.form['amount'])
        except:
            flash('Invalid amount.', 'danger')
            return redirect(url_for('edit', expense_id=expense_id))
        e.category = request.form.get('category') or 'Other'
        e.description = request.form.get('description')
        date_str = request.form.get('date')
        try:
            e.date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else e.date
        except:
            pass
        e.payment_method = request.form.get('payment_method')
        db.session.commit()
        flash('Expense updated.', 'success')
        return redirect(url_for('index'))
    return render_template('edit.html', expense=e)

@app.route('/delete/<int:expense_id>', methods=['POST'])
def delete(expense_id):
    e = Expense.query.get_or_404(expense_id)
    db.session.delete(e)
    db.session.commit()
    flash('Expense deleted.', 'info')
    return redirect(url_for('index'))

@app.route('/export')
def export_csv():
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['id', 'amount', 'category', 'description', 'date', 'payment_method', 'created_at'])
    for ex in Expense.query.order_by(Expense.date.desc()).all():
        cw.writerow([ex.id, ex.amount, ex.category, ex.description, ex.date.isoformat(), ex.payment_method, ex.created_at.isoformat()])
    output = si.getvalue()
    headers = {
        "Content-Disposition": "attachment;filename=expenses.csv",
        "Content-Type": "text/csv"
    }
    return Response(output, headers=headers)

# API for charts
@app.route('/api/summary')
def api_summary():
    # monthly totals (YYYY-MM) using SQLite strftime
    from sqlalchemy import func
    results = db.session.query(func.strftime('%Y-%m', Expense.date), func.sum(Expense.amount))\
                .group_by(func.strftime('%Y-%m', Expense.date))\
                .order_by(func.strftime('%Y-%m', Expense.date)).all()
    data = [{'month': r[0], 'total': float(r[1] or 0)} for r in results]
    return jsonify(data)

@app.route('/api/category-summary')
def api_category_summary():
    from sqlalchemy import func
    results = db.session.query(Expense.category, func.sum(Expense.amount)).group_by(Expense.category).all()
    data = [{'category': r[0], 'total': float(r[1] or 0)} for r in results]
    return jsonify(data)

@app.route('/stats')
def stats():
    return render_template('stats.html')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)


