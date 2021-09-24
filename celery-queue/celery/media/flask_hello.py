# Import the Flask package
import flask
from flask import Flask,render_template,redirect,session,send_from_directory,abort,flash,request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os.path
import os
from os import path,urandom,environ,remove,getcwd
import hashlib
from datetime import timedelta
from flask_sqlalchemy import SQLAlchemy
import flask_login as flog
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect,CSRFError
import uuid
from functools import wraps
import re
from sqlalchemy import func
from PIL import Image
from celery import Celery,result,task
from celery.signals import task_success
from media.encoder_modular import Encoder
from media.vp9dash import AdptEncoder
import boto3
import botocore
from shutil import rmtree
from flask_cors import CORS,cross_origin
import subprocess
from config import Config



# Initialize Flask
app = Flask(__name__)
csrf = CSRFProtect(app)
CORS(app)
app_limiter=Limiter(
       app,
       key_func=get_remote_address,
       default_limits=["400 per day","90 per hour"]
)
db=SQLAlchemy(app)
#app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
#app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
#app.config['CELERYD_TASK_SOFT_TIME_LIMIT'] = 60*60*9
#app.config['CELERY_TRACK_STARTED'] = True
#app.config['CELERYD_PREFETCH_MULTIPLIER']=1
app.config.from_object(Config)
celery = Celery(app.name, backend=app.config['CELERY_RESULT_BACKEND'],
                broker=app.config['CELERY_BROKER_URL'])
#celery.conf.update(app.config)

PASSWORD_SALT ='0'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'tif', 'mp4', 'mp3', 'webm', 'mpg' 'mpeg', 'avi', 'wmv', 'mov','pptx', 'ppt','aac','opus'])

from sql import models


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('username') is None or session.get('if_logged') is None:
            return redirect('/login',code=302)
        return f(*args, **kwargs)
    return decorated_function


# Add administrative views here

# Define the index route
@app.route("/")
def index():
   return render_template("index.html")

@app.route('/favicon.ico')
def logo():
    return redirect('static/icons/favicon.png', code=302)

@app.route("/createpro")
def createpro():
       "route to display profile creation"
       return render_template("create-profile.html")

@app.route("/test")
@login_required
def test():
       return render_template("test.html")

@app.route("/seehim")
def seehim():
	return f'''wait until you see him. Oh no no no no oo oo oo ha ha ha - _ - !! <iframe width="560" height="315" src="https://www.youtube.com/embed/7wivOEXlL9s?end=19"  ; encrypted-media" allowfullscreen></iframe><br><iframe src="https://rive.app/a/nastya/files/flare/under-construction/embed" frameborder="0" allow="autoplay></iframe>'''

@app.route("/testmetro")
def testmetro():
       return render_template("testmetro.html")

@app.route("/contact-us")
def contactus():
	return render_template("contacts.html")

@app.errorhandler(CSRFError)
def csrf_error(reason):
    return 'Error CSRF error',302


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/robots.txt')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])

def awss3config():
        boto_kwargs = {
            "aws_access_key_id": app.config['AWS_ACCESS_KEY_ID'],
            "aws_secret_access_key": app.config['AWS_SECRET_ACCESS_KEY'],
            "region_name": app.config['AWS_REGION'],
        }
        s3_client = boto3.Session(**boto_kwargs).client("s3")
        return s3_client

def aws_upload(filepath,aws_path):
       "upload to s3 bucket"
       s3_client=awss3config()
       try:
          s3_client.upload_file(filepath, app.config['AWS_BUCKET'], aws_path)
          return 0
       except boto3.exceptions.S3UploadFailedError:
              raise


@app.route('/filesrc/<video_id>/<type>/<filename>')
@app.route('/filesrc/<video_id>/<type>/<filename>/<filepath>/')
@app_limiter.limit("790 per hour")
def filesrc(video_id,filename,type,filepath=None):
       "all th files related to video are fetched from here"
       path = app.config['UPLOAD_FOLDER']+ video_id     #upload flder already has backslash.dont add it 
       if(type=="pdf"):
           return redirect(app.config['CLOUDFRONT_DOMAIN']+'/'+path+'/'+'pdf'+'/'+filename)
       elif(type=="video"):
           return redirect(app.config['CLOUDFRONT_DOMAIN']+'/'+path+'/'+'video'+'/'+ filename)
       elif(type=="thumbnail"):
           return redirect(app.config['CLOUDFRONT_DOMAIN']+'/'+path+'/'+'thumbnail'+'/'+ filename)
       elif(type=="audio"):
           return redirect(app.config['CLOUDFRONT_DOMAIN']+'/'+path+'/'+'video'+'/'+'audio'+'/'+filename)
       elif(type=="manifest"):
           return redirect(app.config['CLOUDFRONT_DOMAIN']+'/'+path+'/'+'video'+'/'+filename)
       elif(type=="videoqualities"):
           return redirect(app.config['CLOUDFRONT_DOMAIN']+'/'+path+'/'+'video'+'/'+filepath+'/'+filename)

