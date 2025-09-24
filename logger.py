##logger.py:
import sys
import logging
import os
from datetime import datetime

_logger_configurado = False

def _get_log_filepath():
    """Determina la ruta correcta para el archivo de log."""
    try:
        base_path = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.abspath(os.path.dirname(__file__))
        return os.path.join(base_path, 'evaris_main.log')
    except Exception:
        # Failsafe si todo lo demás falla, guarda en el directorio de trabajo actual
        return 'evaris_main.log'

def _handle_unhandled_exception(exc_type, exc_value, exc_traceback):
    """
    Función que será llamada por Python para cualquier excepción no capturada.
    Esto evita la recursión infinita de redirigir stderr al logger.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # No registrar el Ctrl+C del usuario como un error.
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # Registra el error no manejado con el nivel CRITICAL.
    # exc_info=True adjunta el traceback completo al mensaje de log.
    logging.critical("Excepción no manejada atrapada por el hook:", exc_info=(exc_type, exc_value, exc_traceback))

class StreamToLogger:
    """
    Clase que redirige una corriente (solo stdout para prints) a un logger.
    """
    def __init__(self, logger_instance, log_level):
        self.logger = logger_instance
        self.log_level = log_level

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            if line.strip():
                self.logger.log(self.log_level, line.strip())

    def flush(self):
        # Necesario para la interfaz de stream.
        pass

def setup_global_logger():
    """
    Configura el logger global para toda la aplicación.
    Debe llamarse UNA SOLA VEZ al inicio del programa principal.
    """
    global _logger_configurado
    if _logger_configurado:
        return

    log_filepath = _get_log_filepath()

    # Configuración base del logging para escribir a un archivo
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(threadName)-10s | %(message)s',
        handlers=[
            logging.FileHandler(log_filepath, mode='a', encoding='utf-8')
        ]
    )

    # --- CAMBIO DE ESTRATEGIA ---
    # 1. Asignamos nuestro hook para excepciones fatales. ESTA ES LA SOLUCIÓN CLAVE.
    sys.excepthook = _handle_unhandled_exception

    # 2. Redirigimos solo stdout (para capturar los `print`), lo cual es menos peligroso.
    #    Ya no redirigimos stderr, evitando el bucle de recursión.
    sys.stdout = StreamToLogger(logging.getLogger('STDOUT'), logging.INFO)

    _logger_configurado = True
    
    # Mensaje inicial para confirmar que el logger está vivo
    prog_name = os.path.basename(sys.executable if getattr(sys, 'frozen', False) else sys.argv[0])
    print("="*60)
    print(f"LOGGER GLOBAL INICIALIZADO POR: {prog_name}")
    print(f"Toda la salida de 'print' y los errores fatales serán registrados.")
    print(f"Archivo de log: {log_filepath}")
    print(f"Hora de inicio de sesión: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)