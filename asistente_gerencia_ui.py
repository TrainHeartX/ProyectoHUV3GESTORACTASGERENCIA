# asistente_gerencia_ui.py (VERSIÓN FINAL CON LÓGICA DE REINTENTO MEJORADA)

import tkinter as tk
from tkinter import messagebox, Listbox, simpledialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk
import os
import sys
import threading
import time
import argparse
import logging
import socket
import logger
# --- Importar módulo de lógica ---
import asistente_reuniones_gerencia_logic as arl_gerencia

# --- Función de ayuda para rutas ---
def get_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

class AsistenteGerenciaApp(ttk.Window):
    def __init__(self, theme, nombre_usuario, cargo_usuario, foto_path, ruta_datos):
        super().__init__(themename=theme)
        
        self.current_user = {"nombre": nombre_usuario, "cargo": cargo_usuario}
        self.ruta_datos_central = ruta_datos

        self.title("EVARISIS - Gestor Actas de Reuniones de Gerencia")
        self.state('zoomed')
        
        # --- Carga de recursos ---
        self.foto_usuario = self._cargar_foto_path(foto_path)
        self.iconos = self._cargar_iconos()
        self._set_app_icon()

        # --- Definición de fuentes ---
        self.FONT_TITULO = ("Segoe UI", 22, "bold")
        self.FONT_SUBTITULO = ("Segoe UI", 12)
        self.FONT_NORMAL = ("Segoe UI", 11)
        self.FONT_NOMBRE_PERFIL = ("Segoe UI", 16, "bold")

        # --- Variables de estado ---
        self.active_panel, self.acta_word, self.current_speaker = None, None, None
        self.is_recording = False
        self.reunion_participantes, self.grabacion_frames, self.participant_buttons = [], [], {}
        self.stop_event = None

        # --- Construcción de la UI ---
        self._crear_header()
        self.content_container = ttk.Frame(self, padding=(0, 10)); self.content_container.pack(fill=BOTH, expand=TRUE)
        
        self.panel_setup_gerencia = self._crear_panel_setup_gerencia(self.content_container)
        self.panel_reunion_gerencia = self._crear_panel_reunion_gerencia(self.content_container)

        self._switch_panel(self.panel_setup_gerencia)

    def _cargar_iconos(self):
        try:
            return {"back": ImageTk.PhotoImage(Image.open(get_path("imagenes/back.jpeg")).resize((24, 24), Image.Resampling.LANCZOS))}
        except Exception as e: logging.warning(f"No se pudo cargar icono 'back': {e}"); return {"back": None}
        
    def _cargar_foto_path(self, foto_path):
        if foto_path and foto_path != "SIN_FOTO" and os.path.exists(foto_path):
            try: return ImageTk.PhotoImage(Image.open(foto_path).resize((80, 80), Image.Resampling.LANCZOS))
            except Exception as e: logging.error(f"Error al cargar foto: {e}")
        return None

    def _set_app_icon(self):
        try:
            # 1. Asume que el nombre de tu icono es "GestorActasGerencia.ico" (o el que sea).
            #    La Herramienta 3 ya lo habrá empaquetado en la raíz del .exe.
            icon_path = get_path("GestorActasGerencia.ico") # <-- CAMBIA ESTE NOMBRE

            # 2. Establece el icono de la ventana. Esta es la llamada principal.
            self.iconbitmap(icon_path)
            
        except Exception as e:
            # Si falla, simplemente lo registramos, la app no debe detenerse por esto.
            logging.error(f"No se pudo cargar o establecer el icono de la ventana: {e}")
            
    def _crear_header(self):
        header_frame = ttk.Frame(self, padding=(20, 10)); header_frame.pack(fill=X)
        if self.foto_usuario: ttk.Label(header_frame, image=self.foto_usuario).pack(side=LEFT, padx=(0, 20))
        info_frame = ttk.Frame(header_frame); info_frame.pack(side=LEFT, fill=X, expand=TRUE)
        ttk.Label(info_frame, text=self.current_user["nombre"], font=self.FONT_NOMBRE_PERFIL, anchor=W).pack(fill=X)
        ttk.Label(info_frame, text=self.current_user["cargo"], font=self.FONT_SUBTITULO, bootstyle=SECONDARY, anchor=W).pack(fill=X)
        title_app_frame = ttk.Frame(header_frame); title_app_frame.pack(side=RIGHT)
        ttk.Label(title_app_frame, text="EVARISIS Gestor Actas Gerencia", font=self.FONT_TITULO, anchor=E).pack(fill=X)
        ttk.Label(title_app_frame, text="Gestor Inteligente Exclusivo del HUV para Generar Actas a partir de reuniones de gerencia", font=self.FONT_SUBTITULO, bootstyle=INFO, anchor=E).pack(fill=X)
        ttk.Separator(self, orient=HORIZONTAL).pack(fill=X, padx=20, pady=5)
        
    def _switch_panel(self, panel_a_mostrar):
        if self.active_panel: self.active_panel.pack_forget()
        self.active_panel = panel_a_mostrar
        self.active_panel.pack(fill=BOTH, expand=TRUE)

    def _crear_panel_setup_gerencia(self, parent):
        panel = ttk.Frame(parent)
        header = ttk.Frame(panel); header.pack(fill=X, pady=(0, 10))
        ttk.Label(header, text="Configuración de Reunión", font=self.FONT_SUBTITULO).pack(side=LEFT)
        btn_salir = ttk.Button(header, text=" Salir", image=self.iconos.get('back'), compound=LEFT, bootstyle="light-outline", command=self.destroy)
        btn_salir.pack(side=RIGHT)
        
        lf = ttk.Labelframe(panel, text="Seleccione los participantes (Ctrl+Click para varios)", bootstyle=INFO, padding=10)
        lf.pack(fill=BOTH, expand=TRUE, pady=5)
        
        list_frame = ttk.Frame(lf); list_frame.pack(fill=BOTH, expand=TRUE)
        self.listbox_integrantes_gerencia = Listbox(list_frame, selectmode=tk.MULTIPLE, relief=FLAT, highlightthickness=0, font=self.FONT_NORMAL)
        
        todos_integrantes = arl_gerencia.get_todos_los_integrantes(self.ruta_datos_central)
        for nombre, area in todos_integrantes:
            if nombre != arl_gerencia.JEFE and nombre != self.current_user["nombre"]:
                self.listbox_integrantes_gerencia.insert(tk.END, f"{nombre}  ({area})")
        
        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.listbox_integrantes_gerencia.yview, bootstyle="info-round")
        self.listbox_integrantes_gerencia.config(yscrollcommand=scrollbar.set); scrollbar.pack(side=RIGHT, fill=Y)
        self.listbox_integrantes_gerencia.pack(side=LEFT, fill=BOTH, expand=TRUE)
        
        btn_confirmar = ttk.Button(panel, text="Confirmar Participantes y Empezar Reunión", bootstyle=SUCCESS, command=self._confirmar_participantes_gerencia)
        btn_confirmar.pack(pady=10)
        return panel
    
    def _confirmar_participantes_gerencia(self):
        indices = self.listbox_integrantes_gerencia.curselection()
        participantes_elegidos = [self.listbox_integrantes_gerencia.get(i).split('  (')[0] for i in indices]
        participantes_set = {self.current_user["nombre"], arl_gerencia.JEFE, *participantes_elegidos}
        self.reunion_participantes = sorted(list(participantes_set))
        
        for widget in self.panel_caras_gerencia.winfo_children(): widget.destroy()
        self.participant_buttons.clear()
        
        cols = min(4, len(self.reunion_participantes) + 1) or 1
        
        for i, nombre in enumerate(self.reunion_participantes):
            row, col = divmod(i, cols)
            frame_persona = ttk.Labelframe(self.panel_caras_gerencia, text=nombre, bootstyle=PRIMARY, padding=5); frame_persona.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            ruta_foto = os.path.join(self.ruta_datos_central, 'base_de_usuarios', f"{nombre}.jpeg")
            foto = ImageTk.PhotoImage(Image.open(ruta_foto).resize((90, 90), Image.Resampling.LANCZOS)) if os.path.exists(ruta_foto) else None
            btn = ttk.Button(frame_persona, image=foto, text="" if foto else "Sin Foto", bootstyle=OUTLINE, command=lambda n=nombre: self._on_participant_click(n)); btn.image = foto; btn.pack(fill=BOTH, expand=TRUE); self.participant_buttons[nombre] = btn

        row, col = divmod(len(self.reunion_participantes), cols)
        frame_publico = ttk.Labelframe(self.panel_caras_gerencia, text="Público / Invitado", bootstyle=INFO, padding=5); frame_publico.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        self.btn_publico = ttk.Button(frame_publico, text="🎤", bootstyle=OUTLINE, command=self._on_publico_click); self.btn_publico.pack(fill=BOTH, expand=TRUE)
        
        for i in range(cols): self.panel_caras_gerencia.columnconfigure(i, weight=1)
        
        self.acta_word = arl_gerencia.ActaWord(f"Acta Reunión Gerencia - {time.strftime('%d-%m-%Y')}", self.reunion_participantes)
        self._switch_panel(self.panel_reunion_gerencia)
    
    def _crear_panel_reunion_gerencia(self, parent):
        panel = ttk.Frame(parent)
        lf_control = ttk.Labelframe(panel, text="Control de la Reunión", bootstyle=PRIMARY, padding=15); lf_control.pack(fill=BOTH, expand=TRUE)
        self.lbl_estado_reunion_gerencia = ttk.Label(lf_control, text="Haga clic en un participante para grabar.", font=self.FONT_NORMAL); self.lbl_estado_reunion_gerencia.pack(pady=5)
        self.panel_caras_gerencia = ttk.Frame(lf_control); self.panel_caras_gerencia.pack(pady=10, fill=X, expand=TRUE)
        ttk.Separator(lf_control).pack(fill=X, pady=10)
        btn_terminar = ttk.Button(lf_control, text="Terminar Reunión y Generar Acta", bootstyle=DANGER, command=self._terminar_reunion); btn_terminar.pack(pady=10)
        return panel

    def _on_publico_click(self):
        if self.is_recording: self._on_participant_click(self.current_speaker)
        self.after(200, self._iniciar_grabacion_y_pedir_nombre_publico)

    def _iniciar_grabacion_y_pedir_nombre_publico(self):
        self.current_speaker, self.is_recording, self.stop_event, self.grabacion_frames = "Grabando Invitado...", True, threading.Event(), []
        self.btn_publico.config(bootstyle=DANGER); self.lbl_estado_reunion_gerencia.config(text="🔴 Grabando a (Público)... Ingrese nombre.", bootstyle=DANGER)
        threading.Thread(target=arl_gerencia.hilo_grabacion_manual, args=(self.stop_event, self.grabacion_frames), daemon=True).start()
        nombre_invitado = simpledialog.askstring("Nombre del Interviniente", "Grabación iniciada. Ingrese el nombre:", parent=self)
        if self.is_recording and self.current_speaker == "Grabando Invitado...":
            self.current_speaker = f"{nombre_invitado.strip()} (Público)" if nombre_invitado and nombre_invitado.strip() else "Invitado Anónimo (Público)"
            self.lbl_estado_reunion_gerencia.config(text=f"🔴 Grabando a: {self.current_speaker}...", bootstyle=DANGER)
    
    def _on_participant_click(self, nombre_hablante):
        if self.is_recording:
            hablante_anterior = self.current_speaker
            self._guardar_grabacion_actual()
            if hablante_anterior == nombre_hablante: return
        self.after(150, lambda: self._iniciar_grabacion_para(nombre_hablante))

    def _guardar_grabacion_actual(self):
        if not self.is_recording: return
        self.stop_event.set()
        hablante_anterior, audio_a_guardar = self.current_speaker, self.grabacion_frames
        self.is_recording, self.current_speaker, self.grabacion_frames = False, None, []
        
        if hablante_anterior in self.participant_buttons: self.participant_buttons[hablante_anterior].config(bootstyle=OUTLINE)
        elif "Público" in hablante_anterior or "Invitado" in hablante_anterior: self.btn_publico.config(bootstyle=OUTLINE)
        self.lbl_estado_reunion_gerencia.config(text=f"✅ Intervención de {hablante_anterior} grabada localmente.")

        if self.acta_word and audio_a_guardar:
            self.acta_word.agregar_grabacion(hablante_anterior, b''.join(audio_a_guardar))

    def _iniciar_grabacion_para(self, nombre_hablante):
        if self.is_recording: return
        self.current_speaker, self.is_recording, self.stop_event, self.grabacion_frames = nombre_hablante, True, threading.Event(), []
        if nombre_hablante in self.participant_buttons: self.participant_buttons[nombre_hablante].config(bootstyle=DANGER)
        self.lbl_estado_reunion_gerencia.config(text=f"🔴 Grabando a {nombre_hablante}...", bootstyle=DANGER)
        threading.Thread(target=arl_gerencia.hilo_grabacion_manual, args=(self.stop_event, self.grabacion_frames), daemon=True).start()

    def _terminar_reunion(self):
        if self.is_recording: self._guardar_grabacion_actual()
        self.after(200, self._advertir_y_procesar)

    def _advertir_y_procesar(self):
        if not self.acta_word or not self.acta_word.cola_de_grabaciones:
            if not messagebox.askyesno("Reanudar Proceso", "¿Desea buscar una reunión guardada previamente para reanudar su transcripción?", parent=self, icon='question'):
                self._resetear_paneles_reunion()
                return
        
        # Realizar la comprobación de internet justo antes de preguntar al usuario
        if not self._hay_conexion_internet():
            messagebox.showerror(
                "Sin Conexión a Internet",
                "No se ha podido detectar una conexión a internet activa.\n\n"
                "Puede continuar para guardar una reunión nueva o reanudar una existente, "
                "pero la transcripción probablemente fallará.",
                icon='warning'
            )
        
        if not messagebox.askyesno("Confirmar Finalización", "Se procederá a guardar y/o transcribir el acta.\n\n¿Desea continuar?", icon='question'): return
        self._proceder_al_guardado_final()

    def _proceder_al_guardado_final(self):
        nombre_reunion = simpledialog.askstring("Guardar Acta", "Introduce un nombre para la reunión:", parent=self)
        if not nombre_reunion or not nombre_reunion.strip(): return
        
        try:
            docs_path = os.path.join(os.path.expanduser('~'), 'Documents'); evarisis_path = os.path.join(docs_path, 'evarisis')
            ruta_carpeta_reunion = os.path.join(evarisis_path, nombre_reunion.strip())
            ruta_proyecto_json = os.path.join(ruta_carpeta_reunion, "proyecto_reunion.json")
            if os.path.exists(ruta_proyecto_json):
                if not messagebox.askyesno("Reanudar Proceso", "Ya existe una reunión con este nombre.\n¿Desea reanudar la transcripción?", icon='question'): return
            else:
                if not self.acta_word:
                    messagebox.showerror("Error de Estado", "No hay una reunión activa para guardar. Si desea reanudar una reunión anterior, ingrese su nombre exacto.", parent=self)
                    return
                ruta_proyecto_json, err = self.acta_word.guardar_proyecto_para_transcribir(ruta_carpeta_reunion)
                if err: messagebox.showerror("Error Crítico", f"No se pudieron guardar los audios: {err}", parent=self); return
                messagebox.showinfo("Audios Guardados", "Audios guardados. Iniciando transcripción.", parent=self)
        except Exception as e: messagebox.showerror("Error de Ruta", f"Error al crear carpeta: {e}", parent=self); return
        
        dialogo_progreso, lbl_estado, progress_bar = self._mostrar_ventana_progreso()
        
        def update_progress(value, text): self.after(0, lambda: self._actualizar_progreso_en_hilo_principal(dialogo_progreso, progress_bar, lbl_estado, value, text))
        
        def HiloDeTrabajo():
            stop_event = threading.Event()
            
            def HiloMonitor():
                while not stop_event.is_set():
                    if not self._hay_conexion_internet():
                        logging.error("¡Pérdida de conexión detectada durante el procesamiento!")
                        stop_event.set()
                        break
                    time.sleep(10)

            monitor = threading.Thread(target=HiloMonitor, daemon=True)
            monitor.start()

            # Se crea una instancia del procesador lógico.
            logic_processor = arl_gerencia.ActaWord("", []) 
            
            # --- ETAPA 1: Transcripción del Acta Literal ---
            update_progress(0, "Iniciando transcripción del acta literal...")
            
            exito_literal, msg_literal, ruta_acta_literal = logic_processor.transcribir_desde_proyecto(
                ruta_proyecto_json, 
                update_progress,
                stop_event
            )
            
            # Si la transcripción literal falla, detenemos todo el proceso.
            if not exito_literal:
                if not stop_event.is_set(): stop_event.set()
                self.after(0, lambda: dialogo_progreso.destroy())
                
                mensaje_guia = (
                    "El progreso ha sido guardado.\n\n"
                    "Por favor, revise el problema (ej. su conexión a internet) "
                    "y haga clic en 'Terminar Reunión y Generar Acta' de nuevo para reintentar."
                )
                messagebox.showerror("Error de Transcripción", f"{msg_literal}\n\n{mensaje_guia}", parent=self)
                return # Termina el hilo de trabajo aquí.

            # --- ETAPA 2: Generación del Acta Inteligente ---
            # Si la primera etapa fue exitosa, procedemos con la segunda.
            update_progress(0, "Acta literal creada. Iniciando resumen con IA...")
            time.sleep(2) # Pausa para que el usuario pueda leer el mensaje de estado.

            exito_inteligente, msg_inteligente = logic_processor.generar_acta_inteligente(
                ruta_acta_literal,
                update_progress
            )
            
            # --- FINALIZACIÓN Y MENSAJES AL USUARIO ---
            if not stop_event.is_set():
                stop_event.set()
            
            self.after(0, lambda: dialogo_progreso.destroy())
        
            if exito_inteligente:
                # Caso de éxito total: ambas actas se generaron.
                mensaje_final = f"{msg_literal}\n\n{msg_inteligente}"
                if messagebox.askyesno("Éxito Total", f"{mensaje_final}\n\n¿Desea abrir la carpeta de la reunión?", parent=self):
                    try:
                        os.startfile(ruta_carpeta_reunion)
                    except Exception as e:
                        messagebox.showinfo("Info", f"No se pudo abrir la carpeta: {ruta_carpeta_reunion}\nError: {e}", parent=self)
                self.after(0, self._resetear_paneles_reunion)
            else:
                # Caso de éxito parcial: el acta literal se creó, pero el resumen con IA falló.
                mensaje_final = f"¡Proceso parcialmente exitoso!\n\n- {msg_literal}\n- Error en resumen IA: {msg_inteligente}"
                if messagebox.askyesno("Éxito Parcial", f"{mensaje_final}\n\n¿Desea abrir la carpeta para ver el acta literal?", parent=self):
                    try:
                        os.startfile(ruta_carpeta_reunion)
                    except Exception as e:
                        messagebox.showinfo("Info", f"No se pudo abrir la carpeta: {ruta_carpeta_reunion}\nError: {e}", parent=self)
                self.after(0, self._resetear_paneles_reunion)

        # La línea que inicia el hilo no cambia.
        threading.Thread(target=HiloDeTrabajo, daemon=True).start()


    def _mostrar_ventana_progreso(self):
        dialogo = tk.Toplevel(self); dialogo.title("Procesando..."); dialogo.geometry("450x150"); dialogo.transient(self); dialogo.grab_set(); dialogo.resizable(False, False)
        x, y = self.winfo_x()+(self.winfo_width()/2)-225, self.winfo_y()+(self.winfo_height()/2)-75; dialogo.geometry(f"+{int(x)}+{int(y)}")
        container = ttk.Frame(dialogo, padding=20); container.pack(fill=BOTH, expand=TRUE)
        lbl_estado = ttk.Label(container, text="Iniciando...", font=self.FONT_NORMAL); lbl_estado.pack(pady=(0, 10))
        progress_bar = ttk.Progressbar(container, mode='determinate', length=400); progress_bar.pack(pady=10)
        return dialogo, lbl_estado, progress_bar
        
    def _actualizar_progreso_en_hilo_principal(self, dialogo, progress_bar, lbl_estado, value, text):
        if dialogo.winfo_exists():
            progress_bar['value'] = value * 100
            lbl_estado.config(text=text)
    
    def _resetear_paneles_reunion(self):
        for widget in self.panel_caras_gerencia.winfo_children(): widget.destroy()
        self.participant_buttons.clear()
        self.listbox_integrantes_gerencia.selection_clear(0, tk.END)
        # Limpiamos el objeto de acta para la nueva reunión
        self.acta_word = None
        self.reunion_participantes = []
        self._switch_panel(self.panel_setup_gerencia)

    def _hay_conexion_internet(self, host="8.8.8.8", port=53, timeout=3):
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except socket.error:
            return False

if __name__ == "__main__":
    logger.setup_global_logger()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    parser = argparse.ArgumentParser(description="EVARISIS Asistente Generador de Actas para Reuniones de Gerencia.")
    parser.add_argument("--lanzado-por-evarisis", action="store_true", help="Bandera de seguridad.")
    parser.add_argument("--nombre", default="Usuario Invitado", help="Nombre del usuario.")
    parser.add_argument("--cargo", default="N/A", help="Cargo del usuario.")
    parser.add_argument("--foto", default="SIN_FOTO", help="Ruta a la foto del usuario.")
    parser.add_argument("--tema", default="superhero", help="Tema de ttkbootstrap.")
    parser.add_argument("--ruta-datos", required=True, help="Ruta a la carpeta de datos central de EVARISIS.")

    args = parser.parse_args()

    app = AsistenteGerenciaApp(theme=args.tema, nombre_usuario=args.nombre, cargo_usuario=args.cargo, foto_path=args.foto, ruta_datos=args.ruta_datos)
    app.mainloop()