import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db

class CropPrediction(db.Model):
    __tablename__ = "crop_predictions"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    soil_analysis_id = db.Column(UUID(as_uuid=True), db.ForeignKey('soil_analyses.id'), nullable=False)
    weather_data_id = db.Column(UUID(as_uuid=True), db.ForeignKey('weather_data.id'),nullable=True)
    recommended_crops = db.Column(db.JSON, nullable=True)
    seasonal_advice = db.Column(db.Text, nullable=True)
    weather_warnings = db.Column(db.Text, nullable=True)
    soil_treatments = db.Column(db.JSON, nullable=True)
    risk_factors = db.Column(db.JSON, nullable=True)
    success_probability = db.Column(db.Integer, nullable=True)
    best_planting_date = db.Column(db.Date, nullable=True)
    expected_harvest_date = db.Column(db.Date, nullable=True)
    planting_window_start = db.Column(db.Date, nullable=True)
    planting_window_end = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    soil_analysis = db.relationship('SoilAnalysis', backref=db.backref('crop_predictions', lazy=True))

    def __repr__(self):
        return f"<CropPrediction {self.id} - SoilAnalysis: {self.soil_analysis_id}>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "soil_analysis_id": str(self.soil_analysis_id),
            "weather_data_id": str(self.weather_data_id) if self.weather_data_id else None,
            "recommended_crops": self.recommended_crops,
            "seasonal_advice": self.seasonal_advice,
            "weather_warnings": self.weather_warnings,
            "soil_treatments": self.soil_treatments,
            "risk_factors": self.risk_factors,
            "success_probability": self.success_probability,
            "best_planting_date": self.best_planting_date.isoformat() if self.best_planting_date else None,
            "expected_harvest_date": self.expected_harvest_date.isoformat() if self.expected_harvest_date else None,
            "planting_window_start": self.planting_window_start.isoformat() if self.planting_window_start else None,
            "planting_window_end": self.planting_window_end.isoformat() if self.planting_window_end else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

   