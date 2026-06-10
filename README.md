# Solar Tracking ☀️

Aplicativo web desenvolvido em **Flask** para consulta, monitoramento e comparação da geração de energia solar real versus estimada de painéis fotovoltaicos.  
O sistema consome dados meteorológicos reais diretamente da API do **NASA POWER** para estimar o potencial de geração com base no tamanho, eficiência e rastreamento dos painéis de cada cliente.

---

## 🚀 Funcionalidades Principais
*   **Autenticação de Usuário:** Login seguro para administradores (`admin` / `admin`).
*   **Controle de Clientes:** Listagem, cadastro e edição de clientes (área dos painéis, eficiência e tipo de rastreamento).
*   **Integração NASA POWER:** Consumo de radiação solar diária real e temperatura média para a localidade.
*   **Cálculo de Estimativa:** Cálculo matemático do rendimento teórico esperado.
*   **Dashboard Interativo:** Gráficos comparativos detalhados (Chart.js no front-end e Matplotlib no back-end) e tabela de histórico do período.

---

## ⚙️ Tecnologias Utilizadas
*   **Backend:** Python 3, Flask, SQLAlchemy, SQLite (padrão de desenvolvimento) e MySQL (opção de produção).
*   **Frontend:** HTML5, CSS3 (Design System responsivo em tema escuro), JavaScript e Chart.js.
*   **APIs e Bibliotecas:** NASA POWER API, Matplotlib, Requests, PyMySQL.

---

## 🛠️ Como Executar o Projeto

### 1. Clonar o Repositório
```bash
git clone https://github.com/Braatz-dan/solar-tracking.git
cd solar-tracking
```

### 2. Criar e Ativar o Ambiente Virtual (venv)
```bash
# Criar o ambiente virtual
python -m venv venv

# Ativar no Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Ativar no Linux / macOS
source venv/bin/activate
```

### 3. Instalar as Dependências
```bash
python -m pip install -r requirements.txt
```

### 4. Executar a Aplicação
O projeto vem configurado para usar o **SQLite por padrão** (gerando um arquivo local chamado `solar_tracking.db` na pasta `instance`), o que permite testar tudo de imediato sem instalar nada extra.

Rode o comando:
```bash
python run.py
```
Acesse a aplicação no navegador em: **`http://127.0.0.1:5000`**

*   **Credenciais de Acesso padrão:**
    *   **Usuário:** `admin`
    *   **Senha:** `admin`

---

## 👥 Integrantes do Grupo
*   André Willian de Souza
*   Bruno Henrique Nunes da Rocha
*   Daniel Vitor Rodrigues Braatz
*   Gabriela Pereira Almagro
*   Luis Marcio Guitti
