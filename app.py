from flask import Flask, request, redirect, session, flash, render_template_string
from flask_sqlalchemy import SQLAlchemy
import math

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
    role = db.Column(db.String(10))  # admin, seller, buyer

class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    units = db.Column(db.Integer)
    price_eth = db.Column(db.Float)
    band = db.Column(db.String(10))
    status = db.Column(db.String(20), default="Available")
    buyer_meter = db.Column(db.String(100), nullable=True)
    buyer_email = db.Column(db.String(100), nullable=True)

# ---- Initialize DB ----
with app.app_context():
    db.create_all()
    if not User.query.filter_by(email="gurus@gmail.com").first():
        admin = User(name="Guru", meter_number="0000", email="gurus@gmail.com", password="Guru123", role="admin")
        db.session.add(admin)
        for i in range(50):
            band = ["A", "B", "C", "D"][i % 4]
            db.session.add(Unit(units=1, price_eth=0.0005 + (i % 4) * 0.0001, band=band))
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
        flash('Welcome to YEDC! Connect your wallet or proceed to marketplace.')
        return redirect('/login')
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
    if role in ['admin', 'seller']:
        total_units = Unit.query.count()
        units = Unit.query.offset(offset).limit(per_page).all()
    else:
        total_units = Unit.query.filter_by(status='Available').count()
        units = Unit.query.filter_by(status='Available').offset(offset).limit(per_page).all()

    total_pages = math.ceil(total_units / per_page)

    return render_template_string(dashboard_html, units=units, role=role, meter=session['meter'], page=page, total_pages=total_pages)

@app.route('/add_unit', methods=['POST'])
def add_unit():
    if session.get('role') not in ['admin', 'seller']:
        return redirect('/dashboard')
    units = int(request.form['units'])
    price = float(request.form['price'])
    band = request.form['band']
    db.session.add(Unit(units=units, price_eth=price, band=band))
    db.session.commit()
    flash('Unit listed successfully')
    return redirect('/dashboard')

@app.route('/add_seller', methods=['POST'])
def add_seller():
    if session.get('role') != 'admin':
        return redirect('/dashboard')
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    if User.query.filter_by(email=email).first():
        flash('Email already exists')
        return redirect('/dashboard')
    db.session.add(User(name=name, meter_number="SELLER", email=email, password=password, role='seller'))
    db.session.commit()
    flash('Seller added successfully!')
    return redirect('/dashboard')

@app.route('/buy/<int:unit_id>')
def buy(unit_id):
    if session.get('role') != 'buyer':
        return redirect('/dashboard')
    unit = Unit.query.get(unit_id)
    if unit.status != 'Available':
        flash('Unit not available.')
    else:
        unit.status = 'Pending'
        unit.buyer_meter = session['meter']
        unit.buyer_email = session['user']
        db.session.commit()
        flash(f'Purchase initiated! Awaiting confirmation.')
    return redirect('/dashboard')

@app.route('/pending')
def pending():
    if session.get('role') not in ['admin', 'seller']:
        return redirect('/dashboard')
    pending_units = Unit.query.filter_by(status='Pending').all()
    return render_template_string(pending_html, units=pending_units)

@app.route('/release/<int:unit_id>')
def release(unit_id):
    if session.get('role') not in ['admin', 'seller']:
        return redirect('/dashboard')
    unit = Unit.query.get(unit_id)
    unit.status = 'Sold'
    db.session.commit()
    flash(f'Unit credited to meter {unit.buyer_meter}')
    return redirect('/pending')

@app.route('/history')
def history():
    if session.get('role') != 'buyer':
        return redirect('/dashboard')
    user_email = session['user']
    transactions = Unit.query.filter(Unit.buyer_email == user_email, Unit.status.in_(['Sold', 'Pending'])).all()
    return render_template_string(history_html, units=transactions)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---- HTML Templates ----

footer_html = """
<footer class="bg-dark text-white text-center p-3 mt-5">
YEDC System &copy; 2025. All Rights Reserved.
</footer>
"""

register_html = """
<!DOCTYPE html><html><head><title>Register</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body class="bg-light p-5">
<div class="container"><h2 class="text-center">YEDC Registration</h2>
<form method="POST" class="mt-4">
<input name="name" class="form-control mb-2" placeholder="Name" required>
<input name="meter" class="form-control mb-2" placeholder="Meter Number" required>
<input name="email" class="form-control mb-2" placeholder="Email" required>
<input name="password" class="form-control mb-2" type="password" placeholder="Password" required>
<input name="confirm" class="form-control mb-3" type="password" placeholder="Confirm Password" required>
<button type="submit" class="btn btn-primary w-100">Register</button>
</form><a href="/login" class="d-block text-center mt-3">Already have an account? Login</a></div>""" + footer_html + "</body></html>"

