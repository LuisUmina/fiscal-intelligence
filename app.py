"""
app.py
UI principal de SUNAT Analytics
"""

import os
import time
import queue
import threading
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

from config.branding import (
    WINDOW_TITLE, BRAND_NAME, BRAND_COLOR_HEX,
    MAIN_TITLE, SUBTITLE, VERSION, TAGLINE, STATUS_DESCRIPTION
)

#from src.transformers.excel_exporter import exportar_lista_a_excel, exportar_ruc_a_excel_por_hojas
#from src.transformers.preparar_ssco import preparar_ssco_tablas
#from src.extractors.txt_parser import extract_rucs_from_folder
from src.processors import ejecutar_pipeline_sunat # >>

# ──────────────────────────────────────────────
#  Tema y paleta
# ──────────────────────────────────────────────
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

PW_ORANGE  = "#E0301E"
PW_ORANGE2 = "#FF5147"
PW_SLATE   = "#1E293B"
PW_GRAY    = "#F1F5F9"
PW_BORDER  = "#E2E8F0"
PW_TEXT    = "#1E293B"
PW_MUTED   = "#64748B"
PW_GREEN   = "#15803D"
PW_RED     = "#B91C1C"
PW_AMBER   = "#B45309"
PW_WHITE   = "#FFFFFF"
PW_CARD    = "#FFFFFF"
PW_ACCENT  = "#F8FAFC"

FONT_TITLE = ("Segoe UI", 13, "bold")
FONT_BODY  = ("Segoe UI", 11)
FONT_SMALL = ("Segoe UI", 10)
FONT_TINY  = ("Segoe UI", 9)
FONT_KPI   = ("Segoe UI", 24, "bold")
FONT_STEP  = ("Segoe UI", 11, "bold")
FONT_MONO  = ("Consolas", 9)


