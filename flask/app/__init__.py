from flask import Flask
from .auth import auth_bp
from .export import export_bp
from .play import play_bp
from .config import Config
import os
from celery import Celery, Task


def make_celery(app: Flask) -> Celery:
    class ContextTask(Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.import_name, task_cls=ContextTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app


def create_app():
    app = Flask(__name__)
    app.config.from_mapping(
        CELERY=dict(
            broker_url="redis://redis:6379/0",
            result_backend="redis://redis:6379/0",
        ),
    )
    app.config.from_prefixed_env()
    app.config.from_object(Config)
    app.secret_key = os.urandom(24)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(export_bp, url_prefix='/export')
    app.register_blueprint(play_bp, url_prefix='/play')

    return app


# Create the Flask app and initialize Celery
flask_app = create_app()
celery_app = make_celery(flask_app)