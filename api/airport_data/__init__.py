'''
Airport Data Module

This module provides data about airports, such as
D-ATIS, METAR and TAF.
'''

from flask import Blueprint

airport_data = Blueprint("airport_data", __name__)

import api.airport_data.routes
