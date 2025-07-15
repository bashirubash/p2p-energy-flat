from flask import Flask, render_template_string, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from web3 import Web3
import json

app = Flask(__name__)
app.secret_key = 'yedc_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yedc.db'
db = SQLAlchemy(app)

# --- Blockchain Setup ---
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))  # Local testnet via Hardhat

# Paste your deployed contract address here after deploying locally
contract_address = Web3.to_checksum_address("0xYourLocalContractAddress")

contract_abi = [  # Your ABI here (simplified for brevity)
    {
        "inputs": [],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "buyer", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"}
        ],
        "name": "EnergyBought",
        "type": "event"
    },
    {
        "inputs": [],
        "name": "buyEnergy",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "withdraw",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

contract = w3.eth.contract(address=contract_address, abi=contract_abi)

# --- Database Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    meter_number = db.Column(db.String(50))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(10))  # 'admin' or 'buyer'

class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    units = db.Column(db.Integer)
    price_eth = db.Column(db.Float)
    band = db.Column(db.String(10))
    status = db.Column(db.String(20), default="Available")
    buyer_wallet = db.Column(db.String(100))
    pending = db.Column(db.Boolean, default=False)

# --- Setup ---
with app.app_context():
    db.create_all()
    if not User.query.filter_by(email="gurus@gmail.com").first():
        admin = User(name="Guru", meter_number="0000", email="gurus@gmail.com", password="Guru123", role="admin")
        db.session.add(admin)
        db.session.commit()

# --- Routes ---
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
        flash('Registered successfully.')
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
    units = Unit.query.all()
    return render_template_string(dashboard_html, units=units, role=session['role'], meter=session['meter'])

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

@app.route('/buy/<int:unit_id>', methods=['POST'])
def buy(unit_id):
    if session.get('role') != 'buyer':
        return redirect('/dashboard')
    unit = Unit.query.get(unit_id)
    if unit.status == 'Sold':
        return 'Already sold'
    buyer_wallet = request.json.get('wallet')
    unit.status = 'Pending'
    unit.buyer_wallet = buyer_wallet
    unit.pending = True
    db.session.commit()
    return {'status': 'pending', 'message': 'Transaction recorded. Awaiting admin approval.'}

@app.route('/pending')
def pending():
    if session.get('role') != 'admin':
        return redirect('/dashboard')
    units = Unit.query.filter_by(pending=True).all()
    return render_template_string(pending_html, units=units)

@app.route('/approve/<int:unit_id>')
def approve(unit_id):
    if session.get('role') != 'admin':
        return redirect('/dashboard')
    unit = Unit.query.get(unit_id)
    unit.status = 'Sold'
    unit.pending = False
    db.session.commit()
    return redirect('/pending')

@app.route('/withdraw')
def withdraw():
    if session.get('role') != 'admin':
        return redirect('/dashboard')
    admin = w3.eth.accounts[0]  # Local owner account in Hardhat
    tx = contract.functions.withdraw().transact({'from': admin})
    return f'Withdrawal successful. TX: {tx.hex()}'

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# --- HTML Templates ---

register_html = """
<!DOCTYPE html><html><head><title>Register</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-light p-5"><div class="container">
<h3>Register</h3>
<form method="POST">
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
<body class="bg-light p-5"><div class="container">
<h3>Login</h3>
<form method="POST">
<input name="email" class="form-control mb-3" type="email" placeholder="Email" required>
<input name="password" class="form-control mb-3" type="password" placeholder="Password" required>
<button type="submit" class="btn btn-success w-100">Login</button>
</form><a href="/register" class="d-block text-center mt-3">Register</a></div></body></html>
"""

dashboard_html = """
<!DOCTYPE html><html><head><title>Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/web3@latest/dist/web3.min.js"></script></head>
<body class="p-4"><div class="container">
<h3>Dashboard - {{ role|capitalize }}</h3><p>Meter: {{ meter }}</p>

{% if role == 'admin' %}
<form method="POST" action="/add_unit" class="my-3 row">
<div class="col"><input name="units" class="form-control" placeholder="Units" required></div>
<div class="col"><input name="price" class="form-control" placeholder="Price ETH" required></div>
<div class="col"><select name="band" class="form-control"><option>A</option><option>B</option><option>C</option><option>D</option></select></div>
<div class="col"><button class="btn btn-primary">Add Unit</button></div>
</form>
<a href="/pending" class="btn btn-warning mb-3">View Pending</a>
<a href="/withdraw" class="btn btn-danger mb-3">Withdraw</a>
{% endif %}

<table class="table table-bordered">
<tr><th>ID</th><th>Units</th><th>Price (ETH)</th><th>Band</th><th>Status</th><th>Action</th></tr>
{% for u in units %}
<tr><td>{{ u.id }}</td><td>{{ u.units }}</td><td>{{ u.price_eth }}</td><td>{{ u.band }}</td><td>{{ u.status }}</td><td>
{% if role=='buyer' and u.status == 'Available' %}
<button onclick="buy('{{ u.id }}', '{{ u.price_eth }}')" class="btn btn-success btn-sm">Buy</button>
{% else %}-{% endif %}
</td></tr>
{% endfor %}
</table>

<a href="/logout" class="btn btn-secondary">Logout</a>
</div>

<script>
async function buy(id, price) {
    if (window.ethereum) {
        const web3 = new Web3(window.ethereum);
        await window.ethereum.request({ method: 'eth_requestAccounts' });
        const accounts = await web3.eth.getAccounts();
        const tx = await web3.eth.sendTransaction({
            from: accounts[0],
            to: "{{ contract_address }}",
            value: web3.utils.toWei(price, 'ether')
        });
        await fetch("/buy/" + id, {
            method: "POST",
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({wallet: accounts[0]})
        });
        alert("Transaction sent! Await admin release.");
        window.location.reload();
    } else {
        alert("Please install Metamask.");
    }
}
</script>
</body></html>
"""

pending_html = """
<!DOCTYPE html><html><head><title>Pending Transactions</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="p-4"><div class="container">
<h3>Pending Transactions</h3>
<table class="table table-bordered">
<tr><th>ID</th><th>Buyer Wallet</th><th>Units</th><th>Band</th><th>Action</th></tr>
{% for u in units %}
<tr><td>{{ u.id }}</td><td>{{ u.buyer_wallet }}</td><td>{{ u.units }}</td><td>{{ u.band }}</td>
<td><a href="/approve/{{ u.id }}" class="btn btn-primary">Mark Paid</a></td></tr>
{% endfor %}
</table><a href="/dashboard" class="btn btn-secondary">Back</a></div></body></html>
"""

# --- Run App ---
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
