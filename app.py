from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from web3 import Web3
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'yedc_marketplace_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///marketplace.db'
db = SQLAlchemy(app)

INFURA_URL = os.getenv('INFURA_URL')
web3 = Web3(Web3.HTTPProvider(INFURA_URL))

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    meter_number = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(10))  # admin or buyer

class UnitListing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller = db.Column(db.String(100))  # Always 'Guru' here
    units = db.Column(db.Integer)
    price_eth = db.Column(db.Float)
    band = db.Column(db.String(10))
    buyer_email = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default="Available")  # Available or Sold

# --- Database Initialization ---
@app.before_request
def create_tables():
    db.create_all()
    # Create admin if not exists
    admin = User.query.filter_by(email='guru@yedc.com').first()
    if not admin:
        admin = User(name="Guru", meter_number="0000", email="guru@yedc.com", password="Guru123", role="admin")
        db.session.add(admin)
        # Preload 50 Band D units
        for i in range(50):
            unit = UnitListing(seller="Guru", units=1, price_eth=0.0005, band='D')
            db.session.add(unit)
        db.session.commit()

# --- Routes ---
@app.route('/')
def index():
    return redirect(url_for('login'))

# --- Register Buyer ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        meter = request.form['meter']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm']

        if password != confirm:
            flash("Passwords do not match!")
            return redirect(url_for('register'))

        user = User.query.filter_by(email=email).first()
        if user:
            flash("Email already registered!")
            return redirect(url_for('register'))

        new_user = User(name=name, meter_number=meter, email=email, password=password, role="buyer")
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful. Please login.")
        return redirect(url_for('login'))

    return render_template_string(register_html)

# --- Login ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session['user'] = user.email
            session['role'] = user.role
            flash("Welcome back!")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials!")
            return redirect(url_for('login'))

    return render_template_string(login_html)

# --- Dashboard ---
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    role = session['role']
    email = session['user']

    if role == 'admin':
        units = UnitListing.query.all()
    else:
        units = UnitListing.query.filter_by(status="Available").all()

    return render_template_string(dashboard_html, units=units, role=role)

# --- Seller adds units ---
@app.route('/add_unit', methods=['POST'])
def add_unit():
    if 'user' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    units = int(request.form['units'])
    price = float(request.form['price'])
    band = request.form['band']

    new_listing = UnitListing(seller="Guru", units=units, price_eth=price, band=band)
    db.session.add(new_listing)
    db.session.commit()
    flash("Units listed successfully.")
    return redirect(url_for('dashboard'))

# --- Buyer buys unit ---
@app.route('/buy/<int:unit_id>')
def buy(unit_id):
    if 'user' not in session or session['role'] != 'buyer':
        return redirect(url_for('login'))

    buyer = User.query.filter_by(email=session['user']).first()
    unit = UnitListing.query.get(unit_id)

    if unit.status == "Sold":
        flash("Unit already sold!")
        return redirect(url_for('dashboard'))

    # --- Simulated ETH payment ---
    seller_wallet = "0xSELLERWALLETHERE"  # Replace with real seller wallet
    eth_amount = unit.price_eth

    # In production, use Web3.js frontend to call MetaMask!
    # This is backend simulation only

    unit.buyer_email = buyer.email
    unit.status = "Sold"
    db.session.commit()

    flash(f"Paid {eth_amount} ETH to seller. {unit.units} kWh sent to Meter {buyer.meter_number} (Band {unit.band}).")
    return redirect(url_for('dashboard'))

# --- Logout ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- HTML Templates ---
register_html = '''
<!doctype html>
<title>YEDC Register</title>
<h2>YEDC Energy Marketplace - Register</h2>
<form method=post>
    <input name=name placeholder="Name" required><br>
    <input name=meter placeholder="Meter Number" required><br>
    <input name=email type=email placeholder="Email" required><br>
    <input name=password type=password placeholder="Password" required><br>
    <input name=confirm type=password placeholder="Confirm Password" required><br>
    <button type=submit>Register</button>
</form>
<a href="/login">Already registered? Login</a>
'''

login_html = '''
<!doctype html>
<title>YEDC Login</title>
<h2>YEDC Energy Marketplace - Login</h2>
<form method=post>
    <input name=email type=email placeholder="Email" required><br>
    <input name=password type=password placeholder="Password" required><br>
    <button type=submit>Login</button>
</form>
<a href="/register">Register as Buyer</a>
'''

dashboard_html = '''
<!doctype html>
<title>YEDC Dashboard</title>
<h2>YEDC Energy Dashboard</h2>
{% with messages = get_flashed_messages() %}
  {% if messages %}
    <ul>
    {% for message in messages %}
      <li style="color:green">{{ message }}</li>
    {% endfor %}
    </ul>
  {% endif %}
{% endwith %}

{% if role == 'admin' %}
<h3>Seller (Admin) Section</h3>
<form method=post action="/add_unit">
    <input name=units type=number placeholder="Units (kWh)" required><br>
    <input name=price type=number step=0.0001 placeholder="Price ETH" required><br>
    <select name=band required>
        <option value="A">Band A</option>
        <option value="B">Band B</option>
        <option value="C">Band C</option>
        <option value="D">Band D</option>
    </select><br>
    <button type=submit>Add Unit</button>
</form>
{% endif %}

<h3>Available Listings</h3>
<table border=1>
<tr><th>ID</th><th>Seller</th><th>Units</th><th>Price (ETH)</th><th>Band</th><th>Status</th><th>Action</th></tr>
{% for u in units %}
<tr>
<td>{{u.id}}</td>
<td>{{u.seller}}</td>
<td>{{u.units}}</td>
<td>{{u.price_eth}}</td>
<td>{{u.band}}</td>
<td>{{u.status}}</td>
<td>
{% if role == 'buyer' and u.status == 'Available' %}
<a href="/buy/{{u.id}}">Buy</a>
{% else %}
-
{% endif %}
</td>
</tr>
{% endfor %}
</table>

<br><a href="/logout">Logout</a>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
