from flask import Flask
from flask_migrate import Migrate
from app.extensions import db, jwt
from app.routes import main_bp
from models import *

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    jwt.init_app(app)
    
    # Register blueprints
    app.register_blueprint(main_bp) 

    return app