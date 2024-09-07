import logging
import os

from flask import Flask

from extensions import initialize_extensions
from itinerary_routes import register_itinerary_routes


def create_app():
    print("creat_app 0")
    app = Flask(__name__)
    print("creat_app 1")
    configure_app(app)
    print("creat_app 2")
    setup_logging(app)
    print("creat_app 3")
    initialize_extensions(app)
    print("creat_app 4")
    register_itinerary_routes(app)
    print("creat_app 5")

    return app


def configure_app(app):
    """Configure the Flask application."""
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    # Add additional configuration settings here if needed


def setup_logging(app):
    """Setup logging for the application."""
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s:%(message)s')


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
