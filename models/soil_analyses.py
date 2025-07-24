import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db

class SoilAnalysis(db.Model):
    __tablename__ = "soil_analyses"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    soil_type_reference_id = db.Column(UUID(as_uuid=True), db.ForeignKey('soil_types_reference.id'), nullable=True)
    soil_color = db.Column(db.String, nullable=True)
    soil_texture = db.Column(db.String, nullable=True)
    soil_drainage = db.Column(db.String, nullable=True)
    soil_location_type = db.Column(db.String, nullable=True)
    soil_fertility = db.Column(db.String, nullable=True)
    soil_moisture = db.Column(db.String, nullable=True)
    latitude = db.Column(db.Numeric(precision=10, scale=8), nullable=True)
    longitude = db.Column(db.Numeric(precision=11, scale=8), nullable=True)
    province = db.Column(db.String, nullable=True)
    city = db.Column(db.String, nullable=True)
    classified_soil_type = db.Column(db.String, nullable=True)
    classification_confidence = db.Column(db.String, nullable=True)
    classification_method = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(datetime.timezone.utc))
    claude_api_calls = db.Column(db.Integer, nullable=True)
    ip_address = db.Column(db.String, nullable=True)

    # Relationship with User model
    user = db.relationship('User', backref=db.backref('soil_analyses', lazy=True))

    def __repr__(self):
        return f"<SoilAnalysis {self.id} - User: {self.user_id}>"