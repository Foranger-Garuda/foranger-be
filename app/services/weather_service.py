import requests
from flask import current_app

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