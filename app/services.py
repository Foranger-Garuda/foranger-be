import anthropic
import requests
import base64
from flask import current_app

class ClaudeService:
    def __init__(self):
        self.client = None
    
    def _get_client(self):
        if not self.client:
            api_key = current_app.config.get('CLAUDE_API_KEY')
            if not api_key:
                raise ValueError("CLAUDE_API_KEY not configured")
            self.client = anthropic.Anthropic(
                api_key=api_key
            )
        return self.client
    
    def chat(self, message, model="claude-3-5-sonnet-20241022", max_tokens=1000):
        try:
            client = self._get_client()
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": message}
                ]
            )
            return {
                "success": True,
                "response": response.content[0].text,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def analyze_soil_image(self, image_path, model="claude-3-5-sonnet-20241022", max_tokens=800):
        try:
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode()
            
            # Determine image format
            image_format = "image/jpeg"
            if image_path.lower().endswith('.png'):
                image_format = "image/png"
            elif image_path.lower().endswith('.webp'):
                image_format = "image/webp"
            
            # Indonesian soil types for context
            indonesian_soil_types = """
            Common Indonesian soil types:
            1. Alluvial (Tanah Aluvial) - river valleys, coastal plains
            2. Latosol (Tanah Latosol) - tropical weathered, high in iron/aluminum
            3. Podzolik (Tanah Podzolik) - acidic, low fertility
            4. Regosol (Tanah Regosol) - sandy, volcanic origin
            5. Andosol (Tanah Andosol) - volcanic ash soil
            6. Grumosol (Tanah Grumosol) - clay soil, swells when wet
            7. Organosol (Tanah Organik) - peat soil, high organic matter
            8. Renzina (Tanah Renzina) - limestone-derived soil
            """
            
            prompt = f"""
            Analyze this soil image and identify the soil type common in Indonesia. 
            
            {indonesian_soil_types}
            
            Based on the image, please:
            1. Identify the most likely Indonesian soil type from the list above
            2. Describe the soil characteristics you observe (color, texture, structure)
            3. Assess soil fertility indicators
            4. Note any drainage characteristics
            5. Provide confidence level (high/medium/low) for your identification
            
            Format your response as:
            SOIL_TYPE: [Indonesian soil type name]
            CHARACTERISTICS: [description]
            FERTILITY: [assessment]
            DRAINAGE: [assessment]
            CONFIDENCE: [level]
            """
            
            client = self._get_client()
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user", 
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": image_format,
                                    "data": image_data
                                }
                            }
                        ]
                    }
                ]
            )
            
            return {
                "success": True,
                "soil_analysis": response.content[0].text,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _summarize_hourly_forecast(self, hourly_forecast):
        """Summarize next 48h for key weather events (rain, temp extremes, wind)."""
        if not hourly_forecast:
            return "No hourly forecast available."
        import datetime
        rain_events = []
        high_temp = float('-inf')
        low_temp = float('inf')
        high_wind = float('-inf')
        for h in hourly_forecast[:48]:
            dt = datetime.datetime.fromtimestamp(h['datetime']).strftime('%Y-%m-%d %H:%M')
            temp = h['temperature']
            wind = h['wind_speed']
            rain = h.get('rain_1h', 0)
            if rain and rain > 1:
                rain_events.append(f"{dt}: Heavy rain ({rain}mm/h)")
            if temp > high_temp:
                high_temp = temp
            if temp < low_temp:
                low_temp = temp
            if wind > high_wind:
                high_wind = wind
        summary = f"Next 48h: Temp {low_temp:.1f}°C to {high_temp:.1f}°C, max wind {high_wind:.1f} m/s."
        if rain_events:
            summary += "\nRain events: " + "; ".join(rain_events[:3])
        return summary

    def get_crop_recommendations(self, weather_data, soil_data=None, model="claude-3-5-sonnet-20241022", max_tokens=2000):
        try:
            if not weather_data["success"]:
                return {"success": False, "error": "Weather data unavailable"}
            soil_section = ""
            if soil_data and soil_data.get("success"):
                soil_section = f"""
            \nSoil Analysis:\n{soil_data['soil_analysis']}\n"""
            # Format forecast data for the prompt
            forecast_section = ""
            if weather_data.get('daily_forecast') and len(weather_data['daily_forecast']) > 0:
                forecast_section = "\n\n7-Day Weather Forecast:\n"
                for i, day in enumerate(weather_data['daily_forecast'][:7]):
                    from datetime import datetime
                    date_str = datetime.fromtimestamp(day['date']).strftime('%Y-%m-%d')
                    forecast_section += f"Day {i+1} ({date_str}): {day['temperature']['min']:.1f}°C - {day['temperature']['max']:.1f}°C, {day['weather']}, Rain prob: {day['pop']:.0f}%\n"
            # Format hourly summary
            hourly_section = ""
            if weather_data.get('hourly_forecast'):
                hourly_section = "\n\nNext 48h Hourly Highlights:\n" + self._summarize_hourly_forecast(weather_data['hourly_forecast'])
            # Format alerts if any
            alerts_section = ""
            if weather_data.get('alerts') and len(weather_data['alerts']) > 0:
                alerts_section = "\n\nWeather Alerts:\n"
                for alert in weather_data['alerts']:
                    alerts_section += f"- {alert['event']}: {alert['description'][:100]}...\n"
            # Historical weather summary
            historical_section = ""
            if weather_data.get('location'):
                from .services import weather_service
                lat = weather_data['location']['lat']
                lon = weather_data['location']['lon']
                historical_section = "\n\nHistorical Weather (same week, past 3 years):\n" + weather_service.get_historical_weather_summary(lat, lon, years=3)
            prompt = f"""
            Based on the following comprehensive weather data{' and soil analysis' if soil_data else ''}, please provide detailed crop planting recommendations for Indonesia:

            Location: {weather_data['location']['name']}, {weather_data['location']['country']}
            Coordinates: {weather_data['location']['lat']}, {weather_data['location']['lon']}
            Timezone: {weather_data.get('timezone', 'UTC')}

            Current Weather Conditions:
            - Temperature: {weather_data['current']['temperature']:.1f}°C (feels like {weather_data['current']['feels_like']:.1f}°C)
            - Humidity: {weather_data['current']['humidity']}%
            - Pressure: {weather_data['current']['pressure']} hPa
            - Weather: {weather_data['current']['weather']} ({weather_data['current']['weather_main']})
            - Wind Speed: {weather_data['current']['wind_speed']} m/s
            - UV Index: {weather_data['current']['uv_index']}
            - Cloud Coverage: {weather_data['current']['clouds']}%
            - Visibility: {weather_data['current']['visibility']:.1f} km{f"- Recent Rain: {weather_data['current'].get('rain_1h', 0)} mm/h" if weather_data['current'].get('rain_1h') else ""}{forecast_section}{hourly_section}{alerts_section}{historical_section}{soil_section}

            Please provide comprehensive recommendations including:
            1. **Recommended Crops**: Best crops to plant now considering current season, weather patterns{', and soil compatibility' if soil_data else ''}
            2. **Planting Strategy**: \n   - Optimal planting timing based on weather forecast\n   - Pre-planting soil preparation{' considering soil type' if soil_data else ''}\n   - Seed selection and treatment recommendations
            3. **Weather-Based Care**:\n   - Irrigation schedule based on rainfall forecast and humidity\n   - Protection measures for extreme weather (if alerts present)\n   - UV protection strategies if needed
            4. **Growing Timeline**: Expected planting-to-harvest timeline with key milestones
            5. **Risk Assessment**: \n   - Weather-related risks from forecast\n   - Mitigation strategies\n   - Alternative crop options if conditions deteriorate
            6. **Fertilization & Care**:\n   - NPK requirements{' based on soil analysis' if soil_data else ''}\n   - Organic matter recommendations\n   - Pest and disease prevention in current conditions
            7. **Harvest Planning**: Expected yield and harvest timing based on weather patterns

            Focus specifically on crops suitable for Indonesian climate and commonly grown by local farmers. Consider tropical/subtropical conditions, monsoon patterns, and local agricultural practices.
            """
            client = self._get_client()
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            result = {
                "success": True,
                "recommendations": response.content[0].text,
                "location": weather_data['location'],
                "weather_summary": weather_data['current'],
                "forecast_summary": weather_data.get('daily_forecast', [])[:3],  # Include 3-day forecast in response
                "alerts": weather_data.get('alerts', []),
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            }
            if soil_data and soil_data.get("success"):
                result["soil_analysis"] = soil_data['soil_analysis']
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

class WeatherService:
    def __init__(self):
        self.base_url = "https://api.openweathermap.org"
        # Multiple IP geolocation services for better reliability
        self.ip_services = [
            {
                "url": "http://ip-api.com/json",
                "parser": self._parse_ip_api
            },
            {
                "url": "https://ipapi.co/json/",
                "parser": self._parse_ipapi_co
            },
            {
                "url": "https://freegeoip.app/json/",
                "parser": self._parse_freegeoip
            }
        ]
    
    def _parse_ip_api(self, data):
        """Parse ip-api.com response"""
        if data.get('status') == 'success':
            return {
                "success": True,
                "lat": data['lat'],
                "lon": data['lon'],
                "city": data.get('city', 'Unknown'),
                "country": data.get('country', 'Unknown'),
                "region": data.get('regionName', 'Unknown')
            }
        return None
    
    def _parse_ipapi_co(self, data):
        """Parse ipapi.co response"""
        if 'latitude' in data and 'longitude' in data:
            return {
                "success": True,
                "lat": data['latitude'],
                "lon": data['longitude'],
                "city": data.get('city', 'Unknown'),
                "country": data.get('country_name', 'Unknown'),
                "region": data.get('region', 'Unknown')
            }
        return None
    
    def _parse_freegeoip(self, data):
        """Parse freegeoip.app response"""
        if 'latitude' in data and 'longitude' in data:
            return {
                "success": True,
                "lat": data['latitude'],
                "lon": data['longitude'],
                "city": data.get('city', 'Unknown'),
                "country": data.get('country_name', 'Unknown'),
                "region": data.get('region_name', 'Unknown')
            }
        return None
    
    def get_client_ip(self, request):
        """Extract real client IP from request headers"""
        # Check various headers that might contain the real IP
        ip_headers = [
            'X-Forwarded-For',
            'X-Real-IP',
            'X-Client-IP',
            'CF-Connecting-IP',  # Cloudflare
            'HTTP_X_FORWARDED_FOR',
            'HTTP_X_REAL_IP'
        ]
        
        for header in ip_headers:
            ip = request.headers.get(header)
            if ip:
                # Handle comma-separated IPs (take the first one)
                if ',' in ip:
                    ip = ip.split(',')[0].strip()
                # Basic validation
                if self._is_valid_ip(ip):
                    return ip
        
        # Fallback to remote_addr
        return request.remote_addr
    
    def _is_valid_ip(self, ip):
        """Basic IP validation"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                if not 0 <= int(part) <= 255:
                    return False
            # Exclude private/local IPs for geolocation
            if ip.startswith(('127.', '10.', '192.168.')) or ip.startswith('172.'):
                if int(ip.split('.')[1]) in range(16, 32):  # 172.16-31.x.x
                    return False
            return True
        except:
            return False
    
    def get_user_location(self, user_ip=None):
        """Get user location with multiple fallback services"""
        # Try each IP geolocation service
        for service in self.ip_services:
            try:
                if user_ip:
                    url = f"{service['url']}/{user_ip}" if 'ip-api.com' in service['url'] else service['url']
                    params = {} if 'ip-api.com' in service['url'] else {'ip': user_ip}
                else:
                    url = service['url']
                    params = {}
                
                response = requests.get(url, params=params, timeout=5)
                response.raise_for_status()
                data = response.json()
                
                result = service['parser'](data)
                if result:
                    return result
                    
            except Exception as e:
                print(f"IP service {service['url']} failed: {str(e)}")
                continue
        
        # If all services fail, return default coordinates (you can customize this)
        return {
            "success": False,
            "error": "Unable to determine location from IP",
            "fallback_suggestion": "Please provide coordinates manually"
        }
    
    def _get_api_key(self):
        """Get OpenWeather API key from config"""
        from flask import current_app
        api_key = current_app.config.get('OPENWEATHER_API_KEY')
        if not api_key:
            raise ValueError("OPENWEATHER_API_KEY not configured")
        return api_key

    def _get_location_name(self, lat, lon):
        """Get location name using OpenWeather Geocoding API"""
        try:
            api_key = self._get_api_key()
            params = {
                'lat': lat,
                'lon': lon,
                'limit': 1,
                'appid': api_key
            }
            
            response = requests.get(f"{self.base_url}/geo/1.0/reverse", params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if data:
                location = data[0]
                name_parts = []
                if location.get('name'):
                    name_parts.append(location['name'])
                if location.get('state'):
                    name_parts.append(location['state'])
                if location.get('country'):
                    name_parts.append(location['country'])
                
                return {
                    "name": ", ".join(name_parts) if name_parts else f"Location ({lat}, {lon})",
                    "country": location.get('country', 'Unknown'),
                    "state": location.get('state', 'Unknown'),
                    "city": location.get('name', 'Unknown')
                }
        except Exception as e:
            print(f"Geocoding failed: {str(e)}")
        
        return {
            "name": f"Location ({lat}, {lon})",
            "country": "Unknown",
            "state": "Unknown", 
            "city": "Unknown"
        }

    def get_weather_data(self, lat, lon):
        """Get comprehensive weather data using OpenWeather One Call API 3.0"""
        try:
            api_key = self._get_api_key()
            
            # Get location information
            location_info = self._get_location_name(lat, lon)
            
            # One Call API 3.0 parameters
            params = {
                'lat': lat,
                'lon': lon,
                'appid': api_key,
                'units': 'metric',  # Celsius, m/s, etc.
                'exclude': 'minutely',  # Exclude minutely data to reduce response size
            }
            
            response = requests.get(f"{self.base_url}/data/3.0/onecall", params=params, timeout=10)
            response.raise_for_status()
            weather_data = response.json()
            
            # Extract current weather
            current = weather_data['current']
            current_weather = {
                "temperature": current['temp'],
                "feels_like": current['feels_like'],
                "humidity": current['humidity'],
                "pressure": current['pressure'],
                "uv_index": current.get('uvi', 0),
                "visibility": current.get('visibility', 0) / 1000,  # Convert to km
                "wind_speed": current['wind_speed'],
                "wind_direction": current.get('wind_deg', 0),
                "weather": current['weather'][0]['description'],
                "weather_main": current['weather'][0]['main'],
                "clouds": current['clouds'],
                "sunrise": current['sunrise'],
                "sunset": current['sunset']
            }
            
            # Add optional weather data
            if 'rain' in current:
                current_weather['rain_1h'] = current['rain'].get('1h', 0)
            if 'snow' in current:
                current_weather['snow_1h'] = current['snow'].get('1h', 0)
            
            # Extract daily forecast (7 days)
            daily_forecast = []
            for day in weather_data.get('daily', [])[:7]:
                daily_forecast.append({
                    "date": day['dt'],
                    "temperature": {
                        "min": day['temp']['min'],
                        "max": day['temp']['max'],
                        "morning": day['temp']['morn'],
                        "day": day['temp']['day'],
                        "evening": day['temp']['eve'],
                        "night": day['temp']['night']
                    },
                    "humidity": day['humidity'],
                    "pressure": day['pressure'],
                    "wind_speed": day['wind_speed'],
                    "weather": day['weather'][0]['description'],
                    "weather_main": day['weather'][0]['main'],
                    "clouds": day['clouds'],
                    "uv_index": day.get('uvi', 0),
                    "pop": day.get('pop', 0) * 100,  # Probability of precipitation as percentage
                    "rain": day.get('rain', 0),
                    "snow": day.get('snow', 0)
                })
            
            # Extract hourly forecast (48 hours)
            hourly_forecast = []
            for hour in weather_data.get('hourly', [])[:48]:
                hourly_data = {
                    "datetime": hour['dt'],
                    "temperature": hour['temp'],
                    "feels_like": hour['feels_like'],
                    "humidity": hour['humidity'],
                    "pressure": hour['pressure'],
                    "wind_speed": hour['wind_speed'],
                    "wind_direction": hour.get('wind_deg', 0),
                    "weather": hour['weather'][0]['description'],
                    "weather_main": hour['weather'][0]['main'],
                    "clouds": hour['clouds'],
                    "pop": hour.get('pop', 0) * 100  # Probability of precipitation as percentage
                }
                
                if 'rain' in hour:
                    hourly_data['rain_1h'] = hour['rain'].get('1h', 0)
                if 'snow' in hour:
                    hourly_data['snow_1h'] = hour['snow'].get('1h', 0)
                    
                hourly_forecast.append(hourly_data)
            
            # Extract weather alerts if any
            alerts = []
            for alert in weather_data.get('alerts', []):
                alerts.append({
                    "sender": alert.get('sender_name', 'Unknown'),
                    "event": alert.get('event', 'Weather Alert'),
                    "description": alert.get('description', ''),
                    "start": alert.get('start', 0),
                    "end": alert.get('end', 0),
                    "tags": alert.get('tags', [])
                })
            
            return {
                "success": True,
                "location": {
                    "name": location_info["name"],
                    "country": location_info["country"],
                    "state": location_info["state"],
                    "city": location_info["city"],
                    "lat": lat,
                    "lon": lon
                },
                "current": current_weather,
                "daily_forecast": daily_forecast,
                "hourly_forecast": hourly_forecast,
                "alerts": alerts,
                "timezone": weather_data.get('timezone', 'UTC'),
                "timezone_offset": weather_data.get('timezone_offset', 0)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_historical_weather_summary(self, lat, lon, years=3):
        """Fetch and summarize historical weather for the same week in previous years using One Call API 3.0 (paid)."""
        import time, datetime
        api_key = self._get_api_key()
        base_url = f"{self.base_url}/data/3.0/onecall/timemachine"
        now = datetime.datetime.utcnow()
        summaries = []
        for y in range(1, years+1):
            dt = int((now - datetime.timedelta(days=365*y)).replace(hour=12, minute=0, second=0, microsecond=0).timestamp())
            params = {
                'lat': lat,
                'lon': lon,
                'dt': dt,
                'appid': api_key,
                'units': 'metric',
            }
            try:
                resp = requests.get(base_url, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                temp = data['data'][0]['temp'] if 'data' in data and data['data'] else None
                weather = data['data'][0]['weather'][0]['description'] if 'data' in data and data['data'] else None
                rain = data['data'][0].get('rain', {}).get('1h', 0) if 'data' in data and data['data'] else 0
                summaries.append({
                    'year': now.year - y,
                    'temp': temp,
                    'weather': weather,
                    'rain': rain
                })
            except Exception as e:
                summaries.append({'year': now.year - y, 'error': str(e)})
        # Summarize
        summary_lines = []
        for s in summaries:
            if 'error' in s:
                summary_lines.append(f"{s['year']}: Data unavailable ({s['error']})")
            else:
                summary_lines.append(f"{s['year']}: {s['weather']}, {s['temp']}°C, rain: {s['rain']}mm")
        return '\n'.join(summary_lines)

claude_service = ClaudeService()
weather_service = WeatherService()