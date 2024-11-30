from flask import Blueprint

media_control_bp = Blueprint('media_control', __name__)

from . import routes
