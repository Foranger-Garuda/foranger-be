import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db

class CropRecommendation(db.Model):
    __tablename__ = "crop_recommendations"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crop_prediction_id = db.Column(UUID(as_uuid=True), db.ForeignKey('crop_predictions.id'), nullable=False)
    crop_name = db.Column(db.String, nullable=True)
    crop_category = db.Column(db.String, nullable=True)
    suitability_score = db.Column(db.Integer, nullable=True)
    suitability_level = db.Column(db.String, nullable=True)
    planting_method = db.Column(db.Text, nullable=True)
    spacing_recommendation = db.Column(db.String, nullable=True)
    seed_variety_suggestions = db.Column(db.Text, nullable=True)
    expected_yield_per_hectare = db.Column(db.Numeric(precision=10, scale=2), nullable=True)
    fertilizer_schedule = db.Column(db.JSON, nullable=True)
    watering_schedule = db.Column(db.Text, nullable=True)
    pest_control_measures = db.Column(db.JSON, nullable=True)
    harvesting_indicators = db.Column(db.Text, nullable=True)
    estimated_cost_per_hectare = db.Column(db.Numeric(precision=12, scale=2), nullable=True)
    estimated_revenue_per_hectare = db.Column(db.Numeric(precision=12, scale=2), nullable=True)
    market_demand_level = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    crop_prediction = db.relationship('CropPrediction', backref=db.backref('crop_recommendations', lazy=True))

    def __repr__(self):
        return f"<CropRecommendation {self.id} - {self.crop_name}>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "crop_prediction_id": str(self.crop_prediction_id),
            "crop_name": self.crop_name,
            "crop_category": self.crop_category,
            "suitability_score": self.suitability_score,
            "suitability_level": self.suitability_level,
            "planting_method": self.planting_method,
            "spacing_recommendation": self.spacing_recommendation,
            "seed_variety_suggestions": self.seed_variety_suggestions,
            "expected_yield_per_hectare": self.expected_yield_per_hectare,
            "fertilizer_schedule": self.fertilizer_schedule,
            "watering_schedule": self.watering_schedule,
            "pest_control_measures": self.pest_control_measures,
            "harvesting_indicators": self.harvesting_indicators,
            "estimated_cost_per_hectare": self.estimated_cost_per_hectare,
            "estimated_revenue_per_hectare": self.estimated_revenue_per_hectare,
            "market_demand_level": self.market_demand_level,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

   