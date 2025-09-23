# uniswap_parser.py
from web3 import Web3
from decimal import Decimal

def analyze_tx_for_purchase(w3: Web3, txhash: str, token_address: str, min_amount: Decimal):
    tx = w3.eth.get_transaction(txhash)
    receipt = w3.eth.get_transaction_receipt(txhash)
    amount = None
    buyer = tx['from']

    # Simple check: if token_address appears in logs
    for log in receipt['logs']:
        if log['address'].lower() == token_address.lower():
            # decode amount from data (simplified)
            try:
                amount = Decimal(int(log['data'], 16)) / Decimal(10**18)
            except:
                continue
            if amount >= min_amount:
                return {"txhash": txhash, "buyer": buyer, "amount": amount}
    return None
