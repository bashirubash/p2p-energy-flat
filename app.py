from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from web3 import Web3
import os

app = Flask(__name__)
app.secret_key = 'yedc_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yedc_marketplace.db'
db = SQLAlchemy(app)

# Web3 Connection (Sepolia, Render-compatible via Infura)
w3 = Web3(Web3.HTTPProvider('https://sepolia.infura.io/v3/YOUR_INFURA_PROJECT_ID'))  # Replace with your Infura key

# Contract Setup
contract_address = Web3.to_checksum_address('0xYourContractAddressHere')  # Replace with your deployed contract address

abi = [  # Your Provided ABI
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
		"name": "owner",
		"outputs": [{"internalType": "address", "name": "", "type": "address"}],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "withdraw",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	}
]

contract = w3.eth.contract(address=contract_address, abi=abi)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meter_number = db.Column(db.String(50))
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(50))
    role = db.Column(db.String(10))  # admin or buyer

with app.app_context():
    db.create_all()
    if not User.query.filter_by(email="gurus@gmail.com").first():
        db.session.add(User(meter_number="0000", email="gurus@gmail.com", password="Guru123", role="admin"))
        db.session.commit()

@app.route('/')
def home():
    return redirect('/login')

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
        flash('Invalid login')
    return render_template_string(login_html)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    return render_template_string(dashboard_html, role=session['role'], meter=session['meter'], contract_address=contract_address, abi=abi)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# Flask API for payment status (Optional for frontend to check)
@app.route('/status')
def status():
    balance = w3.eth.get_balance(contract_address)
    return jsonify({'contract_balance_eth': w3.from_wei(balance, 'ether')})

# ---- HTML ----
login_html = """
<!DOCTYPE html>
<html><head><title>YEDC Login</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-light p-5">
<div class="container"><h2 class="text-center">YEDC Login</h2>
<form method="POST" class="mt-4">
<input name="email" class="form-control mb-3" placeholder="Email" required>
<input name="password" type="password" class="form-control mb-3" placeholder="Password" required>
<button type="submit" class="btn btn-success w-100">Login</button>
</form></div></body></html>
"""

dashboard_html = """
<!DOCTYPE html>
<html>
<head>
<title>YEDC Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/web3@latest/dist/web3.min.js"></script>
</head>
<body class="p-4">
<div class="container">
<h3>Dashboard - {{ role|capitalize }}</h3>
<p>Meter: {{ meter }}</p>
{% if role == 'buyer' %}
<button onclick="buyEnergy()" class="btn btn-primary mt-3">Buy Energy (0.001 ETH)</button>
{% else %}
<p>Admin cannot buy energy. Use contract directly for withdrawals.</p>
{% endif %}
<a href="/logout" class="btn btn-danger mt-3 d-block">Logout</a>
</div>

<script>
const contractAddress = "{{ contract_address }}";
const abi = {{ abi|tojson }};

async function buyEnergy() {
    if (typeof window.ethereum !== 'undefined') {
        const web3 = new Web3(window.ethereum);
        await ethereum.request({ method: 'eth_requestAccounts' });
        const accounts = await web3.eth.getAccounts();
        const contract = new web3.eth.Contract(abi, contractAddress);
        
        contract.methods.buyEnergy().send({
            from: accounts[0],
            value: web3.utils.toWei("0.001", "ether")
        })
        .on('transactionHash', function(hash){
            alert("Transaction sent! Hash: " + hash);
        })
        .on('receipt', function(receipt){
            alert("Transaction confirmed! Energy bought.");
        })
        .on('error', function(error, receipt) {
            console.error(error);
            alert("Transaction failed or rejected.");
        });
    } else {
        alert("MetaMask not detected.");
    }
}
</script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
