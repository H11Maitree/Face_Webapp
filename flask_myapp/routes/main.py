from flask import Blueprint, render_template, request, redirect, url_for, session,jsonify, session
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
from oauthlib.oauth2 import WebApplicationClient
from datetime import datetime

UPLOAD_FOLDER = 'flask_myapp/static/images'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
KEY = os.environ.get('FACE_SUBSCRIPTION_KEY',None)
ENDPOINT = os.environ.get('FACE_ENDPOINT',None)
face_client = FaceClient(ENDPOINT, CognitiveServicesCredentials(KEY))
PERSON_GROUP_ID = os.environ.get('PERSON_GROUP_ID',None)
#export FLASK_DEBUG=1
#export FLASK_APP=localrun.py
#export OAUTHLIB_INSECURE_TRANSPORT=1

DATABASE_URL=os.environ.get('DATABASE_URL')

engine = create_engine(DATABASE_URL)
db = scoped_session(sessionmaker(bind=engine))

def addtransac(email,predicted):
  db.execute(""" INSERT INTO "Transcript" (user_email,prediction,timestamp)
                    VALUES (:email,:pre,:time);
                    COMMIT;""",{"email":email,"pre":predicted,"time":int(time.time())})
  print("Added transac")

def getStudentID(PersonID):
    res=db.execute(f"""
                    SELECT "School_ID" FROM "user" WHERE "PersonID" = '{PersonID}';
                    """).fetchall()
    return res[0][0]

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)
client = WebApplicationClient(GOOGLE_CLIENT_ID)

main = Blueprint('main', __name__)

def alreadysignin():
    if session.get('usernow', -1)==-1:
        print("User = -1")
        return False
    else:
        print("User : ",session.get('usernow', -1))
        return session.get('usernow', -1)

def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()

@main.route("/logout")
def logout():
    session['usernow']=-1
    print("usernow = ",session['usernow'])
    print("Re-directing to main.index")
    return redirect(url_for('main.index'))

@main.route("/login")
def login():
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    print("request_uri : ",request_uri)
    print("Re-direct to google uri")
    return redirect(request_uri)

@main.route("/login/callback")
def callback():
    # Get authorization code Google sent back to you
    code = request.args.get("code")

    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    token_url, headers, body = client.prepare_token_request(
    token_endpoint,
    authorization_response=request.url,
    redirect_url=request.base_url,
    code=code)

    token_response = requests.post(
    token_url,
    headers=headers,
    data=body,
    auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    client.parse_request_body_response(json.dumps(token_response.json()))

    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    print(userinfo_endpoint)
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)
    
    print(userinfo_response)
    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
    else:
        return "User email not available or not verified by Google.", 400
    session['usernow']=users_email
    print('usernow : ',session.get('usernow', -1),users_email)
    print("Re-directing to main.upload_file")
    return redirect(url_for('main.upload_file'))


@main.route('/',methods=['POST','GET'])
def index():
    if alreadysignin():
        return "Welcome "+session['usernow']+" to Face Web app<br><br><a href=\""+url_for('main.log')+"\"> See your log.</a><br><a href=\""+url_for('main.logout')+"\"> Logout.</a><br>"+"<br><a href=\""+url_for('main.upload_file')+"\">Upload Photo</a><br>"
    else:
        return "Welcome to Face Web app<br>Login with MWIT account <a href=\""+url_for('main.login')+"\">Signin with Google.</a>"

@main.route('/uploader', methods = ['GET', 'POST'])
def upload_file():
    if (alreadysignin()==False):
        return "You haven't sign-in : "+"<a href=\""+url_for('main.login')+"\">Signin with Google.</a><br>"
    
    return render_template("uploads.html")

@main.route('/result', methods = ['GET', 'POST'])
def result():
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
                addtransac(session.get('usernow', -1),"unknown face")
            else:
                addtransac(session.get('usernow', -1),str(getStudentID(person.candidates[0].person_id)))
                print(person.candidates[0])
                stroutput=stroutput+ "He/She is "+str(getStudentID(person.candidates[0].person_id))+" with a confidence of "+str(person.candidates[0].confidence)+"<br>"
                #stroutput=stroutput+('Person for face ID {} is identified in {} with a confidence of {}.<br>'.format(person.face_id, os.path.basename(image.name), person.candidates[0].confidence)) # Get topmost confidence score
        stroutput=stroutput+"<a href=\""+url_for('main.upload_file')+"\">Go Back to file uploader.</a>"
        return stroutput
    else:
        return "No File Uploaded"

def getStudentIDfromEmail(email=-1):
    if email==-1:
        return "Sorry It seem like you just logout"
    else:
        email=email.lower()
        res=db.execute(f"""
                    SELECT "School_ID" FROM "user" WHERE "email" = '{email}';
                    """).fetchall()
        if(len(res)==0):
            return "No Student ID registered to this email pls contact our stuff."
        return res[0][0]

@main.route('/log', methods = ['GET', 'POST'])
def log():
    if (alreadysignin()==False):
        return "You haven't sign-in : "+"<a href=\""+url_for('main.login')+"\">Signin with Google.</a><br>"
    userstudentid=getStudentIDfromEmail(session.get('usernow', -1))
    stroutput="Your ID : "+userstudentid+"<br><br>"

    res=db.execute(f"""
                    SELECT "user_email","timestamp" FROM "Transcript" WHERE "prediction" = '{userstudentid}';
                    """).fetchall()

    for row in res:
        stroutput=stroutput+"Email : "+row[0]+" predicted you at "+str(datetime.fromtimestamp(row[1]))+"<br>"
    stroutput=stroutput+"<a href=\""+url_for('main.index')+"\">Go Home.</a>"
    return stroutput