import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'this-is-a-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///foodbridge.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = "smtp.gmail.com"  
    MAIL_PORT = 587  
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = "multimosaic.help@gmail.com"  
    MAIL_PASSWORD = "fzrj elkl cvkw aggr"  
    MAIL_DEFAULT_SENDER = "multimosaic.help@gmail.com"
