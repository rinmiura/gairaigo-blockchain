import random
from app.chain_manager import connect
from app.eventloop import Loop
from app.transactions import concur_pool
from app.rsa import export_pair, encrypt_transaction
from app.validator import verify_transactions
from hashlib import sha256
import json
from time import time
from os.path import exists
from asyncio import sleep

from aiohttp import web


PUBLIC_KEY_PATH = 'public.pem'
PRIVATE_KEY_PATH = 'private.pem'
CIPHER_LENGTH = 1024
COIN_BASE_AMOUNT = 10.0

thread_stop = False

config = {}


def get_hex_digest_for_sequence(*args):
    _hash = sha256()
    for arg in args:
        _hash.update(str(arg).encode('utf-8'))
    return _hash.hexdigest()


def get_merkle_tree_hash(data):

    _leaves = []

    for transaction in data:
        for side in transaction.values():
            for item in side:
                _leaves.append(json.dumps(item))

    def calculate(seq):
        if len(seq) == 1:
            return sha256(str(seq[0]).encode()).digest()

        if len(seq) % 2 == 1:
            seq.append(seq[-1])

        seq = [sha256(f'{seq[i]}{seq[i+1]}'.encode()).digest() for i in range(0, len(seq), 2)]
        return calculate(seq)

    return calculate(_leaves)


class Block:

    def __init__(self, timestamp=None, data=None, nonce=0, prevHash=None, from_json=False):
        self.timestamp = timestamp or time()
        self.nonce = nonce
        self.prevHash = prevHash
        self.data = []

        if not from_json:
            try:
                with open(PUBLIC_KEY_PATH) as f:
                    public = f.read()
                self.data.append({
                    'Input': [],
                    'Output': [encrypt_transaction(COIN_BASE_AMOUNT, public)]
                })
            except FileNotFoundError:
                pass

        if data is not None:
            self.data.extend(data)

        self.hash = self.get_hash()

    def get_hash(self):
        _hash = sha256()
        _hash.update(str(self.prevHash).encode('utf-8'))
        _hash.update(str(self.timestamp).encode('utf-8'))
        if len(self.data):
            _hash.update(get_merkle_tree_hash(self.data))
        _hash.update(str(self.nonce).encode('utf-8'))
        return _hash.hexdigest()

    async def mine(self, difficulty):
        while self.hash[:difficulty] != '0' * difficulty and not thread_stop:
            self.nonce += 1
            self.hash = self.get_hash()
            if self.nonce % 100 == 0:
                await sleep(random.randrange(10, 20)/10)


class Blockchain:

    def __init__(self, host):
        self.host = host
        self.chain = [Block()]
        self.difficulty = 3
        self.blockTime = 30
        self.filename = f'blockchain{host[1]}.json'

        self.loop = Loop()
        self.app = web.Application()
        self.routes = list()

        self.config = config

        global PUBLIC_KEY_PATH, PRIVATE_KEY_PATH
        PUBLIC_KEY_PATH = f'public{self.host[1]}.pem'
        PRIVATE_KEY_PATH = f'private{self.host[1]}.pem'

        self.awake()
        print('blockchain is running...')

    def get_last_block(self):
        return self.chain[len(self.chain) - 1]

    async def add_block(self, block, self_mine=True):
        if self_mine:
            block.prevHash = self.get_last_block().hash
            await block.mine(self.difficulty)
            if block.prevHash == self.get_last_block().hash:
                self.chain.append(block)
                print('new block'.center(20, '*'))
                return 1
        else:
            if block.prevHash == self.get_last_block().hash:
                _hash = block.hash
                await block.mine(self.difficulty)
                if block.hash == _hash:
                    if verify_transactions(block, self.chain):
                        self.chain.append(block)
                        return 1
                    else:
                        return -1
        return 0

    def awake(self):
        if exists(PRIVATE_KEY_PATH) and exists(PUBLIC_KEY_PATH):
            with open(PUBLIC_KEY_PATH) as f:
                public = f.read()
        else:
            _, public = export_pair(CIPHER_LENGTH, PRIVATE_KEY_PATH, PUBLIC_KEY_PATH)

        connect(self, Block, public)
        concur_pool(self, Block)
        self.app.add_routes(self.routes)
        self.loop.append(web._run_app, self.app, host=self.host[0], port=self.host[1])

    def servey(self):
        try:
            self.loop.join()
        except KeyboardInterrupt:
            self.loop.event_loop.stop()
            print('goodbye!')

    def __repr__(self):
        return json.dumps([{
                'timestamp': block.timestamp,
                'data': block.data,
                'nonce': block.nonce,
                'prevHash': block.prevHash
            } for block in self.chain
        ], indent=4)
