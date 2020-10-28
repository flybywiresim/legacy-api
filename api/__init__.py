import urllib3
from flask import Flask
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from utilities import Utilities
from apscheduler.schedulers.background import BackgroundScheduler
from api.telex.routes import cleanup_telex

render = Utilities.render
http = urllib3.PoolManager()
cache = Cache(config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': './api_cache'
})
db = SQLAlchemy()
ma = Marshmallow()

FBW_WELCOME_MSG = "FlyByWire Simulations API v1.0"

def create_app():
    app = Flask(__name__)
    app.config.from_pyfile("../config.py")

    cache.init_app(app)
    db.init_app(app)
    ma.init_app(app)

    from api.airport_data import airport_data
    app.register_blueprint(airport_data)

    from api.telex import telex
    app.register_blueprint(telex)
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=cleanup_telex, trigger="interval", seconds=360)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())

    @app.route("/")
    def index():
        return render(FBW_WELCOME_MSG)

    return app
