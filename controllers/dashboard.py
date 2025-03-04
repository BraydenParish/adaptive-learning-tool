from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app import db
from models.answer import Answer
from models.question import Question
from models.subject import Subject
from sqlalchemy import func
import json
from datetime import datetime, timedelta

dashboard = Blueprint('dashboard', __name__)

@dashboard.route('/')
@login_required
def index():
    """Main dashboard view showing performance metrics."""
    return render_template('dashboard/index.html', title='Learning Dashboard')

@dashboard.route('/stats')
@login_required
def get_stats():
    """API endpoint to get user statistics."""
    # Get total questions answered
    total_answers = Answer.query.filter_by(user_id=current_user.id).count()
    
    # Get correct answers
    correct_answers = Answer.query.filter_by(user_id=current_user.id, is_correct=True).count()
    
    # Calculate accuracy
    accuracy = (correct_answers / total_answers * 100) if total_answers > 0 else 0
    
    # Get average response time
    avg_response_time_query = db.session.query(func.avg(Answer.response_time)).filter_by(user_id=current_user.id)
    avg_response_time = avg_response_time_query.scalar() or 0
    
    # Get questions by difficulty
    difficulty_distribution = db.session.query(
        Answer.difficulty_at_time,
        func.count(Answer.id)
    ).filter_by(user_id=current_user.id).group_by(Answer.difficulty_at_time).all()
    
    difficulty_data = {level: count for level, count in difficulty_distribution}
    
    # Get performance by subject
    subject_performance = db.session.query(
        Subject.name,
        func.count(Answer.id).label('total'),
        func.sum(Answer.is_correct.cast(db.Integer)).label('correct')
    ).join(Question, Answer.question_id == Question.id)\
     .join(Subject, Question.subject_id == Subject.id)\
     .filter(Answer.user_id == current_user.id)\
     .group_by(Subject.name).all()
    
    subject_data = [{
        'name': name,
        'total': total,
        'correct': correct,
        'accuracy': (correct / total * 100) if total > 0 else 0
    } for name, total, correct in subject_performance]
    
    # Get improvement over time (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    daily_performance = db.session.query(
        func.date(Answer.created_at).label('date'),
        func.count(Answer.id).label('total'),
        func.sum(Answer.is_correct.cast(db.Integer)).label('correct')
    ).filter(Answer.user_id == current_user.id, Answer.created_at >= thirty_days_ago)\
     .group_by(func.date(Answer.created_at)).all()
    
    time_series_data = [{
        'date': date.strftime('%Y-%m-%d'),
        'accuracy': (correct / total * 100) if total > 0 else 0
    } for date, total, correct in daily_performance]
    
    # Return all stats as JSON
    return jsonify({
        'total_questions': total_answers,
        'correct_answers': correct_answers,
        'accuracy': accuracy,
        'avg_response_time': avg_response_time,
        'difficulty_distribution': difficulty_data,
        'subject_performance': subject_data,
        'time_series': time_series_data
    })

@dashboard.route('/recent-activity')
@login_required
def recent_activity():
    """API endpoint to get user's recent activity."""
    recent_answers = Answer.query.filter_by(user_id=current_user.id)\
        .order_by(Answer.created_at.desc()).limit(10).all()
    
    activity_data = []
    for answer in recent_answers:
        question = Question.query.get(answer.question_id)
        subject = Subject.query.get(question.subject_id)
        
        activity_data.append({
            'question_text': question.text,
            'subject': subject.name,
            'is_correct': answer.is_correct,
            'date': answer.created_at.strftime('%Y-%m-%d %H:%M'),
            'difficulty': answer.difficulty_at_time,
            'response_time': answer.response_time
        })
    
    return jsonify(activity_data)