@app.route('/media/uploads/<path:video_id>')
def uploaded_file(video_id):
    "route to watch a video"
    usermodel = db.session.query(models.Videometa).get(video_id)
    usermodel.view_no=usermodel.view_no+1
    if_qualities=True
    if not usermodel.videoqualities:
        if_qualities=False
        res = result.AsyncResult(video_id)
        if(res.status == 'SUCCESS'):
              newmsg = models.Usermsg(
              usermodel.username, "video_encoding done of video_id:{0}".format(video_id), False)
              db.session.add(newmsg)
              usermodel.videoqualities = ','.join(res.result)
              #os.rmdir(app.config['UPLOAD_FOLDER']+video_id)
    db.session.commit()
    usercomment = db.session.query(models.VideoComments.serial_c, models.VideoComments.contents, models.VideoComments.username, models.VideoComments.published) \
        .filter_by(video_id=video_id) \
        .all()
    return render_template("videowatch.html",usermodel=usermodel,video_id=video_id,usercomment=usercomment,file_src=filesrc,if_qualities=if_qualities)


@app.route('/media/profile/<path:filename>')
def uploaded_icons(filename):
    "make url and send icons"
    return redirect(app.config['CLOUDFRONT_DOMAIN']+'/'+app.config['UPLOAD_ICON_FOLDER']+
                               filename)

@app.route('/profiles/<username>')
def username_out(username):
       "route to view usr info. Accessible to all different template and user specific has different template"
       if(db.session.query(models.Userextended).get(username) != None):
          if(session.get('username')!=username):
             return render_template('user_profile.html',username=username)
          else:
              msg= db.session.query(models.Usermsg).filter_by(username=session['username']).all()
              return render_template('user_data.html',username=username,msg=msg)
       else:
              abort(404)


def make_imagesquare(im, fill_color=(0, 0, 0, 0)):
       x, y = im.size
       size = max(x, y)
       new_im = Image.new('RGBA', (size, size), fill_color)
       new_im.paste(im, (int((size - x) / 2), int((size - y) / 2)))
       return new_im

def make_icon_file(filename,username):
       "generates icons files for profile image at 64x64 and saves it in user folder"
       test_image = Image.open(filename)
       new_squareimage = make_imagesquare(test_image)
       filename_noext = filename.rsplit('.', 1)[0]
       maxsize=max(new_squareimage.size)
       if(maxsize>64):
              new_squareimage.save(os.path.join(app.config['UPLOAD_ICON_FOLDER'],filename_noext+'64'+'.'+'ico'), sizes=[(64, 64)])
              aws_upload(app.config['UPLOAD_ICON_FOLDER']+filename_noext+'64'+'.' +
                         'ico', app.config['UPLOAD_ICON_FOLDER']+filename_noext+'64'+'.'+'ico')
              os.remove(app.config['UPLOAD_ICON_FOLDER']+filename_noext+'64'+'.'+'ico')
       else:
           new_squareimage.save(os.path.join(
               app.config['UPLOAD_ICON_FOLDER'], filename_noext+'verysmall'+'.'+'ico'))
           aws_upload(app.config['UPLOAD_ICON_FOLDER']+
                      filename_noext+'verysmall'+'.'+'ico', app.config['UPLOAD_ICON_FOLDER'] +filename_noext+'verysmall'+'.'+'ico')
           os.remove(app.config['UPLOAD_ICON_FOLDER'] +
                     filename_noext+'verysmall'+'.'+'ico')

