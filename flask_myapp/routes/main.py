from flask import Blueprint, render_template, request, redirect, url_for, session,jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests 
import json
import os
import random
import string
import time
import glob
from azure.cognitiveservices.vision.face import FaceClient
from msrest.authentication import CognitiveServicesCredentials
from azure.cognitiveservices.vision.face.models import TrainingStatusType, Person, SnapshotObjectType, OperationStatusType

UPLOAD_FOLDER = 'flask_myapp/static/images'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
KEY = os.environ['FACE_SUBSCRIPTION_KEY']
ENDPOINT = os.environ['FACE_ENDPOINT']
face_client = FaceClient(ENDPOINT, CognitiveServicesCredentials(KEY))
PERSON_GROUP_ID = 'test01'
#export FLASK_DEBUG=1
#export FLASK_APP=localrun.py

# DATABASE_URL=os.environ.get('DATABASE_URL')

# engine = create_engine(DATABASE_URL)
# db = scoped_session(sessionmaker(bind=engine))

main = Blueprint('main', __name__)

@main.route('/',methods=['POST','GET'])
def index():
    return "Welcome to Face Web app"

@main.route('/uploader', methods = ['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if request.files:
            image = request.files["image"]
            #print("DEBUG -- ",image ,os.listdir())
            image.save(os.path.join(UPLOAD_FOLDER , image.filename))
            '''
            Identify a face against a defined PersonGroup
            '''
            # Group image for testing against
            IMAGES_LOCATION = os.path.join(UPLOAD_FOLDER , image.filename)

            # Get test image
            test_image_array = glob.glob(IMAGES_LOCATION)
            image = open(test_image_array[0], 'r+b')

            # Detect faces
            face_ids = []
            faces = face_client.face.detect_with_stream(image)
            if (len(faces)==0):
                return "No face found"
            for face in faces:
                face_ids.append(face.face_id)
            # Identify faces
            results = face_client.face.identify(face_ids, PERSON_GROUP_ID)
            print('Identifying faces in {}'.format(os.path.basename(image.name)))
            if not results:
                return ('No person identified in the person group for faces from {}.'.format(os.path.basename(image.name)))
            for person in results:
                return ('Person for face ID {} is identified in {} with a confidence of {}.'.format(person.face_id, os.path.basename(image.name), person.candidates[0].confidence)) # Get topmost confidence score
            
            return "Done"
    else:
        return render_template("uploads.html")
