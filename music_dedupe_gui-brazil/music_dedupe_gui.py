#!/usr/bin/env python3
"""
Ferramenta de Deduplicação de Música - Versão em Português Brasileiro

Este aplicativo fornece uma interface gráfica para encontrar e gerenciar arquivos de música duplicados.
Recursos:
- Arrastar e soltar diretórios para escaneamento
- Limite de similaridade ajustável
- Opção para mover duplicatas em vez de excluí-las
- Suporte a tags ID3 para melhor identificação de músicas
- Priorização de formato personalizável
- Atualizações de progresso em tempo real
- Salvar/carregar configuração

Requisitos:
- Python 3.6+
- tkinter (geralmente vem com Python)
- tkinterdnd2 (pip install tkinterdnd2)
- mutagen (pip install mutagen)
"""

import os
import re
import sys
import json
import shutil
import hashlib
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from collections import defaultdict

# Tentar importar mutagen para suporte de tags ID3
try:
    import mutagen
    from mutagen.id3 import ID3
    from mutagen.flac import FLAC
    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False
    print("Mutagen não encontrado. Suporte a tags ID3 será desativado.")
    print("Instale com: pip install mutagen")

# Tentar importar tkinterdnd2 para suporte de arrastar e soltar
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False
    print("TkinterDnD não encontrado. Arrastar e soltar será desativado.")
    print("Instale com: pip install tkinterdnd2")

# Formatos de arquivo padrão em ordem de preferência (mais alta qualidade primeiro)
DEFAULT_FORMAT_PRIORITY = {
    '.flac': 4,  # Sem perdas - maior qualidade
    '.wav': 3,   # Sem perdas, mas maior
    '.aiff': 3,  # Formato Apple sem perdas
    '.alac': 3,  # Apple Lossless
    '.m4a': 2,   # AAC - qualidade decente comprimida
    '.mp3': 1,   # MP3 - comprimido
    '.wma': 0,   # Windows Media - menor prioridade
}

# Variáveis globais
CONFIG_FILE = os.path.expanduser("~/.music_dedupe_config.json")
DEFAULT_CONFIG = {
    "source_dir": "",  # String vazia para padrão em branco
    "dest_dir": "",    # String vazia para padrão em branco
    "threshold": 0.85,
    "action": "move",  # 'move' ou 'delete'
    "verbose": True,
    "use_id3_tags": True,
    "exact_size_match": False,  # Nova opção para correspondência exata de tamanho de arquivo
    "format_priority": DEFAULT_FORMAT_PRIORITY
}

# Textos de ajuda para o painel lateral
HELP_TEXTS = {
    "main": """
    Esta ferramenta ajuda você a encontrar e gerenciar arquivos de música duplicados.
    
    Como usar:
    1. Selecione o diretório de origem
    2. Escolha onde mover duplicatas ou excluí-las
    3. Ajuste as opções conforme necessário
    4. Clique em "Escanear Duplicatas"
    5. Revise os resultados
    6. Clique em "Processar Duplicatas"
    """,
    
    "threshold": """
    Limite de Similaridade:
    
    Controla quão semelhantes os nomes de arquivo precisam ser para serem considerados duplicatas.
    
    - 0.70-0.85: Mais agressivo, encontra mais duplicatas potenciais
    - 0.85-0.95: Equilíbrio, bom para a maioria das coleções
    - 0.95-1.00: Conservador, apenas arquivos muito semelhantes
    """,
    
    "id3": """
    Suporte a Tags ID3:
    
    Quando ativado, o aplicativo usará metadados de seus arquivos de música para identificar duplicatas com mais precisão.
    
    Formatos suportados:
    - MP3 (tags ID3)
    - FLAC (comentários Vorbis)
    - M4A (metadados iTunes)
    """,
    
    "exact_size": """
    Correspondência Exata de Tamanho:
    
    Quando ativada, apenas arquivos com tamanhos idênticos serão considerados duplicatas.
    
    Útil para encontrar duplicatas perfeitas, mas perderá arquivos que foram codificados de forma diferente.
    """,
    
    "format_priority": """
    Prioridade de Formato:
    
    Define a ordem de preferência para formatos de áudio.
    
    - Valor mais alto = maior prioridade
    - O aplicativo manterá o arquivo de maior prioridade
    - Valores padrão: FLAC (4), WAV (3), M4A (2), MP3 (1), WMA (0)
    """
}

class MusicDedupeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ferramenta de Deduplicação de Música v1.0")
        self.root.geometry("1100x850")
        self.root.minsize(900, 600)
        
        # Inicializar variáveis
        self.source_var = tk.StringVar()
        self.dest_var = tk.StringVar()
        self.threshold_var = tk.DoubleVar(value=0.85)
        self.threshold_display = tk.StringVar(value="0.85")
        self.action_var = tk.StringVar(value="move")
        self.verbose_var = tk.BooleanVar(value=True)
        self.use_id3_tags_var = tk.BooleanVar(value=True)
        self.exact_size_match_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Pronto")
        self.help_text_var = tk.StringVar(value=HELP_TEXTS["main"])
        self.log_text = None
        self.progress = None
        self.progress_var = tk.DoubleVar(value=0.0)
        self.duplicates = {}
        self.is_running = False
        
        # Configuração de prioridade de formato
        self.format_priority = DEFAULT_FORMAT_PRIORITY.copy()
        self.format_vars = {}  # Manterá IntVar para cada formato
        
        # Carregar configuração
        self.load_config()
        
        # Criar UI
        self.create_ui()
        
        # Habilitar arrastar e soltar se disponível
        if HAS_DND:
            self.enable_drag_drop()
    
    def create_ui(self):
        # Frame principal dividido em dois painéis
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Painel esquerdo para a aplicação principal
        left_panel = ttk.Frame(main_pane, padding="5")
        main_pane.add(left_panel, weight=3)
        
        # Painel direito para ajuda
        right_panel = ttk.LabelFrame(main_pane, text="Instruções & Ajuda", padding="10")
        main_pane.add(right_panel, weight=1)
        
        # Configurar painel de ajuda
        help_text = tk.Text(right_panel, wrap=tk.WORD, width=30, height=30)
        help_text.grid(row=0, column=0, sticky=tk.NSEW)
        help_text.insert(tk.END, HELP_TEXTS["main"])
        help_text.config(state=tk.DISABLED)
        
        help_scroll = ttk.Scrollbar(right_panel, orient=tk.VERTICAL, command=help_text.yview)
        help_scroll.grid(row=0, column=1, sticky=tk.NS)
        help_text.config(yscrollcommand=help_scroll.set)
        
        # Fazer o painel de ajuda expansível
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)
        
        # Configurar painel esquerdo (aplicativo principal)
        
        # Seleção de diretório de origem
        ttk.Label(left_panel, text="Diretório de Origem:").grid(row=0, column=0, sticky=tk.W, pady=5)
        source_entry = ttk.Entry(left_panel, textvariable=self.source_var, width=50)
        source_entry.grid(row=0, column=1, sticky=tk.EW, pady=5)
        ttk.Button(left_panel, text="Procurar...", command=self.browse_source).grid(row=0, column=2, padx=5, pady=5)
        
        # Mostrar destino apenas se a ação for "mover"
        self.dest_frame = ttk.Frame(left_panel)
        self.dest_frame.grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=5)
        ttk.Label(self.dest_frame, text="Diretório de Destino:").grid(row=0, column=0, sticky=tk.W)
        dest_entry = ttk.Entry(self.dest_frame, textvariable=self.dest_var, width=50)
        dest_entry.grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(self.dest_frame, text="Procurar...", command=self.browse_dest).grid(row=0, column=2, padx=5)
        
        # Frame de opções
        options_frame = ttk.LabelFrame(left_panel, text="Opções", padding=10)
        options_frame.grid(row=2, column=0, columnspan=3, sticky=tk.EW, pady=10)
        
        # Slider de limite
        threshold_label = ttk.Label(options_frame, text="Limite de Similaridade:")
        threshold_label.grid(row=0, column=0, sticky=tk.W, pady=5)
        threshold_label.bind("<Enter>", lambda e: self.update_help_text("threshold"))
        threshold_label.bind("<Leave>", lambda e: self.update_help_text("main"))
        
        threshold_frame = ttk.Frame(options_frame)
        threshold_frame.grid(row=0, column=1, sticky=tk.EW, pady=5)
        
        threshold_slider = ttk.Scale(threshold_frame, from_=0.7, to=1.0, 
                                    orient=tk.HORIZONTAL, variable=self.threshold_var,
                                    length=200)
        threshold_slider.grid(row=0, column=0, sticky=tk.EW)
        
        # Adicionar display preciso de limite
        threshold_display = ttk.Label(threshold_frame, textvariable=self.threshold_display, width=5)
        threshold_display.grid(row=0, column=1, padx=5)
        
        # Atualizar rótulo de limite quando o slider é movido
        def update_threshold(*args):
            self.threshold_display.set(f"{self.threshold_var.get():.2f}")
        self.threshold_var.trace_add("write", update_threshold)
        update_threshold()  # Inicializar display
        
        # Botões de rádio de ação
        ttk.Label(options_frame, text="Ação:").grid(row=1, column=0, sticky=tk.W, pady=5)
        action_frame = ttk.Frame(options_frame)
        action_frame.grid(row=1, column=1, sticky=tk.W, pady=5)
        ttk.Radiobutton(action_frame, text="Mover duplicatas", variable=self.action_var, value="move",
                        command=self.toggle_dest_visibility).grid(row=0, column=0, padx=5)
        ttk.Radiobutton(action_frame, text="Excluir duplicatas", variable=self.action_var, value="delete",
                        command=self.toggle_dest_visibility).grid(row=0, column=1, padx=5)
        
        # Opção de Tag ID3
        id3_check = ttk.Checkbutton(options_frame, text="Usar tags ID3 (mais preciso, mas mais lento)", 
                          variable=self.use_id3_tags_var)
        id3_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        id3_check.bind("<Enter>", lambda e: self.update_help_text("id3"))
        id3_check.bind("<Leave>", lambda e: self.update_help_text("main"))
        
        if not HAS_MUTAGEN:
            ttk.Label(options_frame, text="Suporte a ID3 não disponível (instale mutagen)").grid(
                row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
            self.use_id3_tags_var.set(False)
        
        # Adicionar opção de correspondência exata de tamanho após opção de tag ID3
        exact_size_check = ttk.Checkbutton(options_frame, text="Exigir correspondência exata de tamanho", 
                      variable=self.exact_size_match_var)
        exact_size_check.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        exact_size_check.bind("<Enter>", lambda e: self.update_help_text("exact_size"))
        exact_size_check.bind("<Leave>", lambda e: self.update_help_text("main"))
        
        # Mover opção detalhada para próxima linha
        ttk.Checkbutton(options_frame, text="Saída detalhada", variable=self.verbose_var).grid(
            row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Frame de prioridade de formato
        format_frame = ttk.LabelFrame(left_panel, text="Prioridade de Formato (Maior = Melhor Qualidade)", padding=10)
        format_frame.grid(row=3, column=0, columnspan=3, sticky=tk.EW, pady=10)
        format_frame.bind("<Enter>", lambda e: self.update_help_text("format_priority"))
        format_frame.bind("<Leave>", lambda e: self.update_help_text("main"))
        
        # Criar sliders para cada prioridade de formato
        format_row = 0
        format_col = 0
        self.format_vars = {}
        
        # Ordenar formatos pela prioridade padrão
        sorted_formats = sorted(self.format_priority.items(), key=lambda x: x[0])
        
        for ext, priority in sorted_formats:
            # Remover o ponto da extensão
            ext_name = ext[1:].upper()
            
            # Criar variável para este formato
            self.format_vars[ext] = tk.IntVar(value=priority)
            
            # Criar um frame para este formato
            format_item_frame = ttk.Frame(format_frame)
            format_item_frame.grid(row=format_row, column=format_col, padx=10, pady=5, sticky=tk.W)
            
            # Adicionar rótulo e caixa de seleção numérica
            ttk.Label(format_item_frame, text=f"{ext_name}:").grid(row=0, column=0, padx=5)
            ttk.Spinbox(format_item_frame, from_=0, to=10, width=3, 
                       textvariable=self.format_vars[ext]).grid(row=0, column=1)
            
            # Organizar em uma grade, 3 formatos por linha
            format_col += 1
            if format_col > 2:
                format_col = 0
                format_row += 1
        
        # Botões
        button_frame = ttk.Frame(left_panel)
        button_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        ttk.Button(button_frame, text="Escanear Duplicatas", command=self.start_scan).grid(
            row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Processar Duplicatas", command=self.process_duplicates).grid(
            row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Salvar Configurações", command=self.save_config).grid(
            row=0, column=2, padx=5)
        
        # Barra de progresso
        self.progress = ttk.Progressbar(left_panel, orient=tk.HORIZONTAL, length=100,
                                       mode='determinate', variable=self.progress_var)
        self.progress.grid(row=5, column=0, columnspan=3, sticky=tk.EW, pady=5)
        
        # Rótulo de status
        status_label = ttk.Label(left_panel, textvariable=self.status_var, anchor=tk.W)
        status_label.grid(row=6, column=0, columnspan=3, sticky=tk.W, pady=2)
        
        # Área de texto de log
        log_frame = ttk.LabelFrame(left_panel, text="Log", padding=5)
        log_frame.grid(row=7, column=0, columnspan=3, sticky=tk.NSEW, pady=5)
        
        # Tornar o frame de log expansível
        left_panel.columnconfigure(1, weight=1)
        left_panel.rowconfigure(7, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = tk.Text(log_frame, height=15, width=70, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=tk.NSEW)
        
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Definir estado inicial
        self.toggle_dest_visibility()
        
        # Inicializar log com mensagem de boas-vindas
        self.log("Bem-vindo à Ferramenta de Deduplicação de Música")
        if HAS_MUTAGEN:
            self.log("Suporte a tags ID3 está habilitado para identificação de música mais precisa")
        else:
            self.log("Suporte a tags ID3 não está disponível - instale mutagen para melhores resultados")
        self.log("Arraste e solte diretórios nos campos de origem/destino ou use os botões de procurar")
        self.log(f"Configuração padrão carregada de: {CONFIG_FILE}")
    
    def update_help_text(self, key):
        """Atualiza o texto de ajuda quando o mouse passa sobre um elemento."""
        # Atualizar o texto de ajuda
        help_text = self.root.nametowidget(str(self.root.winfo_children()[0]).split()[0] + ".!labelframe.!text")
        help_text.config(state=tk.NORMAL)
        help_text.delete(1.0, tk.END)
        help_text.insert(tk.END, HELP_TEXTS[key])
        help_text.config(state=tk.DISABLED)
    
    def toggle_dest_visibility(self):
        if self.action_var.get() == "move":
            self.dest_frame.grid()
        else:
            self.dest_frame.grid_remove()
    
    def enable_drag_drop(self):
        # Registrar a entrada de origem para arrastar e soltar
        source_entry = self.root.nametowidget('.!panedwindow.!frame.!entry')
        source_entry.drop_target_register(DND_FILES)
        source_entry.dnd_bind('<<Drop>>', self.drop_on_source)
        
        # Registrar a entrada de destino para arrastar e soltar
        dest_entry = self.root.nametowidget('.!panedwindow.!frame.!frame.!entry')
        dest_entry.drop_target_register(DND_FILES)
        dest_entry.dnd_bind('<<Drop>>', self.drop_on_dest)
    
    def drop_on_source(self, event):
        # Obter o caminho solto, remover chaves e aspas se presentes
        path = event.data
        path = self.clean_dropped_path(path)
        if os.path.isdir(path):
            self.source_var.set(path)
            self.log(f"Diretório de origem definido para: {path}")
    
    def drop_on_dest(self, event):
        # Obter o caminho solto, remover chaves e aspas se presentes
        path = event.data
        path = self.clean_dropped_path(path)
        if os.path.isdir(path):
            self.dest_var.set(path)
            self.log(f"Diretório de destino definido para: {path}")
        else:
            # Se não for um diretório, tente usar o diretório pai
            parent = os.path.dirname(path)
            if parent and os.path.isdir(parent):
                self.dest_var.set(parent)
                self.log(f"Diretório de destino definido para: {parent}")
    
    def clean_dropped_path(self, path):
        """Limpa o caminho retornado de eventos de arrastar e soltar."""
        if path.startswith('{') and path.endswith('}'):
            path = path[1:-1]
        # Lidar com vários arquivos (pegamos apenas o primeiro)
        if ' ' in path and ('"' in path or "'" in path):
            # Este é um caminho complexo com espaços, tente extrair o primeiro caminho
            for quote in ['"', "'"]:
                if quote in path:
                    parts = path.split(quote)
                    if len(parts) >= 3:  # Pelo menos um caminho entre aspas
                        return parts[1]
            # Fallback: apenas retorne a primeira parte separada por espaço
            return path.split()[0]
        return path
    
    def browse_source(self):
        directory = filedialog.askdirectory(initialdir=self.source_var.get())
        if directory:
            self.source_var.set(directory)
            self.log(f"Diretório de origem definido para: {directory}")
    
    def browse_dest(self):
        directory = filedialog.askdirectory(initialdir=self.dest_var.get())
        if directory:
            self.dest_var.set(directory)
            self.log(f"Diretório de destino definido para: {directory}")
    
    def log(self, message):
        if self.log_text:
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
    
    def update_status(self, message):
        self.status_var.set(message)
        self.log(message)
    
    def update_progress(self, value):
        self.progress_var.set(value)
    
    def start_scan(self):
        if self.is_running:
            messagebox.showinfo("Operação em Andamento", "Por favor, aguarde a conclusão da operação atual.")
            return
        
        source_dir = self.source_var.get()
        if not source_dir or not os.path.isdir(source_dir):
            messagebox.showerror("Erro", "Por favor, selecione um diretório de origem válido.")
            return
        
        # Limpar resultados anteriores
        self.duplicates = {}
        
        # Atualizar UI
        self.update_status("Procurando duplicatas...")
        self.update_progress(0)
        self.is_running = True
        
        # Executar o escaneamento em uma thread separada
        threading.Thread(target=self.run_scan, daemon=True).start()
    
    def run_scan(self):
        try:
            source_dir = self.source_var.get()
            threshold = self.threshold_var.get()
            verbose = self.verbose_var.get()
            exact_size_match = self.exact_size_match_var.get()
            
            # Encontrar todos os arquivos de música
            self.update_status("Encontrando arquivos de música...")
            all_files = []
            total_dirs = sum([len(dirs) for _, dirs, _ in os.walk(source_dir)])
            dirs_processed = 0
            
            # Armazenar tamanhos de arquivo para comparação
            file_sizes = {}
            
            for root, dirs, files in os.walk(source_dir):
                dirs_processed += 1
                self.update_progress(dirs_processed / max(1, total_dirs) * 30)
                
                for file in files:
                    if file.lower().endswith(tuple(self.format_priority.keys())):
                        file_path = os.path.join(root, file)
                        all_files.append(file_path)
                        if exact_size_match:
                            file_sizes[file_path] = os.path.getsize(file_path)
            
            self.update_status(f"Encontrados {len(all_files)} arquivos de música")
            
            # Agrupar por nome normalizado
            self.update_status("Agrupando arquivos por nome...")
            songs = defaultdict(list)
            for i, file_path in enumerate(all_files):
                progress = 30 + (i / len(all_files) * 30)
                self.update_progress(progress)
                norm_name = self.normalize_title(file_path)
                songs[norm_name].append(file_path)
            
            # Filtrar para manter apenas grupos com duplicatas
            duplicates = {name: files for name, files in songs.items() if len(files) > 1}
            
            # Se a correspondência exata de tamanho estiver ativada, filtrar ainda mais as duplicatas
            if exact_size_match:
                filtered_duplicates = {}
                for name, files in duplicates.items():
                    # Agrupar arquivos por tamanho
                    size_groups = defaultdict(list)
                    for file in files:
                        size_groups[file_sizes[file]].append(file)
                    
                    # Manter apenas grupos que têm vários arquivos do mesmo tamanho
                    for size, size_files in size_groups.items():
                        if len(size_files) > 1:
                            filtered_duplicates[f"{name} ({size} bytes)"] = size_files
                
                duplicates = filtered_duplicates
            
            # Ordenar cada grupo por qualidade
            self.update_status("Determinando versões de melhor qualidade...")
            for i, (name, files) in enumerate(duplicates.items()):
                progress = 60 + (i / len(duplicates) * 40)  # 60% a 100% da barra de progresso
                self.update_progress(progress)
                
                # Avaliar cada arquivo
                scored_files = [(f, self.get_file_quality_score(f)) for f in files]
                
                # Ordenar por pontuação (mais alta primeiro)
                scored_files.sort(key=lambda x: x[1], reverse=True)
                
                # O arquivo de maior qualidade é o que será mantido
                keeper = scored_files[0][0]
                dupes = [f for f, _ in scored_files[1:]]
                
                self.duplicates[name] = {
                    'keeper': keeper,
                    'duplicates': dupes,
                    'scores': {f: score for f, score in scored_files}
                }
            
            # Exibir resultados
            total_duplicates = sum(len(info['duplicates']) for info in self.duplicates.values())
            self.update_status(f"Encontradas {len(self.duplicates)} músicas com {total_duplicates} arquivos duplicados")
            
            # Mostrar detalhes se verbose
            if verbose and self.duplicates:
                self.log("\n=== Detalhes das Duplicatas ===")
                for name, info in self.duplicates.items():
                    keeper = info['keeper']
                    dupes = info['duplicates']
                    
                    self.log(f"\n{name}")
                    self.log(f"  MANTER: {os.path.basename(keeper)} [{self.format_quality(keeper, info['scores'][keeper])}]")
                    
                    for dupe in dupes:
                        self.log(f"  DUPLICATA: {os.path.basename(dupe)} [{self.format_quality(dupe, info['scores'][dupe])}]")
            
            self.update_progress(100)
            
        except Exception as e:
            self.update_status(f"Erro: {str(e)}")
        finally:
            self.is_running = False
    
    def process_duplicates(self):
        if self.is_running:
            messagebox.showinfo("Operação em Andamento", "Por favor, aguarde a conclusão da operação atual.")
            return
        
        if not self.duplicates:
            messagebox.showinfo("Sem Duplicatas", "Nenhuma duplicata encontrada. Por favor, execute um escaneamento primeiro.")
            return
        
        action = self.action_var.get()
        total_dupes = sum(len(info['duplicates']) for info in self.duplicates.values())
        
        # Confirmar ação
        if action == "delete":
            if not messagebox.askyesno("Confirmar Exclusão", 
                                      f"Tem certeza que deseja excluir {total_dupes} arquivos duplicados?"):
                return
        else:  # mover
            dest_dir = self.dest_var.get()
            if not dest_dir:
                messagebox.showerror("Erro", "Por favor, especifique um diretório de destino.")
                return
            
            if not os.path.exists(dest_dir):
                if messagebox.askyesno("Criar Diretório", 
                                     f"O diretório de destino '{dest_dir}' não existe. Criar?"):
                    try:
                        os.makedirs(dest_dir, exist_ok=True)
                    except Exception as e:
                        messagebox.showerror("Erro", f"Não foi possível criar o diretório: {str(e)}")
                        return
                else:
                    return
            
            if not messagebox.askyesno("Confirmar Mudança", 
                                     f"Tem certeza que deseja mover {total_dupes} arquivos duplicados para {dest_dir}?"):
                return
        
        # Atualizar UI
        self.update_status(f"{'Excluindo' if action == 'delete' else 'Movendo'} arquivos duplicados...")
        self.update_progress(0)
        self.is_running = True
        
        # Executar o processamento em uma thread separada
        threading.Thread(target=self.run_processing, daemon=True).start()
    
    def run_processing(self):
        try:
            action = self.action_var.get()
            dest_dir = self.dest_var.get() if action == "move" else None
            
            total = sum(len(info['duplicates']) for info in self.duplicates.values())
            processed = 0
            
            for name, info in self.duplicates.items():
                for dupe in info['duplicates']:
                    processed += 1
                    progress = (processed / total) * 100
                    self.update_progress(progress)
                    
                    rel_path = os.path.basename(dupe)
                    try:
                        if action == "move":
                            # Criar um nome de arquivo único no diretório de destino
                            target = os.path.join(dest_dir, rel_path)
                            if os.path.exists(target):
                                base, ext = os.path.splitext(rel_path)
                                target = os.path.join(dest_dir, f"{base}_{hashlib.md5(dupe.encode()).hexdigest()[:6]}{ext}")
                            
                            shutil.move(dupe, target)
                            self.log(f"Movido: {rel_path} -> {target}")
                        else:  # delete
                            os.remove(dupe)
                            self.log(f"Excluído: {rel_path}")
                    except Exception as e:
                        self.log(f"Erro ao processar {dupe}: {e}")
            
            self.update_status(f"Processados {processed} arquivos duplicados")
            
            # Limpar a lista de duplicatas após o processamento
            self.duplicates = {}
            
        except Exception as e:
            self.update_status(f"Erro: {str(e)}")
        finally:
            self.is_running = False
    
    def normalize_title(self, filename):
        """Extrair e normalizar o título da música e artista para comparação."""
        # Obter apenas o nome do arquivo sem caminho ou extensão
        base_name = os.path.basename(filename)
        name, ext = os.path.splitext(base_name)
        
        # Se as tags ID3 estiverem habilitadas e tivermos mutagen, tente usar as tags ID3
        if HAS_MUTAGEN and self.use_id3_tags_var.get():
            try:
                if ext.lower() == '.mp3':
                    audio = MP3(filename)
                    # Extrair artista e título se disponíveis
                    if hasattr(audio, 'tags') and audio.tags:
                        artist = audio.tags.get('TPE1', [''])[0]
                        title = audio.tags.get('TIT2', [''])[0]
                        if artist and title:
                            return f"{artist.lower()} - {title.lower()}"
                elif ext.lower() == '.flac':
                    audio = FLAC(filename)
                    artist = audio.get('artist', [''])[0]
                    title = audio.get('title', [''])[0]
                    if artist and title:
                        return f"{artist.lower()} - {title.lower()}"
                elif ext.lower() == '.m4a':
                    audio = MP4(filename)
                    artist = audio.get('\xa9ART', [''])[0]
                    title = audio.get('\xa9nam', [''])[0]
                    if artist and title:
                        return f"{artist.lower()} - {title.lower()}"
                # Voltar para o nome do arquivo se a extração de tags ID3 falhar
            except Exception as e:
                # Se houver um erro ao ler as tags, volte para o nome do arquivo
                pass
        
        # Voltar para a normalização do nome do arquivo se as tags ID3 não estiverem disponíveis ou falharem
        # Remover prefixos numéricos como "01 - " ou "01. " ou "01_"
        name = re.sub(r'^\d+[\s\.-_]+', '', name)
        
        # Remover indicadores de qualidade e outros metadados comuns
        name = re.sub(r'\(Live.*?\)|\(Remaster(ed)?.*?\)|\(.*?Mix.*?\)|\(.*?Version.*?\)|\(From.*?\)|\{.*?\}|\[.*?\]', '', name, flags=re.IGNORECASE)
        
        # Limpar espaços restantes e caracteres especiais
        name = re.sub(r'[-_\s]{2,}', ' ', name).strip().lower()
        
        return name
    
    def get_file_quality_score(self, file_path):
        """Determinar uma pontuação de qualidade para o arquivo com base no formato e tamanho."""
        ext = os.path.splitext(file_path)[1].lower()
        
        # Obter a prioridade de formato atual (o usuário pode ter ajustado)
        current_priority = {}
        for format_ext, var in self.format_vars.items():
            current_priority[format_ext] = var.get()
        
        # Pontuação base do formato (priorizar com base nas configurações do usuário)
        score = current_priority.get(ext, 0) * 1000
        
        # Adicionar tamanho do arquivo como desempate - geralmente maior é melhor qualidade
        size_kb = os.path.getsize(file_path) / 1024  # Tamanho em KB
        score += size_kb
        
        # Se tivermos mutagen, tente obter informações de bitrate para MP3s
        if HAS_MUTAGEN and ext.lower() == '.mp3':
            try:
                audio = MP3(file_path)
                if audio.info.bitrate:
                    # Adicionar pontuação de bitrate (bitrate mais alto é melhor)
                    bitrate_kbps = audio.info.bitrate / 1000
                    score += bitrate_kbps
            except:
                pass
        
        return score
    
    def format_quality(self, file_path, score):
        """Formatar as informações de qualidade para exibição."""
        ext = os.path.splitext(file_path)[1].lower()
        size_kb = os.path.getsize(file_path) / 1024
        
        quality_info = []
        
        # Formatar extensão
        quality_info.append(ext[1:].upper())
        
        # Formatar tamanho
        if size_kb > 1024:
            quality_info.append(f"{size_kb/1024:.1f} MB")
        else:
            quality_info.append(f"{size_kb:.0f} KB")
        
        # Adicionar bitrate para arquivos MP3 se mutagen estiver disponível
        if HAS_MUTAGEN and ext.lower() == '.mp3':
            try:
                audio = MP3(file_path)
                if audio.info.bitrate:
                    bitrate_kbps = audio.info.bitrate / 1000
                    quality_info.append(f"{bitrate_kbps:.0f} kbps")
            except:
                pass
        
        # Retornar string formatada
        return ", ".join(quality_info)
    
    def load_config(self):
        """Carregar a configuração do arquivo."""
        config = DEFAULT_CONFIG.copy()
        
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    loaded_config = json.load(f)
                    
                    # Tratar prioridade de formato especialmente
                    if "format_priority" in loaded_config:
                        self.format_priority = loaded_config.pop("format_priority")
                    
                    # Atualizar configuração com configurações restantes
                    config.update(loaded_config)
        except Exception as e:
            print(f"Erro ao carregar configuração: {e}")
        
        # Aplicar a configuração carregada
        self.source_var.set(config["source_dir"])
        self.dest_var.set(config["dest_dir"])
        self.threshold_var.set(config["threshold"])
        self.threshold_display.set(f"{config['threshold']:.2f}")
        self.action_var.set(config["action"])
        self.verbose_var.set(config["verbose"])
        self.exact_size_match_var.set(config.get("exact_size_match", False))
        
        # Definir use_id3_tags apenas se mutagen estiver disponível
        if HAS_MUTAGEN and "use_id3_tags" in config:
            self.use_id3_tags_var.set(config["use_id3_tags"])
    
    def save_config(self):
        """Salvar a configuração atual no arquivo."""
        # Atualizar prioridade de formato da UI
        for ext, var in self.format_vars.items():
            self.format_priority[ext] = var.get()
        
        config = {
            "source_dir": self.source_var.get(),
            "dest_dir": self.dest_var.get(),
            "threshold": self.threshold_var.get(),
            "action": self.action_var.get(),
            "verbose": self.verbose_var.get(),
            "use_id3_tags": self.use_id3_tags_var.get(),
            "exact_size_match": self.exact_size_match_var.get(),
            "format_priority": self.format_priority
        }
        
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            
            self.log(f"Configuração salva em: {CONFIG_FILE}")
            messagebox.showinfo("Configuração Salva", f"Configuração salva em: {CONFIG_FILE}")
        except Exception as e:
            self.log(f"Erro ao salvar configuração: {e}")
            messagebox.showerror("Erro", f"Não foi possível salvar a configuração: {str(e)}")

def main():
    # Verificar se está sendo executado como um script ou um executável congelado
    if getattr(sys, 'frozen', False):
        # Se congelado, use o diretório do executável
        base_dir = os.path.dirname(sys.executable)
    else:
        # Se estiver executando como um script, use o diretório do script
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Mudar para o diretório base
    os.chdir(base_dir)
    
    # Criar a janela raiz
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    
    # Definir título da janela com versão
    root.title("Ferramenta de Deduplicação de Música v1.0")
    
    # Definir tamanho e posição da janela
    window_width = 1100
    window_height = 850
    root.geometry(f"{window_width}x{window_height}")
    
    # Obter dimensões da tela
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # Calcular posição para o centro da tela
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    
    # Definir posição da janela
    root.geometry(f"+{x}+{y}")
    
    # Definir ícone da janela se estiver executando como um executável congelado
    if getattr(sys, 'frozen', False):
        try:
            icon_path = os.path.join(base_dir, "music_dedupe.ico")
            if os.path.exists(icon_path):
                root.iconbitmap(icon_path)
        except:
            pass
    
    # Inicializar o aplicativo
    app = MusicDedupeApp(root)
    
    # Tratamento especial para macOS para garantir que a janela apareça corretamente
    if sys.platform == 'darwin':
        # Função para trazer a janela para a frente sem usar AppleScript
        def activate_window():
            # Primeiro update para garantir que a janela seja criada
            root.update_idletasks()
            
            # Tornar a janela visível e trazer para a frente usando apenas métodos tkinter
            root.lift()
            root.attributes('-topmost', True)
            root.after(500, lambda: root.attributes('-topmost', False))
            
            # Forçar foco
            root.focus_force()
            
            # Desiconificar caso a janela tenha sido iconificada
            root.deiconify()
        
        # Agendar ativação para acontecer após a renderização inicial
        root.after(100, activate_window)
    
    # Iniciar o loop de eventos principal
    root.mainloop()

if __name__ == "__main__":
    main()