@app.context_processor
def utility_processor():
    def get_user_photo(username):
        usermodel = db.session.query(
            models.Userextended).get(username)
        return usermodel.icon_photo_path
    def get_user_detail(username):
        usermodel = db.session.query(models.Userextended).get(username)
        firstname = usermodel.first_name
        secondname = usermodel.second_name
        user_description = usermodel.user_description
        institution = usermodel.institution
        teacher = usermodel.teacher
        arr=dict(firstname=firstname,secondname=secondname,user_description=user_description,institution=institution,teacher=teacher)
        return arr
    def get_video_id(username):
        usermodel = db.session.query(models.Videometa.video_id,models.Videometa.title,models.Videometa.description,models.Videometa.published,models.Videometa.likes,models.Videometa.view_no,models.Videometa.video_file,models.Videometa.pres_file,models.Videometa.thumbnail_file,models.Videometa.videoqualities) \
            .filter_by(username=username) \
            .all()
        return usermodel

    def get_video_thumbnail(video_id, filename):
        return redirect(app.config['CLOUDFRONT_DOMAIN']+'/'+app.config['UPLOAD_FOLDER']+ video_id+'/'+ 'thumbnail'+'/'+ filename)

    return dict(get_user_photo=get_user_photo,get_user_detail=get_user_detail,get_video_id=get_video_id,get_video_thumbnail=get_video_thumbnail)



@app.route("/edit/profile")
@login_required
def profile_edit():
    "edit your profile"
    username = session['username']
    usermodel = db.session.query(models.Userextended).get(username)
    return render_template("edit_profile.html",usermodel=usermodel)

@app.route("/createcontinue",methods=["GET","POST"])
@login_required
def createcontinue():
       "continue to create profile,fill user detail"
       if flask.request.method == "POST":
              firstname = flask.request.values.get('firstname')
              secondname = flask.request.values.get('secondname')
              description = flask.request.values.get('description')
              email = flask.request.values.get('email')
              institution = flask.request.values.get('institution')
              teacher = flask.request.values.get('teacher')
              icon_file = flask.request.files['avatarid']

              #procssing of user input here
              if(teacher == 'True'):
                     teacher = True
              else:
                     teacher = False
              
              icon_file_path = None
              if(icon_file and icon_file.filename != "" and allowed_file(icon_file.filename)):
                     try:
                            filename=uuid.uuid4()
                            filename=filename.hex
                            filename = filename+'.'+icon_file.filename.rsplit('.', 1)[1]
                            icon_file.save(
                                app.config['UPLOAD_ICON_FOLDER'] + filename)
                            aws_upload(
                                app.config['UPLOAD_ICON_FOLDER'] + filename, app.config['UPLOAD_ICON_FOLDER'] + filename)  #save file to s3
                            os.remove(
                                app.config['UPLOAD_ICON_FOLDER'] + filename)
                            icon_file_path = filename
                     except:
                            return render_template('create-profile-continued.html',error="not allowed file",code=305)
              else:
                     icon_file_path=app.config['ICON_FILE']
              if(firstname == ""):
                     flask.flash('No first name')
                     return render_template("create-profile-continued.html", error="insert first name", code=401)
              #user processing ends here

              usermodel = db.session.query(models.Userextended).get(session["username"])
              if(usermodel is None):
                     return redirect("/",error="fatal error",code=401)
              usermodel.first_name=firstname
              usermodel.second_name=secondname
              usermodel.email=email
              usermodel.user_description=description
              usermodel.icon_photo_path=icon_file_path
              usermodel.institution=institution
              usermodel.teacher=teacher
              db.session.commit()
              return redirect("/",code=200);
       return "NULL"

              
              
def datamodelusers(username,password):
       """initialise all tables for user when created"""
       #sensitive commands dont change order
       new_user=models.Users(username,password)
       new_user_continued_null=models.Userextended(username,"User")
       db.session.add(new_user)
       db.session.commit()
       db.session.add(new_user_continued_null)
       db.session.commit()



@app.route("/login",methods=["GET","POST"])
@app_limiter.limit("25 per day")
def login():
       "login function"
       if flask.request.method == "POST":
            username = flask.request.values.get('userid')
            password = flask.request.values.get('passid')
            remme = flask.request.values.get("remme")
            if(username and password):
                   try:
                          usermodel = db.session.query(
                              models.Users).get(username)
                          assert(usermodel!=None)
                          if(usermodel.password_verify(password)):
                                 session["username"] = username
                                 session["if_logged"] = True
                                 current_user=models.Current_user(username,True,True)
                                 if(remme==1):
                                     session.permanent = True
                                 return redirect("/",code=302)
                          else:
                                 return render_template("login.html",error="Password doesnot match.",code=401)
                   except OSError:
                            return render_template("login.html", error="Temporary Error.Try later.",code=400)
                   except AssertionError:
                            return render_template("login.html", error="Username doesnot exists.",code=401)
       return render_template("login.html",code=200)

