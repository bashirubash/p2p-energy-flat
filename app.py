from flask import Flask, render_template_string, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from web3 import Web3
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///marketplace.db'
db = SQLAlchemy(app)

# Ethereum config (test simulation)
w3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/your_infura_project_id"))
ADMIN_WALLET = "0x9311DeE48D671Db61947a00B3f9Eae6408Ec4D7b"  # For simulation

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    meter_number = db.Column(db.String(50))
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(50))
    role = db.Column(db.String(10))  # 'buyer' or 'admin'

class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float)
    meter_number = db.Column(db.String(50))
    band = db.Column(db.String(50))
    status = db.Column(db.String(20))  # 'pending', 'paid'

# Initialize DB with admin
@app.before_request
def setup():
    db.create_all()
    admin = User.query.filter_by(email="gurus@gmail.com").first()
    if not admin:
        admin = User(name="Guru", meter_number="0000", email="gurus@gmail.com", password="Guru123", role="admin")
        db.session.add(admin)
        db.session.commit()

# Simple CSS style embedded in HTML
style = """
<style>
body {font-family: Arial; background: linear-gradient(to right, #00c6ff, #0072ff); color: white; text-align:center;}
input {padding: 10px; margin:5px; width: 300px;}
button {padding: 10px 20px; background: #222; color:white; border:none;}
.sidebar {position: fixed; left:0; top:0; width:200px; height:100%; background:#111; padding-top:20px;}
.sidebar a {display:block; padding:10px; color:white; text-decoration:none;}
.sidebar a:hover {background:#444;}
.content {margin-left:220px; padding:20px;}
</style>
"""

# Routes

@app.route('/')
def home():
    return redirect('/login')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        meter = request.form['meter']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm']
        if password != confirm:
            return "Passwords do not match!"
        user = User(name=name, meter_number=meter, email=email, password=password, role="buyer")
        db.session.add(user)
        db.session.commit()
        return redirect('/login')
    return render_template_string(style + """
    <h2>P2P Energy Market Registration</h2>
    <form method="post">
    <input name="name" placeholder="Full Name"><br>
    <input name="meter" placeholder="Meter Number"><br>
    <input name="email" placeholder="Email"><br>
    <input type="password" name="password" placeholder="Password"><br>
    <input type="password" name="confirm" placeholder="Confirm Password"><br>
    <button type="submit">Register</button>
    </form>
    """)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session['user'] = user.email
            session['role'] = user.role
            return redirect('/dashboard')
        return "Invalid credentials!"
    return render_template_string(style + """
    <h2>P2P Energy Market Login</h2>
    <form method="post">
    <input name="email" placeholder="Email"><br>
    <input type="password" name="password" placeholder="Password"><br>
    <button type="submit">Login</button>
    </form>
    """)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    if session['role'] == 'admin':
        return redirect('/admin')
    units = Unit.query.filter_by(status='paid').all()
    pending = Unit.query.filter_by(status='pending').all()
    return render_template_string(style + """
    <h2>Welcome {{name}} | Meter: {{meter}}</h2>
    <h3>Available Units</h3>
    {% for u in units %}
        <form method="post" action="/buy/{{u.id}}">
        Band: {{u.band}} | Amount: {{u.amount}}<br>
        <button type="submit">Buy & Pay with Metamask</button><br><br>
        </form>
    {% endfor %}
    """, name=User.query.filter_by(email=session['user']).first().name,
       meter=User.query.filter_by(email=session['user']).first().meter_number,
       units=units)

@app.route('/buy/<int:unit_id>', methods=['POST'])
def buy(unit_id):
    if 'user' not in session:
        return redirect('/login')
    unit = Unit.query.get(unit_id)
    unit.status = 'pending'
    unit.meter_number = User.query.filter_by(email=session['user']).first().meter_number
    db.session.commit()
    return render_template_string(style + f"""
    <h2>Payment Initiated</h2>
    Please send ETH equivalent to {unit.amount} to <b>{ADMIN_WALLET}</b> using your Metamask.<br><br>
    <i>After admin verifies, units will be added to your meter {unit.meter_number}.</i><br><br>
    <a href="/dashboard">Back to Dashboard</a>
    """)

# Admin Section

@app.route('/admin')
def admin():
    if 'user' not in session or session['role'] != 'admin':
        return redirect('/login')
    return render_template_string(style + """
    <div class="sidebar">
    <a href="/add_unit">Add Listing</a>
    <a href="/pending">Pending Transactions</a>
    <a href="/complete">Completed Transactions</a>
    <a href="/logout">Logout</a>
    </div>
    <div class="content">
    <h2>Admin Dashboard</h2>
    <p>Select an action from the side menu.</p>
    </div>
    """)

@app.route('/add_unit', methods=['GET','POST'])
def add_unit():
    if 'user' not in session or session['role'] != 'admin':
        return redirect('/login')
    if request.method == 'POST':
        amount = request.form['amount']
        band = request.form['band']
        u = Unit(amount=amount, band=band, status='paid')
        db.session.add(u)
        db.session.commit()
        return redirect('/admin')
    return render_template_string(style + """
    <div class="sidebar">
    <a href="/add_unit">Add Listing</a>
    <a href="/pending">Pending Transactions</a>
    <a href="/complete">Completed Transactions</a>
    <a href="/logout">Logout</a>
    </div>
    <div class="content">
    <h2>Add New Unit</h2>
    <form method="post">
    <input name="amount" placeholder="Unit Amount"><br>
    <input name="band" placeholder="Band"><br>
    <button type="submit">Add Unit</button>
    </form>
    </div>
    """)

@app.route('/pending')
def pending():
    if 'user' not in session or session['role'] != 'admin':
        return redirect('/login')
    pendings = Unit.query.filter_by(status='pending').all()
    return render_template_string(style + """
    <div class="sidebar">
    <a href="/add_unit">Add Listing</a>
    <a href="/pending">Pending Transactions</a>
    <a href="/complete">Completed Transactions</a>
    <a href="/logout">Logout</a>
    </div>
    <div class="content">
    <h2>Pending Transactions</h2>
    {% for p in pendings %}
        Meter: {{p.meter_number}} | Band: {{p.band}} | Amount: {{p.amount}} <br>
        <form method="post" action="/release/{{p.id}}">
        <button type="submit">Mark as Paid & Release Unit</button><br><br>
        </form>
    {% endfor %}
    </div>
    """, pendings=pendings)

@app.route('/release/<int:uid>', methods=['POST'])
def release(uid):
    unit = Unit.query.get(uid)
    unit.status = 'paid'
    db.session.commit()
    return redirect('/pending')

@app.route('/complete')
def complete():
    if 'user' not in session or session['role'] != 'admin':
        return redirect('/login')
    units = Unit.query.filter_by(status='paid').all()
    return render_template_string(style + """
    <div class="sidebar">
    <a href="/add_unit">Add Listing</a>
    <a href="/pending">Pending Transactions</a>
    <a href="/complete">Completed Transactions</a>
    <a href="/logout">Logout</a>
    </div>
    <div class="content">
    <h2>Completed Transactions</h2>
    {% for u in units %}
        Meter: {{u.meter_number}} | Band: {{u.band}} | Amount: {{u.amount}} <br>
    {% endfor %}
    </div>
    """, units=units)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# Run App
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
