import re
import atexit
import datetime
from flask import jsonify
from flask import request
from apscheduler.schedulers.background import BackgroundScheduler
from flask_apscheduler import APScheduler
from utilities import Utilities
from api.telex.models import TxCxn, TxMsg
from api.telex.models import TxCxn_schema, TxCxns_schema, TxMsg_schema, TxMsgs_schema
from api import db
from api.telex import telex

###############################
########## CONSTANTS ##########
###############################

render = Utilities.render

def cleanup_telex():
    with db.app.app_context():
        cutoff = datetime.datetime.now() - datetime.timedelta(minutes=6)
        filtered_txcxns = TxCxn.query.filter(TxCxn.last_contact < cutoff)
        for c in filtered_txcxns:
            filtered_msgs = TxMsg.query.filter(TxMsg.m_to == c.flight)
            for m in filtered_msgs:
                db.session.delete(m)
            db.session.delete(c)
        print("cleanup_telex() has been run")
        db.session.commit()


#######################################
########## TELEX CONNECTIONS ##########
#######################################

@telex.route('/txcxn', methods=['POST'])
def add_txcxn():
    flight = request.args.get('flight')
    latlong = request.args.get('latlong')
    ip_addr = str(request.remote_addr)
    last_contact = datetime.datetime.now()
    # Generate random private key
    private_key = secrets.token_hex(32)

    existing_flight = TxCxn.query.filter_by(flight=flight).first()
    if existing_flight or flight == "":
        return render(jsonify({"error": "flight_in_use"}))

    new_txcxn = TxCxn(flight, ip_addr, latlong, private_key, last_contact)
    db.session.add(new_txcxn)
    db.session.commit()
    # Private schema returns private ID, only on cxn creation
    return render(TxCxn_private_schema.jsonify(new_txcxn))

# Fake PUT request (fuck CORS)
@telex.route('/txcxn/<id>', methods=['POST'])
def update_txcxn(id):
    txcxn = TxCxn.query.get(id)

    latlong = request.args.get('latlong')
    update = request.args.get('update')
    sentkey = request.args.get('key')

    if sentkey != txcxn.private_key or update != "yes":
        return render(jsonify({"error": "invalid_private_key"}))

    txcxn.latlong = latlong
    txcxn.last_contact = datetime.datetime.now()
    db.session.commit()
    return render(TxCxn_schema.jsonify(txcxn))

@telex.route('/txcxn', methods=['GET'])
def get_txcxns():
    all_txcxns = TxCxn.query.all()
    result = TxCxns_schema.dump(all_txcxns)
    return render(jsonify(result))

@telex.route('/txcxn/<id>', methods=['GET'])
def get_txcxn(id):
    txcxn = TxCxn.query.get(id)
    return render(TxCxn_schema.jsonify(txcxn))

####################################
########## TELEX MESSAGES ##########
####################################

@telex.route('/txmsg', methods=['POST'])
def add_txmsg():
    m_to = request.args.get('to')
    m_from = request.args.get('from')
    message = request.args.get('message')
    sentkey = request.args.get('key')
    
    message = re.sub(r'([^A-Z0-9/ +-\.;])+', '', message)
    filtered = re.sub(r'\W+', '', message)
    pattern = re.compile(r'(N(I|1)GG(AH|ER|A|UH|4H|4)(S|Z)?|F(A|4)GG(E|I|O|0|1)TS?|F(A|4)GS?|F(A|4)GGY|B(E|3)(A|4)N(E|3)RS?|SP(I|1)CK?S?|W(E|3)TB(A|4)CKS?|G(O|0)(O|0)KS?|CH(I|1)NK(S|Y)?|SLUTS?|WH(O|0)RES?|TR(A|4)NN(Y|IE)S?)')
    if pattern.match(filtered):
        return render(jsonify({"error": "prohibited_regex_hit"}))
    
    sender_cxn = TxCxn.query.filter_by(flight=m_from).first()
    recipient_cxn = TxCxn.query.filter_by(flight=m_to).first()

    if not recipient_cxn:
        return render(jsonify({"error": "recipient_not_found"}))
    
    if not sender_cxn or sender_cxn.private_key != sentkey:
        return render(jsonify({"error": "sender_permissions_error"}))

    new_txmsg = TxMsg(m_to, m_from, message)
    db.session.add(new_txmsg)
    db.session.commit()
    return render(TxMsg_schema.jsonify(new_txmsg))

# Fake DELETE request (fuck CORS)
@telex.route('/txmsg/<id>', methods=['POST'])
def delete_txmsg(id):
    txmsg = TxMsg.query.get(id)
    sentkey = request.args.get('key')
    deleteThis = request.args.get('delete')
    recipient_cxn = TxCxn.query.filter_by(flight=txmsg.m_to).first()

    if recipient_cxn and recipient_cxn.private_key == sentkey and deleteThis == "yes":
        db.session.delete(txmsg)
        db.session.commit()
        return render(jsonify({"deleted": True}))
    return render(jsonify({"deleted": False}))

@telex.route('/txmsg', methods=['GET'])
def get_txmsgs():
    all_txmsgs = TxMsg.query.all()
    result = TxMsgs_schema.dump(all_txmsgs)
    return render(jsonify(result))

@telex.route('/txmsg/msgto/<id>', methods=['GET'])
def get_filtered_txmsgs(id):
    filtered_txmsgs = TxMsg.query.filter_by(m_to=id)
    result = TxMsgs_schema.dump(filtered_txmsgs)
    return render(jsonify(result))

@telex.route('/txmsg/<id>', methods=['GET'])
def get_txmsg(id):
    txmsg = TxMsg.query.get(id)
    return render(TxMsg_schema.jsonify(txmsg))
