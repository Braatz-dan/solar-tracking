from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    # Importa os modelos aqui pro SQLAlchemy saber quais tabelas criar no banco
    from app import models

    # Registra o blueprint das rotas que a gente definiu em routes.py
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # Cria as tabelas do banco e gera uns dados de teste se for a primeira vez rodando
    with app.app_context():
        db.create_all()
        from app.models import Clientes, Paineis, Clima
        if Clientes.query.first() is None:
            import random
            from datetime import date, timedelta
            
            # Cadastra os 3 clientes do nosso grupo/projeto com eficiências e tamanhos diferentes
            c1 = Clientes(nome="Daniel", endereco="Rua A, 123", telefone="11999999999", area_paineis=20.5, tipo_tracking="fixo", eficiencia=0.16)
            c2 = Clientes(nome="Gabriela", endereco="Rua B, 456", telefone="11888888888", area_paineis=35.0, tipo_tracking="single", eficiencia=0.18)
            c3 = Clientes(nome="Luis", endereco="Rua C, 789", telefone="11777777777", area_paineis=50.2, tipo_tracking="dual", eficiencia=0.21)
            db.session.add_all([c1, c2, c3])
            db.session.commit()
            
            # Gera um histórico de radiação e clima de 25/05 até 30/06 pro gráfico não ficar vazio
            start_date = date(2026, 5, 25)
            end_date = date(2026, 6, 30)
            
            import random
            dia = start_date
            while dia <= end_date:
                # 1. Curva do Daniel: começa normal, cai de 05/06 até 12/06 e depois volta a subir pro normal (manutenção)
                if dia < date(2026, 6, 5):
                    daniel_real = 22.0 + random.uniform(-0.8, 0.8)
                elif dia <= date(2026, 6, 12):
                    # Mantém em queda/baixo até o dia 12/06
                    dias_pos_queda = (dia - date(2026, 6, 5)).days
                    daniel_real = max(3.0, 22.0 - (dias_pos_queda + 1) * 3.5 + random.uniform(-0.5, 0.5))
                else:
                    # Sobe de volta para a média normal
                    daniel_real = 22.0 + random.uniform(-0.8, 0.8)
                
                # 2. Curva da Gabriela: estável em 35-40 kWh até 10/06, depois sobe para a média de 55-65 kWh
                if dia <= date(2026, 6, 10):
                    gabriela_real = 37.5 + random.uniform(-1.0, 1.0)
                else:
                    gabriela_real = 60.0 + random.uniform(-5.0, 5.0)
                
                # 3. Curva do Luis: cai em 30/05, se recupera em 03/06 para 65-70 kWh e depois do dia 10/06 sobe para 60-65 kWh
                if dia < date(2026, 5, 30):
                    luis_real = 67.5 + random.uniform(-2.5, 2.5)
                elif dia < date(2026, 6, 3):
                    luis_real = 15.0 + random.uniform(-1.0, 1.0)
                elif dia <= date(2026, 6, 10):
                    luis_real = 67.5 + random.uniform(-2.5, 2.5)
                else:
                    luis_real = 62.5 + random.uniform(-2.5, 2.5)
                
                # Salva as leituras reais de geração de energia de cada um
                db.session.add(Paineis(data=dia, cliente_id=c1.id, energia_real=daniel_real))
                db.session.add(Paineis(data=dia, cliente_id=c2.id, energia_real=gabriela_real))
                db.session.add(Paineis(data=dia, cliente_id=c3.id, energia_real=luis_real))
                
                # Grava o clima de Sorocaba/SP (mesmo valor pra todos, já que a cidade é a mesma)
                temp_dia = 24.0 + random.uniform(-2.0, 2.0)
                rad_dia = 20.0 + random.uniform(-3.0, 3.0)
                db.session.add(Clima(cliente=c1.nome, data=dia, temperatura=temp_dia, radiacao=rad_dia))
                db.session.add(Clima(cliente=c2.nome, data=dia, temperatura=temp_dia, radiacao=rad_dia))
                db.session.add(Clima(cliente=c3.nome, data=dia, temperatura=temp_dia, radiacao=rad_dia))
                
                dia += timedelta(days=1)
            
            db.session.commit()

    return app
