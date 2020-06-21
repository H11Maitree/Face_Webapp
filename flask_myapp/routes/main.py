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

UPLOAD_FOLDER = 'flask_myapp/static/images'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
KEY = os.environ.get('FACE_SUBSCRIPTION_KEY',None)
ENDPOINT = os.environ.get('FACE_ENDPOINT',None)
face_client = FaceClient(ENDPOINT, CognitiveServicesCredentials(KEY))
PERSON_GROUP_ID = os.environ.get('PERSON_GROUP_ID',None)
#export FLASK_DEBUG=1
#export FLASK_APP=localrun.py
#export OAUTHLIB_INSECURE_TRANSPORT=1

# DATABASE_URL=os.environ.get('DATABASE_URL')

# engine = create_engine(DATABASE_URL)
# db = scoped_session(sessionmaker(bind=engine))

dic={'b5663c32-50d8-47cd-98b2-cd633ba4e5a2': '17',
 '1a540303-e69a-4c93-9bfa-ab3960c6580e': '15',
 '24c77cd1-bf67-44a6-8345-e46a26d4095c': '17',
 '4639437c-5319-4498-b91d-18848718025a': '15',
 'f60d0c77-d97c-4cf0-b3b5-4e64d03ee109': '17',
 '94bb4e91-b615-4692-bb42-7e9d99fd616d': '17',
 '27123291-fcb4-41dc-9905-0061a02f7a2d': '15',
 '752f8a95-8ff7-470f-9601-422ea0307f37': '17',
 '6d9ad337-433d-471e-aa09-bba7de71ba42': '15',
 'ea0ad98b-4437-42c2-8c07-c9713c423753': '4',
 'a343843a-474c-4a6d-9488-e63cbd5a93f5': '13',
 '07c394d5-5d5a-45cc-93ed-1532895c3156': '12',
 'f6b31dbe-f6bc-4e7a-b559-b1fe32238e0e': '12',
 '0ad86b07-72db-4820-b1ec-8994657b970a': '10',
 'c48aae2b-b4ff-4019-899a-ff5fafd45460': '3',
 '624eb04d-fc9f-4242-98c6-e8666ababf84': '1',
 '0748ce85-3d0a-4d2f-b75a-3ba16ebc875a': '2',
 'b18dd70e-55bc-41e2-a417-f5ca988db799': '5',
 '8ea518b0-32c1-433f-8f62-0239dd18823a': '6',
 '73ab8b1a-971f-4a35-8de9-7ae05ee1c96f': '7',
 'da0944e9-0e89-40f5-a4af-ec80d5707eb5': '8',
 '6a33b4fe-7d8b-42ae-9459-10f0bf355d0c': '9',
 'fb98db8f-2d7e-4e8c-8fa9-90817a67874a': '11',
 '851c9fa9-c112-498e-9b28-1d13123ccd19': '14',
 '9e18bdbc-3a92-427c-ab49-1aa057855423': '16',
 'fa9870d7-44bc-440a-930e-36203ad06865': '18',
 'f5ddee0c-f46f-4bf7-b7b5-a25fe072e512': '19',
 '7263051a-4db2-4619-bdc0-d6e154fb6503': '20',
 '1e3c33fc-46bf-4208-bd62-75cad58a1273': '21',
 '9038f94c-58f4-41fa-b814-a1a1352c0e8c': '22',
 'd471fe4a-689b-4ddc-9bc7-611608b7607e': '23',
 'b53218b8-9133-4148-ad55-5cf75c7f4307': '24',
 '81a0c260-1f0c-44ce-b56e-de1e01f643f3': 'Icon\r',
 '58846f8c-7ac0-411b-8851-5f8958c720b3': '23'}

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)
client = WebApplicationClient(GOOGLE_CLIENT_ID)

main = Blueprint('main', __name__)

def alreadysignin():
    if session.get('usernow', -1)==-1:
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
    print('usernow : ',users_email)
    print("Re-directing to main.upload_file")
    return redirect(url_for('main.upload_file'))


@main.route('/',methods=['POST','GET'])
def index():
    if alreadysignin():
        return "Welcome "+session['usernow']+" to Face Web app<br>Login with MWIT account <a href=\""+url_for('main.logout')+"\"> Logout.</a><br>"+"<a href=\""+url_for('main.upload_file')+"\">Upload Photo</a><br>"
    else:
        return "Welcome to Face Web app<br>Login with MWIT account <a href=\""+url_for('main.login')+"\">Signin with Google.</a>"

@main.route('/uploader', methods = ['GET', 'POST'])
def upload_file():
    if alreadysignin()==False:
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
            else:
                print(person.candidates[0])
                stroutput=stroutput+ "He/She is "+str(dic[person.candidates[0].person_id])+" with a confidence of "+str(person.candidates[0].confidence)+"<br>"
                #stroutput=stroutput+('Person for face ID {} is identified in {} with a confidence of {}.<br>'.format(person.face_id, os.path.basename(image.name), person.candidates[0].confidence)) # Get topmost confidence score
        return stroutput
    else:
        return "No File Uploaded"
