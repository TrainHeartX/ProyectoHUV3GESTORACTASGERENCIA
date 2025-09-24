# huggingface.py (Versión final que lee desde config.dat encriptado)

import os
import json
import logging
from huggingface_hub import InferenceClient
from cryptography.fernet import Fernet
import sys

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE SEGURIDAD Y MODELO
# -----------------------------------------------------------------------------

# ¡Pega aquí la misma clave secreta que usaste en tu script encriptador.py!
ENCRYPTION_KEY = b'VlxXay5JLWZlJI8VoSlwfJEfPIEFSoNOlTx0s8TzINs='

# Nombre del archivo de configuración encriptado que tu aplicación buscará.
# Debe coincidir con el resultado de tu encriptador.py
ENCRYPTED_CONFIG_FILENAME = 'config.dat'

# Modelo de IA a utilizar.
MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"

# -----------------------------------------------------------------------------
# LÓGICA DE CARGA Y DESENCRIPTACIÓN
# -----------------------------------------------------------------------------

# Configura un logger básico para ver posibles problemas
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_path(relative_path):
    """Función de ayuda para encontrar archivos en modo normal y empaquetado (PyInstaller)."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

def _load_hf_token_from_encrypted_file():
    config_path = get_path(ENCRYPTED_CONFIG_FILENAME)
    if ENCRYPTION_KEY == b'AQUI_VA_TU_CLAVE_SEGURA_GENERADA':
        logging.error("¡La clave de encriptación no ha sido configurada! Edita el script.")
        return None
    try:
        logging.info(f"Intentando leer: {config_path}")
               
        # Leemos el contenido completo del archivo, pero como texto.
        with open(config_path, 'r', encoding='utf-8') as f:
            full_content = f.read().strip()

        # Dividimos el contenido usando tu separador personalizado ':::'
        parts = full_content.split(':::')
        
        # Verificamos que el formato sea el esperado (3 partes)
        if len(parts) != 3:
            logging.error(f"El formato del archivo '{config_path}' es incorrecto. Se esperaba 'clave:::extension:::datos_encriptados'.")
            return None

        # La parte que nos interesa es la última (índice 2)
        encrypted_token_str = parts[2]
        
        # Convertimos la parte encriptada (que es un string) a bytes, que es lo que Fernet necesita.
        encrypted_token_bytes = encrypted_token_str.encode('utf-8')

        # Ahora el proceso de desencriptación es el mismo, pero con los datos correctos
        fernet = Fernet(ENCRYPTION_KEY)
        decrypted_bytes = fernet.decrypt(encrypted_token_bytes) # Usamos los bytes que extrajimos
        
        # --- FIN DE LA MODIFICACIÓN ---
        
        config_data = json.loads(decrypted_bytes.decode('utf-8'))
        hf_token = config_data.get("HF_TOKEN")
        
        if not hf_token:
            logging.error(f"'HF_TOKEN' no encontrado dentro de los datos desencriptados.")
            return None
            
        logging.info("Token de Hugging Face cargado y desencriptado exitosamente.")
        return hf_token

    except FileNotFoundError:
        logging.error(f"No se encontró '{config_path}'. Asegúrate de que esté junto al .exe.")
        return None
    except Exception as e:
        # Añadimos más detalles al log para futuras depuraciones
        logging.error(f"Error al procesar '{config_path}': {e}", exc_info=True)
        return None

# --- INICIALIZACIÓN DEL CLIENTE DE INFERENCIA ---
# Se inicializa una sola vez cuando se importa el módulo.

client = None
try:
    # 1. Llamamos a la función para obtener el token del archivo encriptado.
    token = _load_hf_token_from_encrypted_file()
    
    if not token:
        # Si no se pudo obtener el token, lanzamos un error para detener la inicialización.
        raise ValueError("No se pudo obtener el token de Hugging Face desde el archivo de configuración.")
    
    # 2. Creamos el cliente de inferencia con el token obtenido.
    client = InferenceClient(
        model=MODEL_ID,
        token=token
    )
    logging.info(f"Cliente de Hugging Face inicializado correctamente para el modelo: {MODEL_ID}")

except Exception as e:
    logging.error(f"Error fatal durante la inicialización del cliente de IA: {e}")
    # 'client' permanecerá como None, y la función de resumen devolverá un error.

# -----------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL (SIN CAMBIOS)
# -----------------------------------------------------------------------------

def resumir_intervencion_hf(texto_literal, hablante, participantes):
    """
    Toma una transcripción literal y utiliza un LLM de Hugging Face
    para generar una entrada de acta formal.
    """
    if not client:
        return "[Error Crítico: El cliente de IA no está disponible. Revise los logs de inicio.]"

    if not texto_literal or texto_literal.startswith("["):
        return texto_literal

    lista_participantes_str = ", ".join(participantes)
    
    prompt = f"""
Eres un asistente ejecutivo experto en la redacción de actas de reuniones de gerencia. Tu tarea es tomar la transcripción literal de una intervención y convertirla en una entrada de acta formal, concisa y profesional.

**Instrucciones estrictas:**
1.  **Enfoque:** Extrae únicamente la idea principal, la decisión, la propuesta o la preocupación clave.
2.  **Formato:** Redacta en tercera persona y tiempo pasado (ej. "propuso", "señaló", "expresó").
3.  **Limpieza:** Ignora absolutamente todas las muletillas ("eh", "bueno", "o sea"), repeticiones y frases de relleno.
4.  **Brevedad:** El resultado debe ser una o dos oraciones claras y directas. No agregues introducciones ni conclusiones.
5.  **Fidelidad:** No inventes información que no esté en la transcripción.

**Contexto de la Reunión:**
- **Participantes:** {lista_participantes_str}
- **Hablante actual:** {hablante}

**Transcripción a Procesar:**
---
{texto_literal}
---

**Entrada de Acta (Produce únicamente el texto para el acta):**
"""

    try:
        logging.info(f"Enviando petición a Hugging Face para el hablante: {hablante}")
        
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.3,
            stream=False
        )
        
        resumen = response.choices[0].message.content.strip()
        logging.info(f"Respuesta recibida de Hugging Face para {hablante}")
        return resumen

    except Exception as e:
        logging.error(f"Error en la llamada a la API de Hugging Face: {e}")
        return f"[Error al procesar con IA: {str(e)}]"