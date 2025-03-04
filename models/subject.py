from app import db
from datetime import datetime

class Subject(db.Model):
    """Subject model for categorizing questions."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('Question', backref='subject', lazy=True)
    
    def __repr__(self):
        return f"Subject('{self.name}')"
