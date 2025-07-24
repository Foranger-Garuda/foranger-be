import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db

class SoilPhoto(db.Model):
    __tablename__ = "soil_photos"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    soil_analysis_id = db.Column(UUID(as_uuid=True), db.ForeignKey('soil_analyses.id'), nullable=False)
    photo_url = db.Column(db.String, nullable=True)
    photo_filename = db.Column(db.String, nullable=True)
    analysis_result = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(datetime.timezone.utc))

    # Relationships
    soil_analysis = db.relationship('SoilAnalysis', backref=db.backref('soil_photos', lazy=True))

    def __repr__(self):
        return f"<SoilPhoto {self.id} - {self.photo_filename}>"
