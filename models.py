from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    name_ = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # 'admin' или 'user'
    contacts = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        """Хеширует пароль перед сохранением"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Проверяет пароль"""
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        """Возвращает уникальный идентификатор пользователя для Flask-Login"""
        return str(self.user_id)
