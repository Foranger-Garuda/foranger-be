from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
import os
from app.services.claude_service import ClaudeService
from app.services.weather_service import WeatherService
claude_service = ClaudeService()
weather_service = WeatherService()
from app.services.auth_service import login_user, register_user, refresh_access_token, logout_token, is_token_revoked
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from models.soil_type_reference import SoilTypeReference
from app.extensions import db
from models.soil_analyses import SoilAnalysis

main_bp = Blueprint("main", __name__)

@main_bp.route("/", methods=["GET"])
def index():
    return jsonify({"message": "API is working!"})

@main_bp.route("/claude/chat", methods=["POST"])
@jwt_required()
def claude_chat():
    data = request.get_json()
    
    if not data or 'message' not in data:
        return jsonify({"error": "Message is required"}), 400
    
    message = data['message']
    model = data.get('model', 'claude-3-5-sonnet-20241022')
    max_tokens = data.get('max_tokens', 1000)
    
    result = claude_service.chat(message, model, max_tokens)
    
    if result['success']:
        return jsonify({
            "response": result['response'],
            "usage": result['usage']
        })
    else:
        return jsonify({"error": result['error']}), 500

@main_bp.route("/location/detect", methods=["GET"])
def detect_location():
    """Endpoint to test location detection"""
    user_ip = weather_service.get_client_ip(request)
    location_data = weather_service.get_user_location(user_ip)
    
    return jsonify({
        "detected_ip": user_ip,
        "location": location_data
    })

