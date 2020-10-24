import json
from flask import jsonify
from flask import request
from xml.etree import ElementTree
from api import http
from api import cache
from api.airport_data import airport_data
from utilities import Utilities

###############################
########## CONSTANTS ##########
###############################

CACHE_TIMEOUT = 240
MEMOIZE_TIMEOUT = 120
FBW_INVALID_ARGS = 'FBW_ERROR: Provide source and ICAO arguments'
FBW_INVALID_ICAO = 'FBW_ERROR: ICAO not found'
FBW_INVALID_SRC = 'FBW_ERROR: Invalid source'
FBW_NO_DATIS = 'FBW_ERROR: D-ATIS not available at this airport'
FBW_NO_TAF = 'FBW_ERROR: TAF not available at this airport'

AVIATIONWEATHER_TAF_URL = 'https://www.aviationweather.gov/adds/dataserver_current/httpparam?dataSource=tafs&requestType=retrieve&format=xml&stationString=%s&hoursBeforeNow=0'
IVAO_TAF_URL = 'http://wx.ivao.aero/taf.php'

render = Utilities.render

#########################################
########## FLASK API ENDPOINTS ##########
#########################################

@airport_data.route("/metar")
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
        metar = fetch_ivao_metar(icao)
    elif source == 'pilotedge':
        metar = fetch_pilotedge(icao)
    else:
        return render(FBW_INVALID_SRC)
    
    if metar:
        return render(metar)
    else:
        return render(FBW_INVALID_ICAO)

@airport_data.route("/atis")
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
        if 'arr' in atis:
            atis['arr'] = atis['arr'].upper()
        if 'dep' in atis:
            atis['dep'] = atis['dep'].upper()
        if 'combined' in atis:
            atis['combined'] = atis['combined'].upper()

        return render(jsonify(atis))
    else:
        return render(FBW_NO_DATIS)

@airport_data.route("/taf")
def taf():
    if request.args and 'icao' in request.args and 'source' in request.args:
        icao = request.args.get('icao').upper()
        source = request.args.get('source').lower()
    else:
        return render(FBW_INVALID_ARGS)

    if source == "aviationweather":
        taf = fetch_aviationweather_taf(icao)
    elif source == "ivao":
        taf = fetch_ivao_taf(icao)
    else:
        return render(FBW_INVALID_SRC)

    if taf:
        return render(taf)
    else:
        return render(FBW_NO_TAF)
    
#########################################
########### UTILITY FUNCTIONS ###########
#########################################

@cache.cached(timeout=CACHE_TIMEOUT, key_prefix='msblob')
def fetch_ms_blob():
    r = http.request('GET', 'https://fsxweatherstorage.blob.core.windows.net/fsxweather/metars.bin')
    return r.data.decode("utf-8").splitlines()

@cache.cached(timeout=CACHE_TIMEOUT, key_prefix='vatblob')
def fetch_vatsim_blob():
    r = http.request('GET', 'http://cluster.data.vatsim.net/vatsim-data.json')
    return json.loads(r.data.decode('utf-8'))

@cache.cached(timeout=CACHE_TIMEOUT, key_prefix='ivaometarblob')
def fetch_ivao_metar_blob():
    r = http.request('GET', 'http://wx.ivao.aero/metar.php')
    return r.data.decode("utf-8").splitlines()

@cache.cached(timeout=CACHE_TIMEOUT, key_prefix='ivaotafblob')
def fetch_ivao_taf_blob():
    r = http.request('GET', IVAO_TAF_URL)
    return r.data.decode("ISO-8859-1").splitlines()

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
def fetch_ivao_metar(icao):
    lines = fetch_ivao_metar_blob()
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

@cache.memoize(timeout=MEMOIZE_TIMEOUT)
def fetch_aviationweather_taf(icao):
    r = http.request('GET', (AVIATIONWEATHER_TAF_URL % icao))
    d = ElementTree.fromstring((r.data.decode('utf-8')))
    if not d.find('data').find("TAF").find("raw_text").text:
       return None
    taf = d.find('data').find("TAF").find("raw_text").text
    return taf

@cache.memoize(timeout=MEMOIZE_TIMEOUT)
def fetch_ivao_taf(icao):
    lines = fetch_ivao_taf_blob()
    result = [i for i in lines if icao in i[0:4]]
    return result[0] if result else None