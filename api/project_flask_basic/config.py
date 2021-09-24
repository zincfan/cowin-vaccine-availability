import os
from datetime import timedelta

ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'tif',
                          'mp4', 'mp3', 'webm', 'mpg' 'mpeg', 'avi', 'wmv', 'mov', 'pptx', 'ppt','aac','opus'])

class Config:
    SECRET_KEY = os.environ['SECRET_KEY']
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(days=31)
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_ICON_FOLDER = "media/profile/"
    ICON_FILE="default_profile.png"
    ALLOWED_EXTENSIONS = ALLOWED_EXTENSIONS
    UPLOADED_PHOTOS_DEST = "media/profile/"
    UPLOAD_FOLDER="media/uploads/"
    UPLOAD_PRES_FOLDER="media/presfile"
    USE_X_SENDFILE=False
    MAX_CONTENT_LENGTH = 1.8*pow(10, 9)  # 1.8 GB limit
    CELERY_BROKER_URL='redis://redis:6379'
    CELERY_RESULT_BACKEND = 'redis://redis:6379'
    CELERYD_TASK_SOFT_TIME_LIMIT = 60*60*9
    CELERY_TRACK_STARTED=True
    AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
    AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
    AWS_BUCKET=os.environ['AWS_BUCKET']
    AWS_REGION=os.environ['AWS_REGION']
    CLOUDFRONT_DOMAIN = os.environ['CLOUDFRONT_DOMAIN']
    #SESSION_COOKIE_SECURE=True
    STATIC_FOLDER=os.environ['CLOUDFRONT_DOMAIN']+'/'
    REMEMBER_COOKIE_HTTPONLY=True

#if not SECRET_KEY:
    #raise ValueError("No SECRET_KEY set for Flask application")
