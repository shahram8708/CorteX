import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'CorteX-6708b3d-4a2e-8c0f-1a5f7b9c6d2e'
    SQLALCHEMY_DATABASE_URI = 'postgresql://cortex_ufm2_user:eNOilAH83ZFiOw1jxrVcRTJUCx0CknN1@dpg-d0459mbuibrs73ap00ng-a.singapore-postgres.render.com/cortex_ufm2'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = "smtp.gmail.com"  
    MAIL_PORT = 587  
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = "multimosaic.help@gmail.com"  
    MAIL_PASSWORD = "fzrj elkl cvkw aggr"  
    MAIL_DEFAULT_SENDER = "multimosaic.help@gmail.com"