@app.route('/logout')
def logout():
   "logout function "
   # remove the username from the session if it is there
   session.pop('username', None)
   session.pop('if_logged',None)
   current_user = models.Current_user(None, False, False)
   return redirect('/',code=302)

@app.route("/data",methods=["GET",'POST'])
@app_limiter.limit("15 per day")
def data():
       "recieve username and password for profile creation"
       if flask.request.method == 'POST':
            username = str(flask.request.values.get('userid'))
            password = str(flask.request.values.get('passid'))
            if(username!="" and password!=""):
                   try:
                          datamodelusers(username,password)
                          #f=open(f"data/{username}.csv","w")
                          #f.write(username+",")
                          #f.write(passhash+",")
                          #f.write("###")     #to end the file end,simply
                          #f.close()
                          session["username"]=username
                          session["if_logged"]=True
                          current_user = models.Current_user(
                              username, True, True)
                          return render_template("create-profile-continued.html", code=200)
                   except OSError:
                            return "couldnot create.Temporary error",500
                   except:
                            return render_template("create-profile.html",error="Username exists",code=401)
       else:
              return "no credentials recieved",401
       return "NULL"

@app.route('/edit/video/<video_id>')
@login_required
def edit_videometa(video_id):
       "renders form template to change video data"
       return render_template('video_edit.html',video_id=video_id)

@app.route('/changevideo',methods=['POST'])
@login_required
def changevideo():
       "change the data of video after upload"
       username=session['username']
       if flask.request.method == "POST":
           title = flask.request.values.get('title')
           description = flask.request.values.get('description')
           video_id = flask.request.values.get('video_id')
           records = db.session.query(models.Videometa).get(video_id)
           if(records != None):
                  if(username == records.username.rstrip()):
                         records.title = title
                         records.description = description
                         records.search_index = models.Videometa.searchindextsvector(title)
                         db.session.commit()
                         return "done",302
                  else:
                         abort(403)
           else:
                   abort(404)
           return " "
       return "none"
            
@app.route('/trending_page',methods=['GET','POST'])
def trending_page():
       "sends trending videos with 20 videos in json"
       if(flask.request.method=="POST"):
              word = flask.request.values.get('page')
              page = int(word) if word.isdigit() else None
              record_query=None
              try:
                   record_query = db.session.query(models.Videometa).order_by(
                     models.Videometa.likes).paginate(page, 20, False)
              except:
                     record_query=None
              if(record_query==None):
                     return None
              total = record_query.total
              record_items = record_query.items
              res=[]
              if(record_items!=None):
                 res=[[i.video_id,i.username,i.title,i.description,i.view_no,i.likes,i.published,i.thumbnail_file] for i in record_items]
              return flask.jsonify(res)


@app.route('/search_bar')
def search_bar(page=1):
       "search page with trending viedos"
       record_query = db.session.query(models.Videometa).order_by(
              models.Videometa.view_no.desc()).paginate(page, 20, False)
       total = record_query.total
       record_items = record_query.items
       return render_template("search_bar.html",usermodel=record_items)

@app.route("/search",methods=['GET'])
def search():
       "implemetation of search videos"
       if flask.request.method == 'GET':
              search_string = flask.request.values.get('searchstring')
              regexn = r"[^a-zA-Z0-9]"
              arr_search=re.split(regexn,search_string)
              arr_search=list(filter(None, arr_search))
              res_string=" | ".join(arr_search)
              usermodel = db.session.query(models.Videometa).filter(
                  models.Videometa.search_index.op('@@')(func.to_tsquery(res_string))
              ).order_by(func.ts_rank(func.to_tsvector(models.Videometa.search_index),func.to_tsquery(res_string)).desc()).all()
              return render_template("search_result.html",usermodel=usermodel,search_string=search_string)

@app.route("/send_comments",methods=['POST'])
@login_required
def send_comments():
       "add comments to server database"
       comment = flask.request.values.get('comment')
       video_id= flask.request.values.get('video_id')
       new_user= models.VideoComments(video_id,session['username'],comment)
       db.session.add(new_user)
       db.session.commit()
       return "comment added",200

@app.route('/send_replies',methods=['POST'])
@login_required
def send_replies():
       "add replies to server database"
       serial_c = flask.request.values.get('serial_c')
       video_id = flask.request.values.get('video_id')
       reply = flask.request.values.get('reply')
       new_user = models.Replies(video_id, serial_c,session['username'],reply)
       db.session.add(new_user)
       db.session.commit()
       return "reply added", 200

