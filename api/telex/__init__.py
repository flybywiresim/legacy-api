from flask import Blueprint

telex = Blueprint("telex", __name__)

import api.telex.models
import api.telex.routes