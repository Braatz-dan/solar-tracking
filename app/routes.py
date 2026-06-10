from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime, date, timedelta
from app.models import Clientes, Clima, Paineis
from app import db
from app.utils import buscar_dados_nasa, gerar_grafico_matplotlib
from sqlalchemy.exc import IntegrityError
import json

main_bp = Blueprint('main', __name__)

@main_bp.before_app_request
def require_login():
    # Deixa carregar arquivos estáticos (CSS, imagens) e a página de login sem barrar o usuário
    if request.endpoint == 'static' or request.endpoint == 'main.login':
        return
    if not session.get('logged_in'):
        return redirect(url_for('main.login'))

@main_bp.route("/login", methods=["GET", "POST"])
def login():
    # Se já tiver logado, manda direto pra home do dashboard
    if session.get('logged_in'):
        return redirect(url_for('main.index'))
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        # Credenciais padrão que o professor pediu pro teste
        if username == "admin" and password == "admin":
            session['logged_in'] = True
            flash("Login efetuado com sucesso!", "success")
            return redirect(url_for('main.index'))
        else:
            flash("Usuário ou senha incorretos.", "danger")
            
    return render_template("login.html")

@main_bp.route("/logout")
def logout():
    # Apaga a sessão do usuário e manda de volta pra página de login
    session.pop('logged_in', None)
    flash("Sessão encerrada com sucesso.", "info")
    return redirect(url_for('main.login'))

def parse_date(date_str):
    """
    Funçãozinha pra converter a string de data vinda do formulário 
    ou da API para um objeto date do Python.
    """
    if not date_str:
        return None
    try:
        if '-' in date_str:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        return datetime.strptime(date_str, "%Y%m%d").date()
    except ValueError:
        return None

