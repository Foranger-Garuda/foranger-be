import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db

class WeatherData(db.Model):
    __tablename__ = "weather_data"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    latitude = db.Column(db.Numeric(precision=10, scale=8), nullable=True)
    longitude = db.Column(db.Numeric(precision=11, scale=8), nullable=True)
    current_temperature = db.Column(db.Numeric(precision=5, scale=2), nullable=True)
    current_humidity = db.Column(db.Integer, nullable=True)
    current_rainfall = db.Column(db.Numeric(precision=6, scale=2), nullable=True)
    current_wind_speed = db.Column(db.Numeric(precision=5, scale=2), nullable=True)
    current_pressure = db.Column(db.Numeric(precision=7, scale=2), nullable=True)
    forecast_7days = db.Column(db.JSON, nullable=True)
    forecast_14days = db.Column(db.JSON, nullable=True)
    season = db.Column(db.String, nullable=True)
    weather_warnings = db.Column(db.Text, nullable=True)
    data_source = db.Column(db.String, nullable=True)
    fetched_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<WeatherData {self.id} - {self.latitude},{self.longitude}>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "latitude": self.latitude,
            "longitude": self.longitude,
            "current_temperature": self.current_temperature,
            "current_humidity": self.current_humidity,
            "current_rainfall": self.current_rainfall,
            "current_wind_speed": self.current_wind_speed,
            "current_pressure": self.current_pressure,
            "forecast_7days": self.forecast_7days,
            "season": self.season,
            "weather_warnings": self.weather_warnings,
            "data_source": self.data_source,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

   