from .rsa import verify_signature


def verify_transactions(block, chain):
    authenticate = True
    for transaction in block.data[1:]:
        for _input in transaction['Input']:
            authenticate = authenticate and verify_signature(_input)

            if authenticate:
                authorize = False
                for _block in chain:

                    if _input['timestamp'] == _block.timestamp:

                        for _transaction in _block.data:
                            for output in _transaction['Output']:

                                authorize = authorize or (output['address'] == _input['address'] and
                                                          output['amount'] == _input['amount'])

                if authorize:
                    for _block in chain:
                        for _transaction in _block.data:
                            for __tx_input in _transaction['Input']:
                                if __tx_input == _input:
                                    return False
                else:
                    return False
            else:
                return False
    return True