login_html = """
<!DOCTYPE html><html><head><title>Login</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-light p-5"><div class="container">
<h2 class="text-center">YEDC Login</h2><form method="POST" class="mt-4">
<input name="email" class="form-control mb-3" type="email" placeholder="Email" required>
<input name="password" class="form-control mb-3" type="password" placeholder="Password" required>
<button type="submit" class="btn btn-success w-100">Login</button>
</form><a href="/register" class="d-block text-center mt-3">Register</a></div>""" + footer_html + "</body></html>"

dashboard_html = """
<!DOCTYPE html><html><head><title>Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/web3@latest/dist/web3.min.js"></script></head>
<body><div class="container mt-4">
<h3>{{ role|capitalize }} Panel</h3><p>Meter: {{ meter }}</p>

{% with messages = get_flashed_messages() %}
{% if messages %}
<div class="alert alert-info">{{ messages[0] }}</div>
{% endif %}
{% endwith %}

{% if role in ['admin', 'seller'] %}
<form method="POST" action="/add_unit" class="row mb-3">
<div class="col"><input name="units" class="form-control" placeholder="Units" required></div>
<div class="col"><input name="price" class="form-control" placeholder="Price ETH" required></div>
<div class="col"><select name="band" class="form-control"><option>A</option><option>B</option><option>C</option><option>D</option></select></div>
<div class="col"><button class="btn btn-primary">Add Unit</button></div>
</form>

<form method="POST" action="/add_seller" class="row mb-3">
<div class="col"><input name="name" class="form-control" placeholder="Seller Name" required></div>
<div class="col"><input name="email" class="form-control" placeholder="Seller Email" required></div>
<div class="col"><input name="password" class="form-control" placeholder="Password" required></div>
<div class="col"><button class="btn btn-secondary">Add Seller</button></div>
</form>
{% endif %}

<div class="mb-3">
{% if role == 'buyer' %}
<a href="/dashboard" class="btn btn-outline-primary">Home</a>
<a href="/history" class="btn btn-outline-info">Transaction History</a>
<a href="#" onclick="connectWallet()" class="btn btn-primary">Connect Wallet</a>
{% endif %}
</div>

<table class="table table-bordered">
<tr><th>ID</th><th>Units</th><th>Price (ETH)</th><th>Band</th><th>Status</th><th>Action</th></tr>
{% for u in units %}
<tr><td>{{ u.id }}</td><td>{{ u.units }}</td><td>{{ u.price_eth }}</td><td>{{ u.band }}</td><td>{{ u.status }}</td>
<td>
{% if role=='buyer' and u.status == 'Available' %}
<button onclick="buyUnit('{{ u.id }}','{{ u.price_eth }}')" class="btn btn-success btn-sm">Buy</button>
{% else %}-{% endif %}
</td></tr>
{% endfor %}
</table>

<nav><ul class="pagination">
{% for p in range(1, total_pages + 1) %}
<li class="page-item {% if p == page %}active{% endif %}"><a class="page-link" href="/dashboard?page={{p}}">{{p}}</a></li>
{% endfor %}
</ul></nav>

<a href="/logout" class="btn btn-danger mt-3">Logout</a>
</div>

<script>
async function connectWallet() {
    if (typeof window.ethereum !== 'undefined') {
        try {
            await window.ethereum.request({ method: 'eth_requestAccounts' });
            alert("Wallet connected successfully!");
        } catch (err) {
            console.error(err);
            alert("Wallet connection rejected.");
        }
    } else {
        alert("No wallet found. Please open in MetaMask or Trust Wallet browser.");
    }
}

async function buyUnit(id, price) {
    if (typeof window.ethereum === 'undefined') {
        alert("MetaMask not found! Please install MetaMask or use Trust Wallet browser.");
        return;
    }
    try {
        const accounts = await ethereum.request({ method: 'eth_requestAccounts' });
        const tx = {
            from: accounts[0],
            to: "0x9311DeE48D671Db61947a00B3f9Eae6408Ec4D7b",
            value: '0x' + (BigInt(price * 1e18)).toString(16)
        };
        await ethereum.request({ method: 'eth_sendTransaction', params: [tx] });
        window.location.href = "/buy/" + id;
    } catch (err) {
        console.error(err);
        alert("Transaction failed or cancelled.");
    }
}
</script>
""" + footer_html + "</body></html>"

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
</table><a href="/dashboard" class="btn btn-secondary">Back</a></div>""" + footer_html + "</body></html>"

history_html = """
<!DOCTYPE html><html><head><title>History</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head><body>
<div class="container mt-5"><h3>Transaction History</h3>
<table class="table table-bordered">
<tr><th>ID</th><th>Units</th><th>Price</th><th>Band</th><th>Status</th></tr>
{% for u in units %}
<tr><td>{{ u.id }}</td><td>{{ u.units }}</td><td>{{ u.price_eth }}</td><td>{{ u.band }}</td><td>{{ u.status }}</td></tr>
{% endfor %}
</table><a href="/dashboard" class="btn btn-secondary">Back</a></div>""" + footer_html + "</body></html>"

# ---- Run ----
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
