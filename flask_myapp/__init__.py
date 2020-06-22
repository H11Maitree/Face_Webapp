from flask import Flask 
from .routes.main import main
import os

def create_app(config_file='settings.py'):
    app = Flask(__name__)
    app.config.from_pyfile(config_file)
    UPLOAD_FOLDER = './static/images'
    app.config["IMAGE_UPLOADS"] = UPLOAD_FOLDER
    app.register_blueprint(main)
    #app.config.update(SECRET_KEY=os.urandom(24))
    return app