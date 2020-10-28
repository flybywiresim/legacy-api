DEBUG = False

import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:////home/fbw/api/db.sqlite'
SQLALCHEMY_TRACK_MODIFICATIONS = False

JOBS = [
    {
        'id': 'cleanup_telex',
        'func' : 'api.telex.routes:cleanup_telex',
        'trigger' : 'interval',
        'seconds' : 360
    }
]
