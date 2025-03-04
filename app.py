import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-testing')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URI', 'sqlite:///adaptive_learning.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

# Import models
from models.user import User
from models.question import Question
from models.answer import Answer
from models.subject import Subject

# Import blueprints
from controllers.auth import auth
from controllers.learning import learning
from controllers.dashboard import dashboard
from controllers.api import api

# Register blueprints
app.register_blueprint(auth, url_prefix='/auth')
app.register_blueprint(learning, url_prefix='/learn')
app.register_blueprint(dashboard, url_prefix='/dashboard')
app.register_blueprint(api, url_prefix='/api')

@app.route('/')
def index():
    """Landing page route."""
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
