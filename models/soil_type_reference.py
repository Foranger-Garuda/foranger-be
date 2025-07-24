import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db

class SoilTypeReference(db.Model):
    __tablename__ = "soil_types_reference"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    soil_type_name = db.Column(db.String, unique=True, nullable=False)
    local_name = db.Column(db.String, nullable=True)
    description = db.Column(db.Text, nullable=True)
    characteristics = db.Column(db.JSON, nullable=True)
    common_locations = db.Column(db.Text, nullable=True)
    suitable_crops = db.Column(db.Text, nullable=True)
    management_tips = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<SoilTypeReference {self.soil_type_name}>"

    def to_dict(self):
        """Convert model instance to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'soil_type_name': self.soil_type_name,
            'local_name': self.local_name,
            'description': self.description,
            'characteristics': self.characteristics,
            'common_locations': self.common_locations,
            'suitable_crops': self.suitable_crops,
            'management_tips': self.management_tips,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }