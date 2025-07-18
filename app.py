from flask import Flask, request, redirect, session, flash, render_template_string
from flask_sqlalchemy import SQLAlchemy
import random

app = Flask(__name__)
app.secret_key = 'yedc_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///market.db'
db = SQLAlchemy(app)

# ---- Models ----
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    meter_number = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(10))  # admin or buyer

class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    units = db.Column(db.Integer)
    price_eth = db.Column(db.Float)
    band = db.Column(db.String(10))
    status = db.Column(db.String(20), default="Available")
    buyer_meter = db.Column(db.String(100), nullable=True)
    buyer_email = db.Column(db.String(100), nullable=True)
    transaction_status = db.Column(db.String(20), default="Pending")

# ---- Initialize DB ----
with app.app_context():
    db.create_all()
    if not User.query.filter_by(email="gurus@gmail.com").first():
        admin = User(name="Guru", meter_number="0000", email="gurus@gmail.com", password="Guru123", role="admin")
        db.session.add(admin)
        bands = ["A", "B", "C", "D"]
        for i in range(50):
            db.session.add(Unit(units=1, price_eth=0.0005, band=random.choice(bands)))
        for i in range(10):
            unit = Unit(units=1, price_eth=0.0005, band=random.choice(bands), status="Pending", buyer_meter=f"Meter_{i+1}", buyer_email=f"buyer{i+1}@mail.com", transaction_status="Processing")
            db.session.add(unit)
        db.session.commit()

# ---- Routes ----
@app.route('/')
def home():
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        meter = request.form['meter']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm']
        if password != confirm:
            flash('Passwords do not match')
            return redirect('/register')
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect('/register')
        db.session.add(User(name=name, meter_number=meter, email=email, password=password, role='buyer'))
        db.session.commit()
        return render_template_string(welcome_html, name=name)
    return render_template_string(register_html)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session['user'] = user.email
            session['role'] = user.role
            session['meter'] = user.meter_number
            return redirect('/dashboard')
        flash('Invalid credentials')
    return render_template_string(login_html)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')

    page = int(request.args.get('page', 1))
    per_page = 10
    offset = (page - 1) * per_page

    role = session['role']
    if role == 'admin':
        units = Unit.query.offset(offset).limit(per_page).all()
    else:
        units = Unit.query.filter_by(status='Available').offset(offset).limit(per_page).all()

    total_units = Unit.query.count() if role == 'admin' else Unit.query.filter_by(status='Available').count()
    next_page = page + 1 if offset + per_page < total_units else None
    prev_page = page - 1 if page > 1 else None

    return render_template_string(dashboard_html, units=units, role=role, meter=session['meter'], next_page=next_page, prev_page=prev_page)

@app.route('/buy/<int:unit_id>')
def buy(unit_id):
    if session.get('role') != 'buyer':
        return redirect('/dashboard')
    unit = Unit.query.get(unit_id)
    if unit.status != 'Available':
        flash('Unit not available. Please contact admin if already paid.')
    else:
        unit.status = 'Pending'
        unit.buyer_meter = session['meter']
        unit.buyer_email = session['user']
        db.session.commit()
        flash(f'Payment received! Admin will verify and credit your meter: {session["meter"]}')
    return redirect('/dashboard')

@app.route('/pending')
def pending():
    if session.get('role') != 'admin':
        return redirect('/dashboard')
    pending_units = Unit.query.filter_by(status='Pending').limit(15).all()
    return render_template_string(pending_html, units=pending_units)

@app.route('/complete')
def complete():
    if session.get('role') != 'admin':
        return redirect('/dashboard')
    complete_units = Unit.query.filter_by(status='Sold').all()
    return render_template_string(complete_html, units=complete_units)

@app.route('/history')
def history():
    if session.get('role') != 'buyer':
        return redirect('/dashboard')
    history_units = Unit.query.filter_by(buyer_email=session['user']).all()
    return render_template_string(history_html, units=history_units)

@app.route('/release/<int:unit_id>')
def release(unit_id):
    if session.get('role') != 'admin':
        return redirect('/dashboard')
    unit = Unit.query.get(unit_id)
    unit.status = 'Sold'
    unit.transaction_status = 'Paid'
    db.session.commit()
    flash(f'Unit credited to meter {unit.buyer_meter}')
    return redirect('/pending')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---- HTML Templates ----

register_html = """
<!DOCTYPE html><html><head><title>Register</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body class="bg-light p-5">
<div class="container"><h2 class="text-center">Register - YEDC</h2>
<form method="POST" class="mt-4">
<input name="name" class="form-control mb-2" placeholder="Name" required>
<input name="meter" class="form-control mb-2" placeholder="Meter Number" required>
<input name="email" class="form-control mb-2" placeholder="Email" required>
<input name="password" class="form-control mb-2" type="password" placeholder="Password" required>
<input name="confirm" class="form-control mb-3" type="password" placeholder="Confirm Password" required>
<button type="submit" class="btn btn-primary w-100">Register</button>
</form><a href="/login" class="d-block text-center mt-3">Already have an account? Login</a></div></body></html>
"""

welcome_html = """
<!DOCTYPE html><html><head><title>Welcome</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="p-5"><div class="container text-center">
<h2>Welcome {{ name }}!</h2>
<p>Please choose an option below:</p>
<a href="/dashboard" class="btn btn-success m-2">Visit Marketplace</a>
<a href="#" onclick="alert('Connect to any custodial wallet like Trust Wallet, MetaMask, Binance etc.');" class="btn btn-primary m-2">Connect Wallet</a>
</div></body></html>
"""

