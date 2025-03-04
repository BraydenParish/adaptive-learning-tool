from app import db
from datetime import datetime

class Answer(db.Model):
    """Answer model for tracking user responses and performance."""
    id = db.Column(db.Integer, primary_key=True)
    user_response = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    response_time = db.Column(db.Float, nullable=False)  # Time in seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    
    # Additional tracking fields
    mode = db.Column(db.String(20), nullable=False)  # 'multiple_choice' or 'free_recall'
    difficulty_at_time = db.Column(db.Integer, nullable=False)  # The difficulty level when answered
    
    def __repr__(self):
        return f"Answer(User: {self.user_id}, Question: {self.question_id}, Correct: {self.is_correct})"
