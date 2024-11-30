from flask import Blueprint

scan_bp = Blueprint('scan', __name__)

from . import routes
