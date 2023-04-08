import asyncio
import json

import requests
from aiohttp import request, web, ClientSession, ClientError

_add_block_func = None
_block_cls = None
_chain_filename = None
_blockchain = None
routes = None

CLIENT_URL = None


def get_url(method):
    return f'{CLIENT_URL}/{method}'


def connect(blockchain, block_cls, public_key):
    global _add_block_func, _block_cls, _chain_filename, _blockchain, routes, CLIENT_URL
    _add_block_func = blockchain.add_block
    _block_cls = block_cls
    _chain_filename = blockchain.filename
    CLIENT_URL = blockchain.client_url
    _blockchain = blockchain

    _Connection.HOST = blockchain.host
    _Connection.PUBLIC_KEY = public_key

    routes = blockchain.routes

    _Connection.loop = blockchain.loop

    _Connection.setup()
    _Connection.poll()


def str_to_tuple_host(str_host):
    ip, _, port = str_host.partition(':')
    return ip, int(port)


def tuple_to_str_host(tuple_host):
    return '{}:{}'.format(tuple_host[0], tuple_host[1])


async def send_once(host, __block_json):
    try:
        async with ClientSession() as session:
            async with session.post(host, json=__block_json) as resp:
                status = await resp.text()
                if status == 'successfully':
                    _Connection.SCFL_RECV += 1
    except ClientError as e:
        print(e)


async def send_all(data):

    _Connection.SCFL_RECV = 0

    for _node in _Connection.nodes:
        self_host = tuple_to_str_host(_Connection.HOST)
        if _node['host'] != self_host:
            await send_once(f"http://{_node['host']}", data)

    return _Connection.SCFL_RECV >= len(_Connection.nodes) / 2


class _Connection:

    HOST = None
    PUBLIC_KEY = None
    SCFL_RECV = 0

    loop = None

    nodes = list()

    @staticmethod
    def setup():
        __chain_json = requests.get(get_url('chain')).text
        if __chain_json:
            _chain = [_block_cls(**prop_bag, from_json=True) for prop_bag in json.loads(__chain_json)]
            _blockchain.chain = _chain

        async def update():
            data = {'public_key': _Connection.PUBLIC_KEY, 'host': tuple_to_str_host(_Connection.HOST)}
            while True:
                async with request('post', get_url('nodes/'), data=data) as r:
                    _Connection.nodes = json.loads(await r.text())
                with open(_chain_filename, 'w') as chain:
                    chain.write(str(_blockchain))
                async with request('post', get_url('chain/'), data={'document': str(_blockchain)}) as r:
                    await r.text()
                await asyncio.sleep(5)
        _Connection.loop.append(update)

    @staticmethod
    def poll():
        async def consensus_handler(request: web.Request):
            __block_json = await request.json()
            if (await _add_block_func(_block_cls(**__block_json, from_json=True), self_mine=False)) == 1:
                print('approved'.center(20, '*'))
                return web.Response(text='successfully')
            else:
                print('rejected'.center(20, '*'))
                return web.Response(text='rejected')
        routes.append(web.post('/', consensus_handler))
