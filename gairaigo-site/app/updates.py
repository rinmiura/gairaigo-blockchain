from time import sleep

from app import app, get_url
from app.models import Node, User

import requests


def get_current_update():
    while True:
        data = requests.get(get_url('getUpdates')).json()['result']
        updates = [update['message'] for update in data if 'message' in update]
        if updates:
            return max((t['message_id'] for t in updates)), updates


def spray():
    with app.app_context():
        _last_update, updates = get_current_update()

        try:
            while True:
                sleep(3)
                actual = list(filter(lambda _update: _update['message_id'] > _last_update, updates))
                if actual:
                    for _actual in actual:
                        _content_type = 'text' if 'text' in _actual else 'document'
                        resp = {
                            'msg_id': _actual['message_id'],
                            'chat_id': _actual['chat']['id'],
                            'content_type': _content_type,
                            'content': _actual[_content_type],
                            'username': _actual['chat']['username']
                        }
                        if resp['content'] == '/print_utxo':
                            username = _actual['chat']['username']
                            keys = []
                            for user in User.query.filter_by(username=username).all():
                                keys.append(user.filename)
                            resp['keys'] = keys

                        for _node in Node.query.order_by(Node.public_key).all():
                            _host = f'http://{_node.host}/updates'
                            requests.post(_host, json=resp)
                    _last_update = max((t['message_id'] for t in actual))
                _, updates = get_current_update()
        except KeyboardInterrupt:
            return
