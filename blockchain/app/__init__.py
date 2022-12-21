from app.blockchain import Blockchain, config


def run(host, port):
    config['API_TOKEN'] = '5835970149:AAEfSM17wQ3jDmhwQQ3JVLspwbDBCzEVJoo'
    config['PROXY_URL'] = 'http://192.168.0.102:5000'

    chain = Blockchain((host, port))

    chain.servey()
