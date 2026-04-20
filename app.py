"""
app.py
UI principal de SUNAT Analytics
"""

import os
import time
import queue
import sys
import threading
import importlib.util
import contextlib
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

from config.branding import (
    WINDOW_TITLE, BRAND_NAME, BRAND_COLOR_HEX,
    MAIN_TITLE, SUBTITLE, VERSION, TAGLINE, STATUS_DESCRIPTION
)
from src.security import validate_license

#from src.transformers.excel_exporter import exportar_lista_a_excel, exportar_ruc_a_excel_por_hojas
#from src.transformers.preparar_ssco import preparar_ssco_tablas
#from src.extractors.txt_parser import extract_rucs_from_folder
from src.processors import construir_base_bi_basica, ejecutar_pipeline_sunat # >>

# ──────────────────────────────────────────────
#  Tema y paleta
# ──────────────────────────────────────────────
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

PW_ORANGE  = "#FF5A00"
PW_ORANGE2 = "#F65A00"
PW_SLATE   = "#F4DFD4"
PW_GRAY    = "#E8CFC3"
PW_BORDER  = "#D9D9D9"
PW_TEXT    = "#111111"
PW_MUTED   = "#6B6B6B"
PW_GREEN   = "#1F7A3D"
PW_RED     = "#B42318"
PW_AMBER   = "#D97706"
PW_WHITE   = "#FFFFFF"
PW_CARD    = "#FFFFFF"
PW_ACCENT  = "#FFF6F2"

FONT_TITLE = ("Cambria", 15, "bold")
FONT_BODY  = ("Segoe UI", 12)
FONT_SMALL = ("Segoe UI", 11)
FONT_TINY  = ("Segoe UI", 10)
FONT_KPI   = ("Segoe UI", 26, "bold")
FONT_STEP  = ("Segoe UI", 12, "bold")
FONT_MONO  = ("Consolas", 9)


