from datetime import datetime, timezone
from app.extensions import db
from models.users import User
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt, get_jwt_identity
from flask_jwt_extended import jwt_required
from flask import current_app
from models.blacklisted_token import BlacklistedToken

# In-memory blacklist for demonstration (use persistent storage in production)
JWT_BLACKLIST = set()

def create_tokens(user):
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"is_admin": user.is_admin}
    )
    refresh_token = create_refresh_token(identity=str(user.id))
    return access_token, refresh_token

def refresh_access_token(identity):
    user = User.query.get(identity)
    if not user:
        return None
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"is_admin": user.is_admin}
    )
    return access_token

def logout_token(jti):
    # Add the token's jti to the database blacklist
    if not BlacklistedToken.query.filter_by(jti=jti).first():
        blacklisted = BlacklistedToken(jti=jti)
        db.session.add(blacklisted)
        db.session.commit()
    return True

def is_token_revoked(jwt_payload):
    jti = jwt_payload["jti"]
    return BlacklistedToken.query.filter_by(jti=jti).first() is not None

def login_user(data):
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return {
            'message': 'Email and password are required.',
            'status': 400
        }

    user = User.query.filter_by(email=email).first()

    if user is None or not check_password_hash(user.password_hash, password):
        return {
            'message': 'Invalid email or password.',
            'status': 401
        }

    if not user.is_active:
        return {'message': 'Account is inactive.', 'status': 403}

    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()

    # Create JWT token with is_admin claim
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "is_admin": user.is_admin
        }
    )

    user_info = {
        'id': str(user.id),
        'email': user.email,
        'full_name': user.full_name,
        'province': user.province,
        'city': user.city,
        'last_login_at': user.last_login_at.isoformat(),
        'is_admin': user.is_admin
    }

    return {
        'message': 'Login successful', 
        'user': user_info, 
        'access_token': access_token,
        'status': 200
    }

def register_user(data):
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('full_name')
    province = data.get('province')
    city = data.get('city')

    if not email or not password:
        return {
            'message': 'Email and password are required.',
            'status': 400
        }

    if User.query.filter_by(email=email).first():
        return {
            'message': 'Email already exists.',
            'status': 409
        }

    new_user = User(
        email=email,
        full_name=full_name,
        password_hash=generate_password_hash(password),  
        province=province,
        city=city
    )

    db.session.add(new_user)
    db.session.commit()

    return {
        'message': 'User registered successfully',
        'user_id': str(new_user.id),
        'status': 201
    }