@main_bp.route("/", methods=["GET"])
def index():
    clientes = Clientes.query.all()
    
    # Pega os filtros de busca que o usuário selecionou no dashboard
    start = request.args.get("start")
    end = request.args.get("end")
    cliente_nome = request.args.get("cliente")
    
    # Se abrir a página sem nenhum filtro, mostra o painel sem resultados/limpo
    if not start and not end and not cliente_nome:
        return render_template("dashboard.html", clientes=clientes, has_results=False)

    # Valida se todas as informações foram preenchidas corretamente
    if not start or not end or not cliente_nome:
        error_msg = "Por favor, informe o período inicial, final e o cliente para consulta."
        return render_template("dashboard.html", clientes=clientes, has_results=False, error_msg=error_msg)

    start_date = parse_date(start)
    end_date = parse_date(end)

    if not start_date or not end_date:
        error_msg = "Formato de data inválido. Use AAAA-MM-DD."
        return render_template("dashboard.html", clientes=clientes, has_results=False, error_msg=error_msg)

    # Só permite consultar até o dia de ontem, porque os dados de hoje ainda não fecharam
    hoje = date.today()
    limite = hoje - timedelta(days=1)
    if end_date > limite:
        end_date = limite

    cliente_info = Clientes.query.filter_by(nome=cliente_nome).first()
    if not cliente_info:
        error_msg = f"Cliente '{cliente_nome}' não encontrado."
        return render_template("dashboard.html", clientes=clientes, has_results=False, error_msg=error_msg)

    # Busca no banco a geração real de energia que já foi registrada
    reais = db.session.query(Paineis, Clientes).join(Clientes, Paineis.cliente_id == Clientes.id).filter(
        Paineis.data.between(start_date, end_date),
        Clientes.nome == cliente_nome
    ).all()

    if not reais:
        error_msg = f"Nenhum dado real de geração encontrado para '{cliente_nome}' no período informado."
        return render_template("dashboard.html", clientes=clientes, has_results=False, error_msg=error_msg)

    # Puxa o clima daquele período que já tá guardado no nosso banco
    clima_existente = Clima.query.filter(
        Clima.cliente == cliente_nome,
        Clima.data.between(start_date, end_date)
    ).all()

    clima_map = {c.data: c for c in clima_existente}

    # Confere quais dias da consulta estão sem dados climáticos
    datas_necessarias = set(r.data for r, _ in reais)
    datas_para_buscar = []
    for d in datas_necessarias:
        c = clima_map.get(d)
        if c is None or c.radiacao is None or c.radiacao < 0:
            datas_para_buscar.append(d)

    # Se faltar algum dia, a gente bate lá na API da NASA pra buscar a temperatura e a radiação
    if datas_para_buscar:
        buscar_inicio = min(datas_para_buscar)
        buscar_fim = max(datas_para_buscar)
        novos = buscar_dados_nasa(cliente_nome, buscar_inicio, buscar_fim)

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

        # Recarrega os dados do clima do banco agora que a API da NASA respondeu e salvou tudo
        clima_existente = Clima.query.filter(
            Clima.cliente == cliente_nome,
            Clima.data.between(start_date, end_date)
        ).all()
        clima_map = {c.data: c for c in clima_existente}

    # Fórmulas de estimativa: cada tipo de rastreamento tem um multiplicador de eficiência
    fatores = {"fixo": 1.0, "single": 1.2, "dual": 1.3}
    eficiencia = cliente_info.eficiencia if (cliente_info and cliente_info.eficiencia) else 0.18
    dados = []
    
    total_real = 0.0
    total_estimado = 0.0
    soma_temperatura = 0.0
    clima_contados = 0
    
    for r, c in reais:
        clima_dia = clima_map.get(r.data)
        real_val = r.energia_real
        total_real += real_val
        
        if clima_dia and clima_dia.temperatura is not None:
            soma_temperatura += clima_dia.temperatura
            clima_contados += 1

        if not clima_dia or clima_dia.radiacao is None:
            dados.append({
                "data": r.data,
                "cliente": c.nome,
                "real": real_val,
                "estimado": None,
                "diferenca": None,
                "temperatura": clima_dia.temperatura if clima_dia else None,
                "radiacao": clima_dia.radiacao if clima_dia else None
            })
            continue

        irradiancia_kwh_m2 = clima_dia.radiacao * 0.2778
        fator_tracking = fatores.get(c.tipo_tracking, 1.0)
        energia_estim = irradiancia_kwh_m2 * c.area_paineis * eficiencia * fator_tracking
        total_estimado += energia_estim
        diferenca = real_val - energia_estim
        
        dados.append({
            "data": r.data,
            "cliente": c.nome,
            "real": real_val,
            "estimado": energia_estim,
            "diferenca": diferenca,
            "temperatura": clima_dia.temperatura,
            "radiacao": clima_dia.radiacao
        })

    # Ordena o histórico por dia pra tabela e gráfico ficarem arrumados
    dados = sorted(dados, key=lambda x: x['data'])

    # Calcula o status com base nos últimos 3 dias
    # Se render 40% menos do que deveria (ou seja, real < 0.6 * estimado), entra em PERIGO.
    status = "Estável"
    status_classe = "success"
    
    dados_com_estimativa = [d for d in dados if d["estimado"] is not None]
    if len(dados_com_estimativa) >= 3:
        ultimos_3 = dados_com_estimativa[-3:]
        real_3d = sum(d["real"] for d in ultimos_3)
        estimado_3d = sum(d["estimado"] for d in ultimos_3)
        if estimado_3d > 0 and (real_3d / estimado_3d) < 0.6:
            status = "Perigo"
            status_classe = "danger"
    elif len(dados_com_estimativa) > 0:
        real_total_disp = sum(d["real"] for d in dados_com_estimativa)
        estimado_total_disp = sum(d["estimado"] for d in dados_com_estimativa)
        if estimado_total_disp > 0 and (real_total_disp / estimado_total_disp) < 0.6:
            status = "Perigo"
            status_classe = "danger"

    # Soma os totais e faz a média climática do período selecionado pros cards de KPI
    dif_total = total_real - total_estimado
    desempenho_porcentagem = (total_real / total_estimado * 100) if total_estimado > 0 else 0
    temp_media = (soma_temperatura / clima_contados) if clima_contados > 0 else 0.0

    metrics = {
        "total_real": f"{total_real:,.2f}",
        "total_estimado": f"{total_estimado:,.2f}",
        "diferenca": f"{dif_total:,.2f}",
        "diferenca_classe": "success" if dif_total >= 0 else "danger",
        "desempenho": f"{desempenho_porcentagem:.1f}%",
        "temp_media": f"{temp_media:.1f}°C",
        "status": status,
        "status_classe": status_classe
    }

    # Gera a imagem do gráfico no backend usando Matplotlib (ótimo para gerar relatórios PDF/impressos)
    plot_base64 = gerar_grafico_matplotlib(dados, cliente_nome)

    # Prepara o JSON pra desenhar o gráfico interativo e animado com Chart.js no navegador
    chart_data = [{
        "data": d["data"].strftime("%d/%m/%Y"),
        "real": round(d["real"], 2),
        "estimado": round(d["estimado"], 2) if d["estimado"] is not None else None
    } for d in dados]

    return render_template(
        "dashboard.html",
        clientes=clientes,
        has_results=True,
        dados=dados,
        metrics=metrics,
        chart_data_json=json.dumps(chart_data),
        plot_base64=plot_base64,
        selected_cliente=cliente_nome,
        selected_start=start,
        selected_end=end,
        cliente_info=cliente_info
    )

