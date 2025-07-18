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
    if not User.query.filter_by(email="admin@yedc.com").first():
        admin = User(name="Admin", meter_number="0000", email="Gurus@yedc.com", password="Guru123", role="admin")
        db.session.add(admin)
        bands = ['A', 'B', 'C', 'D']
        for i in range(50):
            db.session.add(Unit(units=1, price_eth=round(random.uniform(0.0005, 0.0015), 6), band=random.choice(bands)))
        for i in range(15):
            unit = Unit(units=1, price_eth=round(random.uniform(0.0005, 0.0015), 6), band=random.choice(bands), status='Pending', buyer_meter='123456', buyer_email='buyer@example.com')
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
        session['user'] = email
        session['role'] = 'buyer'
        session['meter'] = meter
        return render_template_string(welcome_html)
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
    role = session['role']
    page = int(request.args.get('page', 1))
    per_page = 10
    if role in ['admin', 'seller']:
        units = Unit.query.paginate(page=page, per_page=per_page, error_out=False)
    else:
        units = Unit.query.filter_by(status='Available').paginate(page=page, per_page=per_page, error_out=False)
    return render_template_string(dashboard_html, units=units, role=role, meter=session['meter'])

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

@app.route('/add_seller', methods=['GET', 'POST'])
def add_seller():
    if session.get('role') != 'admin':
        return redirect('/dashboard')
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Seller email already exists.')
            return redirect('/add_seller')
        db.session.add(User(name=name, meter_number='0000', email=email, password=password, role='seller'))
        db.session.commit()
        flash('Seller added successfully.')
        return redirect('/dashboard')
    return render_template_string(add_seller_html)

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
        flash(f'Unit purchased! Admin/Seller will verify and credit your meter: {session["meter"]}')
    return redirect('/dashboard')

@app.route('/pending')
def pending():
    if session.get('role') not in ['admin', 'seller']:
        return redirect('/dashboard')
    pending_units = Unit.query.filter_by(status='Pending').all()
    return render_template_string(pending_html, units=pending_units)

@app.route('/complete')
def complete():
    if session.get('role') not in ['admin', 'seller']:
        return redirect('/dashboard')
    complete_units = Unit.query.filter_by(status='Sold').all()
    return render_template_string(complete_html, units=complete_units)

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
    buyer_email = session['user']
    transactions = Unit.query.filter_by(buyer_email=buyer_email).all()
    return render_template_string(history_html, units=transactions)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---- HTML Templates ----

register_html = """
<!DOCTYPE html><html><head><title>Register</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body class="bg-light p-5"><div class="container">
<h2 class="text-center">YEDC Registration</h2>
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
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head><body class="p-5">
<div class="container text-center">
<h2>Welcome to YEDC!</h2>
<a href="/dashboard" class="btn btn-primary m-3">Go to Marketplace</a>
<a href="#" onclick="connectWallet()" class="btn btn-success m-3">Connect Wallet</a>
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
        alert("No wallet found. Please open this app in MetaMask or Trust Wallet browser.");
    }
}
</script>
</body></html>
"""

login_html = """
<!DOCTYPE html><html><head><title>Login</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-light p-5"><div class="container">
<h2 class="text-center">YEDC Login</h2><form method="POST" class="mt-4">
<input name="email" class="form-control mb-3" type="email" placeholder="Email" required>
<input name="password" class="form-control mb-3" type="password" placeholder="Password" required>
<button type="submit" class="btn btn-success w-100">Login</button>
</form><a href="/register" class="d-block text-center mt-3">Register</a></div></body></html>
"""

