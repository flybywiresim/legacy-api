import os
import re
import json
import atexit
import urllib3
import datetime
import ipaddress
from flask import Flask
from flask import jsonify
from flask import request
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from sqlalchemy_utils import IPAddressType
from apscheduler.schedulers.background import BackgroundScheduler

###############################
########## CONSTANTS ##########
###############################

CACHE_TIMEOUT = 240
MEMOIZE_TIMEOUT = 120
FBW_WELCOME_MSG = "FlyByWire Simulations API v1.0"
FBW_INVALID_ARGS = 'FBW_ERROR: Provide source and ICAO arguments'
FBW_INVALID_ICAO = 'FBW_ERROR: ICAO not found'
FBW_INVALID_SRC = 'FBW_ERROR: Invalid source'
FBW_NO_DATIS = 'FBW_ERROR: D-ATIS not available at this airport'

####################################
########## INITIALIZATION ##########
####################################

app = Flask(__name__)
cache = Cache(app, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': './api_cache'
})
http = urllib3.PoolManager()

def cleanup_telex():
    cutoff = datetime.datetime.now() - datetime.timedelta(minutes=6)
    filtered_txcxns = TxCxn.query.filter(TxCxn.last_contact < cutoff)
    for c in filtered_txcxns:
        filtered_msgs = TxMsg.query.filter(TxMsg.m_to == c.flight)
        for m in filtered_msgs:
            db.session.delete(m)
        db.session.delete(c)
    print("cleanup_telex() has been run")
    db.session.commit()

scheduler = BackgroundScheduler()
scheduler.add_job(func=cleanup_telex, trigger="interval", seconds=360)
scheduler.start()

###################################
########## INITIALIZE DB ##########
###################################

# basedir = os.path.abspath(os.path.dirname(__file__))
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'db.sqlite')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/fbw/api/db.sqlite' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
ma = Marshmallow(app)

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

#######################################
########## TELEX CONNECTIONS ##########
#######################################

@app.route('/txcxn', methods=['POST'])
def add_txcxn():
    flight = request.args.get('flight')
    latlong = request.args.get('latlong')
    ip_addr = str(request.remote_addr)
    last_contact = datetime.datetime.now()

    existing_flight = TxCxn.query.filter_by(flight=flight).first()
    if existing_flight or flight == "":
        return render(jsonify({"error": "flight_in_use"}))

    new_txcxn = TxCxn(flight, ip_addr, latlong, last_contact)
    db.session.add(new_txcxn)
    db.session.commit()
    return render(TxCxn_schema.jsonify(new_txcxn))

# Fake PUT request (fuck CORS)
@app.route('/txcxn/<id>', methods=['POST'])
def update_txcxn(id):
    txcxn = TxCxn.query.get(id)

    latlong = request.args.get('latlong')
    ip_addr = str(request.remote_addr)
    update = request.args.get('update')

    if ip_addr != txcxn.ip_addr or update != "yes":
        return render(jsonify({"error": "ip_address_changed"}))

    txcxn.latlong = latlong
    txcxn.last_contact = datetime.datetime.now()
    db.session.commit()
    return render(TxCxn_schema.jsonify(txcxn))

@app.route('/txcxn', methods=['GET'])
def get_txcxns():
    all_txcxns = TxCxn.query.all()
    result = TxCxns_schema.dump(all_txcxns)
    return render(jsonify(result))

@app.route('/txcxn/<id>', methods=['GET'])
def get_txcxn(id):
    txcxn = TxCxn.query.get(id)
    return render(TxCxn_schema.jsonify(txcxn))

####################################
########## TELEX MESSAGES ##########
####################################

