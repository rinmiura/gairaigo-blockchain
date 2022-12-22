from app.blockchain import Blockchain, config


def run(host, port):
    config['API_TOKEN'] = '<your token>'
    config['PROXY_URL'] = '<your proxy host>'

    chain = Blockchain((host, port))

    chain.servey()
