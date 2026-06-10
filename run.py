import os
import webbrowser
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Abre o navegador automaticamente só na thread principal (evita abrir duas vezes no debug)
    # Servidor rodando localmente no endereço padrão do Flask
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        webbrowser.open("http://127.0.0.1:5000")
    
    app.run(debug=True)
