from flask_hello import db
from sqlalchemy.sql import func
import sqlalchemy
from werkzeug.security import generate_password_hash, check_password_hash

#specific to user view 
class Users(db.Model):
    __tablename__ = 'users'
    username = db.Column(db.String(50),primary_key=True)

    password_hash = db.Column(db.String(), index=False, nullable=False,unique=False)

    created_on = db.Column(db.DateTime(timezone=True), default=func.now(), nullable=False)

    last_password_changed = db.Column(db.DateTime(timezone=True),default=func.now(),nullable=False)

    last_login = db.Column(db.DateTime(timezone=True),default=func.now(),nullable=False)

    is_authentic = db.Column(db.Boolean(), nullable=False, default=True)

    def __init__(self, username,password):
        self.username=username
        self.password_hash = generate_password_hash(password, "sha256")

    def password_verify(self,password):
        return check_password_hash(self.password_hash,password);
    

    def __repr__(self):
        return '<id {}>'.format(self.username)


#specific to public view
class Userextended(db.Model):
    __tablename__ = 'userextended'

    username = db.Column(db.String(50),db.ForeignKey('users.username'), primary_key=True,nullable=False)

    first_name = db.Column(db.String(50),nullable=False)

    second_name = db.Column(db.String(40),nullable=True)

    icon_photo_path = db.Column(db.String(70),nullable=False)

    user_description = db.Column(db.String(225),nullable=True)

    institution = db.Column(db.String(40), nullable=True)

    teacher = db.Column(db.Boolean(),nullable=False,default=False)

    email = db.Column(db.String(30),nullable=True)

    last_active = db.Column(db.DateTime(timezone=True),default=func.now(), nullable=False)

    upload_folder = db.Column(db.String(30),default="media/uploads")

    def __init__(self, username,first_name, second_name=None, user_description = None, email = None, institution= None, teacher =False, icon_photo_path='default_profile.png',upload_folder ="media/uploads"):
        self.username=username
        self.first_name=first_name
        self.second_name=second_name
        self.user_description = user_description
        self.email = email
        self.icon_photo_path = icon_photo_path
        self.institution = institution
        self.teacher = teacher
        self.upload_folder = upload_folder
    
    

class Videometa(db.Model):
    __tablename__ = "videometa"

    video_id = db.Column(db.String(100),nullable=False,primary_key=True)

    username = db.Column(db.String(50),db.ForeignKey('users.username'),nullable=False)

    title = db.Column(db.String(300),nullable=False)

    description = db.Column(db.String(2000))

    view_no = db.Column(db.Integer(),default=0,nullable=False)

    published = db.Column(db.DateTime(timezone=True), default=func.now(), nullable=False)

    likes = db.Column(db.Integer(),default=0,nullable=False)

    video_file = db.Column(db.String(100),nullable=False)

    search_index = db.Column(db.String(400),nullable=False)

    pres_file = db.Column(db.String(100))

    thumbnail_file = db.Column(db.String(100))

    videoqualities = db.Column(db.String(200))
    
    @staticmethod
    def searchindextsvector(text):
        "returns search index tsvector for a given string"
        return sqlalchemy.func.to_tsvector(text)

    def __init__(self,video_id,username,title,description,video_file,pres_file=None,thumbnail_file=None):
        self.video_id=video_id
        self.username=username
        self.title=title
        self.description=description
        self.video_file=video_file
        self.search_index = sqlalchemy.func.to_tsvector(title)
        self.pres_file=pres_file
        self.thumbnail_file=thumbnail_file
    
    def __repr__(self):
        return '<video_id {}>'.format(self.video_id)

class VideoComments(db.Model):
    __tablename__ = "videocomments"

    serial_c = db.Column(db.Integer(),primary_key=True,autoincrement=True)

    video_id = db.Column(db.String(100), db.ForeignKey('videometa.video_id'),nullable=False)

    username = db.Column(db.String(50), db.ForeignKey(
        'users.username'), nullable=False)
    
    published = db.Column(db.DateTime(timezone=True),
                          default=func.now(), nullable=False)
    
    contents = db.Column(db.String(2000))

    def __init__(self,video_id,username,contents):
        self.video_id = video_id
        self.username = username
        self.contents = contents
    
    

class Replies(db.Model):
    __tablename__ = "replies"

    serial_r = db.Column(db.Integer(), primary_key=True, autoincrement=True)

    video_id = db.Column(db.String(100), db.ForeignKey('videometa.video_id'), nullable=False)

    username = db.Column(db.String(50), db.ForeignKey(
        'users.username'), nullable=False)

    serial_c = db.Column(db.Integer(), db.ForeignKey(
        'videocomments.serial_c'), nullable=False)

    published = db.Column(db.DateTime(timezone=True),
                          default=func.now(), nullable=False)
    
    contents = db.Column(db.String(2000))

    def __init__(self,video_id,serial_c,username,contents):
        self.video_id=video_id
        self.serial_c=serial_c
        self.username=username
        self.contents=contents

    
    
class Usermsg(db.Model):
    __tablename__='usermsg'

    serial_m = db.Column(db.Integer(), primary_key=True, autoincrement=True)

    username = db.Column(db.String(50), db.ForeignKey(
        'users.username'), nullable=False)
    
    msg = db.Column(db.String(500),nullable=False)

    published = db.Column(db.DateTime(timezone=True),
                          default=func.now(), nullable=False)

    if_sentmail = db.Column(db.Boolean(), nullable=False, default=False)

    def __init__(self,username,msg,if_sentmail):
        self.username=username
        self.msg=msg
        self.if_sentmail=if_sentmail

    



class Current_user():
    def username(self):
        return self.username
    def if_logged(self):
        return self.if_logged
    def is_active(self):
        return self.is_active
    def __init__(self,username,if_logged,is_active):
        self.username=username
        self.if_logged=if_logged
        self.is_active=is_active
    def __repr__(self):
        return "<username {}".format(self.username)
