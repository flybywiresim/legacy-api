'''
Airport Data Routes

The routes within this file provide information about airports,
such as D-ATIS, METAR and TAF.
'''

import json
from xml.etree import ElementTree
from flask import jsonify, request
from api import cache, http
from api.airport_data import airport_data
from utilities import render

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
MSFS_METAR_URL = 'https://fsxweatherstorage.blob.core.windows.net/fsxweather/metars.bin'

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

    metar_data = None
    if source == 'vatsim':
        metar_data = fetch_vatsim_metar(icao)
    elif source == 'ms':
        metar_data = fetch_ms_metar(icao)
    elif source == 'ivao':
        metar_data = fetch_ivao_metar(icao)
    elif source == 'pilotedge':
        metar_data = fetch_pilotedge_metar(icao)
    else:
        return render(FBW_INVALID_SRC)

    if metar_data:
        return render(metar_data)

    return render(FBW_INVALID_ICAO)

@airport_data.route("/atis")
def atis():
    if request.args and 'icao' in request.args and 'source' in request.args:
        icao = request.args.get('icao').upper()
        source = request.args.get('source').lower()
    else:
        return render(FBW_INVALID_ARGS)

    atis_data = None
    if source == 'faa':
        atis_data = fetch_faa_atis(icao)
    elif source == 'vatsim':
        atis_data = fetch_vatsim_atis(icao)
    elif source == 'ivao':
        atis_data = fetch_ivao_atis(icao)
    elif source == 'pilotedge':
        atis_data = fetch_pilotedge_atis(icao)
    else:
        return render(jsonify({"error": "invalid src"}))

    if atis_data:
        return render(jsonify(atis_data))

    return render(jsonify({"error": "atis not avail"}))

@airport_data.route("/taf")
def taf():
    if request.args and 'icao' in request.args and 'source' in request.args:
        icao = request.args.get('icao').upper()
        source = request.args.get('source').lower()
    else:
        return render(FBW_INVALID_ARGS)

    taf_data = None
    if source == "aviationweather":
        taf_data = fetch_aviationweather_taf(icao)
    elif source == "ivao":
        taf_data = fetch_ivao_taf(icao)
    else:
        return render(FBW_INVALID_SRC)

    if taf_data:
        return render(taf_data)

    return render(FBW_NO_TAF)

#########################################
########### UTILITY FUNCTIONS ###########
#########################################

@cache.cached(timeout=CACHE_TIMEOUT, key_prefix='msblob')
def fetch_ms_blob():
    '''
    Method for retriving Microsoft Flight Simulator metar data

    Returns:
        metars(list):A list of METARs for all airports
    '''

    response = http.request('GET', MSFS_METAR_URL)
    return response.data.decode("utf-8").splitlines()

@cache.cached(timeout=CACHE_TIMEOUT, key_prefix='vatblob')
def fetch_vatsim_blob():
    '''
    Method for retriving all active clients on VATSIM network

    Returns:
        clients(list):A list of all clients currently active on VATSIM
    '''

    response = http.request('GET', 'http://cluster.data.vatsim.net/vatsim-data.json')
    data = json.loads(response.data.decode('utf-8'))
    return data.get('clients', [])

@cache.cached(timeout=CACHE_TIMEOUT, key_prefix='ivaometarblob')
def fetch_ivao_metar_blob():
    '''
    Method for retriving metars from IVAO

    Returns:
        metars(list):A list of metars from IVAO
    '''

    response = http.request('GET', 'http://wx.ivao.aero/metar.php')
    return response.data.decode("utf-8").splitlines()

@cache.cached(timeout=CACHE_TIMEOUT, key_prefix='ivaotafblob')
def fetch_ivao_taf_blob():
    '''
    Method for retriving TAFs from IVAO

    Returns:
        TAF(list):A list of TAFs from IVAO
    '''

    response = http.request('GET', IVAO_TAF_URL)
    return response.data.decode("ISO-8859-1").splitlines()

@cache.cached(timeout=CACHE_TIMEOUT, key_prefix='ivaowhazzupblob')
def fetch_ivao_whazzup_blob():
    '''
    Method for retriving all active clients on IVAO network

    Returns:
        clients(list):A list of all clients currently active on IVAO
    '''

    response = http.request('GET', 'https://api.ivao.aero/getdata/whazzup/whazzup.txt')
    return response.data.decode("ISO-8859-1").splitlines()

@cache.memoize(timeout=MEMOIZE_TIMEOUT)
def fetch_ms_metar(icao):
    '''
    Retrieve the METAR for an airport from Microsoft Flight Simulator.

    Parameters:
        icao (string):The airport ICAO code

    Returns:
        metar(string):The METAR for the desired airport or "None" if not found
    '''

    lines = fetch_ms_blob()
    result = [i for i in lines if icao in i[0:4]]
    return result[0] if result else None

