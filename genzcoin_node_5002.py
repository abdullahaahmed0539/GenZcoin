import datetime
import hashlib
import json
from flask import Flask, jsonify, request
import requests
from uuid import uuid4
from urllib.parse import urlparse

from werkzeug.wrappers import response

# Part 1: Building a Blockchain


class Blockchain:

    # Constructor initializes a new chain with genesis block
    def __init__(self):
        self.chain = []
        self.transactions = []
        self.create_block(proof=1, prev_hash='0')
        self.nodes = set()

    def create_block(self, proof, prev_hash):
        block = {
            'index': len(self.chain)+1,
            'time_stamp': str(datetime.datetime.now()),
            'proof': proof,
            'transactions': self.transactions,
            'prev_hash': prev_hash
        }
        self.transactions = []
        self.chain.append(block)
        return block

    def get_prev_block(self):
        return self.chain[-1]

    def proof_of_work(self, prev_nonce):
        nonce = 1
        check_proof = False
        while(check_proof is False):
            hash_operation = hashlib.sha256(
                str(nonce**2 - prev_nonce**2).encode()).hexdigest()
            if hash_operation[:4] == '0000':
                check_proof = True
            else:
                nonce += 1
        return nonce

    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def is_chain_valid(self, chain):
        prev_block = chain[0]
        block_index = 1
        while block_index < len(chain):
            block = chain[block_index]
            if block['prev_hash'] != self.hash(prev_block):
                return False
            prev_proof = prev_block['proof']
            proof = block['proof']
            hash_operation = hashlib.sha256(
                str(proof**2 - prev_proof**2).encode()).hexdigest()
            if hash_operation[:4] != '0000':
                return False
            prev_block = block
            block_index += 1
        return True

    def add_transaction(self, sender, reciever, amount):
        self.transactions.append({
            'sender': sender,
            'reciever': reciever,
            'amount': amount
        })
        prev_block = self.get_prev_block()
        return prev_block['index'] + 1

    def add_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def replace_chain(self):
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)
        for node in network:
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                len_of_chain = response.json()['length']
                chain = response.json()['chain']
                if len_of_chain > max_length and self.is_chain_valid(chain):
                    max_length = len_of_chain
                    longest_chain = chain
        if longest_chain:
            self.chain = longest_chain
            return True
        else:
            return False


# Creating Blockchain
blockchain = Blockchain()

# Part 2: Mining the Blockchain
# Creating web app
app = Flask(__name__)

# Creating an address for node on Port 5000
node_address = str(uuid4()).replace('-', '')


# Mining new block
@app.route('/mine_block', methods=['GET'])
def mine_block():
    prev_block = blockchain.get_prev_block()
    prev_proof = prev_block['proof']
    proof = blockchain.proof_of_work(prev_proof)
    blockchain.add_transaction(node_address, reciever='Mom', amount=10)
    prev_hash = blockchain.hash(prev_block)
    block = blockchain.create_block(proof, prev_hash)
    response = {
        'message': 'Block mined.',
        'index': block['index'],
        'time_stamp': block['time_stamp'],
        'proof': block['proof'],
        'transactions': block['transactions'],
        'prev_hash': block['prev_hash']
    }
    return jsonify(response), 200


@app.route('/get_chain', methods=['GET'])
def get_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200


@app.route('/is_valid', methods=['GET'])
def is_valid():
    if blockchain.is_chain_valid(blockchain.chain):
        response = {'valid': True}
    else:
        response = {'valid': False}
    return jsonify(response), 200


@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    json = request.get_json()
    transaction_keys = ['sender', 'reciever', 'amount']
    if not all(key in json for key in transaction_keys):
        return 'incomplete details', 400
    index = blockchain.add_transaction(
        json['sender'], json['reciever'], json['amount'])
    response = {
        'message': f'transaction added to Block = {index}'
    }
    mine_block()
    return jsonify(response), 201

# Connecting new nodes
@app.route('/connect_node', methods=['POST'])
def connect_node():
    json = request.get_json()
    nodes = json.get('nodes')
    if nodes is None:
        return "No nodes", 400
    for node_address in nodes:
        blockchain.add_node(node_address)
    response = {
        'message': 'All the nodes are added to Genzcoin blockchain',
        'total_nodes': list(blockchain.nodes)
    }
    return jsonify(response), 201


@app.route('/replace_chain', methods=['GET'])
def replace_chain():
    is_chain_replaced = blockchain.replace_chain()
    if is_chain_replaced:
        response = {
            'message': 'Chain was updated with longest one.',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Chain is already the largest one.',
            'chain': blockchain.chain
        }
    return jsonify(response), 200


# Running the app
app.run(host='0.0.0.0', port=5002)