def get_runtime_root() -> Path:
    """Return the folder where resources should be resolved at runtime.

    When running as a PyInstaller executable, use the executable directory.
    During development, use the project directory where app.py lives.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_bundle_root() -> Path:
    """Return the PyInstaller extraction dir when frozen, else project root."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent


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
        self._manual_pipe_keys = {"s5", "s6"}
        self._active_run_mode = "full"
        self._active_run_label = "Flujo principal"

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
        # Header corporativo claro con acento naranja
        outer = ctk.CTkFrame(self, fg_color=PW_SLATE, height=104, corner_radius=0)
        outer.pack(fill="x")
        outer.pack_propagate(False)

        top_bar = ctk.CTkFrame(outer, fg_color=PW_ORANGE, height=10, corner_radius=0)
        top_bar.pack(side="top", fill="x")

        bar = ctk.CTkFrame(outer, fg_color="#F3B38B", height=2, corner_radius=0)
        bar.pack(side="bottom", fill="x")

        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=28, pady=0)

        # ── Lado izquierdo: marca ──
        brand = ctk.CTkFrame(inner, fg_color="transparent")
        brand.pack(side="left", fill="y", pady=14)

        top_row = ctk.CTkFrame(brand, fg_color="transparent")
        top_row.pack(anchor="w")

        # Brand en bloque
        brand_pill = ctk.CTkFrame(top_row, fg_color=BRAND_COLOR_HEX, corner_radius=8)
        brand_pill.pack(side="left", padx=(0, 14))
        ctk.CTkLabel(brand_pill, text=BRAND_NAME,
                 font=("Segoe UI", 22, "bold"),
                     text_color=PW_WHITE).pack(padx=10, pady=3)

        # Separador vertical
        sep = ctk.CTkFrame(top_row, fg_color=PW_BORDER, width=1)
        sep.pack(side="left", fill="y", pady=2)

        # Titulo + subtitulo
        title_block = ctk.CTkFrame(top_row, fg_color="transparent")
        title_block.pack(side="left", padx=(14, 0))

        ctk.CTkLabel(title_block, text=MAIN_TITLE,
                     font=("Cambria", 23, "bold"),
                     text_color=PW_TEXT).pack(anchor="w")

        sub_row = ctk.CTkFrame(title_block, fg_color="transparent")
        sub_row.pack(anchor="w")

        ctk.CTkLabel(sub_row, text=SUBTITLE,
                     font=FONT_SMALL, text_color=PW_MUTED).pack(side="left")

        pill = ctk.CTkFrame(sub_row, fg_color="#FFF1EA", corner_radius=4)
        pill.pack(side="left", padx=(8, 0))
        ctk.CTkLabel(pill, text=self.VERSION,
                     font=FONT_TINY, text_color=PW_ORANGE).pack(padx=6, pady=1)

        # Descripcion debajo del titulo
        ctk.CTkLabel(brand,
                     text=TAGLINE,
                     font=FONT_TINY, text_color=PW_MUTED).pack(anchor="w", pady=(5, 0))

        # ── Lado derecho: estado ──
        right_info = ctk.CTkFrame(inner, fg_color="transparent", width=180)
        right_info.pack(side="right", anchor="e", pady=10)
        right_info.pack_propagate(False)

        # Indicador de estado con punto de color
        status_row = ctk.CTkFrame(
            right_info,
            fg_color="#FFF5EF",
            corner_radius=8,
            border_width=1,
            border_color=PW_BORDER,
        )
        status_row.pack(anchor="e")

        self._dot_status = ctk.CTkLabel(status_row, text="●",
                                        font=("Segoe UI", 10), text_color=PW_MUTED)
        self._dot_status.pack(side="left", padx=(8, 3), pady=4)

        self._lbl_status_header = ctk.CTkLabel(
            status_row, text="En espera",
            font=("Segoe UI", 10, "bold"), text_color=PW_MUTED)
        self._lbl_status_header.pack(side="left", padx=(0, 8), pady=4)

        ctk.CTkLabel(
            right_info,
            text=STATUS_DESCRIPTION,
            font=FONT_TINY,
            text_color=PW_MUTED,
            justify="right",
            anchor="e",
            wraplength=210,
        ).pack(anchor="e", pady=(4, 0))

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
                     font=FONT_BODY, height=40).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(r1, text="Buscar", width=80, height=40,
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
                     font=FONT_BODY, height=40).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(r2, text="Buscar", width=80, height=40,
                      fg_color=PW_ORANGE, hover_color=PW_ORANGE2,
                      font=FONT_SMALL, command=self._pick_output).pack(side="left")

        self._divider(scrl)

        # Acciones
        self._section_title(scrl, "Acciones")
        action_card = ctk.CTkFrame(
            scrl,
            fg_color=PW_ACCENT,
            corner_radius=10,
            border_width=1,
            border_color=PW_BORDER,
        )
        action_card.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(
            action_card,
            text="Flujo recomendado",
            font=FONT_SMALL,
            text_color=PW_TEXT,
        ).pack(anchor="w", padx=12, pady=(10, 2))

        self._btn_run = ctk.CTkButton(
            action_card, text="Ejecutar flujo completo",
            height=44, font=("Segoe UI", 13, "bold"),
            fg_color=PW_ORANGE, hover_color=PW_ORANGE2,
            text_color=PW_WHITE,
            command=self._start)
        self._btn_run.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(
            action_card,
            text="Ejecucion paso a paso",
            font=FONT_SMALL,
            text_color=PW_TEXT,
        ).pack(anchor="w", padx=12, pady=(0, 6))

        step_grid = ctk.CTkFrame(action_card, fg_color="transparent")
        step_grid.pack(fill="x", padx=12)
        step_grid.columnconfigure((0, 1), weight=1, uniform="steps")

        self._btn_txt = ctk.CTkButton(
            step_grid, text="1) RUC unico + consolidado TXT",
            height=38, font=FONT_SMALL,
            fg_color="#EFEFEF", hover_color="#E4E4E4",
            text_color=PW_TEXT,
            command=self._start_txt_block)
        self._btn_txt.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=(0, 6))

        self._btn_individual = ctk.CTkButton(
            step_grid, text="2) SUNAT RUC individual",
            height=38, font=FONT_SMALL,
            fg_color="#EFEFEF", hover_color="#E4E4E4",
            text_color=PW_TEXT,
            command=self._start_individual_block)
        self._btn_individual.grid(row=0, column=1, sticky="ew", padx=(4, 0), pady=(0, 6))

        self._btn_ssco = ctk.CTkButton(
            step_grid, text="3) Padron SSCO",
            height=38, font=FONT_SMALL,
            fg_color="#EFEFEF", hover_color="#E4E4E4",
            text_color=PW_TEXT,
            command=self._start_ssco_block)
        self._btn_ssco.grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=(0, 6))

        self._btn_legacy = ctk.CTkButton(
            step_grid, text="4) SUNAT masivo",
            height=38, font=FONT_SMALL,
            fg_color="#EFEFEF", hover_color="#E4E4E4",
            text_color=PW_TEXT,
            command=self._launch_legacy_bot)
        self._btn_legacy.grid(row=1, column=1, sticky="ew", padx=(4, 0), pady=(0, 6))

        self._btn_bi = ctk.CTkButton(
            action_card, text="5) Generar base BI",
            height=38, font=FONT_SMALL,
            fg_color="#EFEFEF", hover_color="#E4E4E4",
            text_color=PW_TEXT,
            command=self._build_bi_base)
        self._btn_bi.pack(fill="x", padx=12, pady=(0, 8))

        self._btn_stop = ctk.CTkButton(
            action_card, text="Detener proceso",
            height=36, font=FONT_SMALL,
            fg_color="#FAFAFA", hover_color="#F1F1F1",
            text_color=PW_RED, border_width=1, border_color=PW_RED,
            command=self._request_stop)
        self._btn_stop.pack(fill="x", padx=12, pady=(0, 10))

        self._divider(scrl)

        # Archivos que se generaran (compacto)
        self._section_title(scrl, "Archivos que se generaran")
        outputs = [
            ("rucs_unicos.xlsx", "Listado unico de RUCs para consulta"),
            ("consolidado_txt.xlsx", "Consolidado transaccional desde TXT (801/804)"),
            ("sunat_ruc_individual.xlsx", "Hojas individuales de SUNAT (incluye historicos)"),
            ("sunat_ssco.xlsx", "Padron SSCO completo"),
            ("sunat_ruc_masivo.xlsx", "Resultado del flujo SUNAT masivo (paso manual)"),
            ("base_bi.xlsx", "Modelo BI con hojas base_bi y consolidado_txt_bi"),
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

        self._pipe_items = {}
        steps = [
            ("s1", "Lectura TXT"),
            ("s2", "RUC unico + consolidado TXT"),
            ("s3", "Extraccion SUNAT RUC individual"),
            ("s4", "Extraccion SSCO"),
            ("s5", "Extraccion SUNAT masivo"),
            ("s6", "Base BI"),
        ]

        pipe_columns = tuple(range(0, len(steps) * 2 - 1, 2))
        pipe_row.columnconfigure(pipe_columns, weight=1, uniform="pipe")

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

            st = ctk.CTkLabel(row, text="", font=("Segoe UI", 10, "bold"),
                              text_color=PW_MUTED)
            st.pack(side="left", padx=(0, 8), pady=5)

            self._pipe_items[key] = (dot, txt, label, st)

            if i < len(steps) - 1:
                ctk.CTkLabel(pipe_row, text="›", font=("Segoe UI", 13, "bold"),
                             text_color=PW_BORDER).grid(row=0, column=i * 2 + 1, padx=2)

        # Log (ocupa todo el ancho disponible)
        log_card = ctk.CTkFrame(bottom, fg_color="#1B1B1B", corner_radius=12)
        log_card.pack(fill="both", expand=True)

        log_top = ctk.CTkFrame(log_card, fg_color="transparent")
        log_top.pack(fill="x", padx=14, pady=(10, 4))

        ctk.CTkLabel(log_top, text="Registro de actividad",
                     font=("Segoe UI", 11, "bold"),
                     text_color="#E7E7E7").pack(side="left")
        ctk.CTkButton(log_top, text="Limpiar", width=58, height=22,
                      font=FONT_TINY, fg_color="#2A2A2A",
                      hover_color="#3A3A3A", text_color="#CFCFCF",
                      command=lambda: self._log_txt.delete("1.0", tk.END)).pack(side="right")

        self._log_txt = scrolledtext.ScrolledText(
            log_card, font=FONT_MONO, bg="#1B1B1B", fg="#CFCFCF",
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
        self._start_pipeline(mode="full")

    def _start_txt_block(self):
        self._start_pipeline(mode="txt")

    def _start_individual_block(self):
        self._start_pipeline(mode="individual")

    def _start_ssco_block(self):
        self._start_pipeline(mode="ssco")

    def _start_pipeline(self, mode):
        if self._thread and self._thread.is_alive():
            messagebox.showwarning("En ejecucion", "Ya hay un proceso en curso.")
            return

        inp = self.v_input.get().strip()
        out = self.v_output.get().strip()

        mode_labels = {
            "full": "Flujo completo",
            "txt": "Paso 1-2: TXT + consolidado",
            "individual": "Paso 3: SUNAT RUC individual",
            "ssco": "Paso 4: SSCO",
        }

        if mode not in mode_labels:
            messagebox.showerror("Error", "Modo de ejecucion no reconocido.")
            return

        needs_input = mode in ("full", "txt")
        if needs_input and (not inp or not os.path.isdir(inp)):
            messagebox.showerror("Error", "La carpeta de entrada no es valida.")
            return

        if not out or not os.path.isdir(out):
            messagebox.showerror("Error", "La carpeta de salida no es valida.")
            return

        self._active_run_mode = mode
        self._active_run_label = mode_labels[mode]
        self._stop = False
        self._lbl_status.configure(text=f"Ejecutando: {self._active_run_label}", text_color=PW_AMBER)
        self._lbl_status_header.configure(text="Ejecutando...", text_color=PW_AMBER)
        self._dot_status.configure(text_color=PW_AMBER)
        self._progress.set(0)
        self._lbl_step.configure(text="")
        self._log_txt.delete("1.0", tk.END)
        for k in ("txt", "rucs", "ok", "err"):
            self._set_kpi(k, "0")
        self._reset_pipe()

        if mode in ("individual", "ssco"):
            self._log(
                "[INFO] Modo incremental: se usaran archivos existentes en carpeta de salida cuando aplique.",
                "info",
            )

        inp_for_mode = inp if needs_input else None
        self._thread = threading.Thread(
            target=self._run, args=(mode, inp_for_mode, out), daemon=True)
        self._thread.start()

    def _request_stop(self):
        self._stop = True
        self._log("[STOP] Detencion solicitada por el usuario.", "warn")

    def _launch_legacy_bot(self):
        if self._thread and self._thread.is_alive():
            messagebox.showwarning("En ejecucion", "Espera a que termine el proceso actual.")
            return

        out = self.v_output.get().strip()
        if not out or not os.path.isdir(out):
            messagebox.showerror("Error", "La carpeta de salida no es valida.")
            return

        def _worker():
            try:
                self._run_sunat_masivo_block_sync(out)
            except Exception as exc:
                self._pipe_state("s5", "error")
                self._log(f"[ERROR] No se pudo ejecutar SUNAT masivo: {exc}", "error")

        threading.Thread(target=_worker, daemon=True).start()

    def _load_legacy_runner(self):
        """Load ejecutar_modo_automatico from legacy bot, from source or bundled data."""
        candidates = [
            get_runtime_root() / "tools" / "legacy" / "bot.py",
            get_bundle_root() / "tools" / "legacy" / "bot.py",
        ]

        legacy_file = next((p for p in candidates if p.exists()), None)
        if legacy_file is None:
            raise FileNotFoundError(
                "No se encontro tools/legacy/bot.py en runtime ni en bundle PyInstaller"
            )

        spec = importlib.util.spec_from_file_location("legacy_bot_runtime", legacy_file)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"No se pudo cargar el modulo legacy desde: {legacy_file}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        runner = getattr(module, "ejecutar_modo_automatico", None)
        if runner is None:
            raise RuntimeError("No se encontro ejecutar_modo_automatico en bot.py")
        return runner

    def _build_bi_base(self):
        if self._thread and self._thread.is_alive():
            messagebox.showwarning("En ejecucion", "Espera a que termine el proceso actual.")
            return

        out = self.v_output.get().strip()
        if not out or not os.path.isdir(out):
            messagebox.showerror("Error", "La carpeta de salida no es valida.")
            return

        self._pipe_state("s6", "running")
        try:
            self._log("[INFO] Generando base_bi.xlsx desde rucs_unicos.xlsx, consolidado_txt.xlsx, sunat_ruc_individual.xlsx y sunat_ruc_masivo.xlsx...", "info")
            resumen = construir_base_bi_basica(out)
            self._log(
                f"[OK] Base BI generada: {resumen['archivo_salida']} | RUCs: {resumen['total_rucs']} | Coincidencias: {resumen['coincidencias_correctos']}",
                "ok",
            )
            self._pipe_state("s6", "ok")
            messagebox.showinfo("Base BI", "base_bi.xlsx generado correctamente.")
        except Exception as exc:
            self._pipe_state("s6", "error")
            self._log(f"[ERROR] No se pudo generar la base BI: {exc}", "error")
            messagebox.showerror("Error", f"No se pudo generar base_bi.xlsx:\n{exc}")

    def _run_sunat_masivo_block_sync(self, out):
        excel_path = Path(out) / "rucs_unicos.xlsx"

        self._pipe_state("s5", "running")
        self._log("[INFO] Iniciando flujo SUNAT masivo...", "info")

        if not excel_path.exists():
            self._pipe_state("s5", "warn")
            raise FileNotFoundError(f"No se encontro el Excel esperado en: {excel_path}")

        runner = self._load_legacy_runner()

        class _LogWriter:
            def __init__(self, push_log):
                self._push_log = push_log
                self._buf = ""

            def write(self, data):
                if not data:
                    return
                self._buf += data
                while "\n" in self._buf:
                    line, self._buf = self._buf.split("\n", 1)
                    line = line.strip()
                    if line:
                        self._push_log(f"[MASIVO] {line}", "info")

            def flush(self):
                line = self._buf.strip()
                if line:
                    self._push_log(f"[MASIVO] {line}", "info")
                self._buf = ""

        writer = _LogWriter(self._log)
        with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
            ok = runner(str(excel_path), "sunat_ruc_masivo_temp")
        writer.flush()

        if ok:
            self._pipe_state("s5", "ok")
            self._log("[OK] Flujo SUNAT masivo finalizo correctamente.", "ok")
        else:
            self._pipe_state("s5", "warn")
            raise RuntimeError("SUNAT masivo devolvio estado no satisfactorio")

    # ══════════════════════════════════════════
    #  PIPELINE DE EJECUCION
    # ══════════════════════════════════════════
    def _run(self, mode, inp, out):
        t0 = time.time()
        try:
            mode_flags = {
                "full": dict(run_txt_block=True, run_individual_block=True, run_ssco_block=True),
                "txt": dict(run_txt_block=True, run_individual_block=False, run_ssco_block=False),
                "individual": dict(run_txt_block=False, run_individual_block=True, run_ssco_block=False),
                "ssco": dict(run_txt_block=False, run_individual_block=False, run_ssco_block=True),
            }

            resultado = ejecutar_pipeline_sunat(
                carpeta_txt=inp,
                carpeta_output=out,
                exportar_excel=True,
                emit=lambda *event: self._q.put(event),
                should_stop=lambda: self._stop,
                **mode_flags.get(mode, mode_flags["full"]),
            )

            if resultado["status"] in ("stopped", "no_data"):
                self._finish(False)
                return

            if mode == "full":
                self._run_sunat_masivo_block_sync(out)

                self._pipe_state("s6", "running")
                self._log("[INFO] Generando base BI al final del flujo completo...", "info")
                resumen = construir_base_bi_basica(out)
                self._pipe_state("s6", "ok")
                self._log(
                    f"[OK] Base BI generada: {resumen['archivo_salida']} | RUCs: {resumen['total_rucs']} | Coincidencias: {resumen['coincidencias_correctos']}",
                    "ok",
                )

            elapsed = time.time() - t0
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            self._log(
                f"[DONE] {self._active_run_label} completado en {mins}m {secs}s  |  "
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
            if key in self._manual_pipe_keys:
                st.configure(text="MANUAL", text_color=PW_MUTED)
            else:
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
                             "warn": PW_AMBER,    "error": PW_RED,
                             "manual": PW_MUTED}
                    t_map = {"running": "En progreso",
                             "ok":      "Completado",
                             "warn":    "Con observaciones",
                             "error":   "Error",
                             "manual":  "Manual"}
                    short_map = {"running": "RUN",
                                 "ok":      "OK",
                                 "warn":    "WARN",
                                 "error":   "ERR",
                                 "manual":  "MANUAL"}
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
                        done_messages = {
                            "full": "El flujo completo finalizo correctamente.",
                            "txt": "Bloque TXT completado. Se generaron rucs_unicos.xlsx y consolidado_txt.xlsx.",
                            "individual": "Bloque RUC individual completado. Se genero sunat_ruc_individual.xlsx.",
                            "ssco": "Bloque SSCO completado. Se genero sunat_ssco.xlsx.",
                        }
                        messagebox.showinfo("Proceso completado", done_messages.get(self._active_run_mode, "Proceso completado correctamente."))
                    else:
                        self._lbl_status.configure(
                            text="Finalizado con observaciones", text_color=PW_RED)
                        self._lbl_status_header.configure(
                            text="Finalizado con observaciones", text_color=PW_RED)
                        self._dot_status.configure(text_color=PW_RED)
                        warn_messages = {
                            "full": "El proceso termino con observaciones. Revisa el registro de actividad.",
                            "txt": "El bloque TXT termino con observaciones. Revisa el registro de actividad.",
                            "individual": "El bloque RUC individual termino con observaciones. Revisa el registro de actividad.",
                            "ssco": "El bloque SSCO termino con observaciones. Revisa el registro de actividad.",
                        }
                        messagebox.showwarning(
                            "Proceso finalizado",
                            warn_messages.get(self._active_run_mode, "El proceso termino. Revisa el registro de actividad."))

        except queue.Empty:
            pass
        finally:
            self.after(120, self._poll)


if __name__ == "__main__":
    app_root = get_runtime_root()
    license_bundle_root = app_root / "license_manager"
    license_result = validate_license(
        license_path=license_bundle_root / "license.json",
        public_key_path=license_bundle_root / "license_public_key.pem",
    )

    if not license_result.valid:
        bootstrap = tk.Tk()
        bootstrap.withdraw()
        messagebox.showerror("Licencia invalida", license_result.message)
        bootstrap.destroy()
        raise SystemExit(1)

    if license_result.days_to_expiry is not None and license_result.days_to_expiry <= 7:
        bootstrap = tk.Tk()
        bootstrap.withdraw()
        messagebox.showwarning(
            "Licencia por vencer",
            (
                f"La licencia vence en {license_result.days_to_expiry} dia(s). "
                "Contacta al administrador para renovarla."
            ),
        )
        bootstrap.destroy()

    app = SunatApp()
    app.mainloop()