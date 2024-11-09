from flask import Flask
from .auth import auth_bp
from .export import export_bp
from .play import play_bp
from .config import Config
import os


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = os.urandom(24)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix = '/auth')
    app.register_blueprint(export_bp, url_prefix = '/export')
    app.register_blueprint(play_bp, url_prefix = '/play')

    return app
