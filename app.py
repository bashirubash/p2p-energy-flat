from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from web3 import Web3
import os

app = Flask(__name__)
app.secret_key = 'secretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///marketplace.db'
db = SQLAlchemy(app)

# Ethereum setup (replace with your real values)
ETH_PROVIDER = "https://mainnet.infura.io/v3/YOUR_INFURA_KEY"
ADMIN_WALLET = "0xYourAdminWalletAddress"

web3 = Web3(Web3.HTTPProvider(ETH_PROVIDER))

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(200))
    meter_number = db.Column(db.String(50))
    role = db.Column(db.String(50), default='buyer')  # 'buyer' or 'admin'

class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    units = db.Column(db.Integer)
    price_eth = db.Column(db.Float)
    band = db.Column(db.String(20))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    buyer_email = db.Column(db.String(150))
    meter_number = db.Column(db.String(50))
    units = db.Column(db.Integer)
    amount_eth = db.Column(db.Float)
    band = db.Column(db.String(20))
    status = db.Column(db.String(50), default="pending")  # pending, paid

# Auto Create Admin and Sample Data
@app.before_first_request
def create_tables():
    db.create_all()
    admin = User.query.filter_by(email="gurus@gmail.com").first()
    if not admin:
        admin_user = User(
            name="Guru Admin",
            email="gurus@gmail.com",
            password=generate_password_hash("Guru123"),
            meter_number="admin",
            role="admin"
        )
        db.session.add(admin_user)
        # Sample Listings
        for i in range(1, 51):
            sample_unit = Unit(units=10+i, price_eth=0.001*i, band="Band A")
            db.session.add(sample_unit)
        db.session.commit()

# Routes
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        meter_number = request.form['meter']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm']
        if password != confirm:
            flash("Passwords do not match")
            return redirect(url_for('register'))
        hashed_pw = generate_password_hash(password)
        new_user = User(name=name, email=email, password=hashed_pw, meter_number=meter_number)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful. Please login.")
        return redirect(url_for('login'))
    return render_template_string(register_html)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user'] = user.email
            session['role'] = user.role
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('buyer_dashboard'))
        else:
            flash("Invalid credentials")
            return redirect(url_for('login'))
    return render_template_string(login_html)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Buyer Dashboard
@app.route('/buyer')
def buyer_dashboard():
    if 'user' not in session or session['role'] != 'buyer':
        return redirect(url_for('login'))
    units = Unit.query.all()
    return render_template_string(buyer_html, units=units)

@app.route('/buy/<int:unit_id>')
def buy_unit(unit_id):
    if 'user' not in session or session['role'] != 'buyer':
        return redirect(url_for('login'))
    unit = Unit.query.get(unit_id)
    user = User.query.filter_by(email=session['user']).first()
    new_order = Order(
        buyer_email=user.email,
        meter_number=user.meter_number,
        units=unit.units,
        amount_eth=unit.price_eth,
        band=unit.band,
        status="pending"
    )
    db.session.add(new_order)
    db.session.commit()
    flash(f"Order placed for {unit.units} units. Awaiting admin approval.")
    return redirect(url_for('buyer_dashboard'))

# Admin Dashboard
@app.route('/admin')
def admin_dashboard():
    if 'user' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    return render_template_string(admin_html)

@app.route('/admin/add', methods=['GET', 'POST'])
def add_listing():
    if request.method == 'POST':
        units = request.form['units']
        price = request.form['price']
        band = request.form['band']
        new_unit = Unit(units=units, price_eth=price, band=band)
        db.session.add(new_unit)
        db.session.commit()
        flash("Listing added successfully.")
    return render_template_string(add_listing_html)

@app.route('/admin/pending')
def pending_orders():
    orders = Order.query.filter_by(status="pending").all()
    return render_template_string(pending_html, orders=orders)

@app.route('/admin/complete')
def complete_orders():
    orders = Order.query.filter_by(status="paid").all()
    return render_template_string(complete_html, orders=orders)

@app.route('/admin/mark_paid/<int:order_id>')
def mark_paid(order_id):
    order = Order.query.get(order_id)
    order.status = "paid"
    db.session.commit()
    flash(f"Meter {order.meter_number} recharged with {order.units} units (Band: {order.band})")
    return redirect(url_for('pending_orders'))

