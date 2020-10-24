DEBUG = False

import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:////home/fbw/api/db.sqlite'
SQLALCHEMY_TRACK_MODIFICATIONS = False