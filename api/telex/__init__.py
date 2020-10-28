'''
Telex Module

This module provides a mechanism to send Telex messages.
'''

from flask import Blueprint

telex = Blueprint("telex", __name__)

import api.telex.models
import api.telex.routes
