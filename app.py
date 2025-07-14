from flask import Flask, request, redirect, url_for, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from web3 import Web3
import json
import os
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = "your_secret_key_here"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

load_dotenv()

INFURA_URL = os.getenv("INFURA_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
PUBLIC_KEY = os.getenv("PUBLIC_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

web3 = Web3(Web3.HTTPProvider(INFURA_URL))

with open("EnergyMarketplaceABI.json") as abi_file:
    contract_abi = json.load(abi_file)

contract = web3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=contract_abi)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    meter_number = db.Column(db.String(50))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------- ROUTES --------------------

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        meter_number = request.form['meter_number']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            return "Passwords do not match."
        if User.query.filter_by(email=email).first():
            return "Email already registered."
        new_user = User(name=name, meter_number=meter_number, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template_string('''
    <html><head><title>YEDC Registration</title>
    <style>
    body {font-family: Arial; background:#f5f7fa; display:flex; justify-content:center; align-items:center; height:100vh;}
    form {background:#fff; padding:30px; border-radius:10px; box-shadow:0 0 10px rgba(0,0,0,0.1);}
    h2 {text-align:center; color:#2c3e50;}
    input {width:100%; padding:10px; margin:8px 0; border-radius:5px; border:1px solid #ccc;}
    button {width:100%; padding:10px; background:#3498db; color:#fff; border:none; border-radius:5px;}
    button:hover {background:#2980b9;}
    </style></head><body>
    <form method="post">
        <h2>YEDC P2P Energy - Register</h2>
        <input name="name" placeholder="Full Name" required>
        <input name="meter_number" placeholder="Meter Number" required>
        <input name="email" placeholder="Email" required>
        <input name="password" type="password" placeholder="Password" required>
        <input name="confirm_password" type="password" placeholder="Confirm Password" required>
        <button type="submit">Register</button>
        <p style="text-align:center;margin-top:10px;">Already have account? <a href="/login">Login</a></p>
    </form>
    </body></html>
    ''')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials."

    return render_template_string('''
    <html><head><title>YEDC Login</title>
    <style>
    body {font-family: Arial; background:#f5f7fa; display:flex; justify-content:center; align-items:center; height:100vh;}
    form {background:#fff; padding:30px; border-radius:10px; box-shadow:0 0 10px rgba(0,0,0,0.1);}
    h2 {text-align:center; color:#2c3e50;}
    input {width:100%; padding:10px; margin:8px 0; border-radius:5px; border:1px solid #ccc;}
    button {width:100%; padding:10px; background:#3498db; color:#fff; border:none; border-radius:5px;}
    button:hover {background:#2980b9;}
    </style></head><body>
    <form method="post">
        <h2>YEDC P2P Energy - Login</h2>
        <input name="email" placeholder="Email" required>
        <input name="password" type="password" placeholder="Password" required>
        <button type="submit">Login</button>
        <p style="text-align:center;margin-top:10px;">No account? <a href="/register">Register</a></p>
    </form>
    </body></html>
    ''')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    trade_data = []
    for i in range(10):
        try:
            t = contract.functions.getTrade(i).call()
            trade_data.append({
                "id": i,
                "seller": t[0],
                "buyer": t[1],
                "energy": t[2],
                "price": web3.from_wei(t[3], 'ether'),
                "completed": t[4]
            })
        except:
            break

    return render_template_string('''
    <html><head><title>YEDC Dashboard</title>
    <style>
    body {font-family: Arial; background:#f5f7fa; padding:20px;}
    h1 {color:#2c3e50;}
    table {width:100%; border-collapse:collapse; margin-top:20px;}
    th, td {border:1px solid #ccc; padding:10px; text-align:center;}
    th {background:#34495e; color:#fff;}
    a {text-decoration:none; color:#3498db;}
    button {padding:10px; background:#3498db; color:#fff; border:none; border-radius:5px;}
    </style></head><body>
    <h1>Welcome to YEDC P2P Energy Marketplace</h1>
    <p>Logged in as: {{current_user.name}} | Meter: {{current_user.meter_number}}</p>
    <p><a href="/logout">Logout</a></p>

    <h2>Seller Section - List Energy</h2>
    <form method="POST" action="/offer">
        <input type="number" name="energy" placeholder="Energy (kWh)" required>
        <input type="number" step="0.01" name="price" placeholder="Price (ETH)" required>
        <button type="submit">List Energy</button>
    </form>

    <h2>Buyer Section - Available Listings</h2>
    <table>
        <tr><th>ID</th><th>Seller</th><th>Buyer</th><th>Energy</th><th>Price (ETH)</th><th>Status</th><th>Action</th></tr>
        {% for t in trades %}
        <tr>
            <td>{{t.id}}</td>
            <td>{{t.seller}}</td>
            <td>{{t.buyer}}</td>
            <td>{{t.energy}}</td>
            <td>{{t.price}}</td>
            <td>{{'Completed' if t.completed else 'Open'}}</td>
            <td>{% if not t.completed %}<a href="/buy/{{t.id}}/{{t.price}}">Buy</a>{% else %}-{% endif %}</td>
        </tr>
        {% endfor %}
    </table>
    </body></html>
    ''', trades=trade_data, current_user=current_user)

# Seller Offer
@app.route('/offer', methods=['POST'])
@login_required
def offer():
    energy = int(request.form['energy'])
    price_eth = float(request.form['price'])
    price_wei = web3.to_wei(price_eth, 'ether')

    nonce = web3.eth.get_transaction_count(PUBLIC_KEY)
    tx = contract.functions.offerEnergy(energy, price_wei).build_transaction({
        'from': PUBLIC_KEY,
        'nonce': nonce,
        'gas': 300000,
        'gasPrice': web3.to_wei('15', 'gwei')
    })
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    return redirect(url_for('dashboard'))

# Buyer Buy
@app.route('/buy/<int:trade_id>/<float:price>')
@login_required
def buy(trade_id, price):
    trade = contract.functions.getTrade(trade_id).call()
    if trade[4]:
        return "Trade already completed."

    amount_wei = web3.to_wei(price, 'ether')
    nonce = web3.eth.get_transaction_count(PUBLIC_KEY)
    tx = contract.functions.buyEnergy(trade_id).build_transaction({
        'from': PUBLIC_KEY,
        'value': amount_wei,
        'nonce': nonce,
        'gas': 300000,
        'gasPrice': web3.to_wei('15', 'gwei')
    })
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    web3.eth.send_raw_transaction(signed_tx.raw_transaction)

    return redirect(url_for('dashboard'))

# Main
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)
