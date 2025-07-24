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

   