'''
Telex Routes

The routes within this file provide the ability to send
and recieve Telex messages.
'''

import re
import atexit
import datetime
from flask import jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
from utilities import render
from api.telex.models import TxCxn, TxMsg
from api.telex.models import TxCxn_schema, TxCxns_schema, TxMsg_schema, TxMsgs_schema
from api import db
from api.telex import telex

###############################
########## CONSTANTS ##########
###############################

def cleanup_telex():
    cutoff = datetime.datetime.now() - datetime.timedelta(minutes=6)
    filtered_txcxns = TxCxn.query.filter(TxCxn.last_contact < cutoff)
    for connection in filtered_txcxns:
        filtered_msgs = TxMsg.query.filter(TxMsg.m_to == connection.flight)
        for message in filtered_msgs:
            db.session.delete(message)
        db.session.delete(connection)
    print("cleanup_telex() has been run")
    db.session.commit()

scheduler = BackgroundScheduler()
scheduler.add_job(func=cleanup_telex, trigger="interval", seconds=360)
scheduler.start()

#######################################
########## TELEX CONNECTIONS ##########
#######################################

@telex.route('/txcxn', methods=['POST'])
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
@telex.route('/txcxn/<id>', methods=['POST'])
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

    message = re.sub(r'([^A-Z0-9/ +-\.;])+', '', message)
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
@telex.route('/txmsg/<id>', methods=['POST'])
def delete_txmsg(id):
    txmsg = TxMsg.query.get(id)
    curr_ip_addr = request.remote_addr
    delete_this = request.args.get('delete')
    recipient_cxn = TxCxn.query.filter_by(flight=txmsg.m_to).first()

    if recipient_cxn and recipient_cxn.ip_addr == curr_ip_addr and delete_this == "yes":
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

atexit.register(lambda: scheduler.shutdown())
