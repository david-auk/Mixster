from flask import Blueprint

play_bp = Blueprint('play', __name__)

from . import routes