login_html = """
<!DOCTYPE html><html><head><title>Login</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-light p-5"><div class="container">
<h2 class="text-center">Login - YEDC</h2><form method="POST" class="mt-4">
<input name="email" class="form-control mb-3" type="email" placeholder="Email" required>
<input name="password" class="form-control mb-3" type="password" placeholder="Password" required>
<button type="submit" class="btn btn-success w-100">Login</button>
</form><a href="/register" class="d-block text-center mt-3">Register</a></div></body></html>
"""

dashboard_html = """
<!DOCTYPE html><html><head><title>Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/web3@latest/dist/web3.min.js"></script></head>
<body><div class="container-fluid">
<div class="row">
<div class="col-2 bg-dark text-white p-3" style="min-height:100vh;">
<h4>{{ 'Admin Panel' if role=='admin' else 'Buyer Panel' }}</h4>
<a href="/dashboard" class="d-block text-white mb-2">Home</a>
{% if role == 'admin' %}
<a href="/pending" class="d-block text-white mb-2">Pending</a>
<a href="/complete" class="d-block text-white mb-2">Completed</a>
{% else %}
<a href="/history" class="d-block text-white mb-2">Transaction History</a>
{% endif %}
<a href="/logout" class="d-block text-white mt-4">Logout</a>
</div>

<div class="col-10 p-4">
<h3>Dashboard - {{ role|capitalize }}</h3>
{% with messages = get_flashed_messages() %}
{% if messages %}<div class="alert alert-info">{{ messages[0] }}</div>{% endif %}
{% endwith %}

{% if role == 'admin' %}
<form method="POST" action="/add_unit" class="row my-3">
<div class="col"><input name="units" class="form-control" placeholder="Units" required></div>
<div class="col"><input name="price" class="form-control" placeholder="Price ETH" required></div>
<div class="col"><select name="band" class="form-control"><option>A</option><option>B</option><option>C</option><option>D</option></select></div>
<div class="col"><button class="btn btn-primary">Add Unit</button></div>
</form>
{% endif %}

<table class="table table-bordered">
<tr><th>ID</th><th>Units</th><th>Price (ETH)</th><th>Band</th><th>Status</th><th>Action</th></tr>
{% for u in units %}
<tr><td>{{ u.id }}</td><td>{{ u.units }}</td><td>{{ u.price_eth }}</td><td>{{ u.band }}</td><td>{{ u.status }}</td>
<td>
{% if role=='buyer' and u.status == 'Available' %}
<button onclick="buyUnit('{{ u.id }}','{{ u.price_eth }}')" class="btn btn-success btn-sm">Pay & Buy</button>
{% else %}-{% endif %}
</td></tr>
{% endfor %}
</table>

<div class="mt-3">
{% if prev_page %}
<a href="/dashboard?page={{ prev_page }}" class="btn btn-secondary">Previous</a>
{% endif %}
{% if next_page %}
<a href="/dashboard?page={{ next_page }}" class="btn btn-primary">Next</a>
{% endif %}
</div>

<footer class="text-center mt-5"><small>&copy; 2025 YEDC Payment System</small></footer>
</div></div></div>

<script>
async function buyUnit(id, price) {
    if (typeof window.ethereum === 'undefined') {
        alert("MetaMask or wallet not found! Please connect your wallet.");
        return;
    }
    try {
        const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
        const tx = {
            from: accounts[0],
            to: "0x9311DeE48D671Db61947a00B3f9Eae6408Ec4D7b",
            value: '0x' + (BigInt(price * 1e18)).toString(16)
        };
        await window.ethereum.request({ method: 'eth_sendTransaction', params: [tx] });
        window.location.href = "/buy/" + id;
    } catch (err) {
        console.error(err);
        alert("Transaction failed or cancelled.");
    }
}
</script>

</body></html>
"""

pending_html = """
<!DOCTYPE html><html><head><title>Pending</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head><body>
<div class="container mt-5"><h3>Pending Transactions</h3>
<table class="table table-bordered">
<tr><th>ID</th><th>Units</th><th>Price</th><th>Meter</th><th>Email</th><th>Band</th><th>Action</th></tr>
{% for u in units %}
<tr><td>{{ u.id }}</td><td>{{ u.units }}</td><td>{{ u.price_eth }}</td><td>{{ u.buyer_meter }}</td><td>{{ u.buyer_email }}</td><td>{{ u.band }}</td>
<td><a href="/release/{{ u.id }}" class="btn btn-primary btn-sm">Release</a></td></tr>
{% endfor %}
</table><a href="/dashboard" class="btn btn-secondary">Back</a></div></body></html>
"""

complete_html = """
<!DOCTYPE html><html><head><title>Completed</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head><body>
<div class="container mt-5"><h3>Completed Transactions</h3>
<table class="table table-bordered">
<tr><th>ID</th><th>Units</th><th>Price</th><th>Meter</th><th>Email</th><th>Band</th></tr>
{% for u in units %}
<tr><td>{{ u.id }}</td><td>{{ u.units }}</td><td>{{ u.price_eth }}</td><td>{{ u.buyer_meter }}</td><td>{{ u.buyer_email }}</td><td>{{ u.band }}</td></tr>
{% endfor %}
</table><a href="/dashboard" class="btn btn-secondary">Back</a></div></body></html>
"""

history_html = """
<!DOCTYPE html><html><head><title>History</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head><body>
<div class="container mt-5"><h3>Transaction History</h3>
<table class="table table-bordered">
<tr><th>ID</th><th>Units</th><th>Price</th><th>Status</th><th>Band</th></tr>
{% for u in units %}
<tr><td>{{ u.id }}</td><td>{{ u.units }}</td><td>{{ u.price_eth }}</td><td>{{ u.status }}</td><td>{{ u.band }}</td></tr>
{% endfor %}
</table><a href="/dashboard" class="btn btn-secondary">Back</a></div></body></html>
"""

# ---- Run ----
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
