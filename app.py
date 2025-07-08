from flask import Flask, request, redirect, url_for, Response, flash
from web3 import Web3
import json
import os
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Needed for flash messages
load_dotenv()

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
PUBLIC_KEY = os.getenv("PUBLIC_KEY")
INFURA_URL = os.getenv("INFURA_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

web3 = Web3(Web3.HTTPProvider(INFURA_URL))

with open("EnergyMarketplaceABI.json", "r") as abi_file:
    contract_abi = json.load(abi_file)

contract = web3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=contract_abi
)

def render_index_html(trades, message=""):
    rows = ""
    for t in trades:
        buyer = t["buyer"] if t["buyer"] != "0x0000000000000000000000000000000000000000" else "None"
        status = "✅ Completed" if t["completed"] else "🟢 Open"
        action = f'<a href="/buy/{t["id"]}/{t["price"]}">Buy</a>' if not t["completed"] else "-"

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
        <meta charset="UTF-8">
        <title>P2P Energy Marketplace</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f5f7fa;
                padding: 30px;
            }}
            h1 {{
                color: #2c3e50;
                text-align: center;
            }}
            .message {{
                text-align: center;
                color: green;
                font-weight: bold;
            }}
            form {{
                margin: 0 auto 30px;
                max-width: 300px;
                display: flex;
                flex-direction: column;
                gap: 10px;
            }}
            input, button {{
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 14px;
            }}
            button {{
                background-color: #3498db;
                color: white;
                cursor: pointer;
            }}
            button:hover {{
                background-color: #2980b9;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 30px;
                background-color: white;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 10px;
                text-align: center;
            }}
            th {{
                background-color: #34495e;
                color: white;
            }}
            a {{
                color: #3498db;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
        </style>
    </head>
    <body>
        <h1>Decentralized Energy Marketplace</h1>
        {f'<p class="message">{message}</p>' if message else ''}
        <form method="POST" action="/offer">
            <input type="number" name="energy" placeholder="Energy (kWh)" required>
            <input type="number" step="0.01" name="price" placeholder="Price (ETH)" required>
            <button type="submit">List Energy</button>
        </form>
        <h2>Available Listings</h2>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Seller</th>
                    <th>Buyer</th>
                    <th>Energy</th>
                    <th>Price</th>
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


@app.route('/')
def home():
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
    message = request.args.get('msg', '')
    return render_index_html(trade_data, message=message)


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
    return redirect(url_for('home', msg="Offer submitted successfully!"))


@app.route('/buy/<int:trade_id>/<float:price>')
def buy(trade_id, price):
    # Check if trade is already completed
    trade = contract.functions.getTrade(trade_id).call()
    if trade[4]:  # completed == True
        return redirect(url_for('home', msg="❌ This trade is already completed."))

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
    return redirect(url_for('home', msg="✅ Trade executed successfully!"))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)
