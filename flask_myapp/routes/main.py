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
PERSON_GROUP_ID = os.environ['PERSON_GROUP_ID']
#export FLASK_DEBUG=1
#export FLASK_APP=localrun.py

# DATABASE_URL=os.environ.get('DATABASE_URL')

# engine = create_engine(DATABASE_URL)
# db = scoped_session(sessionmaker(bind=engine))

dic={'1a8d4b0f-bd6f-43a2-a9dd-0ed93f388f15': '17',
 '802c64ba-1e1e-4ad1-8dd2-71f7f7b23687': '15',
 '909efec8-6673-4b88-961a-09eb26d7ccd3': '4',
 '366a76da-b584-40e4-ab79-5d14b438df15': '13',
 '720915a2-b280-4ecd-8a38-d0f175782678': '12',
 '94390c1c-0353-48b2-b335-ef3535764315': '10',
 'dc112880-8f5c-4ad2-af19-76e2639d9e9b': '3',
 'b9bb6fc1-6bab-43fc-855c-0194dae032c2': 'Icon\r'}

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
            co=0
            for face in faces:
                if(co>=10):
                    break
                face_ids.append(face.face_id)
                co=co+1
            
            # Identify faces
            results = face_client.face.identify(face_ids, PERSON_GROUP_ID)
            print('Identifying faces in {}'.format(os.path.basename(image.name)))
            if not results:
                return ('No person identified in the person group for faces from {}.'.format(os.path.basename(image.name)))
            print(results,len(results))
            stroutput=''
            for person in results:
                print(person)
                if(len(person.candidates)==0):
                    stroutput=stroutput+("Face ID {} isn't match any people.<br>".format(person.face_id))
                else:
                    print(person.candidates[0])
                    stroutput=stroutput+ "He/She is "+str(dic[person.candidates[0].person_id])+" with a confidence of "+str(person.candidates[0].confidence)+"<br>"
                    #stroutput=stroutput+('Person for face ID {} is identified in {} with a confidence of {}.<br>'.format(person.face_id, os.path.basename(image.name), person.candidates[0].confidence)) # Get topmost confidence score
            return stroutput
            
            return "Done"
    else:
        return render_template("uploads.html")
