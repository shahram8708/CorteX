import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'CorteX-6708b3d-4a2e-8c0f-1a5f7b9c6d2e'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db' 
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = "smtp.gmail.com"  
    MAIL_PORT = 587  
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = "multimosaic.help@gmail.com"  
    MAIL_PASSWORD = "fzrj elkl cvkw aggr"  
    MAIL_DEFAULT_SENDER = "multimosaic.help@gmail.com"
    ADMIN_USERNAME = 'cortex'
    ADMIN_PASSWORD = 'cortex@6708'

