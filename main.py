from flask import Flask
import urllib3
import httplib2
app = Flask(__name__)

@app.route("/")
def index():
    return "Welcome to the FlyByWire Simulations API v1.0"

@app.route("/metar")
def mreq():
    request_json = request.get_json()
    http = urllib3.PoolManager()
    headers = {
        'Access-Control-Allow-Origin': '*'
    }

    if request.args and 'icao' in request.args and 'source' in request.args:
        icao = request.args.get('icao').upper()
        source = request.args.get('source').lower()
    elif request.json and 'icao' in request_json and 'source' in request_json:
        icao = request_json['icao'].upper()
        source = request_json['source'].lower()
    else:
        return ('FBW_ERROR: Provide source and ICAO arguments.', 200, headers)
    
    if source == 'vatsim':
        endpoint = 'http://metar.vatsim.net/metar.php?id=' + icao
        r = http.request('GET', endpoint)
        if r.data == '':
            return ("FBW_ERROR: ICAO not found.", 200, headers)
        else:
            return (r.data, 200, headers) 
    elif source == 'ms':
        endpoint = 'https://fsxweatherstorage.blob.core.windows.net/fsxweather/metars.bin'
        r = http.request('GET', endpoint)
        lines = r.data.decode("utf-8").splitlines()
        result = [i for i in lines if icao in i[0:4]]
        try:
           metar = result[0]
        except:
           return ("FBW_ERROR: ICAO not found.", 200, headers)
        return (metar, 200, headers)
    else:
        return ('FBW_ERROR: Provide a valid METAR source.', 200, headers)

if __name__ == "__main__":
    app.run(host='0.0.0.0')
