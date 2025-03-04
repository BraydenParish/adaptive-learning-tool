from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from models.subject import Subject
from models.question import Question
from models.answer import Answer
import google.generativeai as genai
import json
import time
import os

learning = Blueprint('learning', __name__)

@learning.route('/subject-selection')
@login_required
def subject_selection():
    """Page for selecting a subject to study."""
    subjects = Subject.query.all()
    return render_template('learning/subject_selection.html', title='Select a Subject', subjects=subjects)

@learning.route('/create-subject', methods=['POST'])
@login_required
def create_subject():
    """Create a new subject."""
    name = request.form.get('subject_name')
    description = request.form.get('subject_description', '')
    
    if not name:
        flash('Subject name is required.', 'danger')
        return redirect(url_for('learning.subject_selection'))
    
    existing_subject = Subject.query.filter_by(name=name).first()
    if existing_subject:
        flash('This subject already exists.', 'warning')
        return redirect(url_for('learning.study', subject_id=existing_subject.id))
    
    new_subject = Subject(name=name, description=description)
    db.session.add(new_subject)
    db.session.commit()
    
    flash(f'Subject "{name}" created successfully!', 'success')
    return redirect(url_for('learning.study', subject_id=new_subject.id))

@learning.route('/study/<int:subject_id>')
@login_required
def study(subject_id):
    """Main study page for a subject."""
    subject = Subject.query.get_or_404(subject_id)
    return render_template('learning/study.html', title=f'Study {subject.name}', subject=subject)

