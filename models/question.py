from app import db
from datetime import datetime

class Question(db.Model):
    """Question model for storing AI-generated questions."""
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.Integer, default=1)  # 1-10 scale
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    
    # For multiple choice questions
    option_a = db.Column(db.Text, nullable=True)
    option_b = db.Column(db.Text, nullable=True)
    option_c = db.Column(db.Text, nullable=True)
    option_d = db.Column(db.Text, nullable=True)
    correct_option = db.Column(db.String(1), nullable=True)  # a, b, c, or d
    
    # Relationships
    answers = db.relationship('Answer', backref='question', lazy=True)
    
    def __repr__(self):
        return f"Question('{self.text[:30]}...', Difficulty: {self.difficulty})"
    
    def to_dict(self):
        """Convert question to dictionary format for API responses."""
        question_dict = {
            'id': self.id,
            'text': self.text,
            'difficulty': self.difficulty,
            'subject_id': self.subject_id,
            'subject_name': self.subject.name,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Include multiple choice options if present
        if self.option_a:
            question_dict.update({
                'options': {
                    'a': self.option_a,
                    'b': self.option_b,
                    'c': self.option_c,
                    'd': self.option_d
                }
            })
            
        return question_dict
