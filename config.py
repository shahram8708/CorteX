import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'CorteX-6708b3d-4a2e-8c0f-1a5f7b9c6d2e'
    SQLALCHEMY_DATABASE_URI = 'postgresql://cortex_5wwb_user:r3g1L6pYz1U71QW39LziaObjGnajaam6@dpg-d0465kqdbo4c73e9sqfg-a.singapore-postgres.render.com/cortex_5wwb' 
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
    REMEMBER_COOKIE_DURATION = timedelta(days=365)
    PERMANENT_SESSION_LIFETIME = timedelta(days=365)