# /cerebro/main_refactored.py
# Versão refatorada e modular do arquivo main.py original

import sys

from cerebro.app import run_main_app, cleanup_app 

def main():
    """Função principal de entrada do programa."""
    print("--- Iniciando HayDay Test Tool ---")
    
    exit_code = 1 
    try:
        exit_code = run_main_app() 
    except Exception as e:
        print(f"Erro crítico na aplicação: {e}")
        exit_code = 1 
    finally:
        cleanup_app()
        
    return exit_code

if __name__ == "__main__":
    sys.exit(main())