dashboard_html = """
<!DOCTYPE html><html><head><title>Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head><body>
<div class="container mt-4">
<h3>{{ role|capitalize }} Panel</h3>
{% with messages = get_flashed_messages() %}
{% if messages %}
<div class="alert alert-info">{{ messages[0] }}</div>
{% endif %}
{% endwith %}

{% if role == 'buyer' %}
<a href="/dashboard" class="btn btn-outline-primary m-1">Home</a>
<a href="/history" class="btn btn-outline-secondary m-1">Transaction History</a>
<a href="#" onclick="connectWallet()" class="btn btn-outline-success m-1">Connect Wallet</a>
{% endif %}

{% if role in ['admin', 'seller'] %}
<form method="POST" action="/add_unit" class="row my-3">
<div class="col"><input name="units" class="form-control" placeholder="Units" required></div>
<div class="col"><input name="price" class="form-control" placeholder="Price ETH" required></div>
<div class="col"><select name="band" class="form-control"><option>A</option><option>B</option><option>C</option><option>D</option></select></div>
<div class="col"><button class="btn btn-primary">Add Unit</button></div>
</form>
<a href="/pending" class="btn btn-warning m-1">Pending</a>
<a href="/complete" class="btn btn-success m-1">Completed</a>
<a href="/add_seller" class="btn btn-dark m-1">Add Seller</a>
{% endif %}

<table class="table table-bordered mt-3">
<tr><th>ID</th><th>Units</th><th>Price (ETH)</th><th>Band</th><th>Status</th><th>Action</th></tr>
{% for u in units.items %}
<tr><td>{{ u.id }}</td><td>{{ u.units }}</td><td>{{ u.price_eth }}</td><td>{{ u.band }}</td><td>{{ u.status }}</td>
<td>{% if role=='buyer' and u.status == 'Available' %}
<button onclick="buyUnit('{{ u.id }}','{{ u.price_eth }}')" class="btn btn-success btn-sm">Buy</button>
{% else %}-{% endif %}</td></tr>
{% endfor %}
</table>

<nav>
<ul class="pagination">
{% if units.has_prev %}
<li class="page-item"><a class="page-link" href="{{ url_for('dashboard', page=units.prev_num) }}">Previous</a></li>
{% endif %}
{% if units.has_next %}
<li class="page-item"><a class="page-link" href="{{ url_for('dashboard', page=units.next_num) }}">Next</a></li>
{% endif %}
</ul>
</nav>

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
        alert("No wallet found. Use MetaMask or Trust Wallet browser.");
    }
}
async function buyUnit(id, price) {
    if (typeof window.ethereum !== 'undefined') {
        const accounts = await ethereum.request({ method: 'eth_requestAccounts' });
        const tx = { from: accounts[0], to: "0x9311DeE48D671Db61947a00B3f9Eae6408Ec4D7b", value: '0x' + (BigInt(price * 1e18)).toString(16) };
        await ethereum.request({ method: 'eth_sendTransaction', params: [tx] });
        window.location.href = "/buy/" + id;
    } else {
        alert("Wallet not found.");
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
<div class="container mt-5"><h3>Your Transactions</h3>
<table class="table table-bordered">
<tr><th>ID</th><th>Units</th><th>Price</th><th>Status</th><th>Band</th></tr>
{% for u in units %}
<tr><td>{{ u.id }}</td><td>{{ u.units }}</td><td>{{ u.price_eth }}</td><td>{{ u.status }}</td><td>{{ u.band }}</td></tr>
{% endfor %}
</table><a href="/dashboard" class="btn btn-secondary">Back</a></div></body></html>
"""

add_seller_html = """
<!DOCTYPE html><html><head><title>Add Seller</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head><body>
<div class="container mt-5"><h3>Add Seller Account</h3>
<form method="POST" class="mt-4">
<input name="name" class="form-control mb-2" placeholder="Seller Name" required>
<input name="email" class="form-control mb-2" placeholder="Seller Email" required>
<input name="password" class="form-control mb-3" type="password" placeholder="Password" required>
<button type="submit" class="btn btn-primary">Add Seller</button>
</form><a href="/dashboard" class="btn btn-secondary mt-3">Back</a></div></body></html>
"""

# ---- Run ----
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
