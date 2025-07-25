from flask import Flask
from flask_migrate import Migrate
from app.extensions import db, jwt
from app.routes import main_bp
from models import *
from app.services.auth_service import is_token_revoked
from flask_cors import CORS
from flask import send_from_directory
import os

# Always use the same uploads directory relative to this file
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    jwt.init_app(app)

    # Enable CORS
    CORS(app, supports_credentials=True)

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        return is_token_revoked(jwt_payload)
    
    # Serve uploaded files
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(UPLOAD_FOLDER, filename)

    # Register blueprints
    app.register_blueprint(main_bp) 

    return app