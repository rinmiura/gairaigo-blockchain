from app import db


class Node(db.Model):

    public_key = db.Column(db.String(310), primary_key=True)
    host = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return '<Node {}>'.format(self.host)


class User(db.Model):

    id = db.Column(db.Integer, primary_key=True, index=True)
    username = db.Column(db.String(310))
    filename = db.Column(db.String(20))

    def __repr__(self):
        return '<User {}: {}>'.format(self.username, self.filename)