@learning.route('/generate-question/<int:subject_id>')
@login_required
def generate_question(subject_id):
    """API endpoint to generate a new question."""
    subject = Subject.query.get_or_404(subject_id)
    
    # Calculate appropriate difficulty level based on user's past performance
    user_answers = Answer.query.filter_by(user_id=current_user.id).all()
    
    # Default to difficulty level 1 if no previous answers
    difficulty = 1
    
    if user_answers:
        # Simple algorithm: average correct answers increases difficulty
        correct_answers = [a for a in user_answers if a.is_correct]
        accuracy = len(correct_answers) / len(user_answers)
        
        # Adjust difficulty based on accuracy (0.9+ accuracy → increase difficulty)
        if accuracy > 0.9 and len(user_answers) >= 10:
            difficulty = min(10, difficulty + 1)
        elif accuracy < 0.6 and difficulty > 1:
            difficulty = max(1, difficulty - 1)
    
    # Configure Gemini
    api_key = current_app.config.get('GEMINI_API_KEY')
    if not api_key or api_key == 'your-api-key':
        # For development/testing, return a mock question
        mock_question = {
            'text': f"This is a sample question about {subject.name} at difficulty level {difficulty}.",
            'options': {
                'a': 'First option',
                'b': 'Second option',
                'c': 'Third option',
                'd': 'Fourth option (correct)'
            },
            'correct_option': 'd',
            'explanation': 'This is a sample explanation for the correct answer.'
        }
        return jsonify(mock_question)
    
    # Set up Gemini API
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-flash')
    
    # Generate prompt based on difficulty and subject
    prompt = f"""
    Generate a question about {subject.name} at difficulty level {difficulty}/10.
    
    If difficulty is 1-3: Focus on basic recall, definitions, and simple concepts.
    If difficulty is 4-6: Focus on application and understanding of concepts.
    If difficulty is 7-10: Focus on analysis, evaluation, and synthesis of complex concepts.
    
    Format your response as a valid JSON object with the following structure:
    {{
        "text": "The question text",
        "options": {{
            "a": "First option",
            "b": "Second option",
            "c": "Third option",
            "d": "Fourth option"
        }},
        "correct_option": "The correct option letter (a, b, c, or d)",
        "explanation": "Detailed explanation of why the answer is correct"
    }}
    
    The question should be challenging but fair for the given difficulty level.
    """
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Extract JSON from response
        json_str = response_text.strip()
        if '```json' in json_str:
            json_str = json_str.split('```json')[1].split('```')[0].strip()
        
        question_data = json.loads(json_str)
        
        # Save question to database
        new_question = Question(
            text=question_data['text'],
            answer=question_data['correct_option'],
            explanation=question_data['explanation'],
            difficulty=difficulty,
            subject_id=subject_id,
            option_a=question_data['options']['a'],
            option_b=question_data['options']['b'],
            option_c=question_data['options']['c'],
            option_d=question_data['options']['d'],
            correct_option=question_data['correct_option']
        )
        db.session.add(new_question)
        db.session.commit()
        
        # Return question data without correct answer for the frontend
        if current_user.question_mode == 'multiple_choice':
            return jsonify({
                'id': new_question.id,
                'text': new_question.text,
                'options': question_data['options'],
                'difficulty': difficulty
            })
        else:
            # Free recall mode: no options
            return jsonify({
                'id': new_question.id,
                'text': new_question.text,
                'difficulty': difficulty
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@learning.route('/submit-answer', methods=['POST'])
@login_required
def submit_answer():
    """API endpoint to submit and evaluate an answer."""
    data = request.get_json()
    
    question_id = data.get('question_id')
    user_response = data.get('user_response')
    response_time = data.get('response_time')
    
    question = Question.query.get_or_404(question_id)
    
    # Evaluate the answer
    if current_user.question_mode == 'multiple_choice':
        is_correct = user_response.lower() == question.correct_option.lower()
    else:
        # For free recall, use Gemini to evaluate if available, otherwise exact match
        api_key = current_app.config.get('GEMINI_API_KEY')
        if api_key and api_key != 'your-api-key':
            # Use Gemini to evaluate
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-flash')
            
            prompt = f"""
            Question: {question.text}
            Correct answer: {question.answer}
            User answer: {user_response}
            
            Is the user's answer correct? Consider semantic meaning, not just exact wording.
            Respond with only 'Yes' or 'No'.
            """
            
            try:
                response = model.generate_content(prompt)
                is_correct = 'yes' in response.text.strip().lower()
            except Exception:
                # Fallback to simple comparison
                is_correct = user_response.lower() == question.answer.lower()
        else:
            # Simple exact match
            is_correct = user_response.lower() == question.answer.lower()
    
    # Save answer to database
    new_answer = Answer(
        user_id=current_user.id,
        question_id=question_id,
        user_response=user_response,
        is_correct=is_correct,
        response_time=response_time,
        mode=current_user.question_mode,
        difficulty_at_time=question.difficulty
    )
    db.session.add(new_answer)
    db.session.commit()
    
    # Return result with explanation if enabled
    result = {
        'is_correct': is_correct,
        'correct_answer': question.correct_option if current_user.question_mode == 'multiple_choice' else question.answer
    }
    
    if current_user.display_explanations:
        result['explanation'] = question.explanation
    
    return jsonify(result)

@learning.route('/interactive-question', methods=['POST'])
@login_required
def interactive_question():
    """API endpoint for interactive mode follow-up questions."""
    if not current_user.interactive_mode:
        return jsonify({'error': 'Interactive mode is not enabled'}), 400
    
    data = request.get_json()
    question_id = data.get('question_id')
    user_query = data.get('user_query')
    
    question = Question.query.get_or_404(question_id)
    
    # Use Gemini to generate an explanation
    api_key = current_app.config.get('GEMINI_API_KEY')
    if not api_key or api_key == 'your-api-key':
        # Mock response for development/testing
        return jsonify({
            'response': f"This is a sample explanation for '{user_query}' related to the current question."
        })
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-flash')
        
        prompt = f"""
        Original question: {question.text}
        User follow-up query: {user_query}
        
        Provide a clear, educational explanation for the user's query in the context of the original question. 
        Give a step-by-step explanation if appropriate. Be thorough but concise.
        """
        
        response = model.generate_content(prompt)
        return jsonify({'response': response.text})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
