import os

class Config:
    SECRET_KEY = 'your_secret_key_here'  # Установите секретный ключ для сессий Flask
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Настройки подключения к MySQL базе данных
    SQLALCHEMY_DATABASE_URI = 'mysql://root:25102004@localhost:3306/pitomnik'
