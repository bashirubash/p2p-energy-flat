from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from web3 import Web3
import os

app = Flask(__name__)
app.secret_key = "secret"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///market.db'
db = SQLAlchemy(app)

# Mock Web3 (Replace with real provider if needed)
w3 = Web3(Web3.HTTPProvider("https://rpc.ankr.com/eth_sepolia"))
admin_wallet = "0x9311DeE48D671Db61947a00B3f9Eae6408Ec4D7b"

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    meter_number = db.Column(db.String(50))
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(50))
    role = db.Column(db.String(10))  # buyer or admin

class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(100))
    price = db.Column(db.Float)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    buyer_email = db.Column(db.String(50))
    meter_number = db.Column(db.String(50))
    amount = db.Column(db.Float)
    unit_description = db.Column(db.String(100))
    status = db.Column(db.String(10))  # pending, paid

# HTML Templates
style = """
<style>
body { font-family: Arial; background: #f4f6f9; margin:0; padding:0; }
.container { width: 400px; margin: 50px auto; background: #fff; padding:20px; box-shadow:0 0 10px #ccc; border-radius:8px; }
h2 { text-align:center; }
input, button { width: 100%; padding:10px; margin:5px 0; border-radius:5px; border:1px solid #ccc; }
nav { background: #333; color:#fff; padding:15px; }
nav a { color:#fff; margin: 0 10px; text-decoration:none; }
.sidebar { width:200px; background:#222; color:#fff; position:fixed; height:100%; top:0; left:0; padding-top:50px; }
.sidebar a { display:block; color:#fff; padding:10px; text-decoration:none; }
.sidebar a:hover { background:#444; }
.main { margin-left:210px; padding:20px; }
table { width:100%; border-collapse: collapse; margin-top:20px; }
table, th, td { border:1px solid #ccc; padding:8px; text-align:left; }
</style>
"""

# Routes
@app.route('/')
def home():
    return render_template_string(style + """
    <div class="container">
    <h2>Meter Unit Marketplace</h2>
    <a href="/register"><button>Register</button></a>
    <a href="/login"><button>Login</button></a>
    </div>
    """)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        meter = request.form['meter']
        email = request.form['email']
        password = request.form['password']
        role = "buyer"
        user = User(name=name, meter_number=meter, email=email, password=password, role=role)
        db.session.add(user)
        db.session.commit()
        flash("Registration Successful! Please Login.")
        return redirect(url_for('login'))
    return render_template_string(style + """
    <div class="container">
    <h2>Register</h2>
    <form method="post">
        <input name="name" placeholder="Name" required>
        <input name="meter" placeholder="Meter Number" required>
        <input name="email" type="email" placeholder="Email" required>
        <input name="password" type="password" placeholder="Password" required>
        <button type="submit">Register</button>
    </form>
    </div>
    """)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        pwd = request.form['password']
        user = User.query.filter_by(email=email, password=pwd).first()
        if user:
            session['email'] = user.email
            session['role'] = user.role
            return redirect('/dashboard')
        else:
            flash("Invalid Credentials")
    return render_template_string(style + """
    <div class="container">
    <h2>Login</h2>
    <form method="post">
        <input name="email" type="email" placeholder="Email" required>
        <input name="password" type="password" placeholder="Password" required>
        <button type="submit">Login</button>
    </form>
    </div>
    """)

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect('/')
    if session['role'] == "admin":
        return redirect('/admin')
    units = Unit.query.all()
    transactions = Transaction.query.filter_by(buyer_email=session['email']).all()
    return render_template_string(style + """
    <div class="container">
    <h2>Buyer Dashboard</h2>
    <p>Welcome {{session['email']}}</p>
    <h3>Available Units:</h3>
    <table><tr><th>Unit</th><th>Price</th><th>Action</th></tr>
    {% for u in units %}
    <tr><td>{{u.description}}</td><td>${{u.price}}</td>
    <td><a href="/buy/{{u.id}}"><button>Buy</button></a></td></tr>
    {% endfor %}
    </table>
    <h3>Your Transactions:</h3>
    <table><tr><th>Unit</th><th>Amount</th><th>Status</th></tr>
    {% for t in transactions %}
    <tr><td>{{t.unit_description}}</td><td>${{t.amount}}</td><td>{{t.status}}</td></tr>
    {% endfor %}
    </table>
    <a href="/logout"><button>Logout</button></a>
    </div>
    """, units=units, transactions=transactions, session=session)

