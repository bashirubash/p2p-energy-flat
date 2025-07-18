from flask import Flask, request, redirect, session, flash, render_template_string, url_for
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

# ---- Initialize DB ----
with app.app_context():
    db.create_all()
    if not User.query.filter_by(email="admin@yedc.com").first():
        admin = User(name="Admin", meter_number="0000", email="admin@yedc.com", password="Admin123", role="admin")
        db.session.add(admin)
        # Add 50 mixed band products
        bands = ['A', 'B', 'C', 'D']
        for i in range(50):
            db.session.add(Unit(units=1, price_eth=round(random.uniform(0.0005, 0.0015), 6), band=random.choice(bands)))
        # Add 15 random pending transactions
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
    if role == 'admin':
        units = Unit.query.paginate(page=page, per_page=per_page, error_out=False)
    else:
        units = Unit.query.filter_by(status='Available').paginate(page=page, per_page=per_page, error_out=False)
    return render_template_string(dashboard_html, units=units, role=role, meter=session['meter'])

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
        flash(f'Unit purchased! Admin will verify and credit your meter: {session["meter"]}')
    return redirect('/dashboard')

@app.route('/pending')
def pending():
    if session.get('role') != 'admin':
        return redirect('/dashboard')
    pending_units = Unit.query.filter_by(status='Pending').all()
    return render_template_string(pending_html, units=pending_units)

@app.route('/complete')
def complete():
    if session.get('role') != 'admin':
        return redirect('/dashboard')
    complete_units = Unit.query.filter_by(status='Sold').all()
    return render_template_string(complete_html, units=complete_units)

@app.route('/release/<int:unit_id>')
def release(unit_id):
    if session.get('role') != 'admin':
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
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-light p-5"><div class="container"><h2 class="text-center">Register</h2>
<form method="POST" class="mt-4">
<input name="name" class="form-control mb-2" placeholder="Name" required>
<input name="meter" class="form-control mb-2" placeholder="Meter Number" required>
<input name="email" class="form-control mb-2" placeholder="Email" required>
<input name="password" class="form-control mb-2" type="password" placeholder="Password" required>
<input name="confirm" class="form-control mb-3" type="password" placeholder="Confirm Password" required>
<button type="submit" class="btn btn-primary w-100">Register</button>
</form><a href="/login" class="d-block text-center mt-3">Already have an account? Login</a></div></body></html>
"""

login_html = """
<!DOCTYPE html><html><head><title>Login</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-light p-5"><div class="container"><h2 class="text-center">Login</h2>
<form method="POST" class="mt-4">
<input name="email" class="form-control mb-3" type="email" placeholder="Email" required>
<input name="password" class="form-control mb-3" type="password" placeholder="Password" required>
<button type="submit" class="btn btn-success w-100">Login</button>
</form><a href="/register" class="d-block text-center mt-3">Register</a></div></body></html>
"""

welcome_html = """
<!DOCTYPE html><html><head><title>Welcome</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-light p-5"><div class="container text-center">
<h2>Welcome to YEDC System</h2>
<p>Please connect your wallet or visit the marketplace.</p>
<a href="#" onclick="connectWallet()" class="btn btn-primary m-2">Connect Wallet</a>
<a href="/dashboard" class="btn btn-success m-2">Visit Marketplace</a>
</div>

<footer class="text-center mt-5">
<hr><p>&copy; 2025 YEDC Energy Platform</p>
</footer>

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

dashboard_html = """
<!DOCTYPE html><html><head><title>Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body><div class="container-fluid"><div class="row">
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

<div class="col-10 p-4"><h3>Dashboard - {{ role|capitalize }}</h3>
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

<table class="table table-bordered"><tr><th>ID</th><th>Units</th><th>Price</th><th>Band</th><th>Status</th><th>Action</th></tr>
{% for u in units.items %}
<tr><td>{{ u.id }}</td><td>{{ u.units }}</td><td>{{ u.price_eth }}</td><td>{{ u.band }}</td><td>{{ u.status }}</td>
<td>{% if role=='buyer' and u.status=='Available' %}
<button onclick="buyUnit('{{ u.id }}','{{ u.price_eth }}')" class="btn btn-success btn-sm">Buy</button>
{% else %}-{% endif %}</td></tr>
{% endfor %}
</table>

<div class="d-flex justify-content-center">
{% if units.has_prev %}
<a href="{{ url_for('dashboard', page=units.prev_num) }}" class="btn btn-secondary m-1">Previous</a>
{% endif %}
{% if units.has_next %}
<a href="{{ url_for('dashboard', page=units.next_num) }}" class="btn btn-secondary m-1">Next</a>
{% endif %}
</div>

<footer class="text-center mt-4"><hr><p>&copy; 2025 YEDC Energy Platform</p></footer>

<script>
async function buyUnit(id, price) {
    if (typeof window.ethereum === 'undefined') {
        alert("MetaMask or compatible wallet not found. Use DApp browser.");
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
</div></div></div></body></html>
"""

pending_html = """
<!DOCTYPE html><html><head><title>Pending</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head><body>
<div class="container mt-5"><h3>Pending Transactions</h3>
<table class="table table-bordered"><tr><th>ID</th><th>Units</th><th>Price</th><th>Meter</th><th>Email</th><th>Band</th><th>Action</th></tr>
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
<table class="table table-bordered"><tr><th>ID</th><th>Units</th><th>Price</th><th>Meter</th><th>Email</th><th>Band</th></tr>
{% for u in units %}
<tr><td>{{ u.id }}</td><td>{{ u.units }}</td><td>{{ u.price_eth }}</td><td>{{ u.buyer_meter }}</td><td>{{ u.buyer_email }}</td><td>{{ u.band }}</td></tr>
{% endfor %}
</table><a href="/dashboard" class="btn btn-secondary">Back</a></div></body></html>
"""

history_html = """
<!DOCTYPE html><html><head><title>Transaction History</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head><body>
<div class="container mt-5"><h3>Your Transaction History</h3>
<table class="table table-bordered"><tr><th>ID</th><th>Units</th><th>Price</th><th>Band</th><th>Status</th></tr>
{% for u in units %}
<tr><td>{{ u.id }}</td><td>{{ u.units }}</td><td>{{ u.price_eth }}</td><td>{{ u.band }}</td><td>{{ u.status }}</td></tr>
{% endfor %}
</table><a href="/dashboard" class="btn btn-secondary">Back</a></div></body></html>
"""

# ---- Run ----
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
