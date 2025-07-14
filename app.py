from flask import Flask, request, redirect, session, flash, render_template_string
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'yedc_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///market.db'
db = SQLAlchemy(app)

# Models
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

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    buyer_email = db.Column(db.String(100))
    meter_number = db.Column(db.String(100))
    unit_id = db.Column(db.Integer)
    amount_eth = db.Column(db.Float)
    band = db.Column(db.String(10))
    status = db.Column(db.String(20), default="Pending")

# Initialize DB
with app.app_context():
    db.create_all()
    if not User.query.filter_by(email="gurus@gmail.com").first():
        admin = User(name="Guru", meter_number="0000", email="gurus@gmail.com", password="Guru123", role="admin")
        db.session.add(admin)
        for i in range(50):
            db.session.add(Unit(units=1, price_eth=0.0005, band="D"))
        db.session.commit()

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
        flash('Registered successfully. Please log in.')
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
    if session['role'] == 'admin':
        return redirect('/admin')

    units = Unit.query.all()
    transactions = Transaction.query.filter_by(buyer_email=session['user']).all()
    return render_template_string(buyer_dashboard_html, units=units, transactions=transactions, meter=session['meter'])

@app.route('/buy/<int:unit_id>')
def buy(unit_id):
    if session.get('role') != 'buyer':
        return redirect('/dashboard')
    unit = Unit.query.get(unit_id)
    if unit.status != 'Available':
        flash('Unit not available')
    else:
        tx = Transaction(buyer_email=session['user'], meter_number=session['meter'], unit_id=unit.id, amount_eth=unit.price_eth, band=unit.band)
        unit.status = 'Pending'
        db.session.add(tx)
        db.session.commit()
        flash('Payment sent. Waiting for admin approval.')
    return redirect('/dashboard')

@app.route('/admin')
def admin():
    if session.get('role') != 'admin':
        return redirect('/dashboard')
    units = Unit.query.all()
    return render_template_string(admin_dashboard_html, units=units)

@app.route('/admin/add_unit', methods=['POST'])
def add_unit():
    if session.get('role') != 'admin':
        return redirect('/dashboard')
    units = int(request.form['units'])
    price = float(request.form['price'])
    band = request.form['band']
    db.session.add(Unit(units=units, price_eth=price, band=band))
    db.session.commit()
    flash('Unit listed successfully')
    return redirect('/admin')

@app.route('/admin/pending')
def admin_pending():
    txs = Transaction.query.filter_by(status="Pending").all()
    return render_template_string(admin_pending_html, txs=txs)

@app.route('/admin/approve/<int:txid>')
def approve(txid):
    tx = Transaction.query.get(txid)
    unit = Unit.query.get(tx.unit_id)
    tx.status = "Paid"
    unit.status = "Sold"
    db.session.commit()
    flash(f"Approved: {tx.amount_eth} ETH - Meter {tx.meter_number}")
    return redirect('/admin/pending')

@app.route('/admin/completed')
def completed():
    txs = Transaction.query.filter_by(status="Paid").all()
    return render_template_string(admin_completed_html, txs=txs)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---- HTML ----
register_html = """
<!DOCTYPE html><html><head><title>Register - YEDC</title>
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
</form><a href="/login" class="d-block text-center mt-3">Already have an account? Login</a></div></body></html>
"""

login_html = """
<!DOCTYPE html><html><head><title>Login - YEDC</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-light p-5"><div class="container">
<h2 class="text-center">YEDC Login</h2><form method="POST" class="mt-4">
<input name="email" class="form-control mb-3" type="email" placeholder="Email" required>
<input name="password" class="form-control mb-3" type="password" placeholder="Password" required>
<button type="submit" class="btn btn-success w-100">Login</button>
</form><a href="/register" class="d-block text-center mt-3">Register</a></div></body></html>
"""

