"""
flask application factory
configure cors and blueprints
initialize components
register routes
"""

import sys
from pathlib import Path
from flask import Flask
from flask_cors import CORS

# add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# ================ APP CREATION ================

def create_app(config_name="development"):
    # create flask app instance
    app = Flask(__name__)

    # load configuration from config class
    from backend.configuration.config import config
    app.config.from_object(config[config_name])

    # setup cors for api routes
    CORS(
        app,
        resources={
            r"/api/*": {"origins": app.config["CORS_ORIGINS"]},
            r"/search": {"origins": app.config["CORS_ORIGINS"]},
        },
    )

    # disable html caching to avoid stale js links
    @app.after_request
    def _no_cache_html(response):
        # disable browser cache for html
        content_type = response.headers.get("Content-Type", "")
        if content_type.startswith("text/html"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    # initialize all components
    from .components import init_components
    app.components = init_components(app)

    # register all blueprints
    from .routes import main_bp, search_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(search_bp)

    # return configured app
    return app