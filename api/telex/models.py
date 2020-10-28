import datetime
from api import db, ma

class TxCxn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flight = db.Column(db.String(24))
    ip_addr = db.Column(db.String(46))
    latlong = db.Column(db.String(50))
    last_contact = db.Column(db.DateTime, server_default=db.func.now(), server_onupdate=db.func.now())

    def __init__(self, flight, ip_addr, latlong, last_contact=datetime.datetime.now()):
        self.flight = flight
        self.ip_addr = ip_addr
        self.latlong = latlong
        self.last_contact = last_contact

class TxCxnSchema(ma.Schema):
    class Meta:
        fields = ('id', 'flight', 'latlong', 'last_contact')

class TxMsg(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    m_to = db.Column(db.String(24))
    m_from = db.Column(db.String(24))
    message = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

    def __init__(self, m_to, m_from, message):
        self.m_to = m_to
        self.m_from = m_from
        self.message = message

class TxMsgSchema(ma.Schema):
    class Meta:
        fields = ('id', 'm_to', 'm_from', 'message', 'timestamp')

TxCxn_schema = TxCxnSchema()
TxCxns_schema = TxCxnSchema(many=True)
TxMsg_schema = TxMsgSchema()
TxMsgs_schema = TxMsgSchema(many=True)