# Redireciona chamadas da rota antiga (/relatorio) pra home do dashboard, evitando erros de link quebrado
@main_bp.route("/relatorio", methods=["GET"])
def relatorio_legacy():
    start = request.args.get("start")
    end = request.args.get("end")
    cliente_nome = request.args.get("cliente")
    return redirect(url_for("main.index", start=start, end=end, cliente=cliente_nome))

# --- CRUD: CADASTRO E EDIÇÃO DE CLIENTES (ÁREA DO ADMIN) ---

@main_bp.route("/clientes", methods=["GET"])
def clientes_index():
    clientes = Clientes.query.all()
    return render_template("clientes.html", clientes=clientes)

@main_bp.route("/clientes/novo", methods=["GET", "POST"])
def clientes_create():
    if request.method == "POST":
        nome = request.form.get("nome")
        endereco = request.form.get("endereco")
        telefone = request.form.get("telefone")
        
        try:
            area_paineis = float(request.form.get("area_paineis", 0))
        except ValueError:
            area_paineis = 0.0
            
        tipo_tracking = request.form.get("tipo_tracking")
        
        try:
            eficiencia = float(request.form.get("eficiencia", 18.0)) / 100.0
        except ValueError:
            eficiencia = 0.18
        
        # Validação pra garantir que os campos com asterisco foram preenchidos
        if not nome or not area_paineis or not tipo_tracking:
            flash("Por favor, preencha todos os campos obrigatórios (*).", "danger")
            return render_template("cliente_form.html", title="Cadastrar Cliente", action_url=url_for("main.clientes_create"), client=None)
            
        # Não deixa cadastrar dois clientes exatamente com o mesmo nome
        existing = Clientes.query.filter_by(nome=nome).first()
        if existing:
            flash(f"Já existe um cliente cadastrado com o nome '{nome}'.", "danger")
            return render_template("cliente_form.html", title="Cadastrar Cliente", action_url=url_for("main.clientes_create"), client=None)
            
        novo_cliente = Clientes(
            nome=nome,
            endereco=endereco,
            telefone=telefone,
            area_paineis=area_paineis,
            tipo_tracking=tipo_tracking,
            eficiencia=eficiencia
        )
        
        try:
            db.session.add(novo_cliente)
            db.session.commit()
            flash("Cliente cadastrado com sucesso!", "success")
            return redirect(url_for("main.clientes_index"))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao salvar cliente: {str(e)}", "danger")
            
    return render_template("cliente_form.html", title="Cadastrar Cliente", action_url=url_for("main.clientes_create"), client=None)

@main_bp.route("/clientes/editar/<int:id>", methods=["GET", "POST"])
def clientes_edit(id):
    cliente = Clientes.query.get_or_404(id)
    
    if request.method == "POST":
        nome = request.form.get("nome")
        endereco = request.form.get("endereco")
        telefone = request.form.get("telefone")
        
        try:
            area_paineis = float(request.form.get("area_paineis", 0))
        except ValueError:
            area_paineis = 0.0
            
        tipo_tracking = request.form.get("tipo_tracking")
        
        try:
            eficiencia = float(request.form.get("eficiencia", 18.0)) / 100.0
        except ValueError:
            eficiencia = 0.18
        
        # Validação pra garantir que não salvaram campos em branco na edição
        if not nome or not area_paineis or not tipo_tracking:
            flash("Por favor, preencha todos os campos obrigatórios (*).", "danger")
            return render_template("cliente_form.html", title="Editar Cliente", action_url=url_for("main.clientes_edit", id=id), client=cliente)
            
        # Não deixa renomear o cliente pra um nome que outro cliente já esteja usando
        existing = Clientes.query.filter(Clientes.nome == nome, Clientes.id != id).first()
        if existing:
            flash(f"Já existe outro cliente cadastrado com o nome '{nome}'.", "danger")
            return render_template("cliente_form.html", title="Editar Cliente", action_url=url_for("main.clientes_edit", id=id), client=cliente)
            
        cliente.nome = nome
        cliente.endereco = endereco
        cliente.telefone = telefone
        cliente.area_paineis = area_paineis
        cliente.tipo_tracking = tipo_tracking
        cliente.eficiencia = eficiencia
        
        try:
            db.session.commit()
            flash("Cliente atualizado com sucesso!", "success")
            return redirect(url_for("main.clientes_index"))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao atualizar cliente: {str(e)}", "danger")
            
    return render_template("cliente_form.html", title="Editar Cliente", action_url=url_for("main.clientes_edit", id=id), client=cliente)