@main_bp.route("/soil/analyze", methods=["POST"])
@jwt_required()
def analyze_soil():
    """Analyze soil image and return characteristics only (no DB save)"""
    user_id = get_jwt_identity()
    if not user_id:
        return jsonify({"error": "User authentication required."}), 401
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No image file selected"}), 400
    allowed_extensions = {'png', 'jpg', 'jpeg', 'webp'}
    if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
        return jsonify({"error": "Invalid file type. Allowed: PNG, JPG, JPEG, WEBP"}), 400
    try:
        upload_dir = os.path.join(os.getcwd(), 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        filename = secure_filename(file.filename)
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        data = request.form.to_dict()
        model = data.get('model', 'claude-3-5-sonnet-20241022') 
        max_tokens = int(data.get('max_tokens', 800))
        result = claude_service.analyze_soil_image(filepath, model, max_tokens)
        os.remove(filepath)
        if not result['success']:
            return jsonify({"error": result['error']}), 500
        import re
        allowed_soils = [
            "Alluvial Soil", "Andosol Soil", "Regosol Soil", "Latosol Soil", "Podzolic Soil", "Grumosol Soil",
            "Organosol Soil", "Lithosol Soil", "Mediterranean Soil", "Rendzina Soil", "Laterite Soil", "Gleysol Soil"
        ]
        def extract_field(field, text):
            m = re.search(rf"{field}:\s*(.*)", text)
            return m.group(1).strip() if m else None
        detected_soil_type = extract_field("SOIL_TYPE", result['soil_analysis'])
        if not detected_soil_type:
            return jsonify({"error": "Could not extract soil type from analysis."}), 400
        matched_soil_type = None
        for allowed in allowed_soils:
            if detected_soil_type.lower() == allowed.lower():
                matched_soil_type = allowed
                break
        if not matched_soil_type:
            return jsonify({"error": f"Detected soil type '{detected_soil_type}' is not supported.", "supported_soil_types": allowed_soils}), 400
        soil_type_ref = SoilTypeReference.query.filter_by(soil_type_name=matched_soil_type).first()
        soil_type_ref_dict = soil_type_ref.to_dict() if soil_type_ref else None
        # Parse other fields
        soil_color = extract_field("SOIL_COLOR", result['soil_analysis'])
        soil_texture = extract_field("SOIL_TEXTURE", result['soil_analysis'])
        soil_drainage = extract_field("SOIL_DRAINAGE", result['soil_analysis'])
        soil_location_type = extract_field("SOIL_LOCATION_TYPE", result['soil_analysis'])
        soil_fertility = extract_field("SOIL_FERTILITY", result['soil_analysis'])
        soil_moisture = extract_field("SOIL_MOISTURE", result['soil_analysis'])
        classification_confidence = extract_field("CONFIDENCE", result['soil_analysis'])
        classification_method = extract_field("CLASSIFICATION_METHOD", result['soil_analysis'])
        return jsonify({
            "soil_analysis": result['soil_analysis'],
            "usage": result['usage'],
            "detected_soil_type": matched_soil_type,
            "soil_type_reference": soil_type_ref_dict,
            "characteristics": {
                "soil_color": soil_color,
                "soil_texture": soil_texture,
                "soil_drainage": soil_drainage,
                "soil_location_type": soil_location_type,
                "soil_fertility": soil_fertility,
                "soil_moisture": soil_moisture,
                "classified_soil_type": matched_soil_type,
                "classification_confidence": classification_confidence,
                "classification_method": classification_method
            }
        })
    except Exception as e:
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({"error": f"Processing error: {str(e)}"}), 500

@main_bp.route("/soil/submit", methods=["POST"])
@jwt_required()
def submit_soil_analysis():
    """Save user-edited soil analysis to the database, retrieve weather data, and return crop recommendations"""
    user_id = get_jwt_identity()
    if not user_id:
        return jsonify({"error": "User authentication required."}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    # Required fields from soil analysis
    required_fields = [
        "classified_soil_type", "soil_color", "soil_texture", "soil_drainage", "soil_location_type",
        "soil_fertility", "soil_moisture"
    ]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Optional fields
    classification_confidence = data.get("classification_confidence")
    classification_method = data.get("classification_method")

    # Auto-generate soil_analysis summary string
    soil_analysis = (
        f"SOIL_TYPE: {data['classified_soil_type']}\n"
        f"SOIL_COLOR: {data['soil_color']}\n"
        f"SOIL_TEXTURE: {data['soil_texture']}\n"
        f"SOIL_DRAINAGE: {data['soil_drainage']}\n"
        f"SOIL_LOCATION_TYPE: {data['soil_location_type']}\n"
        f"SOIL_FERTILITY: {data['soil_fertility']}\n"
        f"SOIL_MOISTURE: {data['soil_moisture']}\n"
        f"CONFIDENCE: {classification_confidence if classification_confidence is not None else ''}\n"
        f"CLASSIFICATION_METHOD: {classification_method if classification_method is not None else ''}"
    )

    # Get coordinates
    lat = data.get("lat")
    lon = data.get("lon")
    if lat is not None and lon is not None:
        try:
            lat = float(lat)
            lon = float(lon)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid latitude or longitude format"}), 400
    else:
        user_ip = weather_service.get_client_ip(request)
        location_data = weather_service.get_user_location(user_ip)
        if location_data.get('success'):
            lat = location_data['lat']
            lon = location_data['lon']
        else:
            return jsonify({
                "error": "Cannot detect location automatically",
                "details": {
                    "detected_ip": user_ip,
                    "ip_location_error": location_data.get('error', 'Unknown error'),
                    "suggestion": "Please provide coordinates manually in the request body"
                }
            }), 400

    # Validate soil type
    allowed_soils = [
        "Alluvial Soil", "Andosol Soil", "Regosol Soil", "Latosol Soil", "Podzolic Soil", "Grumosol Soil",
        "Organosol Soil", "Lithosol Soil", "Mediterranean Soil", "Rendzina Soil", "Laterite Soil", "Gleysol Soil"
    ]
    matched_soil_type = None
    for allowed in allowed_soils:
        if data["classified_soil_type"] and data["classified_soil_type"].lower() == allowed.lower():
            matched_soil_type = allowed
            break
    if not matched_soil_type:
        return jsonify({"error": f"Soil type '{data['classified_soil_type']}' is not supported.", "supported_soil_types": allowed_soils}), 400
    soil_type_ref = SoilTypeReference.query.filter_by(soil_type_name=matched_soil_type).first()
    soil_type_ref_id = soil_type_ref.id if soil_type_ref else None

    # Step 1: Save soil analysis to DB
    soil_analysis_obj = SoilAnalysis(
        user_id=user_id,
        soil_type_reference_id=soil_type_ref_id,
        soil_color=data["soil_color"],
        soil_texture=data["soil_texture"],
        soil_drainage=data["soil_drainage"],
        soil_location_type=data["soil_location_type"],
        soil_fertility=data["soil_fertility"],
        soil_moisture=data["soil_moisture"],
        classified_soil_type=matched_soil_type,
        classification_confidence=classification_confidence,
        classification_method=classification_method,
        latitude=lat,
        longitude=lon,
        ip_address=request.remote_addr,
        soil_analysis=soil_analysis
    )
    db.session.add(soil_analysis_obj)
    db.session.commit()

    # Step 2: Get weather data
    weather_data = weather_service.get_weather_data(lat, lon)
    if not weather_data['success']:
        return jsonify({"error": f"Weather data error: {weather_data['error']}"}), 500

    # Step 3: Get crop recommendations
    model = data.get('model', 'claude-3-5-sonnet-20241022')
    max_tokens = int(data.get('max_tokens', 1500))
    crop_result = claude_service.get_crop_recommendations(weather_data, {"success": True, "soil_analysis": data["soil_analysis"]}, model, max_tokens)
    if crop_result['success']:
        return jsonify({
            "soil_analysis_record": {
                "id": str(soil_analysis_obj.id),
                "user_id": str(soil_analysis_obj.user_id),
                "classified_soil_type": soil_analysis_obj.classified_soil_type,
                "created_at": soil_analysis_obj.created_at.isoformat() if soil_analysis_obj.created_at else None
            },
            "recommendations": crop_result['recommendations'],
            "location": crop_result['location'],
            "weather_summary": crop_result['weather_summary'],
            "usage": crop_result['usage'],
            "coordinates_used": {
                "lat": lat,
                "lon": lon,
                "source": "manual" if ("lat" in data and "lon" in data) else "ip_detection"
            }
        })
    else:
        return jsonify({"error": crop_result['error']}), 500

@main_bp.route("/crops/recommend", methods=["POST", "GET"])
def get_crop_recommendations():
    # Get data from request
    data = request.get_json() if request.method == "POST" else {}
    if not data:
        data = {}
    
    lat = None
    lon = None
    
    # Priority 1: Check if coordinates are provided in request
    if 'lat' in data and 'lon' in data:
        try:
            lat = float(data['lat'])
            lon = float(data['lon'])
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid latitude or longitude format"}), 400
    
    # Priority 2: Try to get location from IP if no coordinates provided
    if lat is None or lon is None:
        user_ip = weather_service.get_client_ip(request)
        location_data = weather_service.get_user_location(user_ip)
        
        if location_data.get('success'):
            lat = location_data['lat']
            lon = location_data['lon']
        else:
            # Return error with helpful information
            return jsonify({
                "error": "Cannot detect location automatically",
                "details": {
                    "detected_ip": user_ip,
                    "ip_location_error": location_data.get('error', 'Unknown error'),
                    "suggestion": "Please provide coordinates manually"
                },
                "usage": {
                    "manual_coordinates": "POST with: {\"lat\": your_latitude, \"lon\": your_longitude}",
                    "example": {
                        "lat": -6.2088,
                        "lon": 106.8456,
                        "description": "Jakarta, Indonesia coordinates"
                    }
                }
            }), 400
    
    # Get weather data
    weather_data = weather_service.get_weather_data(lat, lon)
    
    if not weather_data['success']:
        return jsonify({"error": f"Weather data error: {weather_data['error']}"}), 500
    
    # Check if soil analysis is provided
    soil_data = None
    if 'soil_analysis' in data:
        soil_data = {"success": True, "soil_analysis": data['soil_analysis']}
    
    # Get crop recommendations from Claude
    model = data.get('model', 'claude-3-5-sonnet-20241022')
    max_tokens = data.get('max_tokens', 1500)
    
    result = claude_service.get_crop_recommendations(weather_data, soil_data, model, max_tokens)
    
    if result['success']:
        response_data = {
            "recommendations": result['recommendations'],
            "location": result['location'],
            "weather_summary": result['weather_summary'],
            "usage": result['usage'],
            "coordinates_used": {
                "lat": lat,
                "lon": lon,
                "source": "manual" if ('lat' in data and 'lon' in data) else "ip_detection"
            }
        }
        
        if 'soil_analysis' in result:
            response_data['soil_analysis'] = result['soil_analysis']
            
        return jsonify(response_data)
    else:
        return jsonify({"error": result['error']}), 500

@main_bp.route("/crops/recommend-with-soil", methods=["POST"])
def get_crop_recommendations_with_soil():
    """Complete workflow: analyze soil image + get crop recommendations"""
    if 'image' not in request.files:
        return jsonify({"error": "No soil image file provided"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No image file selected"}), 400
    
    # Validate file type
    allowed_extensions = {'png', 'jpg', 'jpeg', 'webp'}
    if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
        return jsonify({"error": "Invalid file type. Allowed: PNG, JPG, JPEG, WEBP"}), 400
    
    try:
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(os.getcwd(), 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        
        # Get form data
        form_data = request.form.to_dict()
        
        # Get coordinates
        lat = None
        lon = None
        
        if 'lat' in form_data and 'lon' in form_data:
            try:
                lat = float(form_data['lat'])
                lon = float(form_data['lon'])
            except (ValueError, TypeError):
                os.remove(filepath)
                return jsonify({"error": "Invalid latitude or longitude format"}), 400
        
        # Try to get location from IP if no coordinates provided
        if lat is None or lon is None:
            user_ip = weather_service.get_client_ip(request)
            location_data = weather_service.get_user_location(user_ip)
            
            if location_data.get('success'):
                lat = location_data['lat']
                lon = location_data['lon']
            else:
                os.remove(filepath)
                return jsonify({
                    "error": "Cannot detect location automatically",
                    "details": {
                        "detected_ip": user_ip,
                        "ip_location_error": location_data.get('error', 'Unknown error'),
                        "suggestion": "Please provide coordinates manually in form data"
                    }
                }), 400
        
        # Get optional parameters
        model = form_data.get('model', 'claude-3-5-sonnet-20241022')
        max_tokens = int(form_data.get('max_tokens', 1500))
        
        # Step 1: Analyze soil image
        soil_result = claude_service.analyze_soil_image(filepath, model, 800)
        
        # Clean up uploaded file
        os.remove(filepath)
        
        if not soil_result['success']:
            return jsonify({"error": f"Soil analysis failed: {soil_result['error']}"}), 500
        
        # Step 2: Get weather data
        weather_data = weather_service.get_weather_data(lat, lon)
        
        if not weather_data['success']:
            return jsonify({"error": f"Weather data error: {weather_data['error']}"}), 500
        
        # Step 3: Get crop recommendations with soil data
        crop_result = claude_service.get_crop_recommendations(weather_data, soil_result, model, max_tokens)
        
        if crop_result['success']:
            return jsonify({
                "recommendations": crop_result['recommendations'],
                "location": crop_result['location'],
                "weather_summary": crop_result['weather_summary'],
                "soil_analysis": crop_result['soil_analysis'],
                "usage": {
                    "soil_analysis_tokens": soil_result['usage'],
                    "recommendations_tokens": crop_result['usage']
                },
                "coordinates_used": {
                    "lat": lat,
                    "lon": lon,
                    "source": "manual" if ('lat' in form_data and 'lon' in form_data) else "ip_detection"
                }
            })
        else:
            return jsonify({"error": crop_result['error']}), 500
            
    except Exception as e:
        # Clean up file if it exists
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({"error": f"Processing error: {str(e)}"}), 500

@main_bp.route("/crops/recommend-with-soil-file", methods=["POST"])
def get_crop_recommendations_with_soil_file():
    """
    Use a soil image already stored on the server (in the image/ directory) for crop recommendation.
    Expects JSON: { "filename": "sawah-kering-di-manggeng-raya.jpg", "lat": ..., "lon": ... }
    """
    data = request.get_json()
    filename = data.get("filename")
    if not filename:
        return jsonify({"error": "No filename provided"}), 400

    image_path = os.path.join(os.getcwd(), "image", filename)
    if not os.path.exists(image_path):
        return jsonify({"error": f"File not found: {filename}"}), 404

    # Get coordinates
    lat = data.get("lat")
    lon = data.get("lon")
    if lat is None or lon is None:
        # Try to get from IP (reuse your existing logic)
        user_ip = weather_service.get_client_ip(request)
        location_data = weather_service.get_user_location(user_ip)
        if location_data.get('success'):
            lat = location_data['lat']
            lon = location_data['lon']
        else:
            return jsonify({"error": "Cannot detect location automatically"}), 400

    # Get optional parameters
    model = data.get('model', 'claude-3-5-sonnet-20241022')
    max_tokens = int(data.get('max_tokens', 1500))

    # Step 1: Analyze soil image
    soil_result = claude_service.analyze_soil_image(image_path, model, 800)
    if not soil_result['success']:
        return jsonify({"error": f"Soil analysis failed: {soil_result['error']}"}), 500

    # Step 2: Get weather data
    weather_data = weather_service.get_weather_data(lat, lon)
    if not weather_data['success']:
        return jsonify({"error": f"Weather data error: {weather_data['error']}"}), 500

    # Step 3: Get crop recommendations with soil data
    crop_result = claude_service.get_crop_recommendations(weather_data, soil_result, model, max_tokens)
    if crop_result['success']:
        return jsonify({
            "recommendations": crop_result['recommendations'],
            "location": crop_result['location'],
            "weather_summary": crop_result['weather_summary'],
            "soil_analysis": crop_result['soil_analysis'],
            "usage": {
                "soil_analysis_tokens": soil_result['usage'],
                "recommendations_tokens": crop_result['usage']
            },
            "coordinates_used": {
                "lat": lat,
                "lon": lon,
                "source": "manual" if ('lat' in data and 'lon' in data) else "ip_detection"
            }
        })
    else:
        return jsonify({"error": crop_result['error']}), 500
    
@main_bp.route('/authentication/login', methods=['POST'])
def login_user_route():
    data = request.get_json(silent=True)  
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Email and password are required"}), 400

    result = login_user(data)
    
    if result.get('status') == 200:
        return jsonify(result), 200
    else:
        return jsonify({"error": result['message']}), result['status']
    
@main_bp.route('/authentication/register', methods=['POST'])
def register_user_route():
    data = request.get_json(silent=True)  
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Email and password are required"}), 400

    result = register_user(data)
    
    if result.get('status') == 201:
        return jsonify(result), 201
    else:
        return jsonify({"error": result['message']}), result['status']

@main_bp.route('/authentication/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token_route():
    identity = get_jwt_identity()
    new_access_token = refresh_access_token(identity)
    if new_access_token:
        return jsonify({"access_token": new_access_token}), 200
    else:
        return jsonify({"error": "User not found"}), 404

@main_bp.route('/authentication/logout', methods=['POST'])
@jwt_required()
def logout_route():
    jti = get_jwt()["jti"]
    logout_token(jti)
    return jsonify({"msg": "Successfully logged out"}), 200

@main_bp.route("/soil-type-reference/add", methods=["POST"])
@jwt_required()
def add_soil_type_reference():
    claims = get_jwt()
    if not claims.get("is_admin", False):
        return jsonify({"error": "Admin privileges required."}), 403

    data = request.get_json()
    required_fields = ["soil_type_name"]
    for field in required_fields:
        if not data or field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    try:
        soil_type = SoilTypeReference(
            soil_type_name=data["soil_type_name"],
            local_name=data.get("local_name"),
            description=data.get("description"),
            characteristics=data.get("characteristics"),
            common_locations=data.get("common_locations"),
            suitable_crops=data.get("suitable_crops"),
            management_tips=data.get("management_tips")
        )
        db.session.add(soil_type)
        db.session.commit()
        return jsonify({"soil_type_reference": soil_type.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

