"""
App factory. Building the app with a function (instead of one global `app`
at import time) is what lets pytest spin up a fresh app with its own
temporary database for every test run.
"""
import os

from flask import Flask


def create_app(test_config=None):
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"),
        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "static"),
    )

    from .config import Config
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    from . import models
    models.init_app(app)

    from .auth import bp as auth_bp
    from .main import bp as main_bp
    from .admin import bp as admin_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)

    from . import scoring
    app.jinja_env.globals["learn_url"] = scoring.learn_url
    app.jinja_env.globals["level_name"] = scoring.LEVEL_NAMES.get

    from .errors import register_error_handlers
    register_error_handlers(app)

    return app
