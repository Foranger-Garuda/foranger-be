from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
import os
from .services import claude_service, weather_service

main_bp = Blueprint("main", __name__)

@main_bp.route("/", methods=["GET"])
def index():
    return jsonify({"message": "API is working!"})

@main_bp.route("/claude/chat", methods=["POST"])
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
def analyze_soil():
    """Analyze soil image to determine soil type"""
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
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
        
        # Get optional parameters
        data = request.form.to_dict()
        model = data.get('model', 'claude-3-5-sonnet-20241022') 
        max_tokens = int(data.get('max_tokens', 800))
        
        # Analyze soil image
        result = claude_service.analyze_soil_image(filepath, model, max_tokens)
        
        # Clean up uploaded file
        os.remove(filepath)
        
        if result['success']:
            return jsonify({
                "soil_analysis": result['soil_analysis'],
                "usage": result['usage']
            })
        else:
            return jsonify({"error": result['error']}), 500
            
    except Exception as e:
        # Clean up file if it exists
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({"error": f"Processing error: {str(e)}"}), 500

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
