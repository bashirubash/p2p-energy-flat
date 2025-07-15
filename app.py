from flask import Flask, request, redirect, session, flash, render_template_string
from flask_sqlalchemy import SQLAlchemy
from web3 import Web3
from solcx import compile_standard, install_solc
import json
import os

app = Flask(__name__)
app.secret_key = 'yedc_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///market.db'
db = SQLAlchemy(app)

# Web3 Setup (Ganache Localhost)
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
chain_id = 1337
my_address = w3.eth.accounts[0]
private_key = "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113b37e6d30d5d8c3fb923b5bda"

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    meter_number = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(10))

class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    units = db.Column(db.Integer)
    price_eth = db.Column(db.Float)
    band = db.Column(db.String(10))
    status = db.Column(db.String(20), default="Available")

# Deploy or Load Smart Contract
def deploy_contract():
    if os.path.exists("contract_address.txt"):
        with open("contract_address.txt", "r") as f:
            return f.read().strip()

    install_solc('0.8.0')
    with open("YEDCPayment.sol", "r") as file:
        contract_source_code = file.read()

    compiled_sol = compile_standard({
        "language": "Solidity",
        "sources": {"YEDCPayment.sol": {"content": contract_source_code}},
        "settings": {"outputSelection": {"*": {"*": ["abi", "evm.bytecode"]}}}
    }, solc_version="0.8.0")

    abi = compiled_sol["contracts"]["YEDCPayment.sol"]["YEDCPayment"]["abi"]
    bytecode = compiled_sol["contracts"]["YEDCPayment.sol"]["YEDCPayment"]["evm"]["bytecode"]["object"]

    with open("YEDCPayment_abi.json", "w") as f:
        json.dump(abi, f)

    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.get_transaction_count(my_address)
    tx = contract.constructor().build_transaction({
        'chainId': chain_id,
        'from': my_address,
        'nonce': nonce,
        'gas': 500000,
        'gasPrice': w3.to_wei('5', 'gwei')
    })
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    with open("contract_address.txt", "w") as f:
        f.write(receipt.contractAddress)

    return receipt.contractAddress

contract_address = deploy_contract()

# Load Contract
with open("YEDCPayment_abi.json", "r") as f:
    contract_abi = json.load(f)

contract = w3.eth.contract(address=contract_address, abi=contract_abi)

# Initialize DB
with app.app_context():
    db.create_all()
    if not User.query.filter_by(email="gurus@gmail.com").first():
        admin = User(name="Guru", meter_number="0000", email="gurus@gmail.com", password="Guru123", role="admin")
        db.session.add(admin)
        for i in range(50):
            db.session.add(Unit(units=1, price_eth=0.0005, band="D"))
        db.session.commit()

# Routes
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

@app.route('/buy/<int:unit_id>')
def buy(unit_id):
    if session.get('role') != 'buyer':
        return redirect('/dashboard')
    unit = Unit.query.get(unit_id)
    if unit.status == 'Sold':
        flash('Already sold')
    else:
        unit.status = 'Sold'
        db.session.commit()
        flash('Transaction completed. Please approve the transaction in your wallet.')

    return redirect('/dashboard')

# HTML Templates
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

dashboard_html = """
<!DOCTYPE html><html><head><title>Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/web3@latest/dist/web3.min.js"></script></head>
<body class="p-4"><div class="container">
<h3>YEDC Dashboard - {{ role|capitalize }}</h3><p>Meter: {{ meter }}</p>
{% with messages = get_flashed_messages() %}
{% if messages %}
<div class="alert alert-success">{{ messages[0] }}</div>
{% endif %}{% endwith %}

{% if role == 'admin' %}
<form method="POST" action="/add_unit" class="my-3 row">
<div class="col"><input name="units" class="form-control" placeholder="Units" required></div>
<div class="col"><input name="price" class="form-control" placeholder="Price ETH" required></div>
<div class="col">
<select name="band" class="form-control"><option>A</option><option>B</option><option>C</option><option>D</option></select>
</div><div class="col"><button class="btn btn-primary">Add Unit</button></div></form>
{% endif %}

<table class="table table-bordered mt-4">
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

<a href="/logout" class="btn btn-danger mt-3">Logout</a>
</div>

<script>
async function buyUnit(id, price) {
    if (typeof window.ethereum !== 'undefined') {
        const web3 = new Web3(window.ethereum);
        await window.ethereum.request({ method: 'eth_requestAccounts' });
        const accounts = await web3.eth.getAccounts();
        const contract = new web3.eth.Contract({{ contract_abi|safe }}, "{{ contract_address }}");
        await contract.methods.buyEnergy().send({
            from: accounts[0],
            value: web3.utils.toWei(price, 'ether')
        });
        window.location.href = "/buy/" + id;
    } else {
        alert("MetaMask not detected");
    }
}
</script>
</body></html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