class SunatApp(ctk.CTk):

    VERSION = VERSION  # From config.branding

    def __init__(self):
        super().__init__()

        self.title(WINDOW_TITLE)
        self.geometry("1320x860")
        self.minsize(1160, 760)
        self.configure(fg_color=PW_GRAY)

        self._q      = queue.Queue()
        self._thread = None
        self._stop   = False
        self._kpi    = {}

        self.v_input  = tk.StringVar(value=str(Path("input/txt_files").resolve()))
        self.v_output = tk.StringVar(value=str(Path("output/excel").resolve()))

        self._build()
        self.after(120, self._poll)

    # ══════════════════════════════════════════
    #  LAYOUT PRINCIPAL
    # ══════════════════════════════════════════
    def _build(self):
        self._header()

        body = ctk.CTkFrame(self, fg_color=PW_GRAY)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        left = self._card(body, width=420)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        right = self._card(body)
        right.pack(side="right", fill="both", expand=True, padx=(8, 0))

        self._left_panel(left)
        self._right_panel(right)

    # ──────────────────────────────────────────
    #  HEADER
    # ──────────────────────────────────────────
    def _header(self):
        # Fondo oscuro tipo slate con franja inferior naranja
        outer = ctk.CTkFrame(self, fg_color=PW_SLATE, height=88, corner_radius=0)
        outer.pack(fill="x")
        outer.pack_propagate(False)

        # Franja naranja inferior
        bar = ctk.CTkFrame(outer, fg_color=PW_ORANGE, height=3, corner_radius=0)
        bar.pack(side="bottom", fill="x")

        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=28, pady=0)

        # ── Lado izquierdo: marca ──
        brand = ctk.CTkFrame(inner, fg_color="transparent")
        brand.pack(side="left", fill="y", pady=14)

        top_row = ctk.CTkFrame(brand, fg_color="transparent")
        top_row.pack(anchor="w")

        # Brand en bloque
        brand_pill = ctk.CTkFrame(top_row, fg_color=BRAND_COLOR_HEX, corner_radius=6)
        brand_pill.pack(side="left", padx=(0, 14))
        ctk.CTkLabel(brand_pill, text=BRAND_NAME,
                     font=("Segoe UI", 20, "bold"),
                     text_color=PW_WHITE).pack(padx=10, pady=3)

        # Separador vertical
        sep = ctk.CTkFrame(top_row, fg_color="#334155", width=1)
        sep.pack(side="left", fill="y", pady=2)

        # Titulo + subtitulo
        title_block = ctk.CTkFrame(top_row, fg_color="transparent")
        title_block.pack(side="left", padx=(14, 0))

        ctk.CTkLabel(title_block, text=MAIN_TITLE,
                     font=("Segoe UI", 18, "bold"),
                     text_color=PW_WHITE).pack(anchor="w")

        sub_row = ctk.CTkFrame(title_block, fg_color="transparent")
        sub_row.pack(anchor="w")

        ctk.CTkLabel(sub_row, text=SUBTITLE,
                     font=FONT_SMALL, text_color="#94A3B8").pack(side="left")

        pill = ctk.CTkFrame(sub_row, fg_color="#0F172A", corner_radius=4)
        pill.pack(side="left", padx=(8, 0))
        ctk.CTkLabel(pill, text=self.VERSION,
                     font=FONT_TINY, text_color=PW_ORANGE).pack(padx=6, pady=1)

        # Descripcion debajo del titulo
        ctk.CTkLabel(brand,
                     text=TAGLINE,
                     font=FONT_TINY, text_color="#475569").pack(anchor="w", pady=(5, 0))

        # ── Lado derecho: estado ──
        right_info = ctk.CTkFrame(inner, fg_color="transparent")
        right_info.pack(side="right", anchor="e", pady=14)

        # Indicador de estado con punto de color
        status_row = ctk.CTkFrame(right_info, fg_color="#0F172A", corner_radius=8)
        status_row.pack(anchor="e")

        self._dot_status = ctk.CTkLabel(status_row, text="●",
                                        font=("Segoe UI", 11), text_color="#475569")
        self._dot_status.pack(side="left", padx=(10, 4), pady=6)

        self._lbl_status_header = ctk.CTkLabel(
            status_row, text="En espera",
            font=("Segoe UI", 10, "bold"), text_color="#94A3B8")
        self._lbl_status_header.pack(side="left", padx=(0, 10), pady=6)

        ctk.CTkLabel(right_info,
                     text=STATUS_DESCRIPTION,
                     font=FONT_TINY, text_color="#334155").pack(anchor="e", pady=(6, 0))

    # ──────────────────────────────────────────
    #  PANEL IZQUIERDO
    # ──────────────────────────────────────────
    def _left_panel(self, parent):
        scrl = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scrl.pack(fill="both", expand=True, padx=16, pady=14)

        # Fuente TXT
        self._section_title(scrl, "Fuente de datos")
        ctk.CTkLabel(scrl, text="Carpeta con archivos TXT (formatos 801 y 804)",
                     font=FONT_SMALL, text_color=PW_MUTED).pack(anchor="w", pady=(0, 4))
        r1 = ctk.CTkFrame(scrl, fg_color="transparent")
        r1.pack(fill="x")
        ctk.CTkEntry(r1, textvariable=self.v_input,
                     font=FONT_BODY, height=36).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(r1, text="Buscar", width=70, height=36,
                      fg_color=PW_ORANGE, hover_color=PW_ORANGE2,
                      font=FONT_SMALL, command=self._pick_input).pack(side="left")

        self._divider(scrl)

        # Destino Excel
        self._section_title(scrl, "Carpeta de salida")
        ctk.CTkLabel(scrl, text="Los archivos Excel se guardaran en esta ubicacion",
                     font=FONT_SMALL, text_color=PW_MUTED).pack(anchor="w", pady=(0, 4))
        r2 = ctk.CTkFrame(scrl, fg_color="transparent")
        r2.pack(fill="x")
        ctk.CTkEntry(r2, textvariable=self.v_output,
                     font=FONT_BODY, height=36).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(r2, text="Buscar", width=70, height=36,
                      fg_color=PW_ORANGE, hover_color=PW_ORANGE2,
                      font=FONT_SMALL, command=self._pick_output).pack(side="left")

        self._divider(scrl)

        # Acciones
        self._section_title(scrl, "Acciones")

        self._btn_run = ctk.CTkButton(
            scrl, text="Iniciar proceso completo",
            height=46, font=("Segoe UI", 12, "bold"),
            fg_color=PW_GREEN, hover_color="#166534",
            command=self._start)
        self._btn_run.pack(fill="x", pady=(0, 8))

        self._btn_stop = ctk.CTkButton(
            scrl, text="Detener proceso",
            height=36, font=FONT_BODY,
            fg_color="#F1F5F9", hover_color="#E2E8F0",
            text_color=PW_RED, border_width=1, border_color=PW_RED,
            command=self._request_stop)
        self._btn_stop.pack(fill="x")

        self._divider(scrl)

        # Archivos que se generaran (compacto)
        self._section_title(scrl, "Archivos que se generaran")
        outputs = [
            ("DATOS_RUC.xlsx",                       "Representantes, Trabajadores, Establecimientos y RUCs Únicos (4 hojas)"),
            ("Sujetos sin capacidad operativa.xlsx", "Padron SSCO completo"),
        ]
        for fname, desc in outputs:
            row = ctk.CTkFrame(scrl, fg_color=PW_ACCENT, corner_radius=6)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=fname,
                         font=("Segoe UI", 10, "bold"), text_color=PW_TEXT).pack(
                anchor="w", padx=10, pady=(6, 0))
            ctk.CTkLabel(row, text=desc,
                         font=FONT_TINY, text_color=PW_MUTED).pack(
                anchor="w", padx=10, pady=(0, 6))

    # ──────────────────────────────────────────
    #  PANEL DERECHO
    # ──────────────────────────────────────────
    def _right_panel(self, parent):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=16, pady=14)

        # KPI row
        kpi_row = ctk.CTkFrame(wrap, fg_color="transparent")
        kpi_row.pack(fill="x", pady=(0, 10))
        kpi_row.columnconfigure((0, 1, 2, 3), weight=1, uniform="kpi")

        kpis = [
            ("txt",  "TXT detectados"),
            ("rucs", "RUCs unicos"),
            ("ok",   "Consultas correctas"),
            ("err",  "Sin datos o error"),
        ]
        for i, (key, label) in enumerate(kpis):
            card = ctk.CTkFrame(kpi_row, fg_color=PW_CARD, corner_radius=10,
                                border_width=1, border_color=PW_BORDER)
            card.grid(row=0, column=i, sticky="nsew",
                      padx=(0, 8) if i < 3 else (0, 0))
            ctk.CTkLabel(card, text=label,
                         font=FONT_TINY, text_color=PW_MUTED).pack(
                anchor="w", padx=12, pady=(10, 0))
            lbl = ctk.CTkLabel(card, text="0",
                               font=FONT_KPI, text_color=PW_TEXT)
            lbl.pack(anchor="w", padx=12, pady=(0, 10))
            self._kpi[key] = lbl

        # Estado + progreso
        status_card = self._card(wrap)
        status_card.pack(fill="x", pady=(0, 8))
        s = ctk.CTkFrame(status_card, fg_color="transparent")
        s.pack(fill="x", padx=14, pady=12)

        sh = ctk.CTkFrame(s, fg_color="transparent")
        sh.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(sh, text="Estado de ejecucion",
                     font=FONT_TITLE, text_color=PW_TEXT).pack(side="left")
        self._lbl_status = ctk.CTkLabel(sh, text="En espera",
                                         font=FONT_SMALL, text_color=PW_MUTED)
        self._lbl_status.pack(side="right")

        self._progress = ctk.CTkProgressBar(s, height=14, corner_radius=7)
        self._progress.pack(fill="x")
        self._progress.set(0)

        self._lbl_step = ctk.CTkLabel(s, text="",
                                       font=FONT_STEP, text_color=PW_ORANGE)
        self._lbl_step.pack(anchor="w", pady=(4, 0))

        # Pipeline + Log en layout vertical (pipeline arriba, log abajo)
        bottom = ctk.CTkFrame(wrap, fg_color="transparent")
        bottom.pack(fill="both", expand=True)

        # Pipeline (stepper horizontal compacto)
        pipe_card = self._card(bottom)
        pipe_card.pack(fill="x", pady=(0, 8))

        p = ctk.CTkFrame(pipe_card, fg_color="transparent")
        p.pack(fill="x", padx=14, pady=12)

        ctk.CTkLabel(p, text="Pipeline",
                     font=FONT_TITLE, text_color=PW_TEXT).pack(anchor="w", pady=(0, 8))

        pipe_row = ctk.CTkFrame(p, fg_color="transparent")
        pipe_row.pack(fill="x")
        pipe_row.columnconfigure((0, 2, 4, 6, 8, 10), weight=1, uniform="pipe")

        self._pipe_items = {}
        steps = [
            ("s1", "Lectura TXT"),
            ("s2", "Extraccion RUCs"),
            ("s3", "Warmup"),
            ("s4", "Consulta RUC"),
            ("s5", "Padron SSCO"),
            ("s6", "Exportacion Excel"),
        ]
        for i, (key, label) in enumerate(steps):
            row = ctk.CTkFrame(pipe_row, fg_color=PW_ACCENT, corner_radius=999,
                               border_width=1, border_color=PW_BORDER)
            row.grid(row=0, column=i * 2, sticky="ew", padx=2, pady=2)

            dot = ctk.CTkLabel(row, text="●", font=("Segoe UI", 10),
                               text_color=PW_BORDER)
            dot.pack(side="left", padx=(8, 5), pady=5)

            txt = ctk.CTkLabel(row, text=label, font=FONT_TINY,
                               text_color=PW_MUTED, anchor="w")
            txt.pack(side="left", padx=(0, 4), pady=5)

            st = ctk.CTkLabel(row, text="", font=("Segoe UI", 9, "bold"),
                              text_color=PW_MUTED)
            st.pack(side="left", padx=(0, 8), pady=5)

            self._pipe_items[key] = (dot, txt, label, st)

            if i < len(steps) - 1:
                ctk.CTkLabel(pipe_row, text="›", font=("Segoe UI", 13, "bold"),
                             text_color=PW_BORDER).grid(row=0, column=i * 2 + 1, padx=2)

        # Log (ocupa todo el ancho disponible)
        log_card = ctk.CTkFrame(bottom, fg_color="#0F172A", corner_radius=12)
        log_card.pack(fill="both", expand=True)

        log_top = ctk.CTkFrame(log_card, fg_color="transparent")
        log_top.pack(fill="x", padx=14, pady=(10, 4))

        ctk.CTkLabel(log_top, text="Registro de actividad",
                     font=("Segoe UI", 11, "bold"),
                     text_color="#CBD5E1").pack(side="left")
        ctk.CTkButton(log_top, text="Limpiar", width=58, height=22,
                      font=FONT_TINY, fg_color="#1E293B",
                      hover_color="#334155", text_color="#94A3B8",
                      command=lambda: self._log_txt.delete("1.0", tk.END)).pack(side="right")

        self._log_txt = scrolledtext.ScrolledText(
            log_card, font=FONT_MONO, bg="#0F172A", fg="#94A3B8",
            insertbackground="white", borderwidth=0,
            highlightthickness=0, wrap="word")
        self._log_txt.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        self._log_txt.tag_config("ok",    foreground="#4ADE80")
        self._log_txt.tag_config("warn",  foreground="#FCD34D")
        self._log_txt.tag_config("error", foreground="#F87171")
        self._log_txt.tag_config("info",  foreground="#60A5FA")
        self._log_txt.tag_config("base",  foreground="#94A3B8")

    # ══════════════════════════════════════════
    #  HELPERS DE WIDGETS
    # ══════════════════════════════════════════
    def _card(self, parent, **kw):
        return ctk.CTkFrame(parent, fg_color=PW_CARD, corner_radius=12,
                            border_width=1, border_color=PW_BORDER, **kw)

    def _section_title(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=FONT_TITLE,
                     text_color=PW_TEXT).pack(anchor="w", pady=(10, 4))

    def _divider(self, parent):
        ctk.CTkFrame(parent, fg_color=PW_BORDER, height=1).pack(
            fill="x", pady=10)

    def _set_kpi(self, key, val):
        self._q.put(("kpi", key, str(val)))

    # ══════════════════════════════════════════
    #  EVENTOS
    # ══════════════════════════════════════════
    def _pick_input(self):
        d = filedialog.askdirectory(title="Seleccionar carpeta con TXT")
        if d:
            self.v_input.set(d)

    def _pick_output(self):
        d = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if d:
            self.v_output.set(d)

    def _start(self):
        if self._thread and self._thread.is_alive():
            messagebox.showwarning("En ejecucion", "Ya hay un proceso en curso.")
            return

        inp = self.v_input.get().strip()
        out = self.v_output.get().strip()

        if not inp or not os.path.isdir(inp):
            messagebox.showerror("Error", "La carpeta de entrada no es valida.")
            return

        self._stop = False
        self._lbl_status.configure(text="Ejecutando...", text_color=PW_AMBER)
        self._lbl_status_header.configure(text="Ejecutando...", text_color=PW_AMBER)
        self._dot_status.configure(text_color=PW_AMBER)
        self._progress.set(0)
        self._lbl_step.configure(text="")
        self._log_txt.delete("1.0", tk.END)
        for k in ("txt", "rucs", "ok", "err"):
            self._set_kpi(k, "0")
        self._reset_pipe()

        self._thread = threading.Thread(
            target=self._run, args=(inp, out), daemon=True)
        self._thread.start()

    def _request_stop(self):
        self._stop = True
        self._log("[STOP] Detencion solicitada por el usuario.", "warn")

    # ══════════════════════════════════════════
    #  PIPELINE DE EJECUCION
    # ══════════════════════════════════════════
    """
    def _run(self, inp, out):
        t0 = time.time()
        ok_c = err_c = 0

        try:
            from src.extractors.txt_parser import extract_rucs_from_folder
            from src.extractors.sunat_consulta_ruc_request import (
                _warmup_sesion,
                consultar_representantes_legales,
                consultar_trabajadores,
                consultar_establecimientos,
            )
            from src.extractors.sunat_ssco import consultar_sujetos_sin_capacidad

            # Paso 1 - Lectura de TXT
            self._pipe_state("s1", "running")
            self._step("Leyendo archivos TXT...", 0.04)
            self._log(f"[INFO] Carpeta de entrada: {inp}", "info")

            txt_files = [f for f in os.listdir(inp) if f.lower().endswith(".txt")]
            self._set_kpi("txt", len(txt_files))
            self._log(f"[INFO] TXT encontrados: {len(txt_files)}", "info")
            self._pipe_state("s1", "ok")

            # Paso 2 - Extraccion de RUCs
            self._pipe_state("s2", "running")
            self._step("Extrayendo RUCs de los TXT...", 0.08)

            rucs, rucs_archivos, errores_txt = extract_rucs_from_folder(inp)
            self._set_kpi("rucs", len(rucs))
            self._log(f"[INFO] RUCs unicos extraidos: {len(rucs)}", "info")

            # Mostrar en pantalla los TXT que fallaron (sin logs a archivo)
            for item in errores_txt:
                archivo = item.get("archivo", "")
                error_txt = item.get("error", "")
                self._log(f"[WARN] TXT omitido: {archivo} | {error_txt}", "warn")

            self._pipe_state("s2", "ok")

            if not rucs:
                self._log("[WARN] No se encontraron RUCs para procesar.", "warn")
                self._finish(False)
                return

            # Paso 3 - Warmup
            self._pipe_state("s3", "running")
            self._step("Inicializando sesion SUNAT...", 0.12)
            _warmup_sesion(rucs[0])
            self._log("[INFO] Sesion SUNAT inicializada.", "info")
            self._pipe_state("s3", "ok")

            # Paso 4 - Consulta masiva
            self._pipe_state("s4", "running")
            self._log(f"[INFO] Iniciando consulta masiva: {len(rucs)} RUCs", "info")

            reps, trabs, ests = [], [], []
            total = len(rucs)

            for i, ruc in enumerate(rucs, 1):
                if self._stop:
                    self._log("[STOP] Proceso detenido.", "warn")
                    self._finish(False)
                    return

                prog = 0.12 + (i / total) * 0.60
                self._step(f"Consultando SUNAT  {i} de {total}  |  RUC {ruc}", prog)
                _warmup_sesion(ruc)

                consultas = [
                    (consultar_representantes_legales, reps,
                     {"ruc": ruc, "documento": "SIN_DATOS",
                      "nro_documento": "", "nombre": "", "cargo": "", "fecha_desde": ""}),
                    (consultar_trabajadores, trabs,
                     {"ruc": ruc, "periodo": "SIN_DATOS",
                      "nro_trabajadores": "", "nro_pensionistas": "",
                      "nro_prestadores_servicios": ""}),
                    (consultar_establecimientos, ests,
                     {"ruc": ruc, "codigo": "SIN_DATOS",
                      "tipo_establecimiento": "", "direccion": "",
                      "actividad_economica": ""}),
                ]

                for fn, lst, row_vacio in consultas:
                    resp = fn(ruc)
                    if resp["status"] == "ok":
                        lst.extend(resp["tablas"])
                        ok_c += 1
                    elif resp["status"] == "no_data":
                        lst.append(row_vacio)
                        err_c += 1
                    else:
                        # request_failed / error conexión u otros errores.
                        # Mantenemos la estructura, pero marcamos el campo "SIN_DATOS" como "ERROR".
                        row = dict(row_vacio)
                        if "documento" in row:
                            row["documento"] = "ERROR"
                        elif "periodo" in row:
                            row["periodo"] = "ERROR"
                        elif "codigo" in row:
                            row["codigo"] = "ERROR"
                        lst.append(row)
                        err_c += 1
                    self._set_kpi("ok", ok_c)
                    self._set_kpi("err", err_c)

            self._pipe_state("s4", "ok")
            self._log(f"[OK] Consulta masiva completada. Correctas: {ok_c} | Sin datos o error: {err_c}", "ok")

            # Paso 5 - Padron SSCO
            self._pipe_state("s5", "running")
            self._step("Descargando padron SSCO...", 0.78)
            self._log("[INFO] Descargando Sujetos sin Capacidad Operativa...", "info")
            ssco = consultar_sujetos_sin_capacidad()
            self._pipe_state("s5", "ok" if ssco["status"] == "ok" else "warn")

            # Paso 6 - Exportacion
            self._pipe_state("s6", "running")
            self._step("Exportando archivos Excel...", 0.90)
            self._log(f"[INFO] Guardando en: {out}", "info")

            Path(out).mkdir(parents=True, exist_ok=True)

            exportar_ruc_a_excel_por_hojas(reps, trabs, ests, f"{out}/DATOS_RUC.xlsx", rucs_archivos=rucs_archivos)
            self._log("[OK] DATOS_RUC.xlsx generado (hojas: Representantes, Trabajadores, Establecimientos).", "ok")

            if ssco["status"] == "ok":
                tablas_preparadas = preparar_ssco_tablas(ssco["tablas"])
                exportar_lista_a_excel(tablas_preparadas,
                    f"{out}/Sujetos sin capacidad operativa.xlsx")
                self._log("[OK] Sujetos sin capacidad operativa.xlsx generado.", "ok")
            else:
                self._log("[WARN] No se pudo descargar el padron SSCO.", "warn")

            self._pipe_state("s6", "ok")

            elapsed = time.time() - t0
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            self._log(
                f"[DONE] Proceso completado en {mins}m {secs}s  |  "
                f"Correctas: {ok_c}  |  Sin datos o error: {err_c}", "ok")
            self._finish(True)

        except Exception as exc:
            import traceback
            self._log(f"[ERROR] Error critico: {exc}", "error")
            self._log(f"[ERROR] Detalle: {traceback.format_exc()}", "error")
            self._finish(False)
    """

    def _run(self, inp, out):
        t0 = time.time()
        try:
            resultado = ejecutar_pipeline_sunat(
                carpeta_txt=inp,
                carpeta_output=out,
                exportar_excel=True,
                emit=lambda *event: self._q.put(event),
                should_stop=lambda: self._stop,
            )

            if resultado["status"] in ("stopped", "no_data"):
                self._finish(False)
                return

            elapsed = time.time() - t0
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            self._log(
                f"[DONE] Proceso completado en {mins}m {secs}s  |  "
                f"Correctas: {resultado['ok_count']}  |  Sin datos o error: {resultado['error_count']}",
                "ok",
            )
            self._finish(True)

        except Exception as exc:
            import traceback
            self._log(f"[ERROR] Error critico: {exc}", "error")
            self._log(f"[ERROR] Detalle: {traceback.format_exc()}", "error")
            self._finish(False)

    # ══════════════════════════════════════════
    #  COLA Y ACTUALIZACION DE UI
    # ══════════════════════════════════════════
    def _step(self, text, val):
        self._q.put(("step", text, val))

    def _log(self, msg, lvl="base"):
        self._q.put(("log", msg, lvl))

    def _pipe_state(self, key, state):
        self._q.put(("pipe", key, state))

    def _finish(self, ok):
        self._q.put(("finish", ok))

    def _reset_pipe(self):
        for key, (dot, txt, label, st) in self._pipe_items.items():
            dot.configure(text_color=PW_BORDER)
            txt.configure(text=label, text_color=PW_MUTED)
            st.configure(text="", text_color=PW_MUTED)

    def _poll(self):
        try:
            while True:
                msg = self._q.get_nowait()
                kind = msg[0]

                if kind == "step":
                    self._lbl_step.configure(text=msg[1])
                    self._progress.set(msg[2])

                elif kind == "log":
                    stamp = time.strftime("%H:%M:%S")
                    line  = f"[{stamp}]  {msg[1]}\n"
                    tag   = msg[2] if msg[2] in ("ok", "warn", "error", "info") else "base"
                    self._log_txt.insert(tk.END, line, tag)
                    self._log_txt.see(tk.END)

                elif kind == "kpi":
                    self._kpi[msg[1]].configure(text=msg[2])

                elif kind == "pipe":
                    key, state = msg[1], msg[2]
                    dot, txt, label, st = self._pipe_items[key]
                    c_map = {"running": PW_AMBER, "ok": PW_GREEN,
                             "warn": PW_AMBER,    "error": PW_RED}
                    t_map = {"running": "En progreso",
                             "ok":      "Completado",
                             "warn":    "Con observaciones",
                             "error":   "Error"}
                    short_map = {"running": "RUN",
                                 "ok":      "OK",
                                 "warn":    "WARN",
                                 "error":   "ERR"}
                    c = c_map.get(state, PW_BORDER)
                    dot.configure(text_color=c)
                    txt.configure(text=label, text_color=c)
                    st.configure(text=short_map.get(state, ""), text_color=c)

                elif kind == "finish":
                    ok = msg[1]
                    self._progress.set(1.0 if ok else self._progress.get())
                    if ok:
                        self._lbl_status.configure(
                            text="Completado", text_color=PW_GREEN)
                        self._lbl_status_header.configure(
                            text="Completado", text_color=PW_GREEN)
                        self._dot_status.configure(text_color=PW_GREEN)
                        messagebox.showinfo(
                            "Proceso completado",
                            "Todos los archivos Excel han sido generados correctamente.")
                    else:
                        self._lbl_status.configure(
                            text="Finalizado con observaciones", text_color=PW_RED)
                        self._lbl_status_header.configure(
                            text="Finalizado con observaciones", text_color=PW_RED)
                        self._dot_status.configure(text_color=PW_RED)
                        messagebox.showwarning(
                            "Proceso finalizado",
                            "El proceso termino. Revisa el registro de actividad.")

        except queue.Empty:
            pass
        finally:
            self.after(120, self._poll)


if __name__ == "__main__":
    app = SunatApp()
    app.mainloop()