@app.route('/buy/<int:unit_id>')
def buy(unit_id):
    if 'email' not in session:
        return redirect('/login')
    unit = Unit.query.get(unit_id)
    user = User.query.filter_by(email=session['email']).first()
    tx = Transaction(buyer_email=user.email, meter_number=user.meter_number, amount=unit.price,
                     unit_description=unit.description, status="pending")
    db.session.add(tx)
    db.session.commit()
    flash(f"Transaction created. Send {unit.price} ETH from your Metamask to {admin_wallet}. Wait for admin approval.")
    return redirect('/dashboard')

@app.route('/admin')
def admin_panel():
    if 'email' not in session or session['email'] != "gurus@gmail.com":
        return redirect('/')
    return render_template_string(style + """
    <div class="sidebar">
    <a href="/admin/add">Add Listing</a>
    <a href="/admin/pending">Pending Transactions</a>
    <a href="/admin/completed">Completed Transactions</a>
    <a href="/logout">Logout</a>
    </div>
    <div class="main">
    <h2>Admin Dashboard</h2>
    <p>Welcome Admin</p>
    </div>
    """)

@app.route('/admin/add', methods=['GET','POST'])
def add_listing():
    if 'email' not in session or session['email'] != "gurus@gmail.com":
        return redirect('/')
    if request.method == 'POST':
        desc = request.form['desc']
        price = float(request.form['price'])
        u = Unit(description=desc, price=price)
        db.session.add(u)
        db.session.commit()
        flash("Unit Added.")
        return redirect('/admin')
    return render_template_string(style + """
    <div class="main">
    <h2>Add New Unit</h2>
    <form method="post">
        <input name="desc" placeholder="Unit Description" required>
        <input name="price" placeholder="Price" required>
        <button type="submit">Add</button>
    </form>
    <a href="/admin">Back</a>
    </div>
    """)

@app.route('/admin/pending')
def pending():
    if 'email' not in session or session['email'] != "gurus@gmail.com":
        return redirect('/')
    txs = Transaction.query.filter_by(status="pending").all()
    return render_template_string(style + """
    <div class="main">
    <h2>Pending Transactions</h2>
    <table><tr><th>Buyer</th><th>Meter</th><th>Unit</th><th>Amount</th><th>Action</th></tr>
    {% for t in txs %}
    <tr><td>{{t.buyer_email}}</td><td>{{t.meter_number}}</td><td>{{t.unit_description}}</td><td>{{t.amount}}</td>
    <td><a href="/admin/verify/{{t.id}}"><button>Mark Paid</button></a></td></tr>
    {% endfor %}
    </table>
    <a href="/admin">Back</a>
    </div>
    """, txs=txs)

@app.route('/admin/verify/<int:txid>')
def verify(txid):
    tx = Transaction.query.get(txid)
    tx.status = "paid"
    db.session.commit()
    flash(f"Payment Verified. {tx.amount} for {tx.unit_description} to meter {tx.meter_number}")
    return redirect('/admin/pending')

@app.route('/admin/completed')
def completed():
    if 'email' not in session or session['email'] != "gurus@gmail.com":
        return redirect('/')
    txs = Transaction.query.filter_by(status="paid").all()
    return render_template_string(style + """
    <div class="main">
    <h2>Completed Transactions</h2>
    <table><tr><th>Buyer</th><th>Meter</th><th>Unit</th><th>Amount</th></tr>
    {% for t in txs %}
    <tr><td>{{t.buyer_email}}</td><td>{{t.meter_number}}</td><td>{{t.unit_description}}</td><td>{{t.amount}}</td></tr>
    {% endfor %}
    </table>
    <a href="/admin">Back</a>
    </div>
    """, txs=txs)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Initialize DB
with app.app_context():
    db.create_all()
    admin = User.query.filter_by(email="gurus@gmail.com").first()
    if not admin:
        admin = User(name="Guru", meter_number="0000", email="gurus@gmail.com", password="Guru123", role="admin")
        db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
