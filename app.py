from flask import Flask, request, redirect, url_for, Response, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from web3 import Web3
from dotenv import load_dotenv
from twilio.rest import Client
import json
import os

# === Flask App Config ===
app = Flask(__name__)
app.secret_key = "super_secret_key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

# === Login Setup ===
login_manager = LoginManager()
login_manager.init_app(app)

# === Load .env ===
load_dotenv()
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
PUBLIC_KEY = os.getenv("PUBLIC_KEY")
INFURA_URL = os.getenv("INFURA_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
YEDC_API_KEY = os.getenv("YEDC_API_KEY")
YEDC_ENDPOINT = os.getenv("YEDC_ENDPOINT")

# === Blockchain Setup ===
web3 = Web3(Web3.HTTPProvider(INFURA_URL))
with open("EnergyMarketplaceABI.json", "r") as abi_file:
    contract_abi = json.load(abi_file)
contract = web3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=contract_abi)

# === Twilio Client ===
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# === User Model ===
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    meter_number = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(20), nullable=False)

# === Login loader ===
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# === Helper: Render Page ===
def render_index_html(trades, message=""):
    rows = ""
    for t in trades:
        buyer = t["buyer"] if t["buyer"] != "0x0000000000000000000000000000000000000000" else "None"
        status = "✅ Completed" if t["completed"] else "🟢 Open"
        action = f'''
            <form method="POST" action="/buy/{t["id"]}/{t["price"]}">
                <input type="text" name="meter" placeholder="Buyer Meter #" required />
                <button type="submit">Buy</button>
            </form>
        ''' if not t["completed"] else "-"
        rows += f"""
            <tr>
                <td>{t["id"]}</td>
                <td>{t["seller"]}</td>
                <td>{buyer}</td>
                <td>{t["energy"]}</td>
                <td>{t["price"]}</td>
                <td>{status}</td>
                <td>{action}</td>
            </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>YEDC P2P Energy</title>
        <style>
            body {{ font-family: Arial; background-color: #eef2f5; padding: 20px; }}
            h1 {{ text-align: center; color: #2c3e50; }}
            table {{ width: 100%; border-collapse: collapse; background: #fff; margin-top: 20px; }}
            th, td {{ padding: 10px; border: 1px solid #ccc; text-align: center; }}
            th {{ background-color: #34495e; color: white; }}
            form {{ display: inline-block; }}
            input, button {{ padding: 6px; }}
            .msg {{ text-align: center; color: green; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>YEDC Peer-to-Peer Energy Marketplace</h1>
        {f"<div class='msg'>{message}</div>" if message else ""}
        <form method="POST" action="/offer" style="margin-top:20px;">
            <input type="number" name="energy" placeholder="Energy (kWh)" required />
            <input type="number" name="price" step="0.01" placeholder="Price (ETH)" required />
            <button type="submit">List Energy</button>
        </form>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Seller</th>
                    <th>Buyer</th>
                    <th>Energy</th>
                    <th>Price (ETH)</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </body>
    </html>
    """
    return Response(html, mimetype='text/html')


# === Home Route ===
@app.route('/')
def home():
    trade_data = []
    for i in range(20):
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
    return render_index_html(trade_data, message=request.args.get('msg', ''))


# === Offer Energy ===
@app.route('/offer', methods=["POST"])
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
    return redirect(url_for('home', msg="Energy Listed ✅"))


# === Buy Energy ===
@app.route('/buy/<int:trade_id>/<float:price>', methods=["POST"])
def buy(trade_id, price):
    meter_number = request.form['meter']
    trade = contract.functions.getTrade(trade_id).call()
    if trade[4]:
        return redirect(url_for('home', msg="Trade already completed ❌"))

    nonce = web3.eth.get_transaction_count(PUBLIC_KEY)
    amount_wei = web3.to_wei(price, 'ether')
    tx = contract.functions.buyEnergy(trade_id).build_transaction({
        'from': PUBLIC_KEY,
        'value': amount_wei,
        'nonce': nonce,
        'gas': 300000,
        'gasPrice': web3.to_wei('15', 'gwei')
    })
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

    # Simulate Recharge via YEDC API
    print(f"Recharge initiated for meter: {meter_number} (mocked)")
    # In real code, make requests.post(YEDC_ENDPOINT, headers={...}, json={...})

    return redirect(url_for('home', msg="Trade successful! Meter will be credited 🔌"))


# === Main Entrypoint ===
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)
