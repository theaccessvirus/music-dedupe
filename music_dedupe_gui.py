#!/usr/bin/env python3
"""
Music Deduplication Tool with GUI

This application provides a graphical interface for finding and managing duplicate music files.
Features:
- Drag and drop directories for scanning
- Adjustable similarity threshold
- Option to move duplicates instead of deleting
- ID3 tag support for better music identification
- Customizable format prioritization
- Live progress updates
- Save/load configuration

Requirements:
- Python 3.6+
- tkinter (usually comes with Python)
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

# Try to import mutagen for ID3 tag support
try:
    import mutagen
    from mutagen.id3 import ID3
    from mutagen.flac import FLAC
    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False
    print("Mutagen not found. ID3 tag support will be disabled.")
    print("Install with: pip install mutagen")

# Try to import tkinterdnd2 for drag and drop support
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False
    print("TkinterDnD not found. Drag and drop will be disabled.")
    print("Install with: pip install tkinterdnd2")

# Default file formats in order of preference (highest quality first)
DEFAULT_FORMAT_PRIORITY = {
    '.flac': 4,  # Lossless - highest quality
    '.wav': 3,   # Lossless but larger
    '.aiff': 3,  # Lossless Apple format
    '.alac': 3,  # Apple Lossless
    '.m4a': 2,   # AAC - decent quality compressed
    '.mp3': 1,   # MP3 - compressed
    '.wma': 0,   # Windows Media - lowest priority
}

# Global vars
CONFIG_FILE = os.path.expanduser("~/.music_dedupe_config.json")
DEFAULT_CONFIG = {
    "source_dir": "",  # Empty string for blank default
    "dest_dir": "",    # Empty string for blank default
    "threshold": 0.85,
    "action": "move",  # 'move' or 'delete'
    "verbose": True,
    "use_id3_tags": True,
    "exact_size_match": False,  # New option for exact file size matching
    "format_priority": DEFAULT_FORMAT_PRIORITY
}

class MusicDedupeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Music Deduplication Tool")
        self.root.geometry("850x850")
        self.root.minsize(650, 550)
        
        # Initialize variables
        self.source_var = tk.StringVar()
        self.dest_var = tk.StringVar()
        self.threshold_var = tk.DoubleVar(value=0.85)
        self.threshold_display = tk.StringVar(value="0.85")
        self.action_var = tk.StringVar(value="move")
        self.verbose_var = tk.BooleanVar(value=True)
        self.use_id3_tags_var = tk.BooleanVar(value=True)
        self.exact_size_match_var = tk.BooleanVar(value=False)  # New variable
        self.status_var = tk.StringVar(value="Ready")
        self.log_text = None
        self.progress = None
        self.progress_var = tk.DoubleVar(value=0.0)
        self.duplicates = {}
        self.is_running = False
        
        # Format priority configuration
        self.format_priority = DEFAULT_FORMAT_PRIORITY.copy()
        self.format_vars = {}  # Will hold IntVar for each format
        
        # Load configuration
        self.load_config()
        
        # Create UI
        self.create_ui()
        
        # Enable drag and drop if available
        if HAS_DND:
            self.enable_drag_drop()
    
    def create_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Source directory selection
        ttk.Label(main_frame, text="Source Directory:").grid(row=0, column=0, sticky=tk.W, pady=5)
        source_entry = ttk.Entry(main_frame, textvariable=self.source_var, width=50)
        source_entry.grid(row=0, column=1, sticky=tk.EW, pady=5)
        ttk.Button(main_frame, text="Browse...", command=self.browse_source).grid(row=0, column=2, padx=5, pady=5)
        
        # Only show destination if action is "move"
        self.dest_frame = ttk.Frame(main_frame)
        self.dest_frame.grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=5)
        ttk.Label(self.dest_frame, text="Destination Directory:").grid(row=0, column=0, sticky=tk.W)
        dest_entry = ttk.Entry(self.dest_frame, textvariable=self.dest_var, width=50)
        dest_entry.grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(self.dest_frame, text="Browse...", command=self.browse_dest).grid(row=0, column=2, padx=5)
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding=10)
        options_frame.grid(row=2, column=0, columnspan=3, sticky=tk.EW, pady=10)
        
        # Threshold slider
        ttk.Label(options_frame, text="Similarity Threshold:").grid(row=0, column=0, sticky=tk.W, pady=5)
        threshold_frame = ttk.Frame(options_frame)
        threshold_frame.grid(row=0, column=1, sticky=tk.EW, pady=5)
        
        threshold_slider = ttk.Scale(threshold_frame, from_=0.7, to=1.0, 
                                    orient=tk.HORIZONTAL, variable=self.threshold_var,
                                    length=200)
        threshold_slider.grid(row=0, column=0, sticky=tk.EW)
        
        # Add a precise threshold display
        threshold_display = ttk.Label(threshold_frame, textvariable=self.threshold_display, width=5)
        threshold_display.grid(row=0, column=1, padx=5)
        
        # Update threshold label when slider is moved
        def update_threshold(*args):
            self.threshold_display.set(f"{self.threshold_var.get():.2f}")
        self.threshold_var.trace_add("write", update_threshold)
        update_threshold()  # Initialize display
        
        # Action radio buttons
        ttk.Label(options_frame, text="Action:").grid(row=1, column=0, sticky=tk.W, pady=5)
        action_frame = ttk.Frame(options_frame)
        action_frame.grid(row=1, column=1, sticky=tk.W, pady=5)
        ttk.Radiobutton(action_frame, text="Move duplicates", variable=self.action_var, value="move",
                        command=self.toggle_dest_visibility).grid(row=0, column=0, padx=5)
        ttk.Radiobutton(action_frame, text="Delete duplicates", variable=self.action_var, value="delete",
                        command=self.toggle_dest_visibility).grid(row=0, column=1, padx=5)
        
        # ID3 Tag option
        if HAS_MUTAGEN:
            ttk.Checkbutton(options_frame, text="Use ID3 tags (more accurate but slower)", 
                          variable=self.use_id3_tags_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        else:
            ttk.Label(options_frame, text="ID3 tag support not available (install mutagen)").grid(
                row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
            self.use_id3_tags_var.set(False)
        
        # Add exact size match option after ID3 tag option
        ttk.Checkbutton(options_frame, text="Require exact file size match", 
                      variable=self.exact_size_match_var).grid(
            row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Move verbose option to next row
        ttk.Checkbutton(options_frame, text="Verbose output", variable=self.verbose_var).grid(
            row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Format priority frame
        format_frame = ttk.LabelFrame(main_frame, text="Format Priority (Higher = Better Quality)", padding=10)
        format_frame.grid(row=5, column=0, columnspan=3, sticky=tk.EW, pady=10)
        
        # Create sliders for each format priority
        format_row = 0
        format_col = 0
        self.format_vars = {}
        
        # Sort formats by their default priority
        sorted_formats = sorted(self.format_priority.items(), key=lambda x: x[0])
        
        for ext, priority in sorted_formats:
            # Strip the dot from extension
            ext_name = ext[1:].upper()
            
            # Create variable for this format
            self.format_vars[ext] = tk.IntVar(value=priority)
            
            # Create a frame for this format
            format_item_frame = ttk.Frame(format_frame)
            format_item_frame.grid(row=format_row, column=format_col, padx=10, pady=5, sticky=tk.W)
            
            # Add label and spinbox
            ttk.Label(format_item_frame, text=f"{ext_name}:").grid(row=0, column=0, padx=5)
            ttk.Spinbox(format_item_frame, from_=0, to=10, width=3, 
                       textvariable=self.format_vars[ext]).grid(row=0, column=1)
            
            # Arrange in a grid, 3 formats per row
            format_col += 1
            if format_col > 2:
                format_col = 0
                format_row += 1
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=10)
        
        ttk.Button(button_frame, text="Scan for Duplicates", command=self.start_scan).grid(
            row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Process Duplicates", command=self.process_duplicates).grid(
            row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Save Settings", command=self.save_config).grid(
            row=0, column=2, padx=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=100,
                                       mode='determinate', variable=self.progress_var)
        self.progress.grid(row=7, column=0, columnspan=3, sticky=tk.EW, pady=5)
        
        # Status label
        status_label = ttk.Label(main_frame, textvariable=self.status_var, anchor=tk.W)
        status_label.grid(row=8, column=0, columnspan=3, sticky=tk.W, pady=2)
        
        # Log text area
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding=5)
        log_frame.grid(row=9, column=0, columnspan=3, sticky=tk.NSEW, pady=5)
        
        # Make log frame expandable
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(9, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = tk.Text(log_frame, height=15, width=70, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=tk.NSEW)
        
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Set initial state
        self.toggle_dest_visibility()
        
        # Initialize log with welcome message
        self.log("Welcome to Music Deduplication Tool")
        if HAS_MUTAGEN:
            self.log("ID3 tag support is enabled for more accurate music identification")
        else:
            self.log("ID3 tag support is not available - install mutagen for better results")
        self.log("Drag and drop directories into the source/destination fields or use the browse buttons")
        self.log(f"Default configuration loaded from: {CONFIG_FILE}")
    
    def toggle_dest_visibility(self):
        if self.action_var.get() == "move":
            self.dest_frame.grid()
        else:
            self.dest_frame.grid_remove()
    
    def enable_drag_drop(self):
        # Register the source entry for drag and drop
        source_entry = self.root.nametowidget('.!frame.!entry')
        source_entry.drop_target_register(DND_FILES)
        source_entry.dnd_bind('<<Drop>>', self.drop_on_source)
        
        # Register the destination entry for drag and drop
        dest_entry = self.root.nametowidget('.!frame.!frame.!entry')
        dest_entry.drop_target_register(DND_FILES)
        dest_entry.dnd_bind('<<Drop>>', self.drop_on_dest)
    
    def drop_on_source(self, event):
        # Get the dropped path, remove curly braces and quotes if present
        path = event.data
        path = self.clean_dropped_path(path)
        if os.path.isdir(path):
            self.source_var.set(path)
            self.log(f"Source directory set to: {path}")
    
    def drop_on_dest(self, event):
        # Get the dropped path, remove curly braces and quotes if present
        path = event.data
        path = self.clean_dropped_path(path)
        if os.path.isdir(path):
            self.dest_var.set(path)
            self.log(f"Destination directory set to: {path}")
        else:
            # If it's not a directory, try to use its parent directory
            parent = os.path.dirname(path)
            if parent and os.path.isdir(parent):
                self.dest_var.set(parent)
                self.log(f"Destination directory set to: {parent}")
    
    def clean_dropped_path(self, path):
        """Clean the path returned from drag and drop events."""
        if path.startswith('{') and path.endswith('}'):
            path = path[1:-1]
        # Handle multiple files (we just take the first one)
        if ' ' in path and ('"' in path or "'" in path):
            # This is a complex path with spaces, try to extract the first path
            for quote in ['"', "'"]:
                if quote in path:
                    parts = path.split(quote)
                    if len(parts) >= 3:  # At least one quoted path
                        return parts[1]
            # Fallback: just return the first space-separated part
            return path.split()[0]
        return path
    
    def browse_source(self):
        directory = filedialog.askdirectory(initialdir=self.source_var.get())
        if directory:
            self.source_var.set(directory)
            self.log(f"Source directory set to: {directory}")
    
    def browse_dest(self):
        directory = filedialog.askdirectory(initialdir=self.dest_var.get())
        if directory:
            self.dest_var.set(directory)
            self.log(f"Destination directory set to: {directory}")
    
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
            messagebox.showinfo("Operation in Progress", "Please wait for the current operation to complete.")
            return
        
        source_dir = self.source_var.get()
        if not source_dir or not os.path.isdir(source_dir):
            messagebox.showerror("Error", "Please select a valid source directory.")
            return
        
        # Clear previous results
        self.duplicates = {}
        
        # Update UI
        self.update_status("Scanning for duplicates...")
        self.update_progress(0)
        self.is_running = True
        
        # Run the scan in a separate thread
        threading.Thread(target=self.run_scan, daemon=True).start()
    
    def run_scan(self):
        try:
            source_dir = self.source_var.get()
            threshold = self.threshold_var.get()
            verbose = self.verbose_var.get()
            exact_size_match = self.exact_size_match_var.get()
            
            # Find all music files
            self.update_status("Finding music files...")
            all_files = []
            total_dirs = sum([len(dirs) for _, dirs, _ in os.walk(source_dir)])
            dirs_processed = 0
            
            # Store file sizes for comparison
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
            
            self.update_status(f"Found {len(all_files)} music files")
            
            # Group by normalized name
            self.update_status("Grouping files by name...")
            songs = defaultdict(list)
            for i, file_path in enumerate(all_files):
                progress = 30 + (i / len(all_files) * 30)
                self.update_progress(progress)
                norm_name = self.normalize_title(file_path)
                songs[norm_name].append(file_path)
            
            # Filter to only keep groups with duplicates
            duplicates = {name: files for name, files in songs.items() if len(files) > 1}
            
            # If exact size matching is enabled, further filter duplicates
            if exact_size_match:
                filtered_duplicates = {}
                for name, files in duplicates.items():
                    # Group files by size
                    size_groups = defaultdict(list)
                    for file in files:
                        size_groups[file_sizes[file]].append(file)
                    
                    # Only keep groups that have multiple files of the same size
                    for size, size_files in size_groups.items():
                        if len(size_files) > 1:
                            filtered_duplicates[f"{name} ({size} bytes)"] = size_files
                
                duplicates = filtered_duplicates
            
            # Sort each group by quality
            self.update_status("Determining highest quality versions...")
            for i, (name, files) in enumerate(duplicates.items()):
                progress = 60 + (i / len(duplicates) * 40)  # 60% to 100% of progress bar
                self.update_progress(progress)
                
                # Score each file
                scored_files = [(f, self.get_file_quality_score(f)) for f in files]
                
                # Sort by score (highest first)
                scored_files.sort(key=lambda x: x[1], reverse=True)
                
                # The highest quality file is the keeper
                keeper = scored_files[0][0]
                dupes = [f for f, _ in scored_files[1:]]
                
                self.duplicates[name] = {
                    'keeper': keeper,
                    'duplicates': dupes,
                    'scores': {f: score for f, score in scored_files}
                }
            
            # Display results
            total_duplicates = sum(len(info['duplicates']) for info in self.duplicates.values())
            self.update_status(f"Found {len(self.duplicates)} songs with {total_duplicates} duplicate files")
            
            # Show details if verbose
            if verbose and self.duplicates:
                self.log("\n=== Duplicate Details ===")
                for name, info in self.duplicates.items():
                    keeper = info['keeper']
                    dupes = info['duplicates']
                    
                    self.log(f"\n{name}")
                    self.log(f"  KEEP: {os.path.basename(keeper)} [{self.format_quality(keeper, info['scores'][keeper])}]")
                    
                    for dupe in dupes:
                        self.log(f"  DUPE: {os.path.basename(dupe)} [{self.format_quality(dupe, info['scores'][dupe])}]")
            
            self.update_progress(100)
            
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
        finally:
            self.is_running = False
    
    def process_duplicates(self):
        if self.is_running:
            messagebox.showinfo("Operation in Progress", "Please wait for the current operation to complete.")
            return
        
        if not self.duplicates:
            messagebox.showinfo("No Duplicates", "No duplicates found. Please run a scan first.")
            return
        
        action = self.action_var.get()
        total_dupes = sum(len(info['duplicates']) for info in self.duplicates.values())
        
        # Confirm action
        if action == "delete":
            if not messagebox.askyesno("Confirm Delete", 
                                      f"Are you sure you want to delete {total_dupes} duplicate files?"):
                return
        else:  # move
            dest_dir = self.dest_var.get()
            if not dest_dir:
                messagebox.showerror("Error", "Please specify a destination directory.")
                return
            
            if not os.path.exists(dest_dir):
                if messagebox.askyesno("Create Directory", 
                                     f"Destination directory '{dest_dir}' does not exist. Create it?"):
                    try:
                        os.makedirs(dest_dir, exist_ok=True)
                    except Exception as e:
                        messagebox.showerror("Error", f"Could not create directory: {str(e)}")
                        return
                else:
                    return
            
            if not messagebox.askyesno("Confirm Move", 
                                     f"Are you sure you want to move {total_dupes} duplicate files to {dest_dir}?"):
                return
        
        # Update UI
        self.update_status(f"{'Deleting' if action == 'delete' else 'Moving'} duplicate files...")
        self.update_progress(0)
        self.is_running = True
        
        # Run the processing in a separate thread
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
                            # Create a unique filename in the target directory
                            target = os.path.join(dest_dir, rel_path)
                            if os.path.exists(target):
                                base, ext = os.path.splitext(rel_path)
                                target = os.path.join(dest_dir, f"{base}_{hashlib.md5(dupe.encode()).hexdigest()[:6]}{ext}")
                            
                            shutil.move(dupe, target)
                            self.log(f"Moved: {rel_path} -> {target}")
                        else:  # delete
                            os.remove(dupe)
                            self.log(f"Deleted: {rel_path}")
                    except Exception as e:
                        self.log(f"Error processing {dupe}: {e}")
            
            self.update_status(f"Processed {processed} duplicate files")
            
            # Clear the duplicates list after processing
            self.duplicates = {}
            
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
        finally:
            self.is_running = False
    
    def normalize_title(self, filename):
        """Extract and normalize the song title and artist for comparison."""
        # Get just the filename without path or extension
        base_name = os.path.basename(filename)
        name, ext = os.path.splitext(base_name)
        
        # If ID3 tags are enabled and we have mutagen, try to use ID3 tags
        if HAS_MUTAGEN and self.use_id3_tags_var.get():
            try:
                if ext.lower() == '.mp3':
                    audio = MP3(filename)
                    # Extract artist and title if available
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
                # Fall back to filename if ID3 tags extraction failed
            except Exception as e:
                # If there's an error reading tags, fall back to filename
                pass
        
        # Fall back to filename normalization if ID3 tags are not available or failed
        # Remove numeric prefixes like "01 - " or "01. " or "01_"
        name = re.sub(r'^\d+[\s\.-_]+', '', name)
        
        # Remove quality indicators and other common metadata
        name = re.sub(r'\(Live.*?\)|\(Remaster(ed)?.*?\)|\(.*?Mix.*?\)|\(.*?Version.*?\)|\(From.*?\)|\{.*?\}|\[.*?\]', '', name, flags=re.IGNORECASE)
        
        # Clean up remaining spaces and special characters
        name = re.sub(r'[-_\s]{2,}', ' ', name).strip().lower()
        
        return name
    
    def get_file_quality_score(self, file_path):
        """Determine a quality score for the file based on format and size."""
        ext = os.path.splitext(file_path)[1].lower()
        
        # Get the current format priority (user may have adjusted it)
        current_priority = {}
        for format_ext, var in self.format_vars.items():
            current_priority[format_ext] = var.get()
        
        # Base score from format (prioritize based on user settings)
        score = current_priority.get(ext, 0) * 1000
        
        # Add file size as a tiebreaker - bigger is often better quality
        size_kb = os.path.getsize(file_path) / 1024  # Size in KB
        score += size_kb
        
        # If we have mutagen, try to get bitrate information for MP3s
        if HAS_MUTAGEN and ext.lower() == '.mp3':
            try:
                audio = MP3(file_path)
                if audio.info.bitrate:
                    # Add bitrate score (higher bitrate is better)
                    bitrate_kbps = audio.info.bitrate / 1000
                    score += bitrate_kbps
            except:
                pass
        
        return score
    
    def format_quality(self, file_path, score):
        """Format the quality information for display."""
        ext = os.path.splitext(file_path)[1].lower()
        size_kb = os.path.getsize(file_path) / 1024
        
        quality_info = []
        
        # Format extension
        quality_info.append(ext[1:].upper())
        
        # Format size
        if size_kb > 1024:
            quality_info.append(f"{size_kb/1024:.1f} MB")
        else:
            quality_info.append(f"{size_kb:.0f} KB")
        
        # Add bitrate for MP3 files if mutagen is available
        if HAS_MUTAGEN and ext.lower() == '.mp3':
            try:
                audio = MP3(file_path)
                if audio.info.bitrate:
                    bitrate_kbps = audio.info.bitrate / 1000
                    quality_info.append(f"{bitrate_kbps:.0f} kbps")
            except:
                pass
        
        # Return formatted string
        return ", ".join(quality_info)
    
    def load_config(self):
        """Load the configuration from file."""
        config = DEFAULT_CONFIG.copy()
        
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    loaded_config = json.load(f)
                    
                    # Handle format priority specially
                    if "format_priority" in loaded_config:
                        self.format_priority = loaded_config.pop("format_priority")
                    
                    # Update config with remaining settings
                    config.update(loaded_config)
        except Exception as e:
            print(f"Error loading config: {e}")
        
        # Apply the loaded config
        self.source_var.set(config["source_dir"])
        self.dest_var.set(config["dest_dir"])
        self.threshold_var.set(config["threshold"])
        self.threshold_display.set(f"{config['threshold']:.2f}")
        self.action_var.set(config["action"])
        self.verbose_var.set(config["verbose"])
        self.exact_size_match_var.set(config.get("exact_size_match", False))  # New config option
        
        # Set use_id3_tags only if mutagen is available
        if HAS_MUTAGEN and "use_id3_tags" in config:
            self.use_id3_tags_var.set(config["use_id3_tags"])
    
    def save_config(self):
        """Save the current configuration to file."""
        # Update format priority from UI
        for ext, var in self.format_vars.items():
            self.format_priority[ext] = var.get()
        
        config = {
            "source_dir": self.source_var.get(),
            "dest_dir": self.dest_var.get(),
            "threshold": self.threshold_var.get(),
            "action": self.action_var.get(),
            "verbose": self.verbose_var.get(),
            "use_id3_tags": self.use_id3_tags_var.get(),
            "exact_size_match": self.exact_size_match_var.get(),  # New config option
            "format_priority": self.format_priority
        }
        
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            
            self.log(f"Configuration saved to: {CONFIG_FILE}")
            messagebox.showinfo("Configuration Saved", f"Configuration saved to: {CONFIG_FILE}")
        except Exception as e:
            self.log(f"Error saving config: {e}")
            messagebox.showerror("Error", f"Could not save configuration: {str(e)}")

def main():
    # Check if running as a script or a frozen executable
    if getattr(sys, 'frozen', False):
        # If frozen, use the executable's directory
        base_dir = os.path.dirname(sys.executable)
    else:
        # If running as a script, use the script's directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Change to the base directory
    os.chdir(base_dir)
    
    # Create the root window
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    
    # Set window title with version
    root.title("Music Deduplication Tool v1.0")
    
    # Set window size and position
    window_width = 850
    window_height = 850
    root.geometry(f"{window_width}x{window_height}")
    
    # Get screen dimensions
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # Calculate position for center of screen
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    
    # Set window position
    root.geometry(f"+{x}+{y}")
    
    # Set window icon if running as a frozen executable
    if getattr(sys, 'frozen', False):
        try:
            icon_path = os.path.join(base_dir, "music_dedupe.ico")
            if os.path.exists(icon_path):
                root.iconbitmap(icon_path)
        except:
            pass
    
    # Initialize the app
    app = MusicDedupeApp(root)
    
    # Special handling for macOS to ensure window appears properly
    if sys.platform == 'darwin':
        # Function to bring window to front without using AppleScript
        def activate_window():
            # First update to ensure window is created
            root.update_idletasks()
            
            # Make window visible and bring to front using only tkinter methods
            root.lift()
            root.attributes('-topmost', True)
            root.after(500, lambda: root.attributes('-topmost', False))
            
            # Force focus
            root.focus_force()
            
            # Deiconify in case window was iconified
            root.deiconify()
        
        # Schedule activation to happen after initial rendering
        root.after(100, activate_window)
    
    # Start the main event loop
    root.mainloop()

if __name__ == "__main__":
    main()