# Templates (simplified inline HTML with basic styling)
register_html = """
<!DOCTYPE html><html><head><style>body{font-family:Arial;background:#f5f5f5;padding:50px}form{background:#fff;padding:20px;border-radius:10px;max-width:300px;margin:auto;box-shadow:0 0 10px #ccc}input{margin:5px 0;padding:10px;width:100%}</style></head><body>
<h2 style='text-align:center;'>YEDC Energy Marketplace</h2><form method="POST">
<input name="name" placeholder="Name" required>
<input name="meter" placeholder="Meter Number" required>
<input name="email" placeholder="Email" required>
<input name="password" type="password" placeholder="Password" required>
<input name="confirm" type="password" placeholder="Confirm Password" required>
<button type="submit">Register</button></form></body></html>
"""

login_html = """
<!DOCTYPE html><html><head><style>body{font-family:Arial;background:#f5f5f5;padding:50px}form{background:#fff;padding:20px;border-radius:10px;max-width:300px;margin:auto;box-shadow:0 0 10px #ccc}input{margin:5px 0;padding:10px;width:100%}</style></head><body>
<h2 style='text-align:center;'>YEDC Login</h2><form method="POST">
<input name="email" placeholder="Email" required>
<input name="password" type="password" placeholder="Password" required>
<button type="submit">Login</button></form></body></html>
"""

buyer_html = """
<!DOCTYPE html><html><head><style>body{font-family:Arial;padding:50px}table{width:100%;border-collapse:collapse}th,td{padding:10px;border:1px solid #ccc}</style></head><body>
<h2>Available Energy Units</h2><table><tr><th>Units</th><th>Price (ETH)</th><th>Band</th><th>Action</th></tr>
{% for unit in units %}<tr><td>{{unit.units}}</td><td>{{unit.price_eth}}</td><td>{{unit.band}}</td><td><a href="/buy/{{unit.id}}">Buy</a></td></tr>{% endfor %}
</table><br><a href='/logout'>Logout</a></body></html>
"""

admin_html = """
<!DOCTYPE html><html><head><style>body{font-family:Arial}nav{width:200px;float:left;background:#333;height:100vh;padding:20px;color:white}a{color:white;display:block;margin:10px 0}main{margin-left:220px;padding:20px}</style></head><body>
<nav><h3>Admin Panel</h3><a href='/admin/add'>Add Listing</a><a href='/admin/pending'>Pending Transactions</a><a href='/admin/complete'>Complete Transactions</a><a href='/logout'>Logout</a></nav><main><h2>Welcome Admin</h2></main></body></html>
"""

add_listing_html = """
<!DOCTYPE html><html><body><h2>Add Unit Listing</h2><form method="POST">
<input name="units" placeholder="Units" required>
<input name="price" placeholder="Price ETH" required>
<input name="band" placeholder="Band" required>
<button type="submit">Add</button></form><br><a href='/admin'>Back</a></body></html>
"""

pending_html = """
<!DOCTYPE html><html><body><h2>Pending Transactions</h2><table border=1><tr><th>Buyer</th><th>Meter</th><th>Units</th><th>ETH</th><th>Band</th><th>Action</th></tr>
{% for o in orders %}<tr><td>{{o.buyer_email}}</td><td>{{o.meter_number}}</td><td>{{o.units}}</td><td>{{o.amount_eth}}</td><td>{{o.band}}</td><td><a href="/admin/mark_paid/{{o.id}}">Mark as Paid</a></td></tr>{% endfor %}
</table><br><a href='/admin'>Back</a></body></html>
"""

complete_html = """
<!DOCTYPE html><html><body><h2>Complete Transactions</h2><table border=1><tr><th>Buyer</th><th>Meter</th><th>Units</th><th>ETH</th><th>Band</th></tr>
{% for o in orders %}<tr><td>{{o.buyer_email}}</td><td>{{o.meter_number}}</td><td>{{o.units}}</td><td>{{o.amount_eth}}</td><td>{{o.band}}</td></tr>{% endfor %}
</table><br><a href='/admin'>Back</a></body></html>
"""

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
