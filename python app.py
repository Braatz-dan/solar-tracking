from flask import Flask, request, render_template_string
from flask_sqlalchemy import SQLAlchemy
import matplotlib.pyplot as plt
import io, base64, webbrowser
from datetime import datetime, date, timedelta
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://solar:senha123@localhost/solar_tracking'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# -----------------------
# Modezs
class Clientes(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True)
    endereco = db.Column(db.String(200))
    telefone = db.Column(db.String(20))
    area_paineis = db.Column(db.Float)
    tipo_tracking = db.Column(db.Enum('fixo','single','dual'))

class Clima(db.Model):
    __tablename__ = 'clima'
    # chave composta: cliente + data
    cliente = db.Column(db.String(100), primary_key=True)
    data = db.Column(db.Date, primary_key=True)
    temperatura = db.Column(db.Float)
    radiacao = db.Column(db.Float)  # MJ/m²/dia

class Paineis(db.Model):
    __tablename__ = 'paineis'
    data = db.Column(db.Date, primary_key=True)
    cliente_id = db.Column(db.Integer, primary_key=True)
    energia_real = db.Column(db.Float)

# -----------------------
# HTML deeer
HTML_PAGE = """
<!doctype html>
<html>
<head><title>Solar Tracking</title></head>
<body>
    <h2>Consulta de Energia Solar</h2>
    <form method="get" action="/relatorio">
        Data inicial (YYYYMMDD): <input type="text" name="start"><br><br>
        Data final (YYYYMMDD): <input type="text" name="end"><br><br>
        Cliente: <select name="cliente">
            {% for c in clientes %}
                <option value="{{ c.nome }}">{{ c.nome }}</option>
            {% endfor %}
        </select><br><br>
        <input type="submit" value="Consultar">
    </form>
    {% if table %}
        <h3>Resultados:</h3>
        {{ table|safe }}
        {% if plot %}
            <h3>Gráfico:</h3>
            <img src="data:image/png;base64,{{ plot }}" />
        {% endif %}
    {% endif %}
</body>
</html>
"""

# -----------------------
# Função para buscar dados da NASA

def buscar_dados_nasa(cliente_nome, start_date, end_date):
    """
    Retorna lista de dicts:
    [
      {"data": date_obj, "temperatura": float, "radiacao": float},
      ...
    ]
    Substitua o corpo por chamada real à API POWER da NASA.
    """
    dados = []
    dia = start_date
    base = 18.0
    while dia <= end_date:
        offset = (dia.day % 7) - 3
        radiacao = max(0.0, base + offset * 1.5)
        dados.append({
            "data": dia,
            "temperatura": 25.0 + (offset * 0.5),
            "radiacao": radiacao
        })
        dia += timedelta(days=1)
    return dados

# -----------------------
# Rotas
@app.route("/", methods=["GET"])
def index():
    clientes = Clientes.query.all()
    return render_template_string(HTML_PAGE, clientes=clientes)

