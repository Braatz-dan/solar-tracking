import os

class Config:
    # A gente usa SQLite por padrão pra rodar local sem precisar subir um servidor MySQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///solar_tracking.db'
    
    # Desativa isso aqui pra economizar memória e evitar alertas chatos do SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Chave secreta pra sessão do usuário (se não tiver no env, usa uma padrão de teste)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'solar-tracking-secret-key-12345'
