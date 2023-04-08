import os
import random
from time import time

from aiohttp import web

from .chain_manager import send_all
from app.sec.rsa import sign_transaction, encrypt_transaction, \
    get_public_for_private, is_private_key, get_pair


_add_block_func = None
_block_cls = None
_blockchain_list = None
pool = None
_port = None


CLIENT_URL = None

handlers = dict()
parsed = list()


def concur_pool(blockchain, block_cls):

    global _add_block_func, _blockchain_list, _block_cls, pool, _port, CLIENT_URL

    _add_block_func = blockchain.add_block
    _block_cls = block_cls
    _blockchain_list = blockchain.chain
    _port = blockchain.host[1]

    CLIENT_URL = blockchain.client_url

    pool = Pool()

    blockchain.routes.append(web.get('/get-utxo', get_utxo))
    blockchain.loop.append(pool.reap)


def generate_path_to_key():
    chars = 'ABCDEFGHIJKLMNOPQRSTUWXYZ0123456789'
    path = ''
    for _ in range(9):
        path += chars[random.randrange(len(chars))]
    path += '.pem'
    return path.lower()


async def get_utxo(request: web.Request):
    key = await request.text()
    with open(os.path.join('tmp', key)) as f:
        public = f.read()

    utxo = 0

    for block in _blockchain_list:
        for transaction in block.data:
            for output in transaction['Output']:
                if output['address'] == public:
                    __is_spent_tx = False
                    __block_index = _blockchain_list.index(block) + 1
                    __block_timestamp = block.timestamp
                    __output_amount = output['amount']

                    for _block in _blockchain_list[__block_index:]:
                        for _transaction in _block.data:
                            for __input in _transaction['Input']:
                                __is_spent_tx = __is_spent_tx or \
                                                (__input['timestamp'] == __block_timestamp and
                                                 __input['address'] == public and
                                                 __input['amount'] == __output_amount)

                    if not __is_spent_tx:
                        utxo += __output_amount

    return web.Response(text=str(utxo))


class Pool(list):

    def __init__(self):
        self.timestamp = time()
        super().__init__()

    def append(self, session):
        change, inputs = Pool.gather_inputs(session)
        public_from = session[0]
        public_to = session[2]
        amount = session[3]

        outputs = [encrypt_transaction(amount, public_to)]
        if change > 0:
            outputs.append(encrypt_transaction(change, public_from))

        self.append({
            'Input': inputs,
            'Output': outputs
        })

    @staticmethod
    def gather_inputs(session):
        required_utxo = session[3]
        private = session[1]
        public = session[0]

        utxo = 0
        inputs = []

        for block in _blockchain_list:
            for transaction in block.data:
                for output in transaction['Output']:
                    if output['address'] == public:

                        _input = sign_transaction(output, private, block.timestamp)

                        __is_spent_tx = False
                        __block_index = _blockchain_list.index(block) + 1

                        for _block in _blockchain_list[__block_index:]:
                            for _transaction in _block.data:
                                for __input in _transaction['Input']:
                                    __is_spent_tx = __is_spent_tx or __input == _input

                        if not __is_spent_tx:
                            utxo += _input['amount']
                            inputs.append(_input)
                            if utxo >= required_utxo:
                                return utxo - required_utxo, inputs
        raise InsufficientFundsError

    async def reap(self):
        while True:
            self[:], trs = [], self[:]
            last_block = len(_blockchain_list)
            block = _block_cls(timestamp=self.timestamp, data=trs)
            status = await _add_block_func(block)
            if status < 1:
                if status == 0:
                    for block in _blockchain_list[last_block:]:
                        for t in block.data:
                            if t in trs:
                                trs.remove(t)
                self.extend(trs)
                continue

            block_json = {
                'timestamp': block.timestamp,
                'data': block.data,
                'nonce': block.nonce,
                'prevHash': block.prevHash
            }
            __consensus = await send_all(block_json)
            if not __consensus:
                try:
                    _blockchain_list.remove(block)
                except ValueError:
                    pass

            self.timestamp = time()


class InsufficientFundsError(BaseException):

    def __str__(self):
        return 'An error has occurred! Insufficient funds.'