buyer_dashboard_html = """
<!DOCTYPE html><html><head><title>Buyer Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/web3@latest/dist/web3.min.js"></script></head>
<body><div class="container p-4">
<h3>YEDC Buyer Dashboard</h3><p>Meter: {{ meter }}</p>
{% with messages = get_flashed_messages() %}
{% if messages %}<div class="alert alert-success">{{ messages[0] }}</div>{% endif %}{% endwith %}
<table class="table table-bordered mt-4">
<tr><th>ID</th><th>Units</th><th>Price (ETH)</th><th>Band</th><th>Status</th><th>Action</th></tr>
{% for u in units %}
<tr><td>{{ u.id }}</td><td>{{ u.units }}</td><td>{{ u.price_eth }}</td><td>{{ u.band }}</td><td>{{ u.status }}</td>
<td>{% if u.status == 'Available' %}
<button onclick="buy('{{ u.id }}','{{ u.price_eth }}')" class="btn btn-success btn-sm">Buy</button>
{% else %}-{% endif %}</td></tr>
{% endfor %}
</table>
<script>
async function buy(id, price){
    if(window.ethereum){
        const web3 = new Web3(window.ethereum);
        await window.ethereum.request({ method: 'eth_requestAccounts' });
        const accounts = await web3.eth.getAccounts();
        await web3.eth.sendTransaction({
            from: accounts[0],
            to: "0x9311DeE48D671Db61947a00B3f9Eae6408Ec4D7b",
            value: web3.utils.toWei(price, 'ether')
        });
        window.location.href='/buy/'+id;
    }else{
        alert('Metamask not detected');
    }
}
</script>
<a href="/logout" class="btn btn-danger mt-3">Logout</a>
</div></body></html>
"""

admin_dashboard_html = """
<!DOCTYPE html><html><head><title>Admin Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body><div class="d-flex">
<div class="bg-dark p-3" style="width:200px; height:100vh;">
<h5 class="text-white">Admin Panel</h5>
<ul class="nav flex-column">
<li><a href="/admin" class="nav-link text-white">View Units</a></li>
<li><a href="/admin/pending" class="nav-link text-white">Pending Tx</a></li>
<li><a href="/admin/completed" class="nav-link text-white">Completed Tx</a></li>
<li><a href="/logout" class="nav-link text-white">Logout</a></li>
</ul>
</div>
<div class="p-4 w-100">
<h3>Units Listed</h3>
<form method="POST" action="/admin/add_unit" class="row mb-4">
<div class="col"><input name="units" class="form-control" placeholder="Units" required></div>
<div class="col"><input name="price" class="form-control" placeholder="Price ETH" required></div>
<div class="col"><select name="band" class="form-control"><option>A</option><option>B</option><option>C</option><option>D</option></select></div>
<div class="col"><button class="btn btn-primary">Add</button></div></form>
<table class="table table-bordered">
<tr><th>ID</th><th>Units</th><th>Price</th><th>Band</th><th>Status</th></tr>
{% for u in units %}
<tr><td>{{ u.id }}</td><td>{{ u.units }}</td><td>{{ u.price_eth }}</td><td>{{ u.band }}</td><td>{{ u.status }}</td></tr>
{% endfor %}
</table>
</div></div></body></html>
"""

admin_pending_html = """
<!DOCTYPE html><html><head><title>Pending</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body><div class="container p-4"><h3>Pending Transactions</h3>
<table class="table table-bordered">
<tr><th>ID</th><th>Buyer</th><th>Meter</th><th>Unit</th><th>Amount</th><th>Action</th></tr>
{% for t in txs %}
<tr><td>{{t.id}}</td><td>{{t.buyer_email}}</td><td>{{t.meter_number}}</td><td>{{t.unit_id}}</td><td>{{t.amount_eth}}</td>
<td><a href="/admin/approve/{{t.id}}" class="btn btn-success btn-sm">Approve</a></td></tr>
{% endfor %}
</table><a href="/admin" class="btn btn-secondary">Back</a></div></body></html>
"""

admin_completed_html = """
<!DOCTYPE html><html><head><title>Completed</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body><div class="container p-4"><h3>Completed Transactions</h3>
<table class="table table-bordered">
<tr><th>ID</th><th>Buyer</th><th>Meter</th><th>Unit</th><th>Amount</th></tr>
{% for t in txs %}
<tr><td>{{t.id}}</td><td>{{t.buyer_email}}</td><td>{{t.meter_number}}</td><td>{{t.unit_id}}</td><td>{{t.amount_eth}}</td></tr>
{% endfor %}
</table><a href="/admin" class="btn btn-secondary">Back</a></div></body></html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
