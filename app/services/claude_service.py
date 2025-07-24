import anthropic
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
            
            allowed_soil_types = """
            Only choose the SOIL_TYPE from this list (do not invent new types):
            - Alluvial Soil
            - Andosol Soil
            - Regosol Soil
            - Latosol Soil
            - Podzolic Soil
            - Grumusol Soil
            - Organosol Soil
            - Lithosol Soil
            - Mediterranean Soil
            - Rendzina Soil
            - Laterite Soil
            - Gleysol Soil
            """
            allowed_soil_color = """
            SOIL_COLOR (choose only from):
            - Brown
            - Dark Brown
            - Reddish
            - Yellowish
            - Black
            - Gray
            """
            allowed_soil_texture = """
            SOIL_TEXTURE (choose only from):
            - Sandy
            - Silty
            - Clayey
            - Loamy
            - Peaty
            - Gravelly
            """
            allowed_soil_drainage = """
            SOIL_DRAINAGE (choose only from):
            - Well-drained
            - Poorly-drained
            - Moderately-drained
            - Excessively-drained
            - Waterlogged
            """
            allowed_soil_location_type = """
            SOIL_LOCATION_TYPE (choose only from):
            - Valley
            - Slope
            - Plain
            - Hill
            - Riverbank
            - Coastal
            - Plateau
            """
            allowed_soil_fertility = """
            SOIL_FERTILITY (choose only from):
            - High
            - Medium
            - Low
            - Very Low
            """
            allowed_soil_moisture = """
            SOIL_MOISTURE (choose only from):
            - Wet
            - Moist
            - Dry
            - Very Dry
            - Waterlogged
            """
            
            prompt = f"""
            Analyze this soil image and identify the soil type.\n\n{allowed_soil_types}\n\nFor each field below, choose ONLY from the provided options (or 'Unknown' if you cannot infer):\n{allowed_soil_color}\n{allowed_soil_texture}\n{allowed_soil_drainage}\n{allowed_soil_location_type}\n{allowed_soil_fertility}\n{allowed_soil_moisture}\n\nFormat your response as:\nSOIL_TYPE: [choose only from the list above]\nSOIL_COLOR: [choose only from the SOIL_COLOR list]\nSOIL_TEXTURE: [choose only from the SOIL_TEXTURE list]\nSOIL_DRAINAGE: [choose only from the SOIL_DRAINAGE list]\nSOIL_LOCATION_TYPE: [choose only from the SOIL_LOCATION_TYPE list]\nSOIL_FERTILITY: [choose only from the SOIL_FERTILITY list]\nSOIL_MOISTURE: [choose only from the SOIL_MOISTURE list]\n"""
            
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