@cache.memoize(timeout=MEMOIZE_TIMEOUT)
def fetch_vatsim_metar(icao):
    '''
    Retrieve the METAR for an airport from VATSIM.

    Parameters:
        icao (string):The airport ICAO code

    Returns:
        metar(string):The METAR for the desired airport or "None" if not found
    '''

    response = http.request('GET', 'http://metar.vatsim.net/metar.php?id=' + icao)
    return response.data

@cache.memoize(timeout=MEMOIZE_TIMEOUT)
def fetch_ivao_metar(icao):
    '''
    Retrieve the METAR for an airport from IVAO.

    Parameters:
        icao (string):The airport ICAO code

    Returns:
        metar(string):The METAR for the desired airport or "None" if not found
    '''

    lines = fetch_ivao_metar_blob()
    result = [i for i in lines if icao in i[0:4]]
    return result[0] if result else None

@cache.memoize(timeout=MEMOIZE_TIMEOUT)
def fetch_pilotedge_metar(icao):
    '''
    Retrieve the METAR for an airport from pilotedge.

    Parameters:
        icao (string):The airport ICAO code

    Returns:
        metar(string):The METAR for the desired airport or "None" if not found
    '''

    response = http.request('GET', 'https://www.pilotedge.net/atis/' + icao + '.json')
    if len(response.data) < 3:
        return None
    data = json.loads(response.data.decode('utf-8'))
    return data['metar']

@cache.memoize(timeout=MEMOIZE_TIMEOUT)
def fetch_faa_atis(icao):
    '''
    Retrieve the D-ATIS for an airport from the FAA.

    Parameters:
        icao (string):The airport ICAO code

    Returns:
        atis(object):The D-ATIS for the desired airport or "None" if not found
    '''

    response = http.request('GET', 'https://datis.clowd.io/api/' + icao)
    data = json.loads(response.data.decode('utf-8'))
    if 'error' in data:
        return None
    atis_data = {}
    for airport in data:
        if airport['type'] == 'arr':
            atis_data['arr'] = airport['datis']
        elif airport['type'] == 'dep':
            atis_data['dep'] = airport['datis']
        else:
            atis_data['combined'] = airport['datis']
    return atis_data

@cache.memoize(timeout=MEMOIZE_TIMEOUT)
def fetch_vatsim_atis(icao):
    '''
    Retrieve the D-ATIS for an airport from VATSIM.

    Parameters:
        icao (string):The airport ICAO code

    Returns:
        atis(object):The D-ATIS for the desired airport or "None" if not found
    '''

    clients = fetch_vatsim_blob()
    target = icao + '_ATIS'
    atis_data = [i for i in clients if i['callsign'] == target and i['atis_message'] is not None]
    return {"combined": atis_data[0]['atis_message'].replace('^§', ' ')} if atis_data else None

@cache.memoize(timeout=MEMOIZE_TIMEOUT)
def fetch_ivao_atis(icao):
    '''
    Retrieve the D-ATIS for an airport from IVAO.

    Parameters:
        icao (string):The airport ICAO code

    Returns:
        atis(object):The D-ATIS for the desired airport or "None" if not found
    '''

    lines = fetch_ivao_whazzup_blob()
    print(lines)
    target = icao + '_TWR'
    result = [i for i in lines if target in i[0:8]]
    if not result:
        return None
    atis_data = result[0].split(':')[35]
    if len(atis_data) < 3:
        return None
    atis_tmp = atis_data.split('^§')[1:]
    atis_msg = ' '.join(atis_tmp)
    return {"combined": atis_msg}

@cache.memoize(timeout=MEMOIZE_TIMEOUT)
def fetch_pilotedge_atis(icao):
    '''
    Retrieve the D-ATIS for an airport from pilotedge.

    Parameters:
        icao (string):The airport ICAO code

    Returns:
        atis(object):The D-ATIS for the desired airport or "None" if not found
    '''

    response = http.request('GET', 'https://www.pilotedge.net/atis/' + icao + '.json')
    if len(response.data) < 3:
        return None
    data = json.loads(response.data.decode('utf-8'))
    return {"combined": data['text'].replace('\n\n', ' ')}

@cache.memoize(timeout=MEMOIZE_TIMEOUT)
def fetch_aviationweather_taf(icao):
    '''
    Retrieve the TAF for an airport from Aviation Weather.

    Parameters:
        icao (string):The airport ICAO code

    Returns:
        taf(string):The TAF for the desired airport or "None" if not found
    '''

    response = http.request('GET', (AVIATIONWEATHER_TAF_URL % icao))
    data = ElementTree.fromstring((response.data.decode('utf-8')))
    if not data.find('data').find("TAF").find("raw_text").text:
        return None
    taf_data = data.find('data').find("TAF").find("raw_text").text
    return taf_data

@cache.memoize(timeout=MEMOIZE_TIMEOUT)
def fetch_ivao_taf(icao):
    '''
    Retrieve the TAF for an airport from IVAO.

    Parameters:
        icao (string):The airport ICAO code

    Returns:
        taf(string):The TAF for the desired airport or "None" if not found
    '''

    lines = fetch_ivao_taf_blob()
    result = [i for i in lines if icao in i[0:4]]
    return result[0] if result else None
