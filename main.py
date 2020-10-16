import urllib3
from flask import Flask
from flask import request
from flask.ext.cache import Cache

app = Flask(__name__)
# cache = Cache(app,config={'CACHE_TYPE': 'simple'})

@app.route("/")
def index():
    return "Welcome to the FlyByWire Simulations API v1.0"

@app.route("/metar")
def mreq():
    http = urllib3.PoolManager()
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'no-cache'
    }

    if request.args and 'icao' in request.args and 'source' in request.args:
        icao = request.args.get('icao').upper()
        source = request.args.get('source').lower()
    else:
        return ('FBW_ERROR: Provide source and ICAO arguments.', 200, headers)
    
    if source == 'vatsim':
        result = fetch_vatsim()
        if rresult == '':
            return ("FBW_ERROR: ICAO not found.", 200, headers)
        else:
            return (result, 200, headers) 
    elif source == 'ms':
        try:
           metar = fetch_ms()[0]
        except:
           return ("FBW_ERROR: ICAO not found.", 200, headers)
        return (metar, 200, headers)
    else:
        return ('FBW_ERROR: Provide a valid METAR source.', 200, headers)

# @cache.cached(timeout=240, key_prefix='msblob')
def fetch_ms_blob():
    r = http.request('GET', 'https://fsxweatherstorage.blob.core.windows.net/fsxweather/metars.bin')
    return r.data.decode("utf-8").splitlines()

# @cache.memoize(timeout=120, key_prefix='ms')
def fetch_ms(icao):
    lines = fetch_ms()
    return [i for i in lines if icao in i[0:4]]

# @cache.memoize(timeout=120, key_prefix='vatsim')
def fetch_vatsim(icao):
    endpoint = 'http://metar.vatsim.net/metar.php?id=' + icao
    r = http.request('GET', endpoint)
    return r.data
    
if __name__ == "__main__":
    app.run(host='0.0.0.0')
