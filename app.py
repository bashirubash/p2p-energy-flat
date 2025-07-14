from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from web3 import Web3
import os
import random
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///energy_market.db'
db = SQLAlchemy(app)

# Web3 Setup
INFURA_URL = os.getenv("INFURA_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
PUBLIC_KEY = os.getenv("PUBLIC_KEY")

web3 = Web3(Web3.HTTPProvider(INFURA_URL))

with open("EnergyMarketplaceABI.json", "r") as abi_file:
    contract_abi = abi_file.read()
contract = web3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=contract_abi)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    meter_number = db.Column(db.String(50))
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(100))

class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller = db.Column(db.String(150))
    energy = db.Column(db.Integer)
    price = db.Column(db.Float)
    completed = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Templates (inline with styling)
register_template = """
<!DOCTYPE html>
<html>
<head><title>YEDC Energy P2P - Register</title>
<style>
body {font-family: Arial; background: #f5f7fa; padding: 50px;}
form {background: white; padding: 30px; max-width: 400px; margin: auto; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1);}
input {padding: 10px; margin: 5px 0; width: 100%; border-radius: 5px; border: 1px solid #ccc;}
button {padding: 10px; width: 100%; background: #3498db; color: white; border: none; border-radius: 5px;}
h2 {text-align: center;}
</style>
</head><body>
<h2>YEDC P2P Energy - Register</h2>
<form method="POST">
    <input name="name" placeholder="Full Name" required>
    <input name="meter" placeholder="Meter Number" required>
    <input name="email" type="email" placeholder="Email" required>
    <input name="password" type="password" placeholder="Password" required>
    <input name="confirm" type="password" placeholder="Confirm Password" required>
    <button type="submit">Register</button>
    <p style="text-align:center;margin-top:10px;">Already have an account? <a href="/login">Login</a></p>
</form>
</body></html>
"""

login_template = """
<!DOCTYPE html>
<html>
<head><title>YEDC Energy P2P - Login</title>
<style>
body {font-family: Arial; background: #f5f7fa; padding: 50px;}
form {background: white; padding: 30px; max-width: 400px; margin: auto; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1);}
input {padding: 10px; margin: 5px 0; width: 100%; border-radius: 5px; border: 1px solid #ccc;}
button {padding: 10px; width: 100%; background: #27ae60; color: white; border: none; border-radius: 5px;}
h2 {text-align: center;}
</style>
</head><body>
<h2>YEDC P2P Energy - Login</h2>
<form method="POST">
    <input name="email" type="email" placeholder="Email" required>
    <input name="password" type="password" placeholder="Password" required>
    <button type="submit">Login</button>
    <p style="text-align:center;margin-top:10px;">Don't have an account? <a href="/register">Register</a></p>
</form>
</body></html>
"""

dashboard_template = """
<!DOCTYPE html>
<html>
<head><title>YEDC Energy P2P - Dashboard</title>
<style>
body {font-family: Arial; background: #f5f7fa; padding: 30px;}
h2 {text-align:center;}
table {width:100%; border-collapse: collapse; margin: 20px 0;}
th, td {border:1px solid #ccc; padding:10px; text-align:center;}
form {margin: 20px 0;}
input {padding:5px;}
button {padding:5px 10px;}
.logout {position:absolute; top:10px; right:10px;}
</style>
</head><body>
<a class="logout" href="/logout">Logout</a>
<h2>Welcome {{ user.name }} - YEDC P2P Energy Dashboard</h2>
<h3>Buyer Section</h3>
<table><tr><th>ID</th><th>Seller</th><th>Energy (kWh)</th><th>Price (ETH)</th><th>Action</th></tr>
{% for trade in trades %}
<tr>
<td>{{ trade.id }}</td>
<td>{{ trade.seller }}</td>
<td>{{ trade.energy }}</td>
<td>{{ trade.price }}</td>
<td>{% if not trade.completed %}<a href="/buy/{{ trade.id }}">Buy</a>{% else %}Completed{% endif %}</td>
</tr>
{% endfor %}
</table>

<h3>Seller Section</h3>
<form method="POST" action="/sell">
<input name="energy" type="number" placeholder="Energy (kWh)" required>
<input name="price" type="number" step="0.01" placeholder="Price (ETH)" required>
<button type="submit">List Energy</button>
</form>

</body></html>
"""

# Routes

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form['name']
        meter = request.form['meter']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm']
        if password != confirm:
            flash("Passwords do not match")
            return render_template_string(register_template)
        if User.query.filter_by(email=email).first():
            flash("Email already exists")
            return render_template_string(register_template)
        user = User(name=name, meter_number=meter, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful! Please login.")
        return redirect(url_for("login"))
    return render_template_string(register_template)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for("dashboard"))
        flash("Invalid credentials")
    return render_template_string(login_template)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    trades = Trade.query.all()
    return render_template_string(dashboard_template, trades=trades, user=current_user)

@app.route("/sell", methods=["POST"])
@login_required
def sell():
    energy = int(request.form['energy'])
    price = float(request.form['price'])
    trade = Trade(seller=current_user.name, energy=energy, price=price)
    db.session.add(trade)
    db.session.commit()
    flash("Energy listed successfully")
    return redirect(url_for("dashboard"))

@app.route("/buy/<int:trade_id>")
@login_required
def buy(trade_id):
    trade = Trade.query.get(trade_id)
    if trade.completed:
        flash("Trade already completed")
        return redirect(url_for("dashboard"))
    # In real use, here you’d call the smart contract to transfer ETH & tokens.
    trade.completed = True
    db.session.commit()
    flash(f"Successfully bought {trade.energy} kWh for {trade.price} ETH")
    return redirect(url_for("dashboard"))

# Initialize database and populate sample data
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if Trade.query.count() == 0:
            for i in range(50):
                t = Trade(seller="TestSeller", energy=random.randint(1, 10), price=round(random.uniform(0.01, 0.05), 3))
                db.session.add(t)
            db.session.commit()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