@app.route("/get_replies",methods=['GET'])
def get_replies():
       "send replies to user"
       serial_c = flask.request.values.get('serial_c')
       video_id = flask.request.values.get('video_id')
       replies_model = db.session.query(models.Replies.serial_r,models.Replies.username,models.Replies.published,models.Replies.contents).filter_by(video_id=video_id).filter_by(serial_c=serial_c).all()
       json_string=[]
       if(replies_model!=None):
              json_string=[[replies_models.serial_r,replies_models.username,replies_models.published,replies_models.contents] for replies_models in replies_model]
       return flask.jsonify(json_string)
       
@app.route("/get_comments",methods=['GET'])
def get_comments():
       "send comments to user"
       video_id=flask.request.values.get('video_id')
       comments_model = db.session.query(models.VideoComments.serial_c,models.VideoComments.username,models.VideoComments.published,models.VideoComments.contents).filter_by(video_id=video_id).all()
       json_string=[]
       if(comments_model!=None):
              json_string=[[i.serial_c,i.username,i.published,i.contents] for i in comments_model]
       return flask.jsonify(json_string)

@app.route("/deleteaccount")
@login_required
def deleteaccount():
              "delete a user if logged"
              userextends = models.Userextended.query.get(session['username'])
              db.session.delete(userextends)
              db.session.commit()
              user = models.Users.query.get(session['username'])
              db.session.delete(user)
              db.session.commit()
              return redirect("/logout")

@app.route('/videoupload')
@login_required
def videoupload():
       "render template to upload a video"
       return render_template("upload_videos.html")

@app.route("/task-running/<task_id>")
def running(task_id):
    res = result.AsyncResult(task_id)
    return res


@celery.task(max_retries=3, autoretry_for=(subprocess.CalledProcessError, botocore.exceptions.EndpointConnectionError))
def videoprocess(path,file,video_id,pwd,aws_bucket,aws_access_key_id,aws_secret_access_key,aws_region):
            "celery functioin to process and add to database videos"
            # if user does not select file, browser also
            # submit an empty part without filename
            
            #enc = Encoder(file,(path+'/'+'video'),aws_bucket,aws_access_key_id,aws_secret_access_key,aws_region)
            adptenc= AdptEncoder(file,(path+'/'+'video'),aws_bucket,aws_access_key_id,aws_secret_access_key,aws_region)
            resenc=[]
            try:
              resenc=adptenc.start_encode()
            except subprocess.CalledProcessError:
                   os.chdir(pwd)
                   resenc = adptenc.start_encode()
            return resenc

@app.route('/uploading', methods=['GET', 'POST'])
@login_required
def uploading():
    "recieve upload videos form and process and store in the server"
    if flask.request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in flask.request.files:
            flash('No file part')
            return redirect(flask.request.url)
        file = flask.request.files['file']
        pdfs = flask.request.files['pdf-file']
        thumbnail= flask.request.files['thumbnail']
        title = flask.request.values.get('title')
        description = flask.request.values.get('description')
        if file.filename == '' or title == "" or thumbnail.filename == "":
              flash('No selected file or title or thumbnail')
              return redirect(flask.request.url)
        if file and allowed_file(file.filename):
            video_id = uuid.uuid4().hex
            # if user does not select file, browser also
            # submit an empty part without filename
            
            #create a dir
            path = app.config['UPLOAD_FOLDER']+video_id
            os.makedirs(path+'/'+'video')
            os.makedirs(path+'/'+'pdf')
            os.makedirs(path+'/'+'thumbnail')
            video_ext = file.filename.rsplit('.', 1)[1].lower()
            filename = video_id + '.' + video_ext
            file.save(path+'/'+'video'+'/'+filename)
            aws_upload(path+'/' + 'video'+'/' + filename,
                       path+'/' + 'video'+'/' + filename)
            pdfname, thumbname = None, None
            if(thumbnail.filename != "" or allowed_file(thumbnail.filename)):
               thumbnail_ext = thumbnail.filename.rsplit('.', 1)[1].lower()
               thumbname = video_id + '.' + thumbnail_ext
               thumbnail.save(path+'/'+'thumbnail'+'/'+thumbname)
               aws_upload(
                   path+'/' + 'thumbnail'+'/' + thumbname, path+'/' + 'thumbnail'+'/' + thumbname)
               os.remove(path+'/'+'thumbnail'+'/'+thumbname)
            if(pdfs.filename != "" or allowed_file(pdfs.filename) == True):
               pdfs_ext = pdfs.filename.rsplit('.', 1)[1].lower()
               pdfname = video_id + '.'+pdfs_ext
               pdfs.save(os.path.join(
                   path,'pdf', pdfname))
               aws_upload(
                   path+'/' + 'pdf'+'/' + pdfname, path+'/' + 'pdf'+'/' + pdfname)
               os.remove(os.path.join(
                   path, 'pdf', pdfname))
            videoencode = videoprocess.apply_async(args=[path,
                                                         path+'/'+'video'+'/' + filename,  video_id, os.getcwd(), app.config['AWS_BUCKET'], app.config['AWS_ACCESS_KEY_ID'], app.config['AWS_SECRET_ACCESS_KEY'], app.config['AWS_REGION']], task_id=video_id, timeout=1, retry=True, retry_policy={
                                                        'max_retries': 3,
                                                        'interval_start': 0,
                                                        'interval_step': 1,
                                                        'interval_max': 4, })
            new_user = models.Videometa(
                video_id, session["username"], title, description, filename, pdfname, thumbname)
            db.session.add(new_user)
            db.session.commit()
            return redirect('/media/uploads/{}'.format(video_id)),200
        
    return "none",403

