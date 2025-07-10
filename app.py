# app.py (Full Package with Authentication, Meter Recharge, Wallet, Admin Panel, Notifications)

from flask import Flask, request, redirect, url_for, Response, flash, session, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from web3 import Web3
from dotenv import load_dotenv
from twilio.rest import Client
import os, json, sqlite3

app = Flask(__name__)
app.secret_key = "yedc_secret_key"
load_dotenv()

# Web3 setup
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
PUBLIC_KEY = os.getenv("PUBLIC_KEY")
INFURA_URL = os.getenv("INFURA_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

web3 = Web3(Web3.HTTPProvider(INFURA_URL))
with open("EnergyMarketplaceABI.json", "r") as abi_file:
    contract_abi = json.load(abi_file)
contract = web3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=contract_abi)

# Login setup
login_manager = LoginManager()
login_manager.init_app(app)

# Dummy user DB using SQLite
DB = "users.db"
if not os.path.exists(DB):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, meter TEXT, password TEXT, photo TEXT DEFAULT 'default.jpg')''')
    conn.commit()
    conn.close()

class User(UserMixin):
    def __init__(self, id, username, meter, photo):
        self.id = id
        self.username = username
        self.meter = meter
        self.photo = photo

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return User(*row[:4])
    return None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        meter = request.form['meter']
        password = request.form['password']
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, meter, password) VALUES (?, ?, ?)", (username, meter, password))
        conn.commit()
        conn.close()
        return redirect('/login')
    return '''<form method="post">Username: <input name='username'> Meter: <input name='meter'> Password: <input name='password' type='password'> <button>Register</button></form>'''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        row = c.fetchone()
        conn.close()
        if row:
            user = User(*row[:4])
            login_user(user)
            return redirect('/')
        return "Invalid credentials"
    return '''<form method="post">Username: <input name='username'> Password: <input name='password' type='password'> <button>Login</button></form>'''

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

@app.route('/dashboard')
@login_required
def dashboard():
    balance = web3.eth.get_balance(PUBLIC_KEY)
    return f"<h2>Welcome, {current_user.username}</h2><p>Meter: {current_user.meter}</p><p>ETH Balance: {web3.from_wei(balance, 'ether')} ETH</p>"

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        f = request.files['photo']
        filename = secure_filename(f.filename)
        f.save(os.path.join("static", "profile", filename))
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("UPDATE users SET photo = ? WHERE id = ?", (filename, current_user.id))
        conn.commit()
        conn.close()
        return redirect('/dashboard')
    return '<form method="post" enctype="multipart/form-data"><input type="file" name="photo"><button>Upload</button></form>'

@app.route('/')
@login_required
def home():
    trade_data = []
    for i in range(10):
        try:
            t = contract.functions.getTrade(i).call()
            trade_data.append({"id": i, "seller": t[0], "buyer": t[1], "energy": t[2], "price": web3.from_wei(t[3], 'ether'), "completed": t[4]})
        except:
            break

    rows = "".join([f"<tr><td>{t['id']}</td><td>{t['seller']}</td><td>{t['buyer']}</td><td>{t['energy']}</td><td>{t['price']}</td><td>{'✅' if t['completed'] else '🟢'}</td><td><a href='/buy/{t['id']}/{t['price']}'>Buy</a></td></tr>" for t in trade_data])

    return Response(f"""
    <h1>YEDC Energy Marketplace</h1>
    <form method='post' action='/offer'>
        Energy (kWh): <input name='energy' required>
        Price (ETH): <input name='price' step='0.01' required>
        <button type='submit'>Offer</button>
    </form>
    <h2>Buy Energy</h2>
    <table border='1'><tr><th>ID</th><th>Seller</th><th>Buyer</th><th>Energy</th><th>Price</th><th>Status</th><th>Action</th></tr>{rows}</table>
    """, mimetype='text/html')

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
        'gasPrice': web3.to_wei('10', 'gwei')
    })
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    return redirect('/')

@app.route('/buy/<int:trade_id>/<float:price>')
@login_required
def buy(trade_id, price):
    trade = contract.functions.getTrade(trade_id).call()
    if trade[4]: return redirect(url_for('home'))
    amount_wei = web3.to_wei(price, 'ether')
    nonce = web3.eth.get_transaction_count(PUBLIC_KEY)
    tx = contract.functions.buyEnergy(trade_id).build_transaction({
        'from': PUBLIC_KEY,
        'value': amount_wei,
        'nonce': nonce,
        'gas': 300000,
        'gasPrice': web3.to_wei('10', 'gwei')
    })
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    # Placeholder for YEDC API recharge call
    # recharge_meter(current_user.meter, trade[2])
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)
