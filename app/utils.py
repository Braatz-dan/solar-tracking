from datetime import timedelta
import requests
import matplotlib
matplotlib.use('Agg')  # Configura para rodar sem precisar de uma interface gráfica
import matplotlib.pyplot as plt
import io
import base64

def buscar_dados_nasa(cliente_nome, start_date, end_date):
    """
    Conecta na API oficial da NASA POWER pra obter a radiação solar e 
    temperatura reais de Sorocaba/SP (onde fica a Facens).
    """
    # Formata as datas no padrão AAAAMMDD que a API da NASA exige
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    
    # Coordenadas geográficas de Sorocaba/SP (Facens)
    lat = -23.5015
    lon = -47.4526
    
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        "parameters": "ALLSKY_SFC_SW_DWN,T2M",
        "community": "RE",
        "latitude": lat,
        "longitude": lon,
        "start": start_str,
        "end": end_str,
        "format": "JSON"
    }
    
    dados = []
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            res_json = response.json()
            parameters = res_json.get("properties", {}).get("parameter", {})
            temp_dict = parameters.get("T2M", {})
            rad_dict = parameters.get("ALLSKY_SFC_SW_DWN", {})
            
            # Loop de datas do período selecionado
            from datetime import datetime
            dia = start_date
            while dia <= end_date:
                date_key = dia.strftime("%Y%m%d")
                
                # Pega as leituras retornadas pela API da NASA
                temp = temp_dict.get(date_key)
                rad_kwh = rad_dict.get(date_key)
                
                # Trata valor -999.0 que a NASA retorna quando a leitura falha
                if temp == -999.0:
                    temp = None
                if rad_kwh == -999.0 or rad_kwh is None:
                    rad_mj = None
                else:
                    # Converte de kWh/m²/dia para MJ/m²/dia (multiplica por 3.6) pro banco continuar compatível
                    rad_mj = rad_kwh * 3.6
                
                dados.append({
                    "data": dia,
                    "temperatura": temp,
                    "radiacao": rad_mj
                })
                dia += timedelta(days=1)
                
            return dados
    except Exception as e:
        print(f"Erro ao conectar na API da NASA: {e}")
        
    # Plano B: Se a internet cair ou a API falhar, roda uma simulação com base no dia do mês
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

def gerar_grafico_matplotlib(dados, cliente_nome):
    """
    Cria um gráfico de barras/linhas usando o Matplotlib no backend.
    Fizemos uma estilização escura pra ornar com o visual moderno do app.
    """
    datas_plot = [d["data"] for d in dados if d["estimado"] is not None]
    reais_vals = [d["real"] for d in dados if d["estimado"] is not None]
    estimados_vals = [d["estimado"] for d in dados if d["estimado"] is not None]

    if not datas_plot:
        return ""

    try:
        plt.figure(figsize=(10, 4.5))
        
        # Deixa o fundo combinando com o tema escuro do dashboard
        plt.gcf().patch.set_facecolor('#152030')  # Fundo externo
        ax = plt.gca()
        ax.set_facecolor('#0e1622')  # Fundo interno do gráfico
        
        # Grid e eixos com visual discreto
        ax.grid(True, color='#1e293b', linestyle='--', linewidth=0.5)
        ax.tick_params(colors='#94a3b8', labelsize=9)
        for spine in ax.spines.values():
            spine.set_color('#1e293b')
            
        # Desenha as linhas da geração real (verde) e estimada (azul)
        ax.plot(datas_plot, reais_vals, label=f"Real - {cliente_nome}", color="#2acb78", marker='o', linewidth=2, markersize=5)
        ax.plot(datas_plot, estimados_vals, label="Estimado", color="#2bb1db", marker='s', linewidth=2, linestyle='--', markersize=5)
        
        # Textos e legenda do gráfico
        ax.set_title("Comparativo de Energia: Real vs. Estimado", color='#f8fafc', fontsize=12, pad=15, weight='bold')
        ax.set_ylabel("Energia (kWh)", color='#94a3b8', fontsize=10)
        
        leg = ax.legend(facecolor='#152030', edgecolor='#1e293b', loc='upper left')
        for text in leg.get_texts():
            text.set_color('#f8fafc')
            
        plt.xticks(rotation=30)
        plt.tight_layout()
        
        # Salva o gráfico gerado na memória em formato base64 pra renderizar direto no HTML
        img = io.BytesIO()
        plt.savefig(img, format="png", facecolor='#152030', dpi=120)
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode()
        plt.close()
        return plot_url
    except Exception as e:
        print(f"Erro ao gerar gráfico Matplotlib: {e}")
        return ""
