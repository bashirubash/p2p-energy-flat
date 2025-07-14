from flask import Flask, render_template_string, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from web3 import Web3
import os
from dotenv import load_dotenv
import random

# Initialize app
app = Flask(__name__)
app.secret_key = 'secretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///energy.db'
db = SQLAlchemy(app)

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Load .env
load_dotenv()
INFURA_URL = os.getenv("INFURA_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
PUBLIC_KEY = os.getenv("PUBLIC_KEY")

web3 = Web3(Web3.HTTPProvider(INFURA_URL))

# Load ABI
with open("EnergyMarketplaceABI.json") as abi_file:
    contract_abi = abi_file.read()

contract = web3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=contract_abi)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    meter_number = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    kyc_verified = db.Column(db.Boolean, default=False)

class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller = db.Column(db.String(150))
    buyer = db.Column(db.String(150), nullable=True)
    energy = db.Column(db.Integer)
    price = db.Column(db.Float)
    completed = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize DB with 50 unit trades
@app.before_first_request
def setup():
    db.create_all()
    if Trade.query.count() == 0:
        for i in range(50):
            trade = Trade(seller="TestSeller", energy=random.randint(1, 10), price=round(random.uniform(0.01, 0.05), 3))
            db.session.add(trade)
        db.session.commit()

# Templates
header = """
<style>
    body { font-family: Arial; background: #f4f8fb; padding: 20px; }
    .box { background: white; padding: 20px; max-width: 500px; margin: auto; border-radius: 8px; box-shadow: 0 0 10px #ccc; }
    input, button { width: 100%; padding: 10px; margin-top: 10px; }
    h2 { text-align:center; color:#2c3e50; }
    .menu { text-align:center; margin-bottom:20px; }
    .menu a { margin: 0 10px; text-decoration:none; color:#3498db; }
    table { width:100%; border-collapse:collapse; }
    th, td { border:1px solid #ccc; padding:8px; text-align:center; }
</style>
"""

# Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        meter = request.form['meter']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm']
        if password != confirm:
            return "Passwords do not match"
        user = User(name=name, meter_number=meter, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template_string(header + """
    <div class="box">
        <h2>YEDC Energy Marketplace - Register</h2>
        <form method="post">
            <input name="name" placeholder="Name" required>
            <input name="meter" placeholder="Meter Number" required>
            <input name="email" placeholder="Email" required>
            <input name="password" type="password" placeholder="Password" required>
            <input name="confirm" type="password" placeholder="Confirm Password" required>
            <button type="submit">Register</button>
        </form>
        <div class="menu"><a href="/login">Login</a></div>
    </div>
    """)

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email'], password=request.form['password']).first()
        if user:
            login_user(user)
            return redirect(url_for('dashboard'))
        return "Invalid credentials"
    return render_template_string(header + """
    <div class="box">
        <h2>YEDC Energy Marketplace - Login</h2>
        <form method="post">
            <input name="email" placeholder="Email" required>
            <input name="password" type="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        <div class="menu"><a href="/register">Register</a></div>
    </div>
    """)

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    trades = Trade.query.all()
    return render_template_string(header + f"""
    <div class="box">
        <h2>Welcome {current_user.name} - YEDC Dashboard</h2>
        <div class="menu">
            <a href="/buyer">Buyer Section</a> | 
            <a href="/seller">Seller Section</a> | 
            <a href="/logout">Logout</a>
        </div>
        <p>Status: {"KYC Verified" if current_user.kyc_verified else "Pending KYC"}</p>
    </div>
    """)

# Buyer Section
@app.route('/buyer', methods=['GET', 'POST'])
@login_required
def buyer():
    if request.method == 'POST':
        trade_id = int(request.form['trade_id'])
        trade = Trade.query.get(trade_id)
        if not trade or trade.completed:
            return "Trade not available"
        trade.buyer = current_user.name
        trade.completed = True
        db.session.commit()
        # Simulate meter recharge
        return f"✅ {trade.energy} kWh recharged to Meter {current_user.meter_number}"
    trades = Trade.query.filter_by(completed=False).all()
    rows = "".join(f"<tr><td>{t.id}</td><td>{t.seller}</td><td>{t.energy}</td><td>{t.price} ETH</td><td><form method='post'><input type='hidden' name='trade_id' value='{t.id}'><button>Buy</button></form></td></tr>" for t in trades)
    return render_template_string(header + f"""
    <div class="box">
        <h2>Buyer Section</h2>
        <table>
            <tr><th>ID</th><th>Seller</th><th>Energy</th><th>Price</th><th>Action</th></tr>
            {rows}
        </table>
        <div class="menu"><a href="/dashboard">Back</a></div>
    </div>
    """)

# Seller Section
@app.route('/seller', methods=['GET', 'POST'])
@login_required
def seller():
    if request.method == 'POST':
        energy = int(request.form['energy'])
        price = float(request.form['price'])
        trade = Trade(seller=current_user.name, energy=energy, price=price)
        db.session.add(trade)
        db.session.commit()
        return redirect(url_for('seller'))
    my_trades = Trade.query.filter_by(seller=current_user.name).all()
    rows = "".join(f"<tr><td>{t.id}</td><td>{t.energy}</td><td>{t.price}</td><td>{'✅' if t.completed else 'Open'}</td></tr>" for t in my_trades)
    return render_template_string(header + f"""
    <div class="box">
        <h2>Seller Section</h2>
        <form method="post">
            <input name="energy" placeholder="Energy (kWh)" required>
            <input name="price" placeholder="Price (ETH)" required>
            <button type="submit">List Unit</button>
        </form>
        <table>
            <tr><th>ID</th><th>Energy</th><th>Price</th><th>Status</th></tr>
            {rows}
        </table>
        <div class="menu"><a href="/dashboard">Back</a></div>
    </div>
    """)

# Logout
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
