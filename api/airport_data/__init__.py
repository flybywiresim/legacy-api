from flask import Blueprint

airport_data = Blueprint("airport_data", __name__)

import api.airport_data.routes