@app.route("/relatorio", methods=["GET"])
def relatorio():
    start = request.args.get("start")
    end = request.args.get("end")
    cliente_nome = request.args.get("cliente")

    clientes = Clientes.query.all()

    if not start or not end or not cliente_nome:
        return render_template_string(
            HTML_PAGE,
            clientes=clientes,
            table="<p style='color:red'>Informe datas e cliente.</p>",
            plot=""
        )

    start_date = datetime.strptime(start, "%Y%m%d").date()
    end_date = datetime.strptime(end, "%Y%m%d").date()

    # Limite até ontem
    hoje = date.today()
    limite = hoje - timedelta(days=1)
    if end_date > limite:
        end_date = limite

    cliente_info = Clientes.query.filter_by(nome=cliente_nome).first()
    if not cliente_info:
        return render_template_string(
            HTML_PAGE,
            clientes=clientes,
            table=f"<p style='color:red'>Cliente {cliente_nome} não encontrado.</p>",
            plot=""
        )

    # Buscar dados reais (paineis) para o cliente no período
    reais = db.session.query(Paineis, Clientes).join(Clientes, Paineis.cliente_id == Clientes.id).filter(
        Paineis.data.between(start_date, end_date),
        Clientes.nome == cliente_nome
    ).all()

    # Se não houver dados reais, retorna mensagem
    if not reais:
        return render_template_string(
            HTML_PAGE,
            clientes=clientes,
            table=f"<p style='color:red'>Nenhum dado encontrado para {cliente_nome} nesse período.</p>",
            plot=""
        )

    # Buscar registros de clima apenas para o cliente consultado
    clima_existente = Clima.query.filter(
        Clima.cliente == cliente_nome,
        Clima.data.between(start_date, end_date)
    ).all()

    # Mapear por data
    clima_map = {c.data: c for c in clima_existente}

    # Identificar datas faltantes ou inválidas (radiacao NULL ou negativa)
    datas_necessarias = set(r.data for r, _ in reais)
    datas_para_buscar = []
    for d in datas_necessarias:
        c = clima_map.get(d)
        if c is None or c.radiacao is None or c.radiacao < 0:
            datas_para_buscar.append(d)

    # Se houver datas a buscar, chamar NASA apenas para essas datas que nao tiver
    if datas_para_buscar:
        buscar_inicio = min(datas_para_buscar)
        buscar_fim = max(datas_para_buscar)
        novos = buscar_dados_nasa(cliente_nome, buscar_inicio, buscar_fim)

        # Salvar apenas as datas que precisamos; usar merge = upsert seguro
        for nd in novos:
            if nd['data'] in datas_para_buscar:
                clima_obj = Clima(cliente=cliente_nome, data=nd['data'],
                                  temperatura=nd.get('temperatura'),
                                  radiacao=nd.get('radiacao'))
                db.session.merge(clima_obj)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            for nd in novos:
                if nd['data'] in datas_para_buscar:
                    existing = Clima.query.filter_by(cliente=cliente_nome, data=nd['data']).first()
                    if existing:
                        existing.temperatura = nd.get('temperatura')
                        existing.radiacao = nd.get('radiacao')
                    else:
                        clima_obj = Clima(cliente=cliente_nome, data=nd['data'],
                                          temperatura=nd.get('temperatura'),
                                          radiacao=nd.get('radiacao'))
                        db.session.add(clima_obj)
            db.session.commit()

        # recarregar clima_map
        clima_existente = Clima.query.filter(
            Clima.cliente == cliente_nome,
            Clima.data.between(start_date, end_date)
        ).all()
        clima_map = {c.data: c for c in clima_existente}

    # usar o radiacao do mesmo dia
    fatores = {"fixo": 1.0, "single": 1.2, "dual": 1.3}
    eficiencia = 0.18
    dados = []
    for r, c in reais:
        clima_dia = clima_map.get(r.data)
        if not clima_dia or clima_dia.radiacao is None:
            dados.append({
                "data": r.data,
                "cliente": c.nome,
                "real": r.energia_real,
                "estimado": None,
                "diferenca": None
            })
            continue

        irradiancia_kwh_m2 = clima_dia.radiacao * 0.2778
        fator_tracking = fatores.get(c.tipo_tracking, 1.0)
        energia_estim = irradiancia_kwh_m2 * c.area_paineis * eficiencia * fator_tracking
        diferenca = r.energia_real - energia_estim
        dados.append({
            "data": r.data,
            "cliente": c.nome,
            "real": r.energia_real,
            "estimado": energia_estim,
            "diferenca": diferenca
        })

    # Montar tabela HTML
    rows = []
    for d in sorted(dados, key=lambda x: x['data']):
        estim = f"{d['estimado']:.2f}" if d['estimado'] is not None else "N/A"
        diff = f"{d['diferenca']:.2f}" if d['diferenca'] is not None else "N/A"
        rows.append(f"<tr><td>{d['data']}</td><td>{d['cliente']}</td><td>{d['real']:.2f}</td><td>{estim}</td><td>{diff}</td></tr>")
    table_html = "<table border=1><tr><th>Data</th><th>Cliente</th><th>Real (kWh)</th><th>Estimado (kWh)</th><th>Diferença (kWh)</th></tr>" + "".join(rows) + "</table>"

    # Gráfico (apenas pontos com estimado não-vaziu)
    datas_plot = [d["data"] for d in dados if d["estimado"] is not None]
    reais_vals = [d["real"] for d in dados if d["estimado"] is not None]
    estimados_vals = [d["estimado"] for d in dados if d["estimado"] is not None]

    plt.figure(figsize=(8,4))
    if datas_plot:
        plt.plot(datas_plot, reais_vals, label=f"Real - {cliente_nome}", color="green", marker='o')
        plt.plot(datas_plot, estimados_vals, label="Estimado", color="blue", marker='x')
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        img = io.BytesIO()
        plt.savefig(img, format="png")
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode()
    else:
        plot_url = ""

    return render_template_string(HTML_PAGE, clientes=clientes, table=table_html, plot=plot_url)

# -----------------------
# Exec
if __name__ == "__main__":
    import os
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        webbrowser.open("http://127.0.0.1:5000")
    app.run(debug=True)