# Run Flask if the __name__ variable is equal to __main__
#added below for heroku
def helli():
       app.secret_key = os.environ['SECRET_KEY']
       app.config['SESSION_TYPE'] = 'filesystem'
       app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=31)
       app.config["SQLALCHEMY_DATABASE_URI"] = environ['DATABASE_URL']
       app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
       app.config['UPLOAD_ICON_FOLDER'] = "media/profile/"
       app.config['ICON_FILE']="default_profile.png"
       app.config["ALLOWED_EXTENSIONS"] = ALLOWED_EXTENSIONS
       app.config['UPLOADED_PHOTOS_DEST'] = "media/profile/"
       app.config['UPLOAD_FOLDER']="media/uploads/"
       app.config['UPLOAD_PRES_FOLDER']="media/presfile"
       app.config['USE_X_SENDFILE']=False
       app.config['MAX_CONTENT_LENGTH']=1.8*pow(10,9)  #1 GB limit
       app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379'
       app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379'
       app.config['CELERYD_TASK_SOFT_TIME_LIMIT'] = 60*60*9
       app.config['CELERY_TRACK_STARTED'] = True
       #app.config['SESSION_COOKIE_SECURE']=True
       #app.config['CSRF_COOKIE_SECURE']=True
       app.config['REMEMBER_COOKIE_HTTPONLY']=True
#ended heroku things

if __name__ == "__main__":
       app.secret_key = os.urandom(16)
       app.config['SESSION_TYPE'] = 'filesystem'
       app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=31)
       app.config["SQLALCHEMY_DATABASE_URI"] = environ['DATABASE_URL']
       app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
       app.config['UPLOAD_ICON_FOLDER'] = "media/profile/"
       app.config['ICON_FILE']="default_profile.png"
       app.config["ALLOWED_EXTENSIONS"] = ALLOWED_EXTENSIONS
       app.config['UPLOADED_PHOTOS_DEST'] = "media/profile/"
       app.config['UPLOAD_FOLDER']="media/uploads/"
       app.config['UPLOAD_PRES_FOLDER']="media/presfile"
       app.config['USE_X_SENDFILE']=False
       app.config['MAX_CONTENT_LENGTH'] = 1.8*pow(10, 9)  # 1.8 GB limit
       app.config['CELERY_BROKER_URL']='redis://localhost:6379'
       app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379'
       app.config['CELERYD_TASK_SOFT_TIME_LIMIT'] = 60*60*9
       app.config['CELERY_TRACK_STARTED']=True
       app.config['AWS_ACCESS_KEY_ID'] = environ['AWS_ACCESS_KEY_ID']
       app.config['AWS_SECRET_ACCESS_KEY'] = environ['AWS_SECRET_ACCESS_KEY']
       app.config['AWS_BUCKET']=environ['AWS_BUCKET']
       app.config['AWS_REGION']=environ['AWS_REGION']
       app.config['CLOUDFRONT_DOMAIN'] = environ['AWS_REGION']
       #app.config['SESSION_COOKIE_SECURE']=True
       app.config['REMEMBER_COOKIE_HTTPONLY']=True
       app.run(debug=True,threaded=True)
