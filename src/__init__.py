import logging
import os

from dotenv import load_dotenv
from flask import Flask

from src.services import initialize_extensions

load_dotenv()

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'),
        template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
    )

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s]: %(message)s',
    )

    initialize_extensions(app)

    from src.routes import register_routes
    register_routes(app)

    return app
