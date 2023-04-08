from socket import getfqdn, gethostbyname

from app.core import Blockchain


def run(port):

    chain = Blockchain((gethostbyname(getfqdn()), port))

    chain.servey()
