import uuid
from datetime import datetime
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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(datetime.timezone.utc))

    # Relationships
    crop_prediction = db.relationship('CropPrediction', backref=db.backref('crop_recommendations', lazy=True))

    def __repr__(self):
        return f"<CropRecommendation {self.id} - {self.crop_name}>"

   