@app.route('/txmsg', methods=['POST'])
def add_txmsg():
    m_to = request.args.get('to')
    m_from = request.args.get('from')
    message = request.args.get('message')

    message = re.sub(r'([^A-Z0-9/ +-\.])+', '', message)
    filtered = re.sub(r'\W+', '', message)
    pattern = re.compile(r'(N(I|1)GG(AH|ER|A|UH|4H|4)(S|Z)?|F(A|4)GG(E|I|O|0|1)TS?|F(A|4)GS?|F(A|4)GGY|B(E|3)(A|4)N(E|3)RS?|SP(I|1)CK?S?|W(E|3)TB(A|4)CKS?|G(O|0)(O|0)KS?|CH(I|1)NK(S|Y)?|SLUTS?|WH(O|0)RES?|TR(A|4)NN(Y|IE)S?)')
    if pattern.match(filtered):
        return render(jsonify({"error": "prohibited_regex_hit"}))
    
    curr_ip_addr = request.remote_addr
    sender_cxn = TxCxn.query.filter_by(flight=m_from).first()
    recipient_cxn = TxCxn.query.filter_by(flight=m_to).first()

    if not recipient_cxn:
        return render(jsonify({"error": "recipient_not_found"}))
    
    if not sender_cxn or sender_cxn.ip_addr != curr_ip_addr:
        return render(jsonify({"error": "sender_permissions_error"}))

    new_txmsg = TxMsg(m_to, m_from, message)
    db.session.add(new_txmsg)
    db.session.commit()
    return render(TxMsg_schema.jsonify(new_txmsg))

# Fake DELETE request (fuck CORS)
@app.route('/txmsg/<id>', methods=['POST'])
def delete_txmsg(id):
    txmsg = TxMsg.query.get(id)
    curr_ip_addr = request.remote_addr
    deleteThis = request.args.get('delete')
    recipient_cxn = TxCxn.query.filter_by(flight=txmsg.m_to).first()

    if recipient_cxn and recipient_cxn.ip_addr == curr_ip_addr and deleteThis == "yes":
        db.session.delete(txmsg)
        db.session.commit()
        return render(jsonify({"deleted": True}))
    return render(jsonify({"deleted": False}))

@app.route('/txmsg', methods=['GET'])
def get_txmsgs():
    all_txmsgs = TxMsg.query.all()
    result = TxMsgs_schema.dump(all_txmsgs)
    return render(jsonify(result))

@app.route('/txmsg/msgto/<id>', methods=['GET'])
def get_filtered_txmsgs(id):
    filtered_txmsgs = TxMsg.query.filter_by(m_to=id)
    result = TxMsgs_schema.dump(filtered_txmsgs)
    return render(jsonify(result))

@app.route('/txmsg/<id>', methods=['GET'])
def get_txmsg(id):
    txmsg = TxMsg.query.get(id)
    return render(TxMsg_schema.jsonify(txmsg))

#########################################
########## FLASK API ENDPOINTS ##########
#########################################

@app.route("/")
def index():
    return render(FBW_WELCOME_MSG)

@app.route("/metar")
def metar():
    if request.args and 'icao' in request.args and 'source' in request.args:
        icao = request.args.get('icao').upper()
        source = request.args.get('source').lower()
    else:
        return render(FBW_INVALID_ARGS)
    
    if source == 'vatsim':
        metar = fetch_vatsim(icao)
    elif source == 'ms':
        metar = fetch_ms(icao)
    elif source == 'ivao':
        metar = fetch_ivao(icao)
    elif source == 'pilotedge':
        metar = fetch_pilotedge(icao)
    else:
        return render(FBW_INVALID_SRC)
    
    if metar:
        return render(metar)
    else:
        return render(FBW_INVALID_ICAO)

@app.route("/atis")
def atis():
    if request.args and 'icao' in request.args and 'source' in request.args:
        icao = request.args.get('icao').upper()
        source = request.args.get('source').lower()
    else:
        return render(FBW_INVALID_ARGS)
    
    if source == 'faa':
        atis = fetch_faa_atis(icao)
    elif source == 'vatsim':
        atis = fetch_vatsim_atis(icao)
    elif source == 'ivao':
        atis = fetch_ivao_atis(icao)
    elif source == 'pilotedge':
        atis = fetch_pilotedge_atis(icao)       
    else:
        return render(FBW_INVALID_SRC)
    
    if atis:
        return render(jsonify(atis))
    else:
        return render(FBW_NO_DATIS)
    
#########################################
########### UTILITY FUNCTIONS ###########
#########################################

