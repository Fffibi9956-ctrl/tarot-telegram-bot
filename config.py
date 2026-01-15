import os

class Config:
    # Токен и ID загружаются ТОЛЬКО из переменных окружения (Secrets)
    BOT_TOKEN = os.environ['BOT_TOKEN']  # Значение установится на сервере Fly.io
    ADMIN_ID = int(os.environ['ADMIN_ID'])  # Значение установится на сервере Fly.io
    
    # Статусы вопросов
    STATUS_NEW = "new"
    STATUS_ANSWERED = "answered"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    
    # Роли пользователей
    ROLE_USER = "user"
    ROLE_TAROT = "tarot"
    ROLE_ADMIN = "admin"
