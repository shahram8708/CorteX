from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config
from flask_migrate import Migrate
from flask_mail import Mail

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()

login_manager = LoginManager()
login_manager.login_view = 'main.login'

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from .routes import main
    app.register_blueprint(main)

    with app.app_context():
        db.create_all()

    # @app.errorhandler(404)
    # def page_not_found(e):
    #     return render_template('404.html', message="Sorry, the page you are looking for does not exist."), 404

    # @app.errorhandler(Exception)
    # def handle_exception(e):
    #     return render_template('404.html', message="An error occurred. Please try again later."), 404

    return app
