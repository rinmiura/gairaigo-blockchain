import json
from os.path import join, dirname, abspath


conf_path = join(dirname(abspath(__file__)), 'config.json')

with open(conf_path) as f:
    conf = json.load(f)


def get_client_url():
    return conf['client_url']


def get_cipher_length():
    return conf['cipher_length']
