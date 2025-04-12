"""
Módulo utilitário para auxiliar no encerramento seguro de threads
"""

import threading
import time
import ctypes
import inspect
import sys

def _async_raise(tid, exctype):
    """Levanta uma exceção em uma thread específica pelo seu identificador"""
    if not inspect.isclass(exctype):
        raise TypeError("Only types can be raised (not instances)")
    
    # Descobre a versão do Python
    if sys.version_info[0] >= 3:
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), ctypes.py_object(exctype))
    else:
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
        
    if res == 0:
        raise ValueError("Thread ID inválido")
    elif res > 1:
        # Se mais de uma thread foi afetada, algo está errado
        # Redefine o estado para evitar erros em cascata
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
        raise SystemError("PyThreadState_SetAsyncExc falhou")

def terminate_thread(thread):
    """Termina uma thread Python de forma forçada.
    
    Isso deve ser usado apenas em último caso quando uma thread
    não responde a sinais normais de encerramento.
    
    Args:
        thread: O objeto threading.Thread a ser terminado
    
    Returns:
        bool: True se a thread foi terminada, False caso contrário
    """
    if not thread or not thread.is_alive():
        return False
        
    try:
        # Obtém o ID nativo da thread
        tid = thread.ident
        if not tid:
            return False
            
        # Tenta levantar SystemExit na thread
        _async_raise(tid, SystemExit)
        return True
    except Exception as e:
        print(f"⚠️ Erro ao tentar terminar a thread: {e}")
        return False

def wait_for_thread_termination(thread, timeout=5.0, terminate_on_timeout=True):
    """Espera que uma thread termine dentro de um tempo limite.
    
    Se a thread não terminar dentro do tempo limite e terminate_on_timeout for True,
    tenta encerrar a thread de forma forçada.
    
    Args:
        thread: O objeto threading.Thread a esperar
        timeout: Tempo máximo de espera em segundos
        terminate_on_timeout: Se True, tenta forçar o encerramento após o timeout
        
    Returns:
        bool: True se a thread terminou normalmente, False se foi encerrada forçadamente
    """
    if not thread or not thread.is_alive():
        return True
        
    # Tenta juntar a thread com timeout
    thread.join(timeout=timeout)
    
    # Verifica se ainda está viva
    if not thread.is_alive():
        return True
        
    # Se chegou aqui, a thread não terminou dentro do tempo
    print(f"⚠️ Thread {thread.name} não terminou em {timeout} segundos.")
    
    # Tenta terminar forçadamente se solicitado
    if terminate_on_timeout:
        print("🚫 Tentando terminar forçadamente a thread...")
        success = terminate_thread(thread)
        
        if success:
            print("✅ Thread terminada forçadamente.")
        else:
            print("❌ Falha ao terminar forçadamente a thread.")
            
        return False
    
    return False

def terminate_all_daemon_threads(timeout_per_thread=2.0):
    """Tenta encerrar todas as threads daemon que ainda estão em execução.
    
    Isso é útil para garantir que todos os recursos sejam liberados ao encerrar o programa.
    Primeiro tenta uma abordagem gentil (join), depois tenta encerrar forçadamente se necessário.
    
    Args:
        timeout_per_thread: Tempo máximo de espera por thread em segundos
    """
    # Obtém todas as threads ativas
    active_threads = threading.enumerate()
    main_thread = threading.main_thread()
    current_thread = threading.current_thread()
    
    # Filtra apenas threads daemon, excluindo a thread principal e a atual
    daemon_threads = [t for t in active_threads if 
                     t is not main_thread and 
                     t is not current_thread and 
                     t.daemon and 
                     t.is_alive()]
    
    if not daemon_threads:
        return
        
    print(f"🧹 Limpando {len(daemon_threads)} threads daemon ainda ativas...")
    
    # Tenta encerrar cada thread
    for thread in daemon_threads:
        print(f"⏳ Aguardando thread '{thread.name}' encerrar...")
        wait_for_thread_termination(thread, timeout=timeout_per_thread, terminate_on_timeout=True)
    
    # Verifica se conseguiu encerrar todas
    remaining = [t for t in daemon_threads if t.is_alive()]
    if remaining:
        print(f"⚠️ {len(remaining)} threads daemon ainda persistem, mas são daemon então não bloquearão o encerramento.")
    else:
        print("✅ Todas as threads daemon foram encerradas com sucesso.")
