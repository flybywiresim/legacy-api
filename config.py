'''
Server contants

This module contains constants to be used across the server.
'''

import os

DEBUG = False

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SQLALCHEMY_DATABASE_URI = 'sqlite:////home/fbw/api/db.sqlite'
SQLALCHEMY_TRACK_MODIFICATIONS = False
