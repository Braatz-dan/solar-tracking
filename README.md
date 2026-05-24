# Solar Tracking

Aplicativo web desenvolvido em **Flask** para consulta e comparação de energia solar real versus estimada.  
O sistema utiliza dados de painéis solares e informações climáticas (NASA POWER) para calcular a energia prevista e comparar com a energia medida.

---

## 🚀 Tecnologias utilizadas
- Python 3
- Flask
- SQLAlchemy
- MySQL (PyMySQL)
- Matplotlib
- MySQL Workbench (para gerenciar o banco de dados)

---

## ⚙️ Como executar o projeto

1. Clonar o repositório
   ```bash
   git clone https://github.com/Braatz-dan/solar-tracking.git
   cd solar-tracking

2. Criar ambiente virtual
  python -m venv venv
  venv\Scripts\activate   # Windows
  source venv/bin/activate # Linux/Mac

3. Instalar dependências
  pip install -r requirements.txt

4. Configurar banco de dados MySQL
  Instale e abra o MySQL Workbench.
  Crie um banco de dados chamado: solar_tracking.
  Ajuste usuário e senha no arquivo app.py (linha de conexão com o banco).

5. Rodar aplicação
  python app.py
  Acesse em: http://127.0.0.1:5000

