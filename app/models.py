from app import db

# Tabela para guardar os dados cadastrais e especificações técnicas dos clientes
class Clientes(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False) # Nome único pra não dar conflito nos filtros do dashboard
    endereco = db.Column(db.String(200))
    telefone = db.Column(db.String(20))
    area_paineis = db.Column(db.Float, nullable=False) # Área total dos painéis em m²
    tipo_tracking = db.Column(db.Enum('fixo', 'single', 'dual'), nullable=False) # Tipo de rastreamento (fixo, 1 eixo ou 2 eixos)
    eficiencia = db.Column(db.Float, nullable=False, default=0.18) # Eficiência dos painéis em decimal (ex: 18% vira 0.18)

    def __repr__(self):
        return f"<Clientes {self.nome}>"

# Tabela com dados climáticos históricos de radiação e temperatura
class Clima(db.Model):
    __tablename__ = 'clima'
    cliente = db.Column(db.String(100), primary_key=True)
    data = db.Column(db.Date, primary_key=True)
    temperatura = db.Column(db.Float) # Temperatura média diária em °C
    radiacao = db.Column(db.Float)  # Radiação solar acumulada no dia em MJ/m²/dia

    def __repr__(self):
        return f"<Clima {self.cliente} - {self.data}>"

# Tabela com a produção real de energia registrada pelos inversores
class Paineis(db.Model):
    __tablename__ = 'paineis'
    data = db.Column(db.Date, primary_key=True)
    cliente_id = db.Column(db.Integer, primary_key=True)
    energia_real = db.Column(db.Float, nullable=False) # Energia real gerada no dia em kWh

    def __repr__(self):
        return f"<Paineis ID:{self.cliente_id} - {self.data}>"
