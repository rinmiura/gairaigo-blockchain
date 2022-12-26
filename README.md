# gairaigo-blockchain
### Getting started

requirements for blockchain proj:

```cmd
python -m venv /path/to/venv
/path/to/venv/Scripts/activate
```

```cmd
pip install requests
```

```cmd
pip install aiohttp
```

```cmd
pip install pycryptodome
```

requirements for gairaigo-site proj:

```cmd
python -m venv /path/to/venv
/path/to/venv/Scripts/activate
```

```cmd
pip install requests
```

```cmd
pip install flask
```

```cmd
pip install flask-sqlalchemy
```

```cmd
pip install flask-migrate
```

Specify the `token` for your telegram bot and the host for your gairaigo-site in the config dictionary from the blockchain module (app/__init__.py)
```py
def run(host, port):
    config['API_TOKEN'] = '<your token>'
    config['PROXY_URL'] = '<your proxy host>'
```

### Description of the blockchain

`blockchain.py` implements the main structures of the application - a block and a chain of blocks. File `transactions.py` contains message handlers and logic for collecting and reaping incoming transactions.

`chain_manager.py` implements the main network interfaces. Each node in the blockchain network performs the functions of a server, receiving updates from a telegram bot (via a proxy site) and, directly, data from other nodes.
```py
class _Connection:
  ...
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
```
Each node acts as a client when it completes the proof of work task and sends a new block to the rest of the network participants.
```py
async def send_once(host, __block_json):
    try:
        async with ClientSession() as session:
            async with session.post(host, json=__block_json) as resp:
                status = await resp.text()
                if status == 'successfully':
                    _Connection.SCFL_RECV += 1
    except ClientError as e:
        print(e)
```
```py
async def send_all(data):

    _Connection.SCFL_RECV = 0

    for _node in _Connection.nodes:
        self_host = tuple_to_str_host(_Connection.HOST)
        if _node['host'] != self_host:
            await send_once(f"http://{_node['host']}", data)

    return _Connection.SCFL_RECV >= len(_Connection.nodes) / 2
```
Functions from the file `rsa.py` they are responsible for generating a new public-private key pair, encrypting the transaction using the recipient's public key:
```py
def encrypt_transaction(amount, public):
    rsa = RSA.import_key(public)
    __public_key = PKCS1_OAEP.new(rsa)

    encrypted = __public_key.encrypt(f'{sha256(public.encode()).hexdigest()}-->amount:{amount}'.encode())
    encrypted = b64encode(encrypted).decode()

    return {
        'address': public.strip(),
        'amount': amount,
        'encrypted': encrypted
    }
```
verifying and signing the transaction using the sender's private key, etc.
```py
def sign_transaction(transaction, private, timestamp, comment="it's never been a gairaigo"):
    rsa = RSA.import_key(private)

    PKCS1_OAEP.new(rsa).decrypt(b64decode(transaction['encrypted'])).decode()

    _hash = SHA1.new()
    _hash.update(comment.encode())

    signature = pkcs1_15.new(rsa).sign(_hash)
    signature = b64encode(signature).decode()

    return {
        'address': transaction['address'],
        'amount': transaction['amount'],
        'signature': signature,
        'timestamp': timestamp
    }
```
The `verify_transaction` function verifies transactions in the block that the blockchain nodes receive from other miners who have mined a new block. Allows you to verify the authenticity of the sender's identity, the presence of unspent transactions on his account, necessary for the transaction

### Description of the gairaigo-site

Gairaigo-site is a proxy for interacting with the external telegram API. Collects reports from blockchain nodes and stores pairs of values in the database of the miner's public key-the current ip. Transmits to each node in the network a list of IP addresses of the other participants. Sends updates from the telegram bot to all network participants. Miners do not respond to users directly, but through the site to avoid duplication of messages.

Before launching the blockchain (for example, multiple copies on different ports), make sure that gairaigo-site is working and you have correctly specified the proxy address in app/__init__.py

For more effective tests, you can change the values of the complexity of the new block and the delay time during mining:
```py
while self.hash[:difficulty] != '0' * difficulty and not thread_stop:
    self.nonce += 1
    self.hash = self.get_hash()
    if self.nonce % 100 == 0:
        await sleep(random.randrange(10, 20)/10)
```
```py
class Blockchain:

  def __init__(self, host):
    ...
    self.difficulty = 3
    ...
```
