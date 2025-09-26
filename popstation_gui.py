import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk, simpledialog, colorchooser
from PIL import Image, ImageTk
import webbrowser
import datetime
import winsound
from tkinterdnd2 import TkinterDnD, DND_FILES
from popstation_core import *
import os
import json

# ---------------- Configurações de GUI ----------------
COVER_SIZE = (150, 150)   # Tamanho das capas (aumentado)
LOGO_SIZE = (60, 60)      # Tamanho dos logos
PREVIEW_SIZE = (240, 240) # Tamanho do preview ao passar o mouse
TILE_BG = "#2e2e2e"
BG_COLOR = "#1b1b1b"
TEXT_COLOR = "#e0e0e0"
ACCENT_COLOR = "#4a90e2"
ERROR_COLOR = "#ff555b"
SUCCESS_COLOR = "#50fa7b"
WARNING_COLOR = "#f1fa8c"
CURRENT_VERSION = "4.3"

# ---------------- Tooltip de Imagem ----------------
class ImageTooltip:
    def __init__(self, widget, image_path=None, size=(240, 240)):
        self.widget = widget
        self.image_path = image_path
        self.size = size
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
    
    def show_tooltip(self, event=None):
        if not self.image_path or not os.path.exists(self.image_path):
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        try:
            img = Image.open(self.image_path)
            img.thumbnail(self.size)
            photo = ImageTk.PhotoImage(img)
            label = tk.Label(self.tooltip_window, image=photo, bg="black", bd=2, relief="solid")
            label.image = photo
            label.pack()
        except:
            label = tk.Label(self.tooltip_window, text="Erro ao carregar imagem", bg="red", fg="white", padx=5, pady=5)
            label.pack()
    
    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

