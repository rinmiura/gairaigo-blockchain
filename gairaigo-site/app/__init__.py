import os.path
from threading import Thread

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


app = Flask(__name__)

path_to_workdir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(path_to_workdir, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

path_to_last_messenger_update = os.path.join(path_to_workdir, 'last_messenger_update')

API_TOKEN = '<your token>'


def get_url(method, **options):
    options = '&'.join((f'{key}={value}' for key, value in options.items()))
    return f'https://api.telegram.org/bot{API_TOKEN}/{method}?{options}'


from app import routes, models
from app.updates import spray


Thread(target=spray).start()


with app.app_context():
    db.create_all()
