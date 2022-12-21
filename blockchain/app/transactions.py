import os

from app.chain_manager import send_all
import random
from time import time
from app.rsa import sign_transaction, encrypt_transaction, \
    get_public_for_private, is_private_key, export_pair

from aiohttp import request, web


_add_block_func = None
_block_cls = None
_blockchain_list = None
pool = None
_port = None


API_TOKEN = None
PROXY_URL = None

handlers = dict()
parsed = list()


def concur_pool(blockchain, block_cls):

    global _add_block_func, _blockchain_list, _block_cls, pool, _port, API_TOKEN, PROXY_URL

    _add_block_func = blockchain.add_block
    _block_cls = block_cls
    _blockchain_list = blockchain.chain
    _port = blockchain.host[1]

    API_TOKEN = blockchain.config['API_TOKEN']
    PROXY_URL = blockchain.config['PROXY_URL']

    pool = Pool()

    async def get_concurrent_updates(request: web.Request):
        update = await request.json()
        if update['content_type'] == 'text' and update['content'] in handlers:
            await handlers[update['content']](**update)
        else:
            await handlers[update['content_type']](**update)
        return web.Response(text='updated')

    blockchain.routes.append(web.post('/updates', get_concurrent_updates))
    blockchain.loop.append(pool.reap)


def get_url(method, **options):
    options = '&'.join((f'{key}={value}' for key, value in options.items()))
    return f'https://api.telegram.org/bot{API_TOKEN}/{method}?{options}'


def get_download_url(file_path: str):
    file_path = file_path.replace('/', '//')
    return f'https://api.telegram.org/file/bot{API_TOKEN}/{file_path}'


def get_proxy_url(route):
    return f'{PROXY_URL}/{route}'


async def get_file(file_id):
    async with request('get', get_url('getFile', file_id=file_id)) as resp:
        data = await resp.json()
    file_path = data['result']['file_path']
    async with request('get', get_download_url(file_path)) as resp:
        file = await resp.text()
    return file


async def send_message(msg_id, chat_id, text):
    data = {'msg_id': msg_id, 'chat_id': chat_id, 'text': text}
    async with request('post', get_proxy_url('sendtoBot'), data=data) as resp:
        await resp.text()


async def send_document(msg_id, chat_id, username, filename, content):
    data = {'msg_id': msg_id, 'chat_id': chat_id, 'username': username, 'filename': filename, 'content': content}
    async with request('post', get_proxy_url('sendtoBot'), data=data) as resp:
        await resp.text()


def bind(command):
    def bind_wrapper(func):
        handlers[command] = func
        return func
    return bind_wrapper


def generate_path_to_key():
    chars = 'ABCDEFGHIJKLMNOPQRSTUWXYZ0123456789'
    path = ''
    for _ in range(9):
        path += chars[random.randrange(len(chars))]
    path += '.pem'
    return path.lower()


@bind('/start')
async def print_info(msg_id, chat_id, **kwargs):
    await send_message(msg_id, chat_id, "I'm a thin-client bot of a Gairaigo blockchain. "
                                        "You can control me by sending these commands.\n\n"
                                        "/new_account\n"
                                        "/wire_money\n"
                                        "/print_utxo")


@bind('/new_account')
async def new_account(msg_id, chat_id, username, **kwargs):
    private_filename, public_filename = generate_path_to_key(), generate_path_to_key()
    private_key_path, public_key_path = os.path.join('tmp', private_filename), os.path.join('tmp', public_filename)

    export_pair(1024, private_key_path, public_key_path)

    await send_message(msg_id, chat_id, "Congratulations. You have successfully created a new wallet. "
                                        "Your address (public key) and private key are in the attached files.\n\n"
                                        "Remittance Management:\n"
                                        "/wire_money\n"
                                        "/print_utxo")

    with open(private_key_path, 'r') as private:
        await send_document(msg_id, chat_id, username, private_filename, private.read())

    with open(public_key_path, 'r') as public:
        await send_document(msg_id, chat_id, username, public_filename, public.read())

    os.remove(private_key_path)


@bind('/wire_money')
async def wire_money(msg_id, chat_id, username, **kwargs):
    await send_message(msg_id, chat_id, f"Let's get started, {username}. "
                                        "Please forward the file with the private key (a larger file from the pair) "
                                        "from which account you want to transfer money.")


@bind('document')
async def get_file_key(msg_id, chat_id, username, content, **kwargs):
    file_id = content['file_id']
    key_text = await get_file(file_id)

    session, state = pool.get(username)

    if state == 0:
        try:
            public_key_text = get_public_for_private(key_text)
        except:
            return await send_message(msg_id, chat_id, "Something was wrong. Try again. "
                                                       "Forward the file with your private key.")

        session.append(public_key_text)
        session.append(key_text)

        return await send_message(msg_id, chat_id, "Perfectly. Now you need to attach a file with the address "
                                                   "of the recipient of the transfer.")
    elif state == 2:
        if is_private_key(key_text):
            session.clear()
            return await send_message(msg_id, chat_id, "Something was wrong. Try again. "
                                                       "Forward the file with your private key.")

        session.append(key_text)
        await send_message(msg_id, chat_id, "Transfer amount:")


@bind('text')
async def get_transfer_amount(msg_id, chat_id, username, content, **kwargs):
    try:
        amount = float(content)
        session, state = pool.get(username)

        if state != 3:
            return await send_message(msg_id, chat_id, "Something was wrong. For the transfer, "
                                                       "you must specify your private key and "
                                                       "the public key of the recipient of the transfer")

        session.append(amount)
        pool.gather(session)

        await send_message(msg_id, chat_id, "Your transaction got into the pool! "
                                            "The average block waiting time will be: 30 seconds.")
    except InsufficientFundsError as e:
        await send_message(msg_id, chat_id, e)


@bind('/print_utxo')
async def get_utxo(msg_id, chat_id, keys, **kwargs):
    utxo = {}
    for key in keys:
        with open(os.path.join('tmp', key)) as f:
            public = f.read()
        utxo[key] = 0
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
                            utxo[key] += __output_amount
    text = ''
    for key, amount in utxo.items():
        text += f'{key}: {amount}\t'

    await send_message(msg_id, chat_id, text)


class Pool(list):

    def __init__(self):
        self.sessions = {}
        self.timestamp = time()
        super().__init__()

    def get(self, addr):
        if addr not in self.sessions:
            session = self.sessions[addr] = []
        else:
            session = self.sessions[addr]

        return session, len(session)

    def gather(self, session):
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

        session.clear()

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
