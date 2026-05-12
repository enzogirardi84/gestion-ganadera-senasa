import os
import sys
import webbrowser
from threading import Timer

def open_browser():
    webbrowser.open("http://localhost:8501")

if __name__ == "__main__":
    print("="*60)
    print("  GESTION GANADERA SENASA - Web App")
    print("  Sistema integral de gestion veterinaria")
    print("="*60)
    print()
    print("  Iniciando servidor web...")
    print("  Abriendo navegador en http://localhost:8501")
    print()
    print("  Presiona CTRL+C para detener el servidor")
    print("="*60)
    
    Timer(2, open_browser).start()
    
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.system(f'python -m streamlit run Sanidad.py --server.port 8501 --server.address 0.0.0.0')
