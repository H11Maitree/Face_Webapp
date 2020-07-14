from flask import Blueprint, render_template, request, redirect, url_for, session,jsonify, session, abort
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
import uuid

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *


UPLOAD_FOLDER = 'flask_myapp/static/images'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
KEY = os.environ.get('FACE_SUBSCRIPTION_KEY',None)
ENDPOINT = os.environ.get('FACE_ENDPOINT',None)
face_client = FaceClient(ENDPOINT, CognitiveServicesCredentials(KEY))
PERSON_GROUP_ID = os.environ.get('PERSON_GROUP_ID',None)

# Channel Access Token
line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN',None))
# Channel Secret
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET',None))

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

def addlinemap(email,lineid):
    db.execute(""" INSERT INTO "linemapemail" (email,lineid)
                    VALUES (:email,:lineid);
                    COMMIT;""",{"email":email,"lineid":lineid})
    print("Added linemap")

def getStudentID(PersonID):
    res=db.execute(f"""
                    SELECT "School_ID" FROM "user" WHERE "PersonID" = '{PersonID}';
                    """).fetchall()
    return res[0][0]

def checkpiroline(lineid):
    res=db.execute(f"""
                    SELECT "email" FROM "linemapemail" WHERE "lineid" = '{lineid}';
                    """).fetchall()
    if(len(res)==0):
        return False
    else:
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

@main.route("/linelogin", methods=['GET'])
def linelogin():
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callbackline?lineid="+request.args.get("lineid"),
        scope=["openid", "email", "profile"],
    )
    print("request_uri : ",request_uri)
    print("Re-direct to google uri")
    return redirect(request_uri)

@main.route("/linelogin/callback")
def linelogincallback():
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
    addlinemap(email=users_email,lineid=request.args.get("lineid"))
    return "SUCCESS<br>You may close this tap."

@main.route("/linewebhook", methods=['POST'])
def linewebhook():
# 監聽所有來自 /callback 的 Post Request
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = json.loads(request.get_data(as_text=True))
    # handle webhook body
    print("BODY:\n",body)
    print("Type : ",type(body))
    if(body["events"][0]["message"]["type"]=="image"):
        print("inif")
        checkpi=checkpiroline(lineid=body["events"][0]["source"]["userId"])
        if (checkpi==False):
            line_bot_api.reply_message(body["events"][0]["replyToken"], TextSendMessage(text="Pls Login\n"+url_for(main.linelogin)+"?lineid="+body["events"][0]["source"]["userId"]))
            return "OK"

        message_content = line_bot_api.get_message_content(body["events"][0]["message"]["id"])
        filenamesave=uuid.uuid4().hex
        filenamesave=filenamesave+".png"
        print("Check 1")

        with open(filenamesave, 'wb') as fd:
            for chunk in message_content.iter_content():
                fd.write(chunk)
        
        print("Check 2")
        test_image_array = glob.glob(filenamesave)
        image = open(test_image_array[0], 'r+b')

        print("in detect face")
        # Detect faces
        face_ids = []
        faces = face_client.face.detect_with_stream(image)
        if (len(faces)==0):
            line_bot_api.reply_message(body["events"][0]["replyToken"], TextSendMessage(text="No face found"))
            return "OK"
        co=0
        for face in faces:
            if(co>=10):
                break
            face_ids.append(face.face_id)
            co=co+1
        
        print("in Identify face")
        # Identify faces
        results = face_client.face.identify(face_ids, PERSON_GROUP_ID)
        print('Identifying faces in {}'.format(os.path.basename(image.name)))
        if not results:
            line_bot_api.reply_message(body["events"][0]["replyToken"], TextSendMessage(text="No Persorn"))
            #return ('No person identified in the person group for faces from {}.'.format(os.path.basename(image.name)))
            return 'OK'
        print(results,len(results))
        count_unknown=0
        stroutput=''
        for person in results:
            print(person)
            if(len(person.candidates)==0):
                count_unknown=count_unknown+1
                #stroutput=stroutput+("Face ID {} isn't match any people.\n".format(person.face_id))
                addtransac(checkpi,"unknown face")
            else:
                print(person.candidates[0])
                if(float(person.candidates[0].confidence)<0.604):
                    addtransac(checkpi,"unknown face")
                    count_unknown=count_unknown+1
                else:
                    addtransac(checkpi,str(getStudentID(person.candidates[0].person_id)))
                    stroutput=stroutput+"ID : " +str(getStudentID(person.candidates[0].person_id))+" Confidence :"+str(person.candidates[0].confidence)[:4]+"\n"
        if(count_unknown>0):
            stroutput=stroutput+"There are "+str(count_unknown)+" people we don't know."
        line_bot_api.reply_message(body["events"][0]["replyToken"], TextSendMessage(text=stroutput))
        #stroutput=stroutput+"<a href=\""+url_for('main.upload_file')+"\">Go Back to file uploader.</a>"
        #return stroutput
        #line_bot_api.reply_message(body["events"][0]["replyToken"], TextSendMessage(text="Image"))
    # try:
    #     handler.handle(body, signature)
    # except InvalidSignatureError:
    #     abort(400)
    return 'OK'

# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print("EVENT:\n",str(event))
    message = TextSendMessage(text=event.message.text)
    line_bot_api.reply_message(event.reply_token, message)

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
        stroutput=stroutput+"Email : "+row[0]+" predicted you at "+str(datetime.fromtimestamp(row[1]))+" Coordinated Universal Time (UTC)<br>"
    stroutput=stroutput+"<a href=\""+url_for('main.index')+"\">Go Home.</a>"
    return stroutput