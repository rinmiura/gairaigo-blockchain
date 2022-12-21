import json
import os.path
from io import StringIO

from app import app, db, get_url
from app.models import Node, User
from flask import request
import requests


_dispatched_docs = {}
_dispatched_msgs = []


@app.route('/sendtoBot', methods=['GET', 'POST'])
def send_to_bot():
    global _dispatched_docs
    __out_message_id = request.values.get('msg_id')

    chat_id = request.values.get('chat_id')
    if 'filename' in request.values:
        if __out_message_id not in _dispatched_docs:
            _dispatched_docs[__out_message_id] = 0
        if _dispatched_docs[__out_message_id] > 1:
            return ''

        filename = request.values.get('filename')
        content = request.values.get('content')

        file = StringIO(content)
        file.name = filename
        files = {'document': file}
        data = {'chat_id': chat_id}
        requests.post(get_url('sendDocument'), data=data, files=files)
        if _dispatched_docs[__out_message_id] == 1:
            user = User(username=request.values.get('username'), filename=filename)
            db.session.add(user)
            db.session.commit()
            db.session.flush()
            file.close()
        _dispatched_docs[__out_message_id] += 1
    else:
        if int(__out_message_id) in _dispatched_msgs:
            return ''

        text = request.values.get('text')
        requests.get(get_url('sendMessage', chat_id=chat_id, text=text))
        _dispatched_msgs.append(int(__out_message_id))

    return ''


@app.route('/updateNodes', methods=['GET', 'POST'])
def update_nodes():
    if request.method == 'POST':
        node = Node(**request.values)
        db.session.merge(node)
        db.session.commit()
        db.session.flush()
    data = []
    for _node in Node.query.order_by(Node.public_key).all():
        data.append({
            'public_key': _node.public_key,
            'host': _node.host
        })
    return json.dumps(data)


@app.route('/downloadChain')
def download_chain():
    if os.path.exists('blockchain.json'):
        with open('blockchain.json') as chain:
            return chain.read()
    return ''


@app.route('/updateChain', methods=['GET', 'POST'])
def update_chain():
    file = request.files.get('document')
    with open('blockchain.json', 'w') as chain:
        chain.write(file.stream.read().decode())
    return ''
