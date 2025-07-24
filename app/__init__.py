from flask import Flask
from app.extensions import db
from app.routes import main_bp
from models import *  # import all models so db.create_all works

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)
    app.register_blueprint(main_bp)

    # with app.app_context():
    #     db.create_all()  # Optional: auto-create tables on startup

    return app
