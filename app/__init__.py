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
    if not os.path.exists(auth_path):
        default_auth = {
            "confirm_password": "scrypt:32768:8:1$qz7KQEcSORvFCfop$e4c3d5a2eb97718e584d01101e09188b563b734c3949d8fb41ea7084f9a2c5e1f2399944e95c02b66cd26438e50f1ff3b3afceba4bc950f7eb507abe50dc74a1",
            "users": [
                {"username": "prof", "password": "scrypt:32768:8:1$Y0TbOLEoxQoJr8Or$1168fc8cd0d03b173c4656c3f229f1ff72ede2a15e80050c9a822f8176ea8a169fe7f741ff93cf9ad9cac21eba5dff6528bcb7857ef9f9fe6a1bedc2631d38d7", "role": "prof"},
                {"username": "thead", "password": "scrypt:32768:8:1$suuVPZtGoLA2vyhl$0c40c15ea91ef61cdc375e9fc6555319057d16af56e1b94fb01ef7a70e69655d8b98cb966a9d3c686b75bfd60df0f325b5f67902f80b3a4eb16c7806beb60261", "role": "admin"}
            ]
        }
        with open(auth_path, 'w') as f:
            json.dump(default_auth, f, indent=2)

    app.config['AUTH_USERS'] = []
    app.config['CONFIRM_PASSWORD'] = ''
    with open(auth_path) as f:
        auth_data = json.load(f)
    app.config['AUTH_USERS'] = auth_data.get('users', [])
    app.config['CONFIRM_PASSWORD'] = auth_data.get('confirm_password', '')

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    from app.models import init_db
    init_db(app.config['DATABASE'])

    from app.routes import main
    app.register_blueprint(main)

    return app
