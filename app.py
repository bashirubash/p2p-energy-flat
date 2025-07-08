from flask import Flask, render_template, request, redirect, url_for
from web3 import Web3
import json
import os
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
PUBLIC_KEY = os.getenv("PUBLIC_KEY")
INFURA_URL = os.getenv("INFURA_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

web3 = Web3(Web3.HTTPProvider(INFURA_URL))
with open("EnergyMarketplaceABI.json", "r") as abi_file:
    contract_abi = json.load(abi_file)

contract = web3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=contract_abi)

@app.route('/')
def home():
    trade_data = []
    for i in range(10):  # Loop up to 10 trades
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
    return render_template("index.html", trades=trade_data)

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
    web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return redirect(url_for('home'))

@app.route('/buy/<int:trade_id>/<float:price>')
def buy(trade_id, price):
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
    web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