# ---------------- GUI Principal ----------------
class PopsManagerGUI:
    def __init__(self, root):
        self.root = root
        root.title(f"POPStation v{CURRENT_VERSION}")
        root.geometry("1100x750")  # Tamanho fixo padrão
        root.configure(bg=BG_COLOR)
        self.current_theme = "dark"
        self.retro_mode = False
        self.files = []
        self.covers = {}
        self.logos = {}
        self.target_dir = None
        self.cover_images = {}
        self.game_tiles = {}
        self.bios_files = self.find_bios_files()
        self.advanced_files = []
        self.advanced_output_folder = None
        self.status_var = tk.StringVar(value="Pronto")
        self.status_bar = tk.Label(root, textvariable=self.status_var, bg="#333", fg="#aaa", anchor="w", padx=10)
        self.status_bar.pack(side="bottom", fill="x")
        script_root = get_script_root()
        print(f"[INFO] Pasta raiz do script: {script_root}")
        self.create_menu()
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        self.tab_convert = ttk.Frame(self.notebook)
        self.tab_manage = ttk.Frame(self.notebook)
        self.tab_advanced = ttk.Frame(self.notebook)
        self.tab_usb_install = ttk.Frame(self.notebook)
        self.tab_console = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_convert, text="🎮 Conversão de Jogos")
        self.notebook.add(self.tab_manage, text="📁 Gerenciamento de Jogos")
        self.notebook.add(self.tab_advanced, text="🔄 Conversões Avançadas")
        self.notebook.add(self.tab_usb_install, text="🔌 Installs USB")
        self.notebook.add(self.tab_console, text="⌨️ Console")
        self.setup_convert_tab()
        self.setup_manage_tab()
        self.setup_advanced_tab()
        self.setup_usb_install_tab()
        self.setup_console_tab()
        root.bind("<Control-Shift-R>", self.toggle_retro_mode)
        self.setup_drag_drop()
    
    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Selecionar Pasta Destino", command=self.select_folder)
        file_menu.add_command(label="Abrir Pasta Destino", command=self.open_target_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Alternar Tema", command=self.toggle_theme)
        file_menu.add_separator()
        file_menu.add_command(label="Sair", command=self.root.quit)
        menubar.add_cascade(label="Arquivo", menu=file_menu)
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Exportar Lista (CSV)", command=self.export_csv)
        tools_menu.add_command(label="Exportar Lista (HTML)", command=self.export_html)
        tools_menu.add_command(label="Verificar Integridade", command=self.verify_integrity)
        menubar.add_cascade(label="Ferramentas", menu=tools_menu)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Tutorial no YouTube", command=lambda: webbrowser.open("https://youtube.com"))
        help_menu.add_command(label="Reportar Bug", command=lambda: webbrowser.open("https://github.com"))
        help_menu.add_command(label="Sobre", command=self.show_about)
        menubar.add_cascade(label="Ajuda", menu=help_menu)
    
    def setup_drag_drop(self):
        self.tab_convert.drop_target_register(DND_FILES)
        self.tab_convert.dnd_bind('<<Drop>>', self.on_drop)
    
    def on_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        valid_files = [f for f in files if os.path.splitext(f)[1].lower() in SUPPORTED_FORMATS]
        if valid_files:
            self.files.extend(valid_files)
            self.update_file_listbox()
            self.log(f"📥 {len(valid_files)} arquivos adicionados via arrastar e soltar.")
    
    def setup_convert_tab(self):
        frame_files = ttk.LabelFrame(self.tab_convert, text="1. 📂 Seleção de Jogos")
        frame_files.pack(fill="x", padx=10, pady=5)
        btn_frame = tk.Frame(frame_files)
        btn_frame.pack(side="left", padx=5, pady=5)
        ttk.Button(btn_frame, text="📁 Selecionar Arquivos", command=self.select_files).pack(pady=2)
        ttk.Button(btn_frame, text="🖼️ Selecionar Capas", command=self.select_covers).pack(pady=2)
        ttk.Button(btn_frame, text="🔖 Selecionar Logos", command=self.select_logos).pack(pady=2)
        self.listbox = tk.Listbox(frame_files, width=80, height=10, bg="#2b2b2b", fg=TEXT_COLOR)
        self.listbox.pack(side="left", padx=5, pady=5, fill="both", expand=True)
        frame_bios = ttk.LabelFrame(self.tab_convert, text="2. 🖥️ BIOS")
        frame_bios.pack(fill="x", padx=10, pady=5)
        self.bios_var = tk.StringVar()
        if self.bios_files:
            self.bios_var.set(self.bios_files[0])
            ttk.Combobox(frame_bios, textvariable=self.bios_var, values=self.bios_files, state="readonly").pack(pady=5)
        else:
            tk.Label(frame_bios, text="Nenhum BIOS.BIN encontrado!", fg="red").pack()
        frame_dest = ttk.LabelFrame(self.tab_convert, text="3. 📂 Pasta de Destino")
        frame_dest.pack(fill="x", padx=10, pady=5)
        self.dest_label = tk.Label(frame_dest, text="Nenhuma pasta selecionada", bg=BG_COLOR, fg=TEXT_COLOR)
        self.dest_label.pack(side="left", padx=5, pady=5)
        ttk.Button(frame_dest, text="Selecionar Pasta", command=self.select_folder).pack(side="left", padx=5, pady=5)
        self.progress = ttk.Progressbar(self.tab_convert, orient="horizontal", length=800, mode="determinate")
        self.progress.pack(pady=10)
        self.progress_label = tk.Label(self.tab_convert, text="", bg=BG_COLOR, fg="#00ff00")
        self.progress_label.pack()
        frame_actions = ttk.LabelFrame(self.tab_convert, text="4. ⚡ Ações")
        frame_actions.pack(fill="x", padx=10, pady=5)
        ttk.Button(frame_actions, text="▶️ Processar Jogos", command=self.process_games).pack(side="left", padx=5, pady=5)
        self.log_text = tk.Text(frame_actions, height=8, width=80, bg="#1b1b1b", fg=TEXT_COLOR)
        self.log_text.pack(side="left", padx=5, pady=5, fill="both", expand=True)
        self.log_text.tag_config("error", foreground=ERROR_COLOR)
        self.log_text.tag_config("success", foreground=SUCCESS_COLOR)
        self.log_text.tag_config("warning", foreground=WARNING_COLOR)
    
    def setup_manage_tab(self):
        # --- Frame superior: Contagem e uso de disco ---
        top_frame = tk.Frame(self.tab_manage, bg=BG_COLOR)
        top_frame.pack(fill="x", padx=5, pady=5)
        # Contagem de jogos
        self.games_count_label = tk.Label(
            top_frame,
            text="🔍 Jogos: 0",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=("Arial", 10, "bold")
        )
        self.games_count_label.pack(side="left", padx=10)
        # Uso de disco
        self.disk_usage_label = tk.Label(
            top_frame,
            text="💾 Uso: -- / -- (---% livre)",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=("Arial", 9)
        )
        self.disk_usage_label.pack(side="right", padx=10)
        # --- Barra de pesquisa + modo de exibição ---
        search_and_view_frame = tk.Frame(self.tab_manage, bg=BG_COLOR)
        search_and_view_frame.pack(fill="x", padx=5, pady=5)
        tk.Label(search_and_view_frame, text="🔍 Pesquisar:", bg=BG_COLOR, fg=TEXT_COLOR).pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.refresh_manage_tab())  # Atualiza em tempo real
        tk.Entry(search_and_view_frame, textvariable=self.search_var, width=40).pack(side="left", padx=5, fill="x", expand=True)
        # Botões de modo de exibição
        view_frame = tk.Frame(search_and_view_frame, bg=BG_COLOR)
        view_frame.pack(side="right", padx=10)
        self.view_mode = tk.StringVar(value="grid")  # grid | list | cards
        ttk.Radiobutton(view_frame, text="Grid", variable=self.view_mode, value="grid", command=self.refresh_manage_tab).pack(side="left", padx=2)
        ttk.Radiobutton(view_frame, text="Lista", variable=self.view_mode, value="list", command=self.refresh_manage_tab).pack(side="left", padx=2)
        ttk.Radiobutton(view_frame, text="Cards", variable=self.view_mode, value="cards", command=self.refresh_manage_tab).pack(side="left", padx=2)
        # Botões de exportação e abertura
        ttk.Button(search_and_view_frame, text="📊 Exportar CSV", command=self.export_csv).pack(side="right", padx=5)
        ttk.Button(search_and_view_frame, text="📂 Abrir Pasta", command=self.open_target_folder).pack(side="right", padx=5)
        # --- Canvas com scroll para os jogos ---
        self.canvas = tk.Canvas(self.tab_manage, bg=BG_COLOR, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.tab_manage, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=BG_COLOR)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True, padx=5)
        self.scrollbar.pack(side="right", fill="y")
        # Inicializa a interface
        self.refresh_manage_tab()
    
    def setup_advanced_tab(self):
        frame = ttk.Frame(self.tab_advanced)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        tk.Label(frame, text="🔄 Conversões Avançadas", font=("Arial", 12, "bold")).pack(pady=5)
        # --- Arquivo de origem ---
        file_frame = ttk.LabelFrame(frame, text="1. Selecione o arquivo de origem")
        file_frame.pack(fill="x", pady=5)
        self.advanced_file_label = tk.Label(file_frame, text="Nenhum arquivo selecionado", bg=BG_COLOR, fg=TEXT_COLOR)
        self.advanced_file_label.pack(side="left", padx=5, pady=5)
        ttk.Button(file_frame, text="Selecionar Arquivo", command=self.select_advanced_file).pack(side="left", padx=5, pady=5)
        # --- Formato de saída ---
        format_frame = ttk.LabelFrame(frame, text="2. Escolha o formato de saída")
        format_frame.pack(fill="x", pady=5)
        self.output_format = tk.StringVar(value="cue_bin")
        formats = [
            ("CUE + BIN", "cue_bin"),
            ("ISO", "iso"),
            ("ZSO", "zso"),
            ("GDI", "gdi"),
            ("CHD", "chd"),
            ("VCD", "vcd"),
        ]
        for text, value in formats:
            ttk.Radiobutton(format_frame, text=text, variable=self.output_format, value=value).pack(anchor="w", padx=20)
        # --- Pasta de saída ---
        output_frame = ttk.LabelFrame(frame, text="3. Pasta de Saída")
        output_frame.pack(fill="x", pady=5)
        self.advanced_output_label = tk.Label(output_frame, text="Nenhuma pasta selecionada", bg=BG_COLOR, fg=TEXT_COLOR)
        self.advanced_output_label.pack(side="left", padx=5, pady=5)
        ttk.Button(output_frame, text="Selecionar Pasta", command=self.select_advanced_output).pack(side="left", padx=5, pady=5)
        # --- Botão de iniciar ---
        ttk.Button(frame, text="▶️ Iniciar Conversão", command=self.start_advanced_conversion).pack(pady=10)
        # --- Log ---
        self.advanced_log_text = tk.Text(frame, height=10, bg="#1b1b1b", fg=TEXT_COLOR)
        self.advanced_log_text.pack(fill="both", expand=True, pady=5)
        self.advanced_log_text.tag_config("error", foreground=ERROR_COLOR)
        self.advanced_log_text.tag_config("success", foreground=SUCCESS_COLOR)
    
    def setup_usb_install_tab(self):
        frame = ttk.Frame(self.tab_usb_install)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        tk.Label(frame, text="🔌 Installs USB", font=("Arial", 14, "bold"), bg=BG_COLOR, fg=ACCENT_COLOR).pack(pady=10)
        desc = tk.Label(
            frame,
            text="Copie toda a estrutura da pasta 'usb_install' para seu dispositivo USB.\nTodos os arquivos e pastas serão copiados e ocultados automaticamente.",
            bg=BG_COLOR, fg=TEXT_COLOR, wraplength=900, justify="center"
        )
        desc.pack(pady=5)
        dest_frame = ttk.LabelFrame(frame, text="📂 Selecione o diretório de destino (USB)")
        dest_frame.pack(fill="x", pady=10, padx=20)
        self.usb_dest_label = tk.Label(dest_frame, text="Nenhum destino selecionado", bg=BG_COLOR, fg=TEXT_COLOR, anchor="w")
        self.usb_dest_label.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        ttk.Button(dest_frame, text="📁 Selecionar Pasta", command=self.select_usb_destination).pack(side="right", padx=10, pady=10)
        origin_frame = ttk.LabelFrame(frame, text="📦 Origem (automática)")
        origin_frame.pack(fill="x", pady=10, padx=20)
        script_root = get_script_root()
        usb_install_path = os.path.join(script_root, "usb_install")
        self.usb_origin_label = tk.Label(
            origin_frame,
            text=f"📂 {usb_install_path}",
            bg=BG_COLOR, fg="#888", anchor="w", font=("Consolas", 9)
        )
        self.usb_origin_label.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        self.origin_status = tk.Label(
            origin_frame,
            text="⏳ Verificando...",
            bg=BG_COLOR, fg=WARNING_COLOR, font=("Arial", 9, "italic")
        )
        self.origin_status.pack(side="right", padx=10, pady=10)
        self.update_usb_origin_status()
        btn_frame = tk.Frame(frame, bg=BG_COLOR)
        btn_frame.pack(pady=20)
        self.install_btn = ttk.Button(
            btn_frame,
            text="🚀 Iniciar Instalação USB",
            command=self.start_usb_install,
            style="Accent.TButton"
        )
        self.install_btn.pack(ipadx=20, ipady=8)
        log_frame = ttk.LabelFrame(frame, text="📝 Log de Operação")
        log_frame.pack(fill="both", expand=True, pady=10, padx=20)
        self.usb_log_text = tk.Text(log_frame, height=12, bg="#1b1b1b", fg=TEXT_COLOR, font=("Consolas", 9))
        self.usb_log_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.usb_log_text.tag_config("error", foreground=ERROR_COLOR)
        self.usb_log_text.tag_config("success", foreground=SUCCESS_COLOR)
        self.usb_log_text.tag_config("warning", foreground=WARNING_COLOR)
        self.usb_log_text.tag_config("info", foreground="#aaa")
        self.usb_log_text.insert("1.0", ">>> Aguardando seleção de destino...\n", "info")
        self.usb_log_text.config(state="disabled")
    
    def setup_console_tab(self):
        frame = ttk.Frame(self.tab_console)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        tk.Label(frame, text="⌨️ Console", font=("Arial", 10, "bold")).pack(anchor="w")
        self.console_input = tk.Entry(frame, font=("Consolas", 10))
        self.console_input.pack(fill="x", pady=5)
        self.console_input.bind("<Return>", self.execute_console_command)
        self.console_output = tk.Text(frame, height=20, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 10))
        self.console_output.pack(fill="both", expand=True, pady=5)
        self.console_output.insert("1.0", ">>> Console iniciado. Digite 'help'.\n")
    
    def execute_console_command(self, event=None):
        cmd = self.console_input.get().strip()
        self.console_output.insert("end", f">>> {cmd}\n")
        responses = {
            "help": "Comandos: help, clear, list, version",
            "clear": lambda: self.console_output.delete("1.0", "end"),
            "list": lambda: self.list_games_in_console(),
            "version": f"POPStation v{CURRENT_VERSION}"
        }
        if cmd in responses:
            if callable(responses[cmd]):
                responses[cmd]()
            else:
                self.console_output.insert("end", responses[cmd] + "\n")
        else:
            self.console_output.insert("end", "Comando não reconhecido.\n")
        self.console_input.delete(0, "end")
        self.console_output.see("end")
    
    def list_games_in_console(self):
        if not self.target_dir:
            self.console_output.insert("end", "Nenhuma pasta selecionada.\n")
            return
        conf_file = os.path.join(self.target_dir, "conf_apps.cfg")
        if not os.path.exists(conf_file):
            self.console_output.insert("end", "Nenhum jogo encontrado.\n")
            return
        with open(conf_file, 'r', encoding='utf-8') as f:
            for line in f:
                if "=" in line:
                    game_key, _ = line.strip().split("=", 1)
                    self.console_output.insert("end", f" - {game_key}\n")
    
    def find_bios_files(self):
        script_root = get_script_root()
        bios_files = []
        for file in os.listdir(script_root):
            if file.upper().startswith("BIOS") and file.upper().endswith(".BIN"):
                bios_files.append(file)
        return bios_files if bios_files else ["BIOS.BIN"]
    
    def log(self, message, level="info", advanced=False):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        print(full_message)
        if advanced:
            tag = "error" if "❌" in message else "success" if "✅" in message else ""
            self.advanced_log_text.insert(tk.END, full_message + "\n", tag)
            self.advanced_log_text.see(tk.END)
        else:
            tag = "error" if "❌" in message or "Erro" in message else "success" if "✅" in message else "warning" if "⚠️" in message else ""
            self.log_text.insert(tk.END, full_message + "\n", tag)
            self.log_text.see(tk.END)
        ensure_dir("logs")
        with open(os.path.join("logs", "popstation.log"), "a", encoding="utf-8") as f:
            f.write(full_message + "\n")
        self.status_var.set(message[:50] + "..." if len(message) > 50 else message)
        self.root.update_idletasks()
    
    def update_progress(self, message, value):
        self.progress_label.config(text=message)
        self.progress['value'] = value
        self.root.update_idletasks()
    
    def select_files(self):
        files = filedialog.askopenfilenames(
            filetypes=[("Jogos PS1/CHD", "*.iso *.bin *.cue *.mdf *.ecm *.img *.chd *.gdi *.zso")]
        )
        if files:
            self.files.extend(files)
            self.update_file_listbox()
            self.log(f"📥 {len(files)} arquivos selecionados.")
    
    def update_file_listbox(self):
        self.listbox.delete(0, tk.END)
        for f in self.files:
            self.listbox.insert(tk.END, os.path.basename(f))
    
    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.target_dir = folder
            self.dest_label.config(text=f"📁 Pasta destino: {folder}")
            self.log(f"✅ Pasta selecionada: {folder}")
            self.refresh_manage_tab()
    
    def open_target_folder(self):
        if self.target_dir and os.path.exists(self.target_dir):
            os.startfile(self.target_dir)
        else:
            messagebox.showwarning("Aviso", "Nenhuma pasta válida selecionada!")
    
    def select_covers(self):
        for file_path in self.files:
            cover_path = filedialog.askopenfilename(
                title=f"Capa para {os.path.basename(file_path)}",
                filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp")]
            )
            if cover_path:
                game_name = os.path.splitext(os.path.basename(file_path))[0]
                self.covers[game_name] = cover_path
                self.log(f"🖼️ Capa selecionada para {game_name}")
    
    def select_logos(self):
        for file_path in self.files:
            logo_path = filedialog.askopenfilename(
                title=f"Logo para {os.path.basename(file_path)}",
                filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp")]
            )
            if logo_path:
                game_name = os.path.splitext(os.path.basename(file_path))[0]
                self.logos[game_name] = logo_path
                self.log(f"🔖 Logo selecionado para {game_name}")
    
    def process_games(self):
        if not self.files or not self.target_dir:
            messagebox.showwarning("⚠️ Aviso", "Selecione arquivos e pasta destino!")
            return
        script_root = get_script_root()
        essential_files = [POPS_ELF_NAME, SLOT0_VMC_NAME, SLOT1_VMC_NAME]
        bios_selected = self.bios_var.get()
        if not os.path.exists(os.path.join(script_root, bios_selected)):
            messagebox.showerror("❌ Erro", f"BIOS não encontrado: {bios_selected}")
            return
        essential_files.append(bios_selected)
        missing = []
        for f in essential_files:
            if not os.path.exists(os.path.join(script_root, f)):
                missing.append(f)
        if missing:
            messagebox.showerror("❌ Erro", f"Arquivos ausentes: {', '.join(missing)}")
            return
        total = len(self.files)
        self.progress['maximum'] = total * 100
        self.log(f"▶️ Processando {total} jogos...")
        pops_dir = os.path.join(self.target_dir, POPS_DIR_NAME)
        ensure_dir(pops_dir)
        copy_file(os.path.join(script_root, bios_selected), os.path.join(pops_dir, BIOS_FILE_NAME))
        copy_file(os.path.join(script_root, POPS_ELF_NAME), os.path.join(pops_dir, "POPSTARTER.ELF"))
        copy_src = os.path.join(script_root, "_copy")
        if os.path.exists(copy_src):
            self.log(f"📦 Copiando conteúdo de _copy para POPS...")
            copy_tree(copy_src, pops_dir, self.log)
        success_count = 0
        for i, f in enumerate(self.files):
            self.update_progress(f"Jogo {i+1}/{total}", i * 100)
            game_name = os.path.splitext(os.path.basename(f))[0]
            cover_path = self.covers.get(game_name)
            logo_path = self.logos.get(game_name)
            if process_game(f, pops_dir, self.target_dir, cover_path, logo_path, self.log, self.update_progress):
                success_count += 1
        self.update_progress("✅ Concluído!", total * 100)
        self.log(f"🎉 {success_count}/{total} jogos processados!", "success")
        try:
            winsound.PlaySound(os.path.join(script_root, "success.wav"), winsound.SND_ASYNC)
        except:
            pass
        self.files = []
        self.covers = {}
        self.logos = {}
        self.listbox.delete(0, tk.END)
        self.log("📋 Lista limpa.")
        self.refresh_manage_tab()
    
    def refresh_manage_tab(self):
        """Atualiza a lista de jogos com base no modo de exibição e no filtro de busca."""
        self.cover_images.clear()
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.game_tiles = {}
        if not self.target_dir:
            self.games_count_label.config(text="🔍 Jogos: 0")
            self.disk_usage_label.config(text="💾 Uso: -- / -- (---% livre)")
            return
        conf_file = os.path.join(self.target_dir, "conf_apps.cfg")
        art_dir = os.path.join(self.target_dir, ART_DIR_NAME)
        pops_dir = os.path.join(self.target_dir, POPS_DIR_NAME)
        if not os.path.exists(conf_file):
            self.games_count_label.config(text="🔍 Jogos: 0")
            self.disk_usage_label.config(text=f"💾 Uso: -- / -- (---% livre)")
            return
        # Coleta jogos válidos
        games = []
        with open(conf_file, 'r', encoding='utf-8') as f:
            for line in f:
                if "=" in line:
                    game_key, elf = line.strip().split("=", 1)
                    elf_name_no_ext = get_elf_name_from_game_key(game_key, self.target_dir)
                    if not elf_name_no_ext:
                        continue
                    valid_game = any(
                        os.path.exists(os.path.join(pops_dir, f"{elf_name_no_ext}{ext}")) 
                        for ext in SUPPORTED_FORMATS + [".VCD"]
                    )
                    if valid_game:
                        games.append(game_key)
        # Ordena alfabeticamente (ignorando case)
        games.sort(key=str.lower)
        # Aplica filtro de busca
        search_text = self.search_var.get().lower().strip()
        if search_text:
            games = [g for g in games if search_text in g.lower()]
        count = len(games)
        self.games_count_label.config(text=f"🔍 Jogos: {count}")
        # Calcula uso de disco
        try:
            usage = shutil.disk_usage(self.target_dir)
            total_gb = usage.total / (1024**3)
            used_gb = usage.used / (1024**3)
            free_gb = usage.free / (1024**3)
            percent_used = (used_gb / total_gb) * 100 if total_gb > 0 else 0
            self.disk_usage_label.config(
                text=f"💾 Uso: {used_gb:.1f} GB / {total_gb:.1f} GB ({free_gb:.1f} GB livre)"
            )
        except Exception as e:
            self.disk_usage_label.config(text=f"💾 Uso: ❌ Não acessível ({str(e)})")
        # --- RENDERIZAÇÃO BASEADA NO MODO DE EXIBIÇÃO ---
        mode = self.view_mode.get()
        if mode == "list":
            # Modo Lista: Tabela com colunas
            headers = ["Nome do Jogo", "Arquivo ELF", "Tamanho", "Status"]
            for col, header in enumerate(headers):
                tk.Label(
                    self.scrollable_frame,
                    text=header,
                    bg=TILE_BG,
                    fg=ACCENT_COLOR,
                    font=("Arial", 9, "bold"),
                    anchor="w",
                    relief="raised",
                    padx=8,
                    pady=5
                ).grid(row=0, column=col, sticky="ew", padx=1, pady=1)
            for idx, game_key in enumerate(games, start=1):
                elf_name_no_ext = get_elf_name_from_game_key(game_key, self.target_dir)
                elf_name = f"XX.{elf_name_no_ext}.ELF"
                vcd_path = os.path.join(pops_dir, f"{elf_name_no_ext}.VCD")
                # --- NOVO: TAMANHO DO JOGO ---
                size_str = "N/A"
                if os.path.exists(vcd_path):
                    size_bytes = os.path.getsize(vcd_path)
                    if size_bytes < 1024**2:
                        size_str = f"{size_bytes / 1024:.1f} KB"
                    elif size_bytes < 1024**3:
                        size_str = f"{size_bytes / (1024**2):.1f} MB"
                    else:
                        size_str = f"{size_bytes / (1024**3):.1f} GB"
                status = "✅ VCD" if os.path.exists(vcd_path) else "⚠️ Ausente"
                # Linha da tabela
                tk.Label(self.scrollable_frame, text=game_key, bg=BG_COLOR, fg=TEXT_COLOR, anchor="w", font=("Arial", 9)).grid(row=idx, column=0, sticky="ew", padx=1, pady=1)
                tk.Label(self.scrollable_frame, text=elf_name, bg=BG_COLOR, fg=TEXT_COLOR, anchor="w", font=("Arial", 9)).grid(row=idx, column=1, sticky="ew", padx=1, pady=1)
                tk.Label(self.scrollable_frame, text=size_str, bg=BG_COLOR, fg=TEXT_COLOR, anchor="w", font=("Arial", 9)).grid(row=idx, column=2, sticky="ew", padx=1, pady=1)
                tk.Label(self.scrollable_frame, text=status, bg=BG_COLOR, fg=SUCCESS_COLOR if status == "✅ VCD" else WARNING_COLOR, anchor="w", font=("Arial", 9)).grid(row=idx, column=3, sticky="ew", padx=1, pady=1)
                # Menu contextual
                menu = tk.Menu(self.root, tearoff=0)
                menu.add_command(label="✏️ Renomear", command=lambda g=game_key: self.rename_game(g))
                menu.add_command(label="🗑️ Apagar", command=lambda g=game_key: self.delete_game(g))
                menu.add_command(label="🖼️ Atualizar Capa", command=lambda g=game_key: self.update_cover(g))
                menu.add_command(label="🔖 Atualizar Logo", command=lambda g=game_key: self.update_logo(g))
                menu.add_separator()
                menu.add_command(label="💿 Converter para CUE+BIN", command=lambda g=game_key: self.convert_game_to_cue_bin(g))
                menu.add_command(label="📀 Converter para ISO", command=lambda g=game_key: self.convert_game_to_iso(g))
                row_frame = tk.Frame(self.scrollable_frame, bg=BG_COLOR)
                row_frame.grid(row=idx, column=0, columnspan=4, sticky="ew", padx=1, pady=1)
                row_frame.bind("<Button-3>", lambda e, m=menu: m.tk_popup(e.x_root, e.y_root))
                for child in row_frame.winfo_children():
                    child.bind("<Button-3>", lambda e, m=menu: m.tk_popup(e.x_root, e.y_root))
        elif mode == "cards":
            # Modo Cards: Visualização tipo "cartão" com imagem menor
            columns = 4
            idx = 0
            for game_key in games:
                frame = tk.Frame(self.scrollable_frame, bg=TILE_BG, padx=8, pady=8, relief="raised", bd=1, width=180, height=200)
                frame.grid_propagate(False)
                frame.grid(row=idx // columns, column=idx % columns, padx=10, pady=10, sticky="n")
                self.game_tiles[game_key] = frame
                idx += 1
                elf_name_no_ext = get_elf_name_from_game_key(game_key, self.target_dir)
                cover_path = None
                logo_path = None
                for ext in [".png", ".jpg", ".jpeg", ".bmp"]:
                    test_cover = os.path.join(art_dir, f"XX.{elf_name_no_ext}.ELF_COV{ext}")
                    test_logo = os.path.join(art_dir, f"XX.{elf_name_no_ext}.ELF_LGO{ext}")
                    if os.path.exists(test_cover):
                        cover_path = test_cover
                    if os.path.exists(test_logo):
                        logo_path = test_logo
                # Imagem da capa (miniatura)
                if cover_path and os.path.exists(cover_path):
                    try:
                        img = Image.open(cover_path)
                        img.thumbnail((120, 120))
                        photo = ImageTk.PhotoImage(img)
                        self.cover_images[cover_path] = photo
                        lbl_cover = tk.Label(frame, image=photo, bg=TILE_BG)
                        lbl_cover.pack(pady=2)
                        ImageTooltip(lbl_cover, cover_path, PREVIEW_SIZE)
                    except Exception as e:
                        self.log(f"Erro ao carregar capa {cover_path}: {e}", "error")
                        lbl_cover = tk.Label(frame, text="❌ Capa", width=15, height=7, bg=TILE_BG, fg="red")
                        lbl_cover.pack(pady=2)
                else:
                    lbl_cover = tk.Label(frame, text="Sem capa", width=15, height=7, bg=TILE_BG, fg=TEXT_COLOR)
                    lbl_cover.pack(pady=2)
                # Nome do jogo
                tk.Label(frame, text=game_key, bg=TILE_BG, fg=TEXT_COLOR, wraplength=160, font=("Arial", 9, "bold")).pack(pady=2)
                # --- NOVO: TAMANHO DO JOGO ---
                vcd_path = os.path.join(pops_dir, f"{elf_name_no_ext}.VCD")
                size_str = "N/A"
                if os.path.exists(vcd_path):
                    size_bytes = os.path.getsize(vcd_path)
                    if size_bytes < 1024**2:
                        size_str = f"{size_bytes / 1024:.1f} KB"
                    elif size_bytes < 1024**3:
                        size_str = f"{size_bytes / (1024**2):.1f} MB"
                    else:
                        size_str = f"{size_bytes / (1024**3):.1f} GB"
                tk.Label(frame, text=f"Tamanho: {size_str}", bg=TILE_BG, fg=TEXT_COLOR, font=("Arial", 8)).pack(pady=1)
                # Status
                status = "✅" if os.path.exists(vcd_path) else "❌"
                tk.Label(frame, text=status, bg=TILE_BG, fg=SUCCESS_COLOR if status == "✅" else ERROR_COLOR, font=("Arial", 8)).pack(pady=1)
                # Menu contextual
                menu = tk.Menu(self.root, tearoff=0)
                menu.add_command(label="✏️ Renomear", command=lambda g=game_key: self.rename_game(g))
                menu.add_command(label="🗑️ Apagar", command=lambda g=game_key: self.delete_game(g))
                menu.add_command(label="🖼️ Atualizar Capa", command=lambda g=game_key: self.update_cover(g))
                menu.add_command(label="🔖 Atualizar Logo", command=lambda g=game_key: self.update_logo(g))
                menu.add_separator()
                menu.add_command(label="💿 Converter para CUE+BIN", command=lambda g=game_key: self.convert_game_to_cue_bin(g))
                menu.add_command(label="📀 Converter para ISO", command=lambda g=game_key: self.convert_game_to_iso(g))
                frame.bind("<Button-3>", lambda e, m=menu: m.tk_popup(e.x_root, e.y_root))
                for child in frame.winfo_children():
                    child.bind("<Button-3>", lambda e, m=menu: m.tk_popup(e.x_root, e.y_root))
        else:  # mode == "grid" (padrão)
            # Modo Grid: Layout clássico com capas grandes
            columns = 5
            idx = 0
            for game_key in games:
                frame = tk.Frame(self.scrollable_frame, bg=TILE_BG, padx=5, pady=5, relief="raised", bd=1)
                frame.grid(row=idx // columns, column=idx % columns, padx=10, pady=10, sticky="n")
                self.game_tiles[game_key] = frame
                idx += 1
                elf_name_no_ext = get_elf_name_from_game_key(game_key, self.target_dir)
                cover_path = None
                logo_path = None
                for ext in [".png", ".jpg", ".jpeg", ".bmp"]:
                    test_cover = os.path.join(art_dir, f"XX.{elf_name_no_ext}.ELF_COV{ext}")
                    test_logo = os.path.join(art_dir, f"XX.{elf_name_no_ext}.ELF_LGO{ext}")
                    if os.path.exists(test_cover):
                        cover_path = test_cover
                    if os.path.exists(test_logo):
                        logo_path = test_logo
                # Capa
                if cover_path and os.path.exists(cover_path):
                    try:
                        img = Image.open(cover_path)
                        img.thumbnail(COVER_SIZE)
                        photo = ImageTk.PhotoImage(img)
                        self.cover_images[cover_path] = photo
                        lbl_cover = tk.Label(frame, image=photo, bg=TILE_BG)
                        lbl_cover.pack(pady=2)
                        ImageTooltip(lbl_cover, cover_path, PREVIEW_SIZE)
                    except Exception as e:
                        self.log(f"Erro ao carregar capa {cover_path}: {e}", "error")
                        lbl_cover = tk.Label(frame, text="Erro na capa", width=15, height=7, bg=TILE_BG, fg="red")
                        lbl_cover.pack(pady=2)
                else:
                    lbl_cover = tk.Label(frame, text="Sem capa", width=15, height=7, bg=TILE_BG, fg=TEXT_COLOR)
                    lbl_cover.pack(pady=2)
                # Logo (pequeno)
                if logo_path and os.path.exists(logo_path):
                    try:
                        img = Image.open(logo_path)
                        img.thumbnail(LOGO_SIZE)
                        photo = ImageTk.PhotoImage(img)
                        self.cover_images[logo_path] = photo
                        lbl_logo = tk.Label(frame, image=photo, bg=TILE_BG)
                        lbl_logo.pack(pady=2)
                        ImageTooltip(lbl_logo, logo_path, PREVIEW_SIZE)
                    except:
                        pass
                # Nome do jogo
                tk.Label(frame, text=game_key, bg=TILE_BG, fg=TEXT_COLOR, wraplength=150, font=("Arial", 9, "bold")).pack()
                # Arquivo ELF
                tk.Label(frame, text=os.path.basename(get_elf_name_from_game_key(game_key, self.target_dir)) + ".ELF", bg=TILE_BG, fg=TEXT_COLOR, font=("Arial", 8)).pack()
                # --- NOVO: TAMANHO DO JOGO ---
                vcd_path = os.path.join(pops_dir, f"{elf_name_no_ext}.VCD")
                size_str = "N/A"
                if os.path.exists(vcd_path):
                    size_bytes = os.path.getsize(vcd_path)
                    if size_bytes < 1024**2:
                        size_str = f"{size_bytes / 1024:.1f} KB"
                    elif size_bytes < 1024**3:
                        size_str = f"{size_bytes / (1024**2):.1f} MB"
                    else:
                        size_str = f"{size_bytes / (1024**3):.1f} GB"
                tk.Label(frame, text=f"Tamanho: {size_str}", bg=TILE_BG, fg=TEXT_COLOR, font=("Arial", 8)).pack()
                # Status VCD
                status = "✅" if os.path.exists(vcd_path) else "❌"
                tk.Label(frame, text=status, bg=TILE_BG, fg=SUCCESS_COLOR if status == "✅" else ERROR_COLOR, font=("Arial", 8)).pack()
                # Menu contextual
                menu = tk.Menu(self.root, tearoff=0)
                menu.add_command(label="✏️ Renomear", command=lambda g=game_key: self.rename_game(g))
                menu.add_command(label="🗑️ Apagar", command=lambda g=game_key: self.delete_game(g))
                menu.add_command(label="🖼️ Atualizar Capa", command=lambda g=game_key: self.update_cover(g))
                menu.add_command(label="🔖 Atualizar Logo", command=lambda g=game_key: self.update_logo(g))
                menu.add_separator()
                menu.add_command(label="💿 Converter para CUE+BIN", command=lambda g=game_key: self.convert_game_to_cue_bin(g))
                menu.add_command(label="📀 Converter para ISO", command=lambda g=game_key: self.convert_game_to_iso(g))
                frame.bind("<Button-3>", lambda e, m=menu: m.tk_popup(e.x_root, e.y_root))
                for child in frame.winfo_children():
                    child.bind("<Button-3>", lambda e, m=menu: m.tk_popup(e.x_root, e.y_root))
    
    def rename_game(self, game_key):
        new_name = simpledialog.askstring("Renomear", f"Novo nome para '{game_key}':")
        if not new_name or not self.target_dir:
            return
        conf_file = os.path.join(self.target_dir, "conf_apps.cfg")
        if not os.path.exists(conf_file):
            return
        backup_conf_file(self.target_dir)
        with open(conf_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        with open(conf_file, 'w', encoding='utf-8') as f:
            for line in lines:
                if line.startswith(game_key + "="):
                    f.write(line.replace(game_key, new_name, 1))
                else:
                    f.write(line)
        self.log(f"✏️ Renomeado: {game_key} → {new_name}", "success")
        self.refresh_manage_tab()
    
    def delete_game(self, game_key):
        if not messagebox.askyesno("⚠️ Confirmação", f"Apagar '{game_key}'?"):
            return
        if not self.target_dir:
            return
        elf_name_no_ext = get_elf_name_from_game_key(game_key, self.target_dir)
        if not elf_name_no_ext:
            messagebox.showerror("❌ Erro", f"ELF não encontrado para '{game_key}'")
            return
        backup_conf_file(self.target_dir)
        pops_dir = os.path.join(self.target_dir, POPS_DIR_NAME)
        art_dir = os.path.join(self.target_dir, ART_DIR_NAME)
        conf_file = os.path.join(self.target_dir, "conf_apps.cfg")
        save_folder = os.path.join(pops_dir, elf_name_no_ext)
        if os.path.exists(save_folder):
            shutil.rmtree(save_folder)
        elf_path = os.path.join(self.target_dir, f"XX.{elf_name_no_ext}.ELF")
        if os.path.exists(elf_path):
            os.remove(elf_path)
        for ext in SUPPORTED_FORMATS + [".VCD"]:
            path = os.path.join(pops_dir, f"{elf_name_no_ext}{ext}")
            if os.path.exists(path):
                os.remove(path)
        for ext in [".png", ".jpg", ".jpeg", ".bmp"]:
            for prefix in [".ELF_COV", ".ELF_LGO"]:
                file_path = os.path.join(art_dir, f"XX.{elf_name_no_ext}{prefix}{ext}")
                if os.path.exists(file_path):
                    os.remove(file_path)
        if os.path.exists(conf_file):
            with open(conf_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            with open(conf_file, 'w', encoding='utf-8') as f:
                for line in lines:
                    if not line.startswith(game_key + "="):
                        f.write(line)
        self.log(f"🗑️ Jogo '{game_key}' removido.", "success")
        messagebox.showinfo("✅ Sucesso", f"'{game_key}' removido.")
        self.refresh_manage_tab()
    
    def update_cover(self, game_key):
        cover_path = filedialog.askopenfilename(
            title=f"Capa para {game_key}",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp")]
        )
        if not cover_path or not self.target_dir:
            return
        elf_name_no_ext = get_elf_name_from_game_key(game_key, self.target_dir)
        if not elf_name_no_ext:
            messagebox.showerror("❌ Erro", f"ELF não encontrado para '{game_key}'")
            return
        art_dir = os.path.join(self.target_dir, ART_DIR_NAME)
        saved_cover = save_cover(elf_name_no_ext, art_dir, cover_path)
        self.log(f"🖼️ Capa atualizada: {saved_cover}", "success")
        self.refresh_manage_tab()
    
    def update_logo(self, game_key):
        logo_path = filedialog.askopenfilename(
            title=f"Logo para {game_key}",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp")]
        )
        if not logo_path or not self.target_dir:
            return
        elf_name_no_ext = get_elf_name_from_game_key(game_key, self.target_dir)
        if not elf_name_no_ext:
            messagebox.showerror("❌ Erro", f"ELF não encontrado para '{game_key}'")
            return
        art_dir = os.path.join(self.target_dir, ART_DIR_NAME)
        saved_logo = save_logo(elf_name_no_ext, art_dir, logo_path)
        self.log(f"🔖 Logo atualizado: {saved_logo}", "success")
        self.refresh_manage_tab()
    
    def convert_game_to_cue_bin(self, game_key):
        elf_name_no_ext = get_elf_name_from_game_key(game_key, self.target_dir)
        if not elf_name_no_ext:
            messagebox.showerror("Erro", f"ELF não encontrado para '{game_key}'")
            return
        pops_dir = os.path.join(self.target_dir, POPS_DIR_NAME)
        source_path = os.path.join(pops_dir, f"{elf_name_no_ext}.VCD")
        if not os.path.exists(source_path):
            messagebox.showerror("Erro", f".VCD não encontrado para '{game_key}'")
            return
        output_dir = filedialog.askdirectory(title="Salvar CUE+BIN")
        if not output_dir:
            return
        temp_vcd = os.path.join(output_dir, os.path.basename(source_path))
        shutil.copy2(source_path, temp_vcd)
        if convert_vcd_to_cue_bin_with_pops2cue(temp_vcd, log_callback=self.log):
            output_cue = os.path.splitext(temp_vcd)[0] + ".cue"
            output_bin = os.path.splitext(temp_vcd)[0] + ".bin"
            try:
                os.remove(temp_vcd)
                self.log(f"🗑️ Arquivo temporário deletado: {os.path.basename(temp_vcd)}", "success")
            except Exception as e:
                self.log(f"⚠️ Não foi possível deletar o VCD temporário: {e}", "warning")
            messagebox.showinfo("Sucesso", f"Arquivos gerados:\n{output_cue}\n{output_bin}")
        else:
            messagebox.showerror("Erro", "Falha na conversão.")
    
    def convert_game_to_iso(self, game_key):
        elf_name_no_ext = get_elf_name_from_game_key(game_key, self.target_dir)
        if not elf_name_no_ext:
            messagebox.showerror("Erro", f"ELF não encontrado para '{game_key}'")
            return
        pops_dir = os.path.join(self.target_dir, POPS_DIR_NAME)
        source_path = os.path.join(pops_dir, f"{elf_name_no_ext}.VCD")
        if not os.path.exists(source_path):
            messagebox.showerror("Erro", f".VCD não encontrado para '{game_key}'")
            return
        output_dir = filedialog.askdirectory(title="Salvar ISO")
        if not output_dir:
            return
        output_iso = os.path.join(output_dir, f"{game_key}.iso")
        if convert_vcd_to_iso(source_path, output_iso, log_callback=self.log):
            messagebox.showinfo("Sucesso", f"Salvo em:\n{output_iso}")
        else:
            messagebox.showerror("Erro", "Falha na conversão.")
    
    def export_csv(self):
        if not self.target_dir:
            messagebox.showwarning("⚠️ Aviso", "Nenhuma pasta selecionada!")
            return
        conf_file = os.path.join(self.target_dir, "conf_apps.cfg")
        if not os.path.exists(conf_file):
            messagebox.showwarning("⚠️ Aviso", "Nenhum jogo encontrado!")
            return
        games = []
        with open(conf_file, 'r', encoding='utf-8') as f:
            for line in f:
                if "=" in line:
                    game_key, elf = line.strip().split("=", 1)
                    elf_name = os.path.basename(elf.replace("mass:/", ""))
                    games.append([game_key, elf_name])
        export_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile="jogos.csv")
        if not export_path:
            return
        with open(export_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Nome do Jogo", "Arquivo ELF"])
            writer.writerows(games)
        self.log(f"📊 Exportado: {export_path}", "success")
        messagebox.showinfo("✅ Sucesso", f"Exportado para:\n{export_path}")
    
    def export_html(self):
        if not self.target_dir:
            messagebox.showwarning("⚠️ Aviso", "Nenhuma pasta selecionada!")
            return
        conf_file = os.path.join(self.target_dir, "conf_apps.cfg")
        if not os.path.exists(conf_file):
            messagebox.showwarning("⚠️ Aviso", "Nenhum jogo encontrado!")
            return
        games = []
        with open(conf_file, 'r', encoding='utf-8') as f:
            for line in f:
                if "=" in line:
                    game_key, elf = line.strip().split("=", 1)
                    elf_name = os.path.basename(elf.replace("mass:/", ""))
                    games.append({"name": game_key, "elf": elf_name})
        html = f"""<!DOCTYPE html><html><head><title>Jogos POPStarter</title><meta charset="UTF-8"><style>body{{font-family:Arial,sans-serif;background:#222;color:#eee;margin:40px;}}h1{{color:#4a90e2;}}table{{width:100%;border-collapse:collapse;margin-top:20px;}}th,td{{padding:12px;border:1px solid #444;text-align:left;}}th{{background:#333;}}tr:nth-child(even){{background:#2a2a2a;}}</style></head><body><h1>🎮 Lista de Jogos</h1><p>Gerado em: {datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</p><table><tr><th>Nome do Jogo</th><th>Arquivo ELF</th></tr>"""
        for game in games:
            html += f"<tr><td>{game['name']}</td><td>{game['elf']}</td></tr>"
        html += "</table></body></html>"
        export_path = filedialog.asksaveasfilename(defaultextension=".html", filetypes=[("HTML", "*.html")], initialfile="jogos.html")
        if not export_path:
            return
        with open(export_path, 'w', encoding='utf-8') as f:
            f.write(html)
        self.log(f"📊 Exportado: {export_path}", "success")
        messagebox.showinfo("✅ Sucesso", f"Exportado para:\n{export_path}")
    
    def verify_integrity(self):
        if not self.target_dir:
            messagebox.showwarning("⚠️ Aviso", "Nenhuma pasta!")
            return
        self.log("🔍 Verificando integridade...", "warning")
        conf_file = os.path.join(self.target_dir, "conf_apps.cfg")
        if not os.path.exists(conf_file):
            self.log("❌ conf_apps.cfg não encontrado.", "error")
            return
        pops_dir = os.path.join(self.target_dir, POPS_DIR_NAME)
        with open(conf_file, 'r', encoding='utf-8') as f:
            for line in f:
                if "=" in line:
                    game_key, elf = line.strip().split("=", 1)
                    elf_name = os.path.basename(elf.replace("mass:/", ""))
                    elf_path = os.path.join(self.target_dir, elf_name)
                    elf_name_no_ext = get_elf_name_from_game_key(game_key, self.target_dir)
                    if not os.path.exists(elf_path):
                        self.log(f"❌ ELF ausente: {elf_name}", "error")
                    vcd_path = os.path.join(pops_dir, f"{elf_name_no_ext}.VCD")
                    if not os.path.exists(vcd_path):
                        self.log(f"⚠️ VCD ausente: {elf_name_no_ext}", "warning")
        self.log("✅ Verificação concluída!", "success")
        messagebox.showinfo("✅ Concluído", "Verificação finalizada!")
    
    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        if self.current_theme == "dark":
            self.root.configure(bg=BG_COLOR)
            self.status_bar.configure(bg="#333", fg="#aaa")
        else:
            self.root.configure(bg="white")
            self.status_bar.configure(bg="#ddd", fg="#333")
        self.log(f"🎨 Tema: {self.current_theme}", "success")
    
    def toggle_retro_mode(self, event=None):
        self.retro_mode = not self.retro_mode
        if self.retro_mode:
            try:
                font = tkfont.Font(family="Press Start 2P", size=10)
                self.root.option_add("*Font", font)
            except:
                self.root.option_add("*Font", ("Courier", 10))
            self.root.configure(bg="#0f0f23")
            self.status_bar.configure(bg="#1a1a3a", fg="#00ff00")
            self.log("🕹️ MODO RETRO ATIVADO!", "success")
        else:
            self.root.option_add("*Font", ("TkDefaultFont"))
            self.toggle_theme()
            self.toggle_theme()
            self.log("🎨 Modo Retro desativado.", "success")
    
    def show_about(self):
        messagebox.showinfo("Sobre", f"POPStation v{CURRENT_VERSION}\nGerenciador POPStarter Ultimate para PS2.\nDesenvolvido para a comunidade PS2 Homebrew.\nPressione Ctrl+Shift+R para modo RETRO!")
    
    def select_advanced_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Todos formatos suportados", "*.chd *.cue *.bin *.iso *.vcd *.gdi *.zso")]
        )
        if file_path:
            self.advanced_files = [file_path]
            self.advanced_file_label.config(text=f"Arquivo: {os.path.basename(file_path)}")
            self.log(f"📥 Arquivo selecionado: {os.path.basename(file_path)}", advanced=True)
    
    def select_advanced_output(self):
        folder = filedialog.askdirectory()
        if folder:
            self.advanced_output_folder = folder
            self.advanced_output_label.config(text=f"Pasta: {folder}")
            self.log(f"📁 Pasta de saída selecionada: {folder}", advanced=True)
    
    def start_advanced_conversion(self):
        if not hasattr(self, 'advanced_files') or not self.advanced_files:
            messagebox.showwarning("Aviso", "Selecione um arquivo de origem!")
            return
        if not hasattr(self, 'advanced_output_folder'):
            messagebox.showwarning("Aviso", "Selecione uma pasta de saída!")
            return
        input_file = self.advanced_files[0]
        output_format = self.output_format.get()
        input_ext = os.path.splitext(input_file)[1].lower()
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        script_root = get_script_root()
        chdman_path = os.path.join(script_root, CHDMAN_EXE)
        cue2pops_path = os.path.join(script_root, CUE2POPS_EXE)
        pops2cue_path = os.path.join(script_root, POPS2CUE_EXE)
        vcd2iso_path = os.path.join(script_root, VCD2ISO_EXE)
        ziso_path = os.path.join(script_root, ZISO_EXE)
        try:
            if output_format == "chd" and input_ext in [".cue", ".iso", ".gdi"]:
                if not os.path.exists(chdman_path):
                    self.log(f"❌ {CHDMAN_EXE} não encontrado!", "error", advanced=True)
                    return
                output_chd = os.path.join(self.advanced_output_folder, f"{base_name}.chd")
                if convert_to_chd(input_file, output_chd, lambda msg: self.log(msg, advanced=True)):
                    self.log(f"✅ CHD salvo: {output_chd}", "success", advanced=True)
            elif input_ext == ".chd" and output_format == "cue_bin":
                if not os.path.exists(chdman_path):
                    self.log(f"❌ {CHDMAN_EXE} não encontrado!", "error", advanced=True)
                    return
                self.log(f"▶️ Convertendo {os.path.basename(input_file)} para CUE+BIN...", advanced=True)
                cue_temp, bin_temp, temp_dir = convert_chd_to_iso_temp(
                    input_file,
                    lambda msg: self.log(msg, advanced=True),
                    None
                )
                if cue_temp and bin_temp and os.path.exists(cue_temp) and os.path.exists(bin_temp):
                    dest_cue = os.path.join(self.advanced_output_folder, os.path.basename(cue_temp))
                    dest_bin = os.path.join(self.advanced_output_folder, os.path.basename(bin_temp))
                    shutil.move(cue_temp, dest_cue)
                    shutil.move(bin_temp, dest_bin)
                    self.log(f"✅ Arquivos movidos para: {self.advanced_output_folder}", "success", advanced=True)
                    self.log(f"   {os.path.basename(dest_cue)}", "success", advanced=True)
                    self.log(f"   {os.path.basename(dest_bin)}", "success", advanced=True)
                else:
                    self.log("❌ Falha na extração do CHD.", "error", advanced=True)
                if 'temp_dir' in locals() and temp_dir:
                    shutil.rmtree(temp_dir, ignore_errors=True)
            elif input_ext == ".chd" and output_format == "gdi":
                if not os.path.exists(chdman_path):
                    self.log(f"❌ {CHDMAN_EXE} não encontrado!", "error", advanced=True)
                    return
                output_gdi = os.path.join(self.advanced_output_folder, f"{base_name}.gdi")
                if convert_chd_to_gdi(input_file, output_gdi, lambda msg: self.log(msg, advanced=True)):
                    self.log(f"✅ GDI salvo: {output_gdi}", "success", advanced=True)
            elif input_ext == ".chd" and output_format == "iso":
                if not os.path.exists(chdman_path):
                    self.log(f"❌ {CHDMAN_EXE} não encontrado!", "error", advanced=True)
                    return
                output_iso = os.path.join(self.advanced_output_folder, f"{base_name}.iso")
                if convert_chd_to_iso_only(input_file, output_iso, lambda msg: self.log(msg, advanced=True)):
                    self.log(f"✅ ISO salvo: {output_iso}", "success", advanced=True)
            elif input_ext == ".cue" and output_format == "vcd":
                if not os.path.exists(cue2pops_path):
                    self.log(f"❌ {CUE2POPS_EXE} não encontrado!", "error", advanced=True)
                    return
                bin_path = os.path.splitext(input_file)[0] + ".bin"
                if not os.path.exists(bin_path):
                    self.log(f"❌ Arquivo BIN não encontrado: {bin_path}", "error", advanced=True)
                    return
                self.log(f"▶️ Convertendo {os.path.basename(input_file)} para VCD...", advanced=True)
                output_path = os.path.join(self.advanced_output_folder, f"{base_name}.vcd")
                if convert_cue_to_vcd(input_file, output_path, lambda msg: self.log(msg, advanced=True)):
                    self.log(f"✅ VCD salvo: {output_path}", "success", advanced=True)
            elif input_ext in [".iso", ".bin"] and output_format == "vcd":
                self.log(f"▶️ Convertendo {os.path.basename(input_file)} para VCD...", advanced=True)
                output_path = os.path.join(self.advanced_output_folder, f"{base_name}.vcd")
                convert_to_vcd(input_file, output_path, lambda msg: self.log(msg, advanced=True))
                self.log(f"✅ VCD salvo: {output_path}", "success", advanced=True)
            elif input_ext == ".vcd" and output_format == "cue_bin":
                if not os.path.exists(pops2cue_path):
                    self.log(f"❌ {POPS2CUE_EXE} não encontrado!", "error", advanced=True)
                    return
                temp_vcd = os.path.join(self.advanced_output_folder, os.path.basename(input_file))
                shutil.copy2(input_file, temp_vcd)
                self.log(f"▶️ Convertendo {os.path.basename(temp_vcd)} para CUE+BIN...", advanced=True)
                if convert_vcd_to_cue_bin_with_pops2cue(temp_vcd, lambda msg: self.log(msg, advanced=True)):
                    output_cue = os.path.splitext(temp_vcd)[0] + ".cue"
                    output_bin = os.path.splitext(temp_vcd)[0] + ".bin"
                    self.log(f"✅ CUE+BIN salvos em: {self.advanced_output_folder}", "success", advanced=True)
                    self.log(f"   {os.path.basename(output_cue)}", "success", advanced=True)
                    self.log(f"   {os.path.basename(output_bin)}", "success", advanced=True)
                    try:
                        os.remove(temp_vcd)
                        self.log(f"🗑️ Arquivo temporário deletado: {os.path.basename(temp_vcd)}", "success", advanced=True)
                    except Exception as e:
                        self.log(f"⚠️ Não foi possível deletar o VCD temporário: {e}", "warning", advanced=True)
                else:
                    self.log("❌ Falha na conversão com POPS2CUE.EXE.", "error", advanced=True)
            elif input_ext == ".vcd" and output_format == "iso":
                if not os.path.exists(vcd2iso_path):
                    self.log(f"❌ {VCD2ISO_EXE} não encontrado!", "error", advanced=True)
                    return
                self.log(f"▶️ Convertendo {os.path.basename(input_file)} para ISO...", advanced=True)
                output_iso = os.path.join(self.advanced_output_folder, f"{base_name}.iso")
                if convert_vcd_to_iso(input_file, output_iso, lambda msg: self.log(msg, advanced=True)):
                    self.log(f"✅ ISO salvo: {output_iso}", "success", advanced=True)
            elif input_ext == ".iso" and output_format == "zso":
                if not os.path.exists(ziso_path):
                    self.log(f"❌ {ZISO_EXE} não encontrado! Certifique-se de que está na pasta do script.", "error", advanced=True)
                    return
                output_zso = os.path.join(self.advanced_output_folder, f"{base_name}.zso")
                self.log(f"▶️ Convertendo ISO → ZSO: {os.path.basename(input_file)}", advanced=True)
                if convert_iso_to_zso(input_file, output_zso, lambda msg: self.log(msg, advanced=True)):
                    self.log(f"✅ ZSO salvo: {output_zso}", "success", advanced=True)
                else:
                    self.log("❌ Falha na conversão ISO → ZSO.", "error", advanced=True)
            elif input_ext == ".zso" and output_format == "iso":
                if not os.path.exists(ziso_path):
                    self.log(f"❌ {ZISO_EXE} não encontrado! Certifique-se de que está na pasta do script.", "error", advanced=True)
                    return
                output_iso = os.path.join(self.advanced_output_folder, f"{base_name}.iso")
                self.log(f"▶️ Convertendo ZSO → ISO: {os.path.basename(input_file)}", advanced=True)
                if convert_zso_to_iso(input_file, output_iso, lambda msg: self.log(msg, advanced=True)):
                    self.log(f"✅ ISO salvo: {output_iso}", "success", advanced=True)
                else:
                    self.log("❌ Falha na conversão ZSO → ISO.", "error", advanced=True)
            else:
                self.log("❌ Conversão não suportada para esta combinação.", "error", advanced=True)
                return
            try:
                winsound.PlaySound(os.path.join(script_root, "success.wav"), winsound.SND_ASYNC)
            except:
                pass
        except Exception as e:
            self.log(f"❌ Erro: {e}", "error", advanced=True)
    
    def update_usb_origin_status(self):
        script_root = get_script_root()
        usb_install_path = os.path.join(script_root, "usb_install")
        if os.path.exists(usb_install_path) and os.listdir(usb_install_path):
            self.origin_status.config(text="✅ Pronto!", fg=SUCCESS_COLOR)
        elif os.path.exists(usb_install_path):
            self.origin_status.config(text="⚠️ Pasta vazia!", fg=WARNING_COLOR)
        else:
            self.origin_status.config(text="❌ Pasta 'usb_install' não encontrada!", fg=ERROR_COLOR)
    
    def select_usb_destination(self):
        folder = filedialog.askdirectory(title="Selecione a pasta de destino no USB")
        if not folder:
            return
        self.usb_dest = folder
        self.usb_dest_label.config(text=f"📁 {folder}")
        self.usb_log_text.config(state="normal")
        self.usb_log_text.delete("1.0", tk.END)
        self.usb_log_text.insert("1.0", f">>> Destino selecionado: {folder}\n", "info")
        self.usb_log_text.config(state="disabled")
        self.log_usb(f"🔌 Destino USB definido: {folder}", "info")
    
    def start_usb_install(self):
        if not hasattr(self, 'usb_dest') or not self.usb_dest:
            messagebox.showwarning("⚠️ Aviso", "Por favor, selecione um destino no USB!")
            return
        script_root = get_script_root()
        usb_install_path = os.path.join(script_root, "usb_install")
        if not os.path.exists(usb_install_path):
            self.log_usb("❌ Pasta 'usb_install' não existe no diretório do script!", "error")
            return
        items = os.listdir(usb_install_path)
        if not items:
            self.log_usb("⚠️ A pasta 'usb_install' está vazia. Nada para copiar.", "warning")
            return
        total_items = len(items)
        self.log_usb(f"🚀 Iniciando instalação USB... ({total_items} itens)", "info")
        success_count = 0
        failed_count = 0
        skipped_count = 0
        for item in items:
            src = os.path.join(usb_install_path, item)
            dst = os.path.join(self.usb_dest, item)
            try:
                if os.path.isdir(src):
                    if os.path.exists(dst):
                        self.log_usb(f"📁 Mesclando pasta: {item}", "info")
                        copy_tree(src, dst, self.log)
                    else:
                        shutil.copytree(src, dst)
                        self.log_usb(f"📁 Copiado diretório: {item}", "success")
                else:
                    if os.path.exists(dst):
                        if os.path.getsize(src) == os.path.getsize(dst):
                            with open(src, 'rb') as f1, open(dst, 'rb') as f2:
                                if f1.read() == f2.read():
                                    self.log_usb(f"✅ Ignorado (igual): {item}", "info")
                                    skipped_count += 1
                                    continue
                        shutil.copy2(src, dst)
                        self.log_usb(f"📄 Atualizado: {item}", "success")
                    else:
                        shutil.copy2(src, dst)
                        self.log_usb(f"📄 Copiado: {item}", "success")
                if sys.platform == "win32":
                    import ctypes
                    FILE_ATTRIBUTE_HIDDEN = 0x02
                    ctypes.windll.kernel32.SetFileAttributesW(dst, FILE_ATTRIBUTE_HIDDEN)
                    self.log_usb(f"👁️  Ocultado: {item}", "info")
                success_count += 1
            except Exception as e:
                failed_count += 1
                self.log_usb(f"❌ Falha ao copiar '{item}': {str(e)}", "error")
        self.status_var.set(f"✅ Concluído: {success_count} itens instalados")
        self.log_usb(f"\n🎉 INSTALAÇÃO CONCLUÍDA!\n   ✔️ Sucesso: {success_count}\n   ⚠️ Ignorados (iguais): {skipped_count}\n   ❌ Falhas: {failed_count}", "success")
        try:
            winsound.PlaySound(os.path.join(script_root, "success.wav"), winsound.SND_ASYNC)
        except:
            pass
        self.update_usb_origin_status()
    
    def log_usb(self, message, level="info"):
        self.usb_log_text.config(state="normal")
        tag = level
        self.usb_log_text.insert(tk.END, message + "\n", tag)
        self.usb_log_text.see(tk.END)
        self.usb_log_text.config(state="disabled")

if __name__ == "__main__":
    ensure_dir("logs")
    log_file = os.path.join("logs", "popstation.log")
    if os.path.exists(log_file):
        open(log_file, "w", encoding="utf-8").close()
    script_root = get_script_root()
    print(f"[INFO] Pasta raiz do script: {script_root}")
    root = TkinterDnD.Tk()
    app = PopsManagerGUI(root)
    root.mainloop()
