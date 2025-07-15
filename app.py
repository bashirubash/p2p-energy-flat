from flask import Flask, request, redirect, session, flash, render_template_string, jsonify
from flask_sqlalchemy import SQLAlchemy
import os

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
    meter_number = db.Column(db.String(100), nullable=True)

# ---- Initialize DB ----
with app.app_context():
    db.create_all()
    if not User.query.filter_by(email="gurus@gmail.com").first():
        admin = User(name="Guru", meter_number="0000", email="gurus@gmail.com", password="Guru123", role="admin")
        db.session.add(admin)
        for i in range(50):
            db.session.add(Unit(units=1, price_eth=0.0005, band="D"))
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

    role = session['role']
    if role == 'admin':
        units = Unit.query.all()
        return render_template_string(admin_dashboard_html, units=units)
    else:
        units = Unit.query.filter_by(status="Available").all()
        return render_template_string(buyer_dashboard_html, units=units, meter=session['meter'])

@app.route('/add_unit', methods=['POST'])
def add_unit():
    if session.get('role') != 'admin':
        return redirect('/dashboard')
    units = int(request.form['units'])
    price = float(request.form['price'])
    band = request.form['band']
    db.session.add(Unit(units=units, price_eth=price, band=band))
    db.session.commit()
    flash('Unit listed successfully')
    return redirect('/dashboard')

@app.route('/confirm_purchase', methods=['POST'])
def confirm_purchase():
    if 'user' not in session or session['role'] != 'buyer':
        return jsonify({'message':'Unauthorized'}), 401

    data = request.get_json()
    unit_id = data.get('unit_id')
    unit = Unit.query.get(unit_id)

    if not unit or unit.status != 'Available':
        return jsonify({'message':'Unit not available'}), 400

    unit.status = 'Pending'
    unit.meter_number = session['meter']
    db.session.commit()
    return jsonify({'message':'Purchase pending. Admin will process recharge to your meter: ' + session['meter']})

@app.route('/release_unit/<int:unit_id>')
def release_unit(unit_id):
    if session.get('role') != 'admin':
        return redirect('/dashboard')
    unit = Unit.query.get(unit_id)
    if unit and unit.status == 'Pending':
        unit.status = 'Paid'
        db.session.commit()
        flash(f"Unit {unit.id} released to {unit.meter_number}")
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---- HTML Templates ----
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
<!DOCTYPE html><html><head><title>Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/web3@latest/dist/web3.min.js"></script></head>
<body class="p-4"><div class="container">
<h3>YEDC Dashboard - Buyer</h3><p>Meter: {{ meter }}</p>
{% with messages = get_flashed_messages() %}
{% if messages %}
<div class="alert alert-success">{{ messages[0] }}</div>
{% endif %}{% endwith %}

<table class="table table-bordered mt-4">
<tr><th>ID</th><th>Units</th><th>Price (ETH)</th><th>Band</th><th>Status</th><th>Action</th></tr>
{% for u in units %}
<tr><td>{{ u.id }}</td><td>{{ u.units }}</td><td>{{ u.price_eth }}</td><td>{{ u.band }}</td><td>{{ u.status }}</td>
<td><button onclick="buy('{{ u.id }}','{{ u.price_eth }}')" class="btn btn-success btn-sm">Buy</button></td></tr>
{% endfor %}
</table>

<a href="/logout" class="btn btn-danger mt-3">Logout</a>
</div>

<script>
async function buy(id, price){
    if(window.ethereum){
        try {
            const web3 = new Web3(window.ethereum);
            await ethereum.request({ method: 'eth_requestAccounts' });
            const accounts = await web3.eth.getAccounts();

            await web3.eth.sendTransaction({
                from: accounts[0],
                to: "0x9311DeE48D671Db61947a00B3f9Eae6408Ec4D7b",
                value: web3.utils.toWei(price, 'ether')
            });

            const response = await fetch('/confirm_purchase', {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({unit_id:id})
            });

            const data = await response.json();

            if (response.ok) {
                alert(data.message);
                window.location.reload();
            } else {
                alert("Error: " + data.message);
            }
        } catch (err) {
            console.error(err);
            alert("Transaction cancelled or failed.");
        }
    } else {
        alert('Metamask not detected.');
    }
}
</script>
</body></html>
"""

admin_dashboard_html = """
<!DOCTYPE html><html><head><title>Admin Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="p-4"><div class="container-fluid">
<div class="row">
<div class="col-3 bg-dark text-white p-3" style="height:100vh;">
<h4>Admin Panel</h4>
<ul class="nav flex-column">
<li class="nav-item"><a class="nav-link text-white" href="/dashboard">View Units</a></li>
<li class="nav-item mt-2"><form method="POST" action="/add_unit">
<input name="units" class="form-control my-1" placeholder="Units" required>
<input name="price" class="form-control my-1" placeholder="Price ETH" required>
<select name="band" class="form-control my-1"><option>A</option><option>B</option><option>C</option><option>D</option></select>
<button class="btn btn-primary w-100 mt-2">Add Unit</button></form></li>
<li class="nav-item mt-4"><a class="nav-link text-white" href="/logout">Logout</a></li>
</ul></div>
<div class="col-9 p-4">
<h3>All Units</h3>
{% with messages = get_flashed_messages() %}
{% if messages %}
<div class="alert alert-info">{{ messages[0] }}</div>
{% endif %}{% endwith %}
<table class="table table-bordered mt-3">
<tr><th>ID</th><th>Units</th><th>Price</th><th>Band</th><th>Status</th><th>Meter</th><th>Action</th></tr>
{% for u in units %}
<tr><td>{{ u.id }}</td><td>{{ u.units }}</td><td>{{ u.price_eth }}</td><td>{{ u.band }}</td><td>{{ u.status }}</td><td>{{ u.meter_number }}</td>
<td>{% if u.status == 'Pending' %}<a href="/release_unit/{{ u.id }}" class="btn btn-success btn-sm">Release</a>{% endif %}</td></tr>
{% endfor %}
</table>
</div></div></div></body></html>
"""

# ---- Run ----
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
