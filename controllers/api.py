from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app import db
import google.generativeai as genai
import json

api = Blueprint('api', __name__)

@api.route('/gemini-test', methods=['GET'])
@login_required
def test_gemini():
    """Test the Gemini API configuration."""
    api_key = current_app.config.get('GEMINI_API_KEY')
    
    if not api_key or api_key == 'your-api-key':
        return jsonify({
            'status': 'error',
            'message': 'No API key configured. Please add your Gemini API key to the .env file.'
        }), 400
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-flash')
        response = model.generate_content("Respond with 'API connection successful' if you receive this message.")
        
        return jsonify({
            'status': 'success',
            'message': response.text,
            'model': 'gemini-flash'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api.route('/toggle-preference', methods=['POST'])
@login_required
def toggle_preference():
    """API endpoint to toggle user preferences."""
    data = request.get_json()
    preference = data.get('preference')
    value = data.get('value')
    
    if preference == 'display_explanations':
        current_user.display_explanations = value
    elif preference == 'question_mode':
        current_user.question_mode = value
    elif preference == 'interactive_mode':
        current_user.interactive_mode = value
    else:
        return jsonify({'status': 'error', 'message': 'Invalid preference'}), 400
    
    db.session.commit()
    return jsonify({'status': 'success', 'message': f'{preference} updated'})
