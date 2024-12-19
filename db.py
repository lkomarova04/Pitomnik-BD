from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()


def init_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'  # Перенаправление на страницу логина, если пользователь не авторизован

    return app, db, login_manager
