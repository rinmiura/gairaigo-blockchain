from base64 import b64encode, b64decode
from hashlib import sha256

from Crypto.PublicKey import RSA
from Crypto import Random
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA1


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


def verify_signature(transaction, comment="it's never been a gairaigo"):
    _hash = SHA1.new()
    _hash.update(comment.encode())

    if not transaction.__contains__('signature'):
        return False

    signature = b64decode(transaction['signature'])
    address = transaction['address']

    try:
        pkcs1_15.new(RSA.import_key(address)).verify(_hash, signature)
        return True
    except ValueError:
        return False


def export_pair(length=None, private_key_file_path=None, public_key_file_path=None):
    random_generator = Random.new().read
    key = RSA.generate(length, random_generator)

    public, private = key.public_key().export_key('PEM'), key.export_key('PEM')

    with open(private_key_file_path, 'w') as private_file:
        private_file.write(private.decode())

    with open(public_key_file_path, 'w') as public_file:
        public_file.write(public.decode())

    return private.decode(), public.decode()


def get_public_for_private(key):
    rsa_key = RSA.import_key(key)

    if not rsa_key.has_private():
        raise

    rsa_key_text = rsa_key.public_key().export_key('PEM')

    return rsa_key_text.decode().rstrip()


def is_private_key(key):
    return RSA.import_key(key).has_private()
