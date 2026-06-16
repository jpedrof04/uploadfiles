import os
import json
from flask import Flask

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'change-this-to-a-random-key'
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
    app.config['DATABASE'] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database.db')
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
    app.config['SESSION_PERMANENT'] = False

    auth_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.auth.json')
    if os.path.exists(auth_path):
        with open(auth_path) as f:
            auth_data = json.load(f)
        app.config['AUTH_USERNAME'] = auth_data.get('username', '')
        app.config['AUTH_PASSWORD'] = auth_data.get('password', '')
    else:
        app.config['AUTH_USERNAME'] = ''
        app.config['AUTH_PASSWORD'] = ''

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    from app.models import init_db
    init_db(app.config['DATABASE'])

    from app.routes import main
    app.register_blueprint(main)

    return app
