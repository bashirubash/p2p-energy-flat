from flask import Flask, request, redirect, url_for, session, flash, render_template_string
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'secretkey'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///p2p_energy.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

ADMIN_EMAIL = "gurus@gmail.com"
ADMIN_PASSWORD = "Guru123"
ADMIN_WALLET = "0x9311DeE48D671Db61947a00B3f9Eae6408Ec4D7b"

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    meter_number = db.Column(db.String(100))
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    wallet = db.Column(db.String(200))
    kyc = db.Column(db.Boolean, default=False)

class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    band = db.Column(db.String(50))
    amount = db.Column(db.Float)
    status = db.Column(db.String(50), default="Available")

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer)
    meter_number = db.Column(db.String(100))
    band = db.Column(db.String(50))
    amount = db.Column(db.Float)
    status = db.Column(db.String(50), default="Pending")

with app.app_context():
    db.create_all()

# Styles
style = """
<style>
body { font-family: Arial; background: #f4f6f9; padding:20px; }
.container { max-width: 500px; margin: auto; background: white; padding:20px; border-radius:10px; box-shadow:0 0 10px #ccc; }
h2 { text-align:center; color:#333; }
input, select { width:100%; padding:10px; margin:5px 0; }
button { background: #28a745; color:white; border:none; padding:10px; width:100%; margin-top:10px; }
nav { background:#343a40; padding:10px; color:white; text-align:center; }
a { color: white; margin:0 10px; text-decoration:none; }
table { width:100%; border-collapse:collapse; margin-top:10px;}
th, td { border:1px solid #ccc; padding:8px; text-align:center; }
</style>
"""

# Templates with inline style
index_page = style + """
<div class="container">
<h2>P2P Energy Marketplace</h2>
<a href='/register'>Register</a> | <a href='/login'>Login</a>
</div>
"""

register_page = style + """
<div class="container">
<h2>Register as Buyer</h2>
<form method="post">
<input name="name" placeholder="Full Name" required>
<input name="meter" placeholder="Meter Number" required>
<input name="email" type="email" placeholder="Email" required>
<input name="password" type="password" placeholder="Password" required>
<input name="confirm" type="password" placeholder="Confirm Password" required>
<button type="submit">Register</button>
</form>
</div>
"""

login_page = style + """
<div class="container">
<h2>Login</h2>
<form method="post">
<input name="email" type="email" placeholder="Email" required>
<input name="password" type="password" placeholder="Password" required>
<button type="submit">Login</button>
</form>
</div>
"""

kyc_page = style + """
<div class="container">
<h2>KYC Verification</h2>
<form method="post">
<input name="wallet" placeholder="Enter Wallet Address" required>
<button type="submit">Submit</button>
</form>
</div>
"""

dashboard_page = style + """
<div class="container">
<h2>Buyer Dashboard</h2>
<p>Welcome {{user.name}} | Meter: {{user.meter_number}}</p>
<a href="/logout">Logout</a>
<h3>Available Units:</h3>
<table>
<tr><th>Band</th><th>Amount</th><th>Action</th></tr>
{% for unit in units %}
<tr>
<td>{{unit.band}}</td>
<td>{{unit.amount}}</td>
<td><a href="/buy/{{unit.id}}">Buy</a></td>
</tr>
{% endfor %}
</table>
</div>
"""

admin_dashboard = style + """
<nav>
Admin Dashboard | <a href="/admin/add_unit">Add Unit</a> | <a href="/admin/pending">Pending Txns</a> | <a href="/admin/transactions">All Txns</a> | <a href="/logout">Logout</a>
</nav>
<div class="container">
<h2>Listed Units</h2>
<table>
<tr><th>ID</th><th>Band</th><th>Amount</th><th>Status</th></tr>
{% for u in units %}
<tr><td>{{u.id}}</td><td>{{u.band}}</td><td>{{u.amount}}</td><td>{{u.status}}</td></tr>
{% endfor %}
</table>
</div>
"""

add_unit_page = style + """
<div class="container">
<h2>Add Unit</h2>
<form method="post">
<input name="band" placeholder="Band" required>
<input name="amount" type="number" step="any" placeholder="Amount" required>
<button type="submit">Add</button>
</form>
</div>
"""