def render(output):
    return(output, 200, {
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'no-cache'
    })

@cache.cached(timeout=CACHE_TIMEOUT, key_prefix='msblob')
def fetch_ms_blob():
    r = http.request('GET', 'https://fsxweatherstorage.blob.core.windows.net/fsxweather/metars.bin')
    return r.data.decode("utf-8").splitlines()

@cache.cached(timeout=CACHE_TIMEOUT, key_prefix='vatblob')
def fetch_vatsim_blob():
    r = http.request('GET', 'http://cluster.data.vatsim.net/vatsim-data.json')
    return json.loads(r.data.decode('utf-8'))

@cache.cached(timeout=CACHE_TIMEOUT, key_prefix='ivaoblob')
def fetch_ivao_blob():
    r = http.request('GET', 'http://wx.ivao.aero/metar.php')
    return r.data.decode("utf-8").splitlines()

@cache.cached(timeout=CACHE_TIMEOUT, key_prefix='ivaowhazzupblob')
def fetch_ivao_whazzup_blob():
    r = http.request('GET', 'https://api.ivao.aero/getdata/whazzup/whazzup.txt')
    return r.data.decode("ISO-8859-1").splitlines()

@cache.memoize(timeout=MEMOIZE_TIMEOUT)
def fetch_ms(icao):
    lines = fetch_ms_blob()
    result = [i for i in lines if icao in i[0:4]]
    return result[0] if result else None

@cache.memoize(timeout=MEMOIZE_TIMEOUT)
def fetch_vatsim(icao):
    r = http.request('GET', 'http://metar.vatsim.net/metar.php?id=' + icao)
    return r.data

@cache.memoize(timeout=MEMOIZE_TIMEOUT)
def fetch_ivao(icao):
    lines = fetch_ivao_blob()
    result = [i for i in lines if icao in i[0:4]]
    return result[0] if result else None

@cache.memoize(timeout=MEMOIZE_TIMEOUT)
def fetch_pilotedge(icao):
    r = http.request('GET', 'https://www.pilotedge.net/atis/' + icao + '.json')
    if len(r.data) < 3:
        return None
    d = json.loads(r.data.decode('utf-8'))
    return d['metar']

@cache.memoize(timeout=MEMOIZE_TIMEOUT)
def fetch_faa_atis(icao):
    r = http.request('GET', 'https://datis.clowd.io/api/' + icao)
    d = json.loads(r.data.decode('utf-8'))
    if 'error' in d:
        return None
    atis = {}
    for a in d:
        if a['type'] == 'arr':
            atis['arr'] = a['datis']
        elif a['type'] == 'dep':
            atis['dep'] = a['datis']
        else:
            atis['combined'] = a['datis']
    return atis

@cache.memoize(timeout=MEMOIZE_TIMEOUT)
def fetch_vatsim_atis(icao):
    vdata = fetch_vatsim_blob()
    clients = vdata['clients']
    target = icao + '_ATIS'
    atis = [i for i in clients if i['callsign'] == target and i['atis_message'] is not None]
    return {"combined": atis[0]['atis_message'].replace('^§', ' ')} if atis else None

@cache.memoize(timeout=MEMOIZE_TIMEOUT)
def fetch_ivao_atis(icao):
    lines = fetch_ivao_whazzup_blob()
    print(lines)
    target = icao + '_TWR'
    result = [i for i in lines if target in i[0:8]]
    if not result:
        return None
    atis = result[0].split(':')[35]
    if len(atis) < 3:
        return None
    atis_tmp = atis.split('^§')[1:]
    atis_msg = ' '.join(atis_tmp)
    return {"combined": atis_msg}
    
@cache.memoize(timeout=MEMOIZE_TIMEOUT)
def fetch_pilotedge_atis(icao):
    r = http.request('GET', 'https://www.pilotedge.net/atis/' + icao + '.json')
    if len(r.data) < 3:
        return None
    d = json.loads(r.data.decode('utf-8'))
    return {"combined": d['text'].replace('\n\n', ' ')}

atexit.register(lambda: scheduler.shutdown())
    
if __name__ == "__main__":
    app.run(host='0.0.0.0')