pending_txns = style + """
<nav>
Admin Dashboard | <a href="/admin/add_unit">Add Unit</a> | <a href="/admin/pending">Pending Txns</a> | <a href="/admin/transactions">All Txns</a> | <a href="/logout">Logout</a>
</nav>
<div class="container">
<h2>Pending Transactions</h2>
<table>
<tr><th>ID</th><th>Buyer ID</th><th>Meter</th><th>Band</th><th>Amount</th><th>Action</th></tr>
{% for t in txns %}
<tr>
<td>{{t.id}}</td><td>{{t.buyer_id}}</td><td>{{t.meter_number}}</td><td>{{t.band}}</td><td>{{t.amount}}</td>
<td><a href="/admin/approve/{{t.id}}">Approve</a></td>
</tr>
{% endfor %}
</table>
</div>
"""

all_txns = style + """
<nav>
Admin Dashboard | <a href="/admin/add_unit">Add Unit</a> | <a href="/admin/pending">Pending Txns</a> | <a href="/admin/transactions">All Txns</a> | <a href="/logout">Logout</a>
</nav>
<div class="container">
<h2>All Transactions</h2>
<table>
<tr><th>ID</th><th>Buyer ID</th><th>Meter</th><th>Band</th><th>Amount</th><th>Status</th></tr>
{% for t in txns %}
<tr>
<td>{{t.id}}</td><td>{{t.buyer_id}}</td><td>{{t.meter_number}}</td><td>{{t.band}}</td><td>{{t.amount}}</td><td>{{t.status}}</td>
</tr>
{% endfor %}
</table>
</div>
"""

# Routes

@app.route('/')
def index():
    return render_template_string(index_page)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        meter = request.form['meter']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm']
        if password != confirm:
            return "Password Mismatch!"
        hashed = generate_password_hash(password)
        user = User(name=name, meter_number=meter, email=email, password=hashed)
        db.session.add(user)
        db.session.commit()
        return redirect('/login')
    return render_template_string(register_page)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session['admin']=True
            return redirect('/admin/dashboard')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user'] = user.id
            return redirect('/kyc')
        return "Invalid Credentials"
    return render_template_string(login_page)

@app.route('/kyc', methods=['GET','POST'])
def kyc():
    user = User.query.get(session['user'])
    if request.method == 'POST':
        user.wallet = request.form['wallet']
        user.kyc = True
        db.session.commit()
        return redirect('/dashboard')
    return render_template_string(kyc_page)

@app.route('/dashboard')
def dashboard():
    user = User.query.get(session['user'])
    units = Unit.query.filter_by(status="Available").all()
    return render_template_string(dashboard_page, user=user, units=units)

@app.route('/buy/<int:id>')
def buy(id):
    unit = Unit.query.get(id)
    user = User.query.get(session['user'])
    txn = Transaction(buyer_id=user.id, meter_number=user.meter_number, band=unit.band, amount=unit.amount)
    db.session.add(txn)
    unit.status = "Pending"
    db.session.commit()
    return f"Order placed for {unit.amount} of {unit.band} to {user.meter_number}. Awaiting admin release."

@app.route('/admin/dashboard')
def admin_dash():
    units = Unit.query.all()
    return render_template_string(admin_dashboard, units=units)

@app.route('/admin/add_unit', methods=['GET','POST'])
def add_unit():
    if request.method=='POST':
        band = request.form['band']
        amount = request.form['amount']
        unit = Unit(band=band, amount=amount)
        db.session.add(unit)
        db.session.commit()
        return redirect('/admin/dashboard')
    return render_template_string(add_unit_page)

@app.route('/admin/pending')
def pending():
    txns = Transaction.query.filter_by(status="Pending").all()
    return render_template_string(pending_txns, txns=txns)

@app.route('/admin/transactions')
def transactions():
    txns = Transaction.query.all()
    return render_template_string(all_txns, txns=txns)

@app.route('/admin/approve/<int:id>')
def approve(id):
    txn = Transaction.query.get(id)
    txn.status = "Completed"
    unit = Unit.query.filter_by(band=txn.band, amount=txn.amount).first()
    if unit:
        unit.status="Sold"
    db.session.commit()
    return f"Released {txn.amount} of {txn.band} to meter {txn.meter_number}."

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Run
if __name__=="__main__":
    app.run(debug=True)
