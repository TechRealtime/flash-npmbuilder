"""
Flash npmBuilder v1.02
Developed by: Tech Realtime & SaQuiz Perks
Conceived and Designed by: Mr. Saqlain
YouTube: https://www.youtube.com/@TechRealtime

Zero-config portable Windows GUI application for building, previewing,
and running React/Vite/Next.js projects locally without command lines or manual setup.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import json
import threading
import subprocess
import shutil
import zipfile
import socket
import webbrowser
import random
import string
import time
import urllib.parse
import re
import platform
import urllib.request
import traceback
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn, TCPServer

# Enable High DPI Awareness for Windows
if platform.system() == "Windows":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

try:
    from send2trash import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    HAS_SEND2TRASH = False

APP_NAME = "Flash npmBuilder"
APP_VERSION = "v1.02"
DEVELOPER = "Tech Realtime & SaQuiz Perks"
AUTHOR = "Mr. Saqlain"
CHANNEL_URL = "https://www.youtube.com/@TechRealtime"
NODE_DOWNLOAD_URL = "https://nodejs.org/en/download/current"


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

    def server_bind(self):
        TCPServer.server_bind(self)
        self.server_name = 'localhost'
        self.server_port = self.server_address[1]


class BuildHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parts = self.path.split('?')[0].split('/')
        project_id = None
        
        # 1. Check path for project ID (e.g., /id-xxxxx/ or /temp_build/)
        if len(parts) > 1 and parts[1]:
            candidate = parts[1]
            if candidate.startswith('id-') or candidate.startswith('temp_'):
                project_id = candidate
        
        # 2. Check Referer header
        if not project_id:
            referer = self.headers.get('Referer', '')
            if referer:
                ref_path = urllib.parse.urlparse(referer).path
                ref_parts = ref_path.split('/')
                if len(ref_parts) > 1 and ref_parts[1]:
                    candidate = ref_parts[1]
                    if candidate.startswith('id-') or candidate.startswith('temp_'):
                        project_id = candidate
        
        # 3. Check Cookie header
        if not project_id:
            cookie_header = self.headers.get('Cookie', '')
            if 'project_id=' in cookie_header:
                match = re.search(r'project_id=([^;]+)', cookie_header)
                if match:
                    project_id = match.group(1).strip()
        
        self.current_project_id = project_id
        return super().do_GET()
        
    def end_headers(self):
        if hasattr(self, 'current_project_id') and self.current_project_id:
            self.send_header('Set-Cookie', f'project_id={self.current_project_id}; Path=/')
        super().end_headers()

    def translate_path(self, path):
        project_id = getattr(self, 'current_project_id', None)
        
        parsed_path = urllib.parse.urlparse(path).path
        parts = parsed_path.split('/')
        rel_path = parsed_path.lstrip('/')
        
        if len(parts) > 1 and (parts[1].startswith('id-') or parts[1].startswith('temp_')):
            rel_path = '/'.join(parts[2:])
            
        if project_id:
            # Check temp project first
            if project_id.startswith('temp_') and FlashNpmBuilderApp.ACTIVE_TEMP_PATH:
                temp_build_path = FlashNpmBuilderApp.ACTIVE_TEMP_PATH
                if os.path.exists(temp_build_path):
                    return self._resolve_project_route(temp_build_path, rel_path, is_nextjs=True)
                    
            # Check saved builds.json
            builds_file = Path(FlashNpmBuilderApp.get_settings()['builds_dir']) / 'builds.json'
            if builds_file.exists():
                try:
                    with open(builds_file, 'r', encoding='utf-8') as f:
                        builds = json.load(f)
                    for b in builds:
                        if b.get('project_id') == project_id and b.get('status') == 'Ready':
                            build_path = b.get('path', '')
                            is_nextjs = (b.get('type') == 'Next.js')
                            return self._resolve_project_route(build_path, rel_path, is_nextjs=is_nextjs)
                except Exception as e:
                    print(f"Error reading builds.json for routing: {e}")
                    
        return super().translate_path(path)

    def _resolve_project_route(self, build_path, rel_path, is_nextjs=False):
        # Next.js mapping: /_next/static/... -> static/...
        if is_nextjs and os.path.basename(build_path) == '.next':
            if rel_path.startswith('_next/'):
                rel_path = rel_path[len('_next/'):]

        safe_rel_path = rel_path.replace('/', os.sep)
        full_path = os.path.join(build_path, safe_rel_path)

        # Next.js specific routing hacks for .next dir
        if is_nextjs and os.path.basename(build_path) == '.next':
            if rel_path == '' or rel_path == '/':
                app_index = os.path.join(build_path, 'server', 'app', 'index.html')
                pages_index = os.path.join(build_path, 'server', 'pages', 'index.html')
                if os.path.exists(app_index): return app_index
                if os.path.exists(pages_index): return pages_index
            
            if not os.path.exists(full_path) or os.path.isdir(full_path):
                app_route = os.path.join(build_path, 'server', 'app', safe_rel_path + '.html')
                if os.path.exists(app_route): return app_route
                pages_route = os.path.join(build_path, 'server', 'pages', safe_rel_path + '.html')
                if os.path.exists(pages_route): return pages_route
                
                app_index_route = os.path.join(build_path, 'server', 'app', safe_rel_path, 'index.html')
                if os.path.exists(app_index_route): return app_index_route

        # SPA Routing & Fallbacks for React / Vite / Next.js
        if not os.path.exists(full_path) or os.path.isdir(full_path):
            if os.path.exists(full_path + '.html'):
                return full_path + '.html'
            index_path = os.path.join(build_path, 'index.html')
            if os.path.exists(index_path) and '.' not in os.path.basename(full_path):
                return index_path

        return full_path

    def list_directory(self, path):
        self.send_error(404, "No permission to list directory (or missing index.html)")
        return None

    def log_message(self, format, *args):
        # Keep background log silent
        pass


class FlashNpmBuilderApp:
    ACTIVE_TEMP_PATH = None
    ACTIVE_TEMP_ID = None

    # Store configurations cleanly in Windows AppData
    app_data_root = Path(os.environ.get('APPDATA', str(Path.home()))) / 'Flash_npmBuilder'
    _settings_file = app_data_root / 'config' / 'settings.json'

    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("860x700")
        self.root.minsize(760, 560)
        
        # Window Icon Setup
        self.set_app_icon()

        # State Variables
        self.current_project_path = None
        self.current_project_type = None
        self.is_building = False
        self.stop_requested = False
        self.build_process = None
        self.server_thread = None
        self.httpd = None
        self.current_build_dir = None
        self.current_build_id = None
        self.current_build_zip = None

        # Temp Build State Variables
        self.temp_project_path = None
        self.temp_project_type = None
        self.is_temp_building = False
        self.stop_temp_requested = False
        self.temp_build_process = None

        # Requirements State
        self.node_version = None
        self.npm_version = None
        self.node_check_done = False
        self.latest_node_version = "Checking online..."
        self._cached_lan_ip = "127.0.0.1"

        # Console Animation State
        self._anim_frame = 0

        self.load_settings()
        self.ensure_directories()
        self.start_server()

        self.setup_ui()
        self.refresh_builds_list()
        
        # Non-blocking async background checks: eliminates freeze and "Not Responding" title
        threading.Thread(target=self._async_startup_checks, daemon=True).start()

    def _async_startup_checks(self):
        # 1. Warm-up LAN IP in background
        try:
            self.get_lan_ip()
            self.root.after(0, self.refresh_builds_list)
        except Exception:
            pass

        # 2. Check Node.js and npm without freezing main UI
        self.check_nodejs()
        self.root.after(0, self._on_nodejs_detected)

        # 3. Check latest Node version online
        self.fetch_latest_node_version()

    def _on_nodejs_detected(self):
        self.node_check_done = True
        node_text = f"Node.js: {self.node_version} (npm: {self.npm_version})" if self.node_version else "Node.js: Not Installed / PATH Missing"
        if hasattr(self, 'lbl_global_node'):
            self.lbl_global_node.config(
                text=node_text,
                foreground='#16a34a' if self.node_version else '#dc2626'
            )
        self.update_requirement_labels()

        # Prompt user if Node.js is missing
        if not self.node_version:
            self.root.after(250, self.prompt_nodejs_missing)

    def set_app_icon(self):
        base_dir = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
        script_dir = Path(__file__).resolve().parent
        ico_candidates = [
            base_dir / "icon.ico",
            base_dir / "assets" / "icon.ico",
            script_dir / "icon.ico",
            script_dir / "assets" / "icon.ico",
        ]
        png_candidates = [
            base_dir / "icon.png",
            base_dir / "assets" / "icon.png",
            script_dir / "icon.png",
            script_dir / "assets" / "icon.png",
        ]

        found_ico = False
        for ico in ico_candidates:
            try:
                if ico.is_file():
                    self.root.iconbitmap(str(ico))
                    found_ico = True
                    break
            except Exception:
                pass

        if not found_ico:
            try:
                ext_ico = Path(r"D:\Apps\Control Lib\users\saqla\Pictures\Icon\icon.ico")
                if ext_ico.is_file():
                    self.root.iconbitmap(str(ext_ico))
            except Exception:
                pass

        found_png = False
        for png in png_candidates:
            try:
                if png.is_file():
                    icon_img = tk.PhotoImage(file=str(png))
                    self.root.iconphoto(True, icon_img)
                    found_png = True
                    break
            except Exception:
                pass

        if not found_png:
            try:
                ext_png = Path(r"D:\Apps\Control Lib\users\saqla\Pictures\Icon\icon.png")
                if ext_png.is_file():
                    icon_img = tk.PhotoImage(file=str(ext_png))
                    self.root.iconphoto(True, icon_img)
            except Exception:
                pass

    @classmethod
    def get_settings(cls):
        default_base = cls.app_data_root
        default_settings = {
            'auto_port': True,
            'port': 3000,
            'projects_dir': str(default_base / 'projects'),
            'builds_dir': str(default_base / 'builds'),
            'temp_dir': str(default_base / 'temp'),
            'cache_dir': str(default_base / 'cache')
        }
        if cls._settings_file.exists():
            try:
                with open(cls._settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    default_settings.update(data)
                    return default_settings
            except Exception:
                pass
        return default_settings

    def load_settings(self):
        self.settings = self.get_settings()

    def save_settings(self):
        self._settings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=4)

    def ensure_directories(self):
        Path(self.settings['projects_dir']).mkdir(parents=True, exist_ok=True)
        Path(self.settings['builds_dir']).mkdir(parents=True, exist_ok=True)
        Path(self.settings['temp_dir']).mkdir(parents=True, exist_ok=True)
        Path(self.settings['cache_dir']).mkdir(parents=True, exist_ok=True)
        self._settings_file.parent.mkdir(parents=True, exist_ok=True)

        builds_json = Path(self.settings['builds_dir']) / 'builds.json'
        if not builds_json.exists():
            with open(builds_json, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def check_nodejs(self):
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        node_cmd = shutil.which('node') or 'node'
        npm_cmd = shutil.which('npm') or ('npm.cmd' if os.name == 'nt' else 'npm')

        try:
            res_node = subprocess.run([node_cmd, '--version'], capture_output=True, text=True, timeout=5, startupinfo=startupinfo)
            self.node_version = res_node.stdout.strip() if res_node.returncode == 0 else None
        except Exception:
            self.node_version = None

        if self.node_version:
            try:
                res_npm = subprocess.run([npm_cmd, '--version'], capture_output=True, text=True, timeout=6, startupinfo=startupinfo)
                self.npm_version = res_npm.stdout.strip() if res_npm.returncode == 0 else None
            except Exception:
                self.npm_version = None
        else:
            self.npm_version = None

    def prompt_nodejs_missing(self):
        """Displays custom dialog when Node.js is not installed with direct download and website options."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Node.js Required - Flash npmBuilder")
        dialog.geometry("520x220")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog relative to main window
        try:
            dialog.update_idletasks()
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 260
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 110
            dialog.geometry(f"+{x}+{y}")
        except Exception:
            pass

        content_frame = ttk.Frame(dialog, padding=16)
        content_frame.pack(fill='both', expand=True)

        header_lbl = ttk.Label(
            content_frame,
            text="⚠️ Node.js Not Detected!",
            font=('', 12, 'bold'),
            foreground='#d9381e'
        )
        header_lbl.pack(anchor='w', pady=(0, 6))

        msg = (
            "Node.js is not detected on your system or is missing from your PATH.\n"
            "You need to download and install it first to build and preview React or Next.js apps.\n\n"
            "Choose an option below to proceed:"
        )
        msg_lbl = ttk.Label(content_frame, text=msg, justify='left', wraplength=480)
        msg_lbl.pack(anchor='w', pady=(0, 16))

        btn_row = ttk.Frame(content_frame)
        btn_row.pack(fill='x', pady=5)

        def on_direct_download():
            dialog.destroy()
            self.direct_download_nodejs()

        def on_website():
            dialog.destroy()
            self.open_nodejs_download()

        def on_later():
            dialog.destroy()

        btn_dl = ttk.Button(btn_row, text="📥 Download Node.js Directly", command=on_direct_download)
        btn_dl.pack(side='left', padx=(0, 8))

        btn_web = ttk.Button(btn_row, text="🌐 Website (Manual Download)", command=on_website)
        btn_web.pack(side='left', padx=8)

        btn_close = ttk.Button(btn_row, text="Close", command=on_later)
        btn_close.pack(side='right')

    def direct_download_nodejs(self):
        """Directly downloads official Windows x64 MSI installer to downloads folder and executes it."""
        threading.Thread(target=self._direct_download_thread, daemon=True).start()

    def _direct_download_thread(self):
        # Progress window
        prog_win = tk.Toplevel(self.root)
        prog_win.title("Downloading Node.js Installer...")
        prog_win.geometry("440x160")
        prog_win.resizable(False, False)
        prog_win.transient(self.root)

        # Center window
        try:
            prog_win.update_idletasks()
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 220
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 80
            prog_win.geometry(f"+{x}+{y}")
        except Exception:
            pass

        frame = ttk.Frame(prog_win, padding=16)
        frame.pack(fill='both', expand=True)

        status_lbl = ttk.Label(frame, text="Resolving latest Node.js Windows installer...", font=('', 10, 'bold'))
        status_lbl.pack(anchor='w', pady=(0, 8))

        p_bar = ttk.Progressbar(frame, mode='indeterminate')
        p_bar.pack(fill='x', pady=(0, 10))
        p_bar.start(10)

        detail_lbl = ttk.Label(frame, text="Connecting to nodejs.org...", foreground='gray')
        detail_lbl.pack(anchor='w')

        try:
            # 1. Query Node.js releases to find latest version with win-x64-msi
            req = urllib.request.Request("https://nodejs.org/dist/index.json", headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))

            chosen_ver = None
            for item in data:
                files = item.get('files', [])
                if 'win-x64-msi' in files:
                    chosen_ver = item.get('version')
                    break

            if not chosen_ver:
                chosen_ver = "v22.14.0"  # Safe LTS fallback

            msi_filename = f"node-{chosen_ver}-x64.msi"
            download_url = f"https://nodejs.org/dist/{chosen_ver}/{msi_filename}"

            dest_folder = Path.home() / "Downloads"
            dest_folder.mkdir(parents=True, exist_ok=True)
            dest_file = dest_folder / msi_filename

            detail_lbl.config(text=f"Downloading {msi_filename}...")
            p_bar.stop()
            p_bar.config(mode='determinate', maximum=100)

            def report_hook(block_num, block_size, total_size):
                if total_size > 0:
                    percent = min(100, int((block_num * block_size * 100) / total_size))
                    p_bar['value'] = percent
                    mb_downloaded = (block_num * block_size) / (1024 * 1024)
                    mb_total = total_size / (1024 * 1024)
                    detail_lbl.config(text=f"Downloaded {mb_downloaded:.1f} MB of {mb_total:.1f} MB ({percent}%)")

            urllib.request.urlretrieve(download_url, str(dest_file), reporthook=report_hook)

            prog_win.destroy()

            # Offer to run the installer
            if messagebox.askyesno(
                "Download Complete",
                f"Node.js installer was downloaded successfully to:\n{dest_file}\n\nWould you like to run the installer now?"
            ):
                os.startfile(str(dest_file))

        except Exception as e:
            try:
                prog_win.destroy()
            except Exception:
                pass
            if messagebox.askyesno(
                "Direct Download Failed",
                f"Could not complete automatic download:\n{e}\n\nWould you like to open the official Node.js download website instead?"
            ):
                self.open_nodejs_download()

    def fetch_latest_node_version(self):
        try:
            req = urllib.request.Request(
                "https://nodejs.org/dist/index.json",
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data and len(data) > 0:
                    latest = data[0].get('version', 'Unknown')
                    self.latest_node_version = latest
                else:
                    self.latest_node_version = "Unknown"
        except Exception:
            self.latest_node_version = "Unable to fetch (Offline or check URL)"
        
        # Refresh requirement tab UI if present
        if hasattr(self, 'lbl_req_latest_val'):
            self.root.after(0, self.update_requirement_labels)

    def get_lan_ip(self):
        if hasattr(self, '_cached_lan_ip') and self._cached_lan_ip and self._cached_lan_ip != "127.0.0.1":
            return self._cached_lan_ip
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.3)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            self._cached_lan_ip = ip
            return ip
        except Exception:
            self._cached_lan_ip = "127.0.0.1"
            return "127.0.0.1"

    def find_available_port(self, start_port):
        port = start_port
        while port < 65535:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    return port
            except OSError:
                port += 1
        return start_port

    def start_server(self):
        if self.httpd:
            try:
                self.httpd.shutdown()
            except Exception:
                pass

        if self.settings.get('auto_port', True):
            self.current_port = self.find_available_port(self.settings.get('port', 3000))
        else:
            self.current_port = int(self.settings.get('port', 3000))

        try:
            self.httpd = ThreadingHTTPServer(('', self.current_port), BuildHandler)
            self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            self.server_thread.start()
        except Exception as e:
            messagebox.showerror("Server Error", f"Could not start preview server on port {self.current_port}:\n{e}")

    # ========================== UI SETUP ==========================

    def setup_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Tabs
        self.tab_main = ttk.Frame(self.notebook)
        self.tab_temp = ttk.Frame(self.notebook)
        self.tab_builds = ttk.Frame(self.notebook)
        self.tab_requirements = ttk.Frame(self.notebook)
        self.tab_settings = ttk.Frame(self.notebook)
        self.tab_about = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_main, text="Main")
        self.notebook.add(self.tab_temp, text="Temp Build")
        self.notebook.add(self.tab_builds, text="Builds List")
        self.notebook.add(self.tab_requirements, text="Requirenments")
        self.notebook.add(self.tab_settings, text="Settings")
        self.notebook.add(self.tab_about, text="About")

        self.setup_tab_main()
        self.setup_tab_temp()
        self.setup_tab_builds()
        self.setup_tab_requirements()
        self.setup_tab_settings()
        self.setup_tab_about()

        # Global Bottom Status Bar
        status_bar = ttk.Frame(self.root)
        status_bar.pack(fill='x', padx=10, pady=(0, 6))

        self.lbl_global_node = ttk.Label(status_bar, text="Node.js: Checking environment...", foreground='#0284c7')
        self.lbl_global_node.pack(side='left')

        ttk.Label(status_bar, text=f"Serving on Port: {self.current_port} | Portable Windows Mode", foreground='gray').pack(side='right')

    # ---------------- TAB 1: MAIN DASHBOARD ----------------
    def setup_tab_main(self):
        selection_frame = ttk.LabelFrame(self.tab_main, text="Project Selection & Source")
        selection_frame.pack(side='top', fill='x', padx=10, pady=5)

        btn_frame = ttk.Frame(selection_frame)
        btn_frame.pack(fill='x', padx=5, pady=5)

        ttk.Button(btn_frame, text="Select Folder", command=self.select_folder).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Select ZIP", command=self.select_zip).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Clear Workspace", command=self.clear_workspace).pack(side='left', padx=5)

        self.lbl_project_path = ttk.Label(selection_frame, text="No project selected", wraplength=700)
        self.lbl_project_path.pack(fill='x', padx=10, pady=(0, 3))

        self.lbl_project_type = ttk.Label(selection_frame, text="Framework Type: Unknown", font=('', 10, 'bold'))
        self.lbl_project_type.pack(fill='x', padx=10, pady=(0, 5))

        prog_frame = ttk.Frame(self.tab_main)
        prog_frame.pack(side='top', fill='x', padx=10, pady=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(prog_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side='left', fill='x', expand=True)

        self.lbl_progress = ttk.Label(prog_frame, text="0%", width=6)
        self.lbl_progress.pack(side='left', padx=5)

        urls_frame = ttk.LabelFrame(self.tab_main, text="Local Live Hosting & Previews")
        urls_frame.pack(side='top', fill='x', padx=10, pady=5)

        self.local_url_var = tk.StringVar(value="Waiting for build...")
        self.lan_url_var = tk.StringVar(value="Waiting for build...")

        local_frame = ttk.Frame(urls_frame)
        local_frame.pack(fill='x', padx=5, pady=3)
        ttk.Label(local_frame, text="Local Host:", width=14).pack(side='left')
        ttk.Entry(local_frame, textvariable=self.local_url_var, state='readonly').pack(side='left', fill='x', expand=True, padx=5)
        ttk.Button(local_frame, text="Copy", command=lambda: self.copy_to_clipboard(self.local_url_var.get())).pack(side='left', padx=2)
        ttk.Button(local_frame, text="Open Browser", command=lambda: self.open_url(self.local_url_var.get())).pack(side='left', padx=2)

        lan_frame = ttk.Frame(urls_frame)
        lan_frame.pack(fill='x', padx=5, pady=3)
        ttk.Label(lan_frame, text="LAN Network:", width=14).pack(side='left')
        ttk.Entry(lan_frame, textvariable=self.lan_url_var, state='readonly').pack(side='left', fill='x', expand=True, padx=5)
        ttk.Button(lan_frame, text="Copy", command=lambda: self.copy_to_clipboard(self.lan_url_var.get())).pack(side='left', padx=2)
        ttk.Button(lan_frame, text="Open Browser", command=lambda: self.open_url(self.lan_url_var.get())).pack(side='left', padx=2)

        # Bottom Action Bar
        control_frame = ttk.Frame(self.tab_main)
        control_frame.pack(side='bottom', fill='x', padx=10, pady=8)

        self.btn_build = ttk.Button(control_frame, text="Build Project", state='disabled', command=self.start_build)
        self.btn_build.pack(side='left', padx=5)

        self.btn_stop = ttk.Button(control_frame, text="Stop Build", state='disabled', command=self.stop_build)
        self.btn_stop.pack(side='left', padx=5)

        self.btn_download = ttk.Button(control_frame, text="Download as ZIP", state='disabled', command=self.download_current_build)
        self.btn_download.pack(side='right', padx=5)

        # Terminal Output
        term_frame = ttk.LabelFrame(self.tab_main, text="Console Build Logs")
        term_frame.pack(side='bottom', fill='both', expand=True, padx=10, pady=5)

        term_header = ttk.Frame(term_frame)
        term_header.pack(fill='x', padx=4, pady=2)
        self.lbl_anim_main = ttk.Label(term_header, text="", font=('Segoe UI', 9, 'bold'), foreground='#0284c7')
        self.lbl_anim_main.pack(side='left', padx=4)
        ttk.Button(term_header, text="Copy Logs", command=lambda: self.copy_text_from(self.terminal)).pack(side='right', padx=2, pady=2)

        self.terminal = tk.Text(term_frame, bg='#181818', fg='#e0e0e0', font=('Consolas', 9), state='disabled', wrap='none')
        scrollbar_y = ttk.Scrollbar(term_frame, orient="vertical", command=self.terminal.yview)
        scrollbar_x = ttk.Scrollbar(term_frame, orient="horizontal", command=self.terminal.xview)
        self.terminal.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        scrollbar_y.pack(side='right', fill='y')
        scrollbar_x.pack(side='bottom', fill='x')
        self.terminal.pack(side='left', fill='both', expand=True, padx=2, pady=2)

        self.terminal.tag_config('success', foreground='#55ff55')
        self.terminal.tag_config('error', foreground='#ff6666')
        self.terminal.tag_config('info', foreground='#55ffff')
        self.terminal.tag_config('warn', foreground='#ffff55')
        self.terminal.tag_config('anim', foreground='#38bdf8', font=('Consolas', 9, 'italic'))

    # ---------------- TAB 2: TEMP BUILD (AUTO-CLEANUP) ----------------
    def setup_tab_temp(self):
        info_header = ttk.Label(
            self.tab_temp,
            text="⚡ Temp Build Mode: Ephemeral workspace for quick testing. Previous temp build is deleted whenever\na new app is built or when the app closes. Stored cleanly in AppData/temp.",
            font=('', 9, 'italic'),
            foreground='#0055aa'
        )
        info_header.pack(fill='x', padx=10, pady=6)

        selection_frame = ttk.LabelFrame(self.tab_temp, text="Temp Project Input")
        selection_frame.pack(side='top', fill='x', padx=10, pady=5)

        btn_frame = ttk.Frame(selection_frame)
        btn_frame.pack(fill='x', padx=5, pady=5)

        ttk.Button(btn_frame, text="Choose Folder for Temp Build", command=self.select_temp_folder).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Choose ZIP for Temp Build", command=self.select_temp_zip).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Purge Temp Now", command=self.delete_current_temp_project).pack(side='left', padx=5)

        self.lbl_temp_project_path = ttk.Label(selection_frame, text="No temp project selected", wraplength=700)
        self.lbl_temp_project_path.pack(fill='x', padx=10, pady=(0, 3))

        self.lbl_temp_project_type = ttk.Label(selection_frame, text="Framework Type: Unknown", font=('', 10, 'bold'))
        self.lbl_temp_project_type.pack(fill='x', padx=10, pady=(0, 5))

        prog_frame = ttk.Frame(self.tab_temp)
        prog_frame.pack(side='top', fill='x', padx=10, pady=5)

        self.temp_progress_var = tk.DoubleVar()
        self.temp_progress_bar = ttk.Progressbar(prog_frame, variable=self.temp_progress_var, maximum=100)
        self.temp_progress_bar.pack(side='left', fill='x', expand=True)

        self.lbl_temp_progress = ttk.Label(prog_frame, text="0%", width=6)
        self.lbl_temp_progress.pack(side='left', padx=5)

        urls_frame = ttk.LabelFrame(self.tab_temp, text="Temp Build Dynamic URLs")
        urls_frame.pack(side='top', fill='x', padx=10, pady=5)

        self.temp_local_url_var = tk.StringVar(value="Waiting for temp build...")
        self.temp_lan_url_var = tk.StringVar(value="Waiting for temp build...")

        local_frame = ttk.Frame(urls_frame)
        local_frame.pack(fill='x', padx=5, pady=3)
        ttk.Label(local_frame, text="Temp Local:", width=14).pack(side='left')
        ttk.Entry(local_frame, textvariable=self.temp_local_url_var, state='readonly').pack(side='left', fill='x', expand=True, padx=5)
        ttk.Button(local_frame, text="Copy", command=lambda: self.copy_to_clipboard(self.temp_local_url_var.get())).pack(side='left', padx=2)
        ttk.Button(local_frame, text="Open Browser", command=lambda: self.open_url(self.temp_local_url_var.get())).pack(side='left', padx=2)

        lan_frame = ttk.Frame(urls_frame)
        lan_frame.pack(fill='x', padx=5, pady=3)
        ttk.Label(lan_frame, text="Temp LAN:", width=14).pack(side='left')
        ttk.Entry(lan_frame, textvariable=self.temp_lan_url_var, state='readonly').pack(side='left', fill='x', expand=True, padx=5)
        ttk.Button(lan_frame, text="Copy", command=lambda: self.copy_to_clipboard(self.temp_lan_url_var.get())).pack(side='left', padx=2)
        ttk.Button(lan_frame, text="Open Browser", command=lambda: self.open_url(self.temp_lan_url_var.get())).pack(side='left', padx=2)

        # Control Bar
        control_frame = ttk.Frame(self.tab_temp)
        control_frame.pack(side='bottom', fill='x', padx=10, pady=8)

        self.btn_temp_build = ttk.Button(control_frame, text="⚡ Run Temp Build", state='disabled', command=self.start_temp_build)
        self.btn_temp_build.pack(side='left', padx=5)

        self.btn_temp_stop = ttk.Button(control_frame, text="Stop Temp Build", state='disabled', command=self.stop_temp_build)
        self.btn_temp_stop.pack(side='left', padx=5)

        self.btn_open_temp_loc = ttk.Button(control_frame, text="Open Temp Folder", command=self.open_temp_folder)
        self.btn_open_temp_loc.pack(side='right', padx=5)

        # Terminal Output for Temp
        term_frame = ttk.LabelFrame(self.tab_temp, text="Temp Build Console")
        term_frame.pack(side='bottom', fill='both', expand=True, padx=10, pady=5)

        term_header = ttk.Frame(term_frame)
        term_header.pack(fill='x', padx=4, pady=2)
        self.lbl_anim_temp = ttk.Label(term_header, text="", font=('Segoe UI', 9, 'bold'), foreground='#0284c7')
        self.lbl_anim_temp.pack(side='left', padx=4)
        ttk.Button(term_header, text="Copy Logs", command=lambda: self.copy_text_from(self.temp_terminal)).pack(side='right', padx=2, pady=2)

        self.temp_terminal = tk.Text(term_frame, bg='#10141a', fg='#d1d5db', font=('Consolas', 9), state='disabled', wrap='none')
        scrollbar_y = ttk.Scrollbar(term_frame, orient="vertical", command=self.temp_terminal.yview)
        scrollbar_x = ttk.Scrollbar(term_frame, orient="horizontal", command=self.temp_terminal.xview)
        self.temp_terminal.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        scrollbar_y.pack(side='right', fill='y')
        scrollbar_x.pack(side='bottom', fill='x')
        self.temp_terminal.pack(side='left', fill='both', expand=True, padx=2, pady=2)

        self.temp_terminal.tag_config('success', foreground='#4ade80')
        self.temp_terminal.tag_config('error', foreground='#f87171')
        self.temp_terminal.tag_config('info', foreground='#38bdf8')
        self.temp_terminal.tag_config('warn', foreground='#facc15')
        self.temp_terminal.tag_config('anim', foreground='#38bdf8', font=('Consolas', 9, 'italic'))

    # ---------------- TAB 3: BUILDS MANAGEMENT ----------------
    def setup_tab_builds(self):
        tree_frame = ttk.Frame(self.tab_builds)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)

        columns = ("name", "type", "status", "url", "lan_url", "path")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")

        self.tree.heading("name", text="Project Name")
        self.tree.heading("type", text="Framework")
        self.tree.heading("status", text="Status")
        self.tree.heading("url", text="Local URL")
        self.tree.heading("lan_url", text="LAN URL")
        self.tree.heading("path", text="Directory Path")

        self.tree.column("name", width=140)
        self.tree.column("type", width=90)
        self.tree.column("status", width=80)
        self.tree.column("url", width=190)
        self.tree.column("lan_url", width=190)
        self.tree.column("path", width=180)

        scrollbar_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        scrollbar_y.pack(side='right', fill='y')
        scrollbar_x.pack(side='bottom', fill='x')
        self.tree.pack(side='left', fill='both', expand=True)

        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)

        # Context Menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Open in Browser", command=self.open_selected_build)
        self.context_menu.add_command(label="Open Project Location", command=self.open_selected_project_location)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Copy Local URL", command=self.copy_selected_local_url)
        self.context_menu.add_command(label="Copy LAN URL", command=self.copy_lan_url)
        self.context_menu.add_command(label="Download as ZIP", command=self.download_selected_build)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Scan & Detect Restored Builds", command=self.scan_and_detect_restored_builds)
        self.context_menu.add_command(label="Move to Recycle Bin (Delete)", command=self.delete_selected_build)

        btn_frame = ttk.Frame(self.tab_builds)
        btn_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(btn_frame, text="🔍 Detect Restored Builds", command=self.scan_and_detect_restored_builds).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Open Project Location", command=self.open_selected_project_location).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Open All Builds Folder", command=self.open_all_builds_dir).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Refresh List", command=self.refresh_builds_list).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Delete Selected (Recycle Bin)", command=self.delete_selected_build).pack(side='right', padx=5)

    # ---------------- TAB 4: REQUIREMENTS CHECK ----------------
    def setup_tab_requirements(self):
        req_frame = ttk.LabelFrame(self.tab_requirements, text="System & Node.js Environment Detection")
        req_frame.pack(fill='x', padx=15, pady=15)

        # Node Installed Status
        node_box = ttk.Frame(req_frame)
        node_box.pack(fill='x', padx=10, pady=8)
        ttk.Label(node_box, text="Node.js Status:", width=20, font=('', 10, 'bold')).pack(side='left')
        self.lbl_req_node_status = ttk.Label(node_box, text="", font=('', 10))
        self.lbl_req_node_status.pack(side='left')

        # Installed Version
        ver_box = ttk.Frame(req_frame)
        ver_box.pack(fill='x', padx=10, pady=8)
        ttk.Label(ver_box, text="Installed Node Version:", width=20, font=('', 10, 'bold')).pack(side='left')
        self.lbl_req_node_ver = ttk.Label(ver_box, text="", font=('', 10))
        self.lbl_req_node_ver.pack(side='left')

        # npm Version
        npm_box = ttk.Frame(req_frame)
        npm_box.pack(fill='x', padx=10, pady=8)
        ttk.Label(npm_box, text="npm Package Manager:", width=20, font=('', 10, 'bold')).pack(side='left')
        self.lbl_req_npm_ver = ttk.Label(npm_box, text="", font=('', 10))
        self.lbl_req_npm_ver.pack(side='left')

        # Latest Version Available
        latest_box = ttk.Frame(req_frame)
        latest_box.pack(fill='x', padx=10, pady=8)
        ttk.Label(latest_box, text="Latest Version Online:", width=20, font=('', 10, 'bold')).pack(side='left')
        self.lbl_req_latest_val = ttk.Label(latest_box, text=self.latest_node_version, font=('', 10))
        self.lbl_req_latest_val.pack(side='left')

        # Version Comparison Result
        comp_box = ttk.Frame(req_frame)
        comp_box.pack(fill='x', padx=10, pady=8)
        ttk.Label(comp_box, text="Update Check:", width=20, font=('', 10, 'bold')).pack(side='left')
        self.lbl_req_diff = ttk.Label(comp_box, text="Checking...", font=('', 10))
        self.lbl_req_diff.pack(side='left')

        # Action Buttons
        act_frame = ttk.Frame(self.tab_requirements)
        act_frame.pack(fill='x', padx=15, pady=10)

        ttk.Button(act_frame, text="📥 Download Directly", command=self.direct_download_nodejs).pack(side='left', padx=5)
        ttk.Button(act_frame, text="🌐 Website (Manual Download)", command=self.open_nodejs_download).pack(side='left', padx=5)
        ttk.Button(act_frame, text="🔄 Re-Check Node.js Status", command=self.recheck_requirements).pack(side='left', padx=5)

        # Helpful explanation
        help_frame = ttk.LabelFrame(self.tab_requirements, text="Why Node.js is required")
        help_frame.pack(fill='both', expand=True, padx=15, pady=10)
        desc = (
            "Flash npmBuilder uses your local Node.js and npm engine to compile React, Vite, and Next.js projects.\n\n"
            "Key Advantages:\n"
            "• Zero Visual Studio Code required: prompt creators & designers can preview projects in one click.\n"
            "• Zero manual CLI configuration or path debugging.\n"
            "• If Node.js is not yet installed on this PC, click 'Download / Update Node.js' above to get the latest installer.\n"
            "• After installing Node.js, click 'Re-Check Node.js Status' to start building right away!"
        )
        ttk.Label(help_frame, text=desc, justify='left', wraplength=680).pack(padx=10, pady=10, anchor='nw')

        self.update_requirement_labels()

    def update_requirement_labels(self):
        if not self.node_check_done:
            self.lbl_req_node_status.config(text="Detecting environment...", foreground='#0284c7')
            self.lbl_req_node_ver.config(text="Scanning system PATH...", foreground='gray')
            self.lbl_req_npm_ver.config(text="Scanning system PATH...", foreground='gray')
            self.lbl_req_diff.config(text="Checking...", foreground='gray')
            return

        if self.node_version:
            self.lbl_req_node_status.config(text="Installed and Ready \u2705", foreground='green')
            self.lbl_req_node_ver.config(text=self.node_version, foreground='black')
        else:
            self.lbl_req_node_status.config(text="Not Found on System \u274C", foreground='red')
            self.lbl_req_node_ver.config(text="None detected in PATH", foreground='red')

        self.lbl_req_npm_ver.config(text=self.npm_version if self.npm_version else "Not Found", foreground='green' if self.npm_version else 'red')
        self.lbl_req_latest_val.config(text=self.latest_node_version)

        # Version Comparison
        if not self.node_version:
            self.lbl_req_diff.config(text="Node.js is missing. Please download current version.", foreground='red')
        elif "Checking" in self.latest_node_version or "Unable" in self.latest_node_version:
            self.lbl_req_diff.config(text=self.latest_node_version, foreground='gray')
        else:
            curr = self.node_version.lstrip('v')
            lat = self.latest_node_version.lstrip('v')
            if curr == lat:
                self.lbl_req_diff.config(text="You have the latest version installed! \u2705", foreground='green')
            else:
                self.lbl_req_diff.config(text=f"A newer version ({self.latest_node_version}) is available online.", foreground='#cc6600')

    def open_nodejs_download(self):
        webbrowser.open(NODE_DOWNLOAD_URL)

    def recheck_requirements(self):
        self.lbl_global_node.config(text="Node.js: Re-checking environment...", foreground='#0284c7')
        self.lbl_req_node_status.config(text="Detecting...", foreground='#0284c7')
        self.lbl_req_node_ver.config(text="Scanning...", foreground='gray')
        self.lbl_req_npm_ver.config(text="Scanning...", foreground='gray')

        def _bg_recheck():
            self.check_nodejs()
            self.root.after(0, self._on_nodejs_detected)
            self.fetch_latest_node_version()
            self.root.after(0, lambda: messagebox.showinfo("Status Refreshed", "Environment status refreshed successfully."))

        threading.Thread(target=_bg_recheck, daemon=True).start()

    # ---------------- TAB 5: SETTINGS & STORAGE ----------------
    def setup_tab_settings(self):
        port_frame = ttk.LabelFrame(self.tab_settings, text="Port Configuration")
        port_frame.pack(fill='x', padx=10, pady=8)

        self.var_auto_port = tk.BooleanVar(value=self.settings.get('auto_port', True))
        cb_auto = ttk.Checkbutton(port_frame, text="Automatic Port Assignment (Prevents port conflict errors)", variable=self.var_auto_port, command=self.toggle_port_entry)
        cb_auto.pack(anchor='w', padx=10, pady=5)

        inner_port = ttk.Frame(port_frame)
        inner_port.pack(fill='x', padx=10, pady=5)
        ttk.Label(inner_port, text="Manual Port:").pack(side='left')

        self.entry_port = ttk.Entry(inner_port, width=10)
        self.entry_port.insert(0, str(self.settings.get('port', 3000)))
        self.entry_port.pack(side='left', padx=5)
        self.toggle_port_entry()

        dir_frame = ttk.LabelFrame(self.tab_settings, text="Storage & AppData Locations")
        dir_frame.pack(fill='x', padx=10, pady=8)

        # Projects Dir
        p_frame = ttk.Frame(dir_frame)
        p_frame.pack(fill='x', padx=10, pady=4)
        ttk.Label(p_frame, text="Projects Workspace:", width=18).pack(side='left')
        self.entry_proj_dir = ttk.Entry(p_frame)
        self.entry_proj_dir.insert(0, self.settings['projects_dir'])
        self.entry_proj_dir.pack(side='left', fill='x', expand=True, padx=5)
        ttk.Button(p_frame, text="Browse", command=lambda: self.browse_dir(self.entry_proj_dir)).pack(side='left')

        # Builds Dir
        b_frame = ttk.Frame(dir_frame)
        b_frame.pack(fill='x', padx=10, pady=4)
        ttk.Label(b_frame, text="Builds Directory:", width=18).pack(side='left')
        self.entry_build_dir = ttk.Entry(b_frame)
        self.entry_build_dir.insert(0, self.settings['builds_dir'])
        self.entry_build_dir.pack(side='left', fill='x', expand=True, padx=5)
        ttk.Button(b_frame, text="Browse", command=lambda: self.browse_dir(self.entry_build_dir)).pack(side='left')

        # Temp Dir
        t_frame = ttk.Frame(dir_frame)
        t_frame.pack(fill='x', padx=10, pady=4)
        ttk.Label(t_frame, text="Temp Dir (Ephemeral):", width=18).pack(side='left')
        self.entry_temp_dir = ttk.Entry(t_frame)
        self.entry_temp_dir.insert(0, self.settings.get('temp_dir', str(self.app_data_root / 'temp')))
        self.entry_temp_dir.pack(side='left', fill='x', expand=True, padx=5)
        ttk.Button(t_frame, text="Browse", command=lambda: self.browse_dir(self.entry_temp_dir)).pack(side='left')

        # Quick Explorer Buttons
        exp_frame = ttk.Frame(self.tab_settings)
        exp_frame.pack(fill='x', padx=10, pady=8)

        ttk.Button(exp_frame, text="📂 Open Projects Folder", command=self.open_all_projects_dir).pack(side='left', padx=5)
        ttk.Button(exp_frame, text="📂 Open Builds Folder", command=self.open_all_builds_dir).pack(side='left', padx=5)
        ttk.Button(exp_frame, text="📂 Open AppData Root Folder", command=self.open_appdata_root).pack(side='left', padx=5)

        ttk.Button(self.tab_settings, text="💾 Save Settings", command=self.save_settings_action).pack(pady=15)

    def toggle_port_entry(self):
        if self.var_auto_port.get():
            self.entry_port.config(state='disabled')
        else:
            self.entry_port.config(state='normal')

    def browse_dir(self, entry_widget):
        path = filedialog.askdirectory()
        if path:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, path)

    def save_settings_action(self):
        try:
            port_val = int(self.entry_port.get())
        except ValueError:
            messagebox.showerror("Error", "Port must be a valid number.")
            return

        self.settings['auto_port'] = self.var_auto_port.get()
        self.settings['port'] = port_val
        self.settings['projects_dir'] = self.entry_proj_dir.get()
        self.settings['builds_dir'] = self.entry_build_dir.get()
        self.settings['temp_dir'] = self.entry_temp_dir.get()

        self.save_settings()
        self.ensure_directories()
        self.start_server()
        self.refresh_builds_list()
        messagebox.showinfo("Saved", "Settings saved successfully! Server reconfigured.")

    # ---------------- TAB 6: ABOUT & CREDITS ----------------
    def setup_tab_about(self):
        frame = ttk.Frame(self.tab_about)
        frame.pack(fill='both', expand=True, padx=20, pady=20)

        title = ttk.Label(frame, text=f"{APP_NAME} {APP_VERSION}", font=('', 16, 'bold'))
        title.pack(anchor='w', pady=(0, 6))

        tagline = ttk.Label(frame, text="Zero-Config Portable Windows GUI App for React, Vite & Next.js Builds", font=('', 10, 'italic'))
        tagline.pack(anchor='w', pady=(0, 15))

        info_box = ttk.LabelFrame(frame, text="Project Information & Copyright")
        info_box.pack(fill='x', pady=10)

        ttk.Label(info_box, text=f"• Conceived & Developed by: {AUTHOR}", font=('', 10, 'bold')).pack(anchor='w', padx=10, pady=4)
        ttk.Label(info_box, text=f"• Copyright & Engineering: Developed by {DEVELOPER}", font=('', 10)).pack(anchor='w', padx=10, pady=4)
        ttk.Label(info_box, text=f"• License: MIT Open Source License", font=('', 10)).pack(anchor='w', padx=10, pady=4)

        link_frame = ttk.Frame(info_box)
        link_frame.pack(anchor='w', padx=10, pady=6)
        ttk.Label(link_frame, text="• YouTube Channel: ", font=('', 10)).pack(side='left')
        link_lbl = ttk.Label(link_frame, text=CHANNEL_URL, foreground='#0066cc', cursor='hand2', font=('', 10, 'underline'))
        link_lbl.pack(side='left')
        link_lbl.bind("<Button-1>", lambda e: webbrowser.open(CHANNEL_URL))

        desc_box = ttk.LabelFrame(frame, text="Core Mission & Benefits")
        desc_box.pack(fill='both', expand=True, pady=10)

        mission_text = (
            "Why Flash npmBuilder?\n"
            "Visual Studio Code is heavily complex for creators who just want to turn zipped AI code\n"
            "into running local web apps. VS Code requires terminal proficiency, package manager commands,\n"
            "handling missing dependencies, and debugging blank screens.\n\n"
            "Flash npmBuilder removes every obstacle:\n"
            "✓ Drag & drop or pick any project folder or ZIP archive.\n"
            "✓ Automatic package installation and static production builds.\n"
            "✓ Multi-port simultaneous previewing without port crashes.\n"
            "✓ Safe recycle bin deletion without leaving residual files behind.\n"
            "✓ Dedicated Temp Build Mode for zero-clutter instant tests."
        )
        ttk.Label(desc_box, text=mission_text, justify='left', wraplength=680).pack(padx=10, pady=10, anchor='nw')

    # ========================== CONSOLE BUILD ANIMATION ==========================

    def start_build_animation(self, mode="main"):
        self._anim_frame = 0
        self.root.after(80, self._anim_tick)

    def _anim_tick(self):
        if not (self.is_building or self.is_temp_building):
            self._cleanup_anim()
            return

        self._anim_frame += 1

        # Animated dots wave: 1 to 6 dots cycling
        dot_count = (self._anim_frame % 6) + 1
        dots = "." * dot_count
        dots_padded = dots + (" " * (6 - dot_count))

        # Rotating spinner symbols
        spinners = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        spin = spinners[self._anim_frame % len(spinners)]

        # Informative sub-states cycling smoothly so user never gets bored
        steps = [
            "Compiling & resolving project modules",
            "Resolving dependencies & peer packages",
            "Optimizing production chunks & bundles",
            "Bundling React & Next.js static assets",
            "Executing npm compile toolchain",
            "Generating local preview routes & assets"
        ]
        curr_step = steps[(self._anim_frame // 10) % len(steps)]

        anim_line = f"  {spin} {curr_step} {dots_padded} [working]"
        header_text = f"⚡ Building in progress {dots}"

        if self.is_building and hasattr(self, 'terminal'):
            self._render_anim_line(self.terminal, anim_line)
            if hasattr(self, 'lbl_anim_main'):
                self.lbl_anim_main.config(text=header_text)

        if self.is_temp_building and hasattr(self, 'temp_terminal'):
            self._render_anim_line(self.temp_terminal, anim_line)
            if hasattr(self, 'lbl_anim_temp'):
                self.lbl_anim_temp.config(text=header_text)

        self.root.after(200, self._anim_tick)

    def _render_anim_line(self, widget, anim_line):
        try:
            widget.config(state='normal')
            if 'anim_mark' in widget.mark_names():
                widget.delete('anim_mark', 'end')
            else:
                widget.mark_set('anim_mark', 'end-1c')
                widget.mark_gravity('anim_mark', 'left')
            widget.insert('anim_mark', anim_line + '\n', 'anim')
            widget.see('end')
        except Exception:
            pass
        finally:
            widget.config(state='disabled')

    def _cleanup_anim(self):
        for widget in (getattr(self, 'terminal', None), getattr(self, 'temp_terminal', None)):
            if widget:
                try:
                    widget.config(state='normal')
                    if 'anim_mark' in widget.mark_names():
                        widget.delete('anim_mark', 'end')
                        widget.mark_unset('anim_mark')
                    widget.config(state='disabled')
                except Exception:
                    pass
        if hasattr(self, 'lbl_anim_main'):
            self.lbl_anim_main.config(text="")
        if hasattr(self, 'lbl_anim_temp'):
            self.lbl_anim_temp.config(text="")

    # ========================== MAIN BUILD LOGIC ==========================

    def log_terminal(self, message, tag=None):
        self.terminal.config(state='normal')
        try:
            if 'anim_mark' in self.terminal.mark_names():
                self.terminal.delete('anim_mark', 'end')
                self.terminal.mark_unset('anim_mark')
            self.terminal.insert('end', message + '\n', tag)
            self.terminal.see('end')
        finally:
            self.terminal.config(state='disabled')

    def copy_text_from(self, widget):
        logs = widget.get(1.0, tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(logs)
        messagebox.showinfo("Copied", "Logs copied to clipboard.")

    def copy_to_clipboard(self, text):
        if text and "Waiting" not in text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            messagebox.showinfo("Copied", f"Copied URL to clipboard:\n{text}")

    def open_url(self, url):
        if url and "Waiting" not in url:
            webbrowser.open(url)

    def clear_workspace(self):
        if self.is_building:
            messagebox.showwarning("Warning", "Cannot clear workspace while build is in progress.")
            return

        self.current_project_path = None
        self.current_project_type = None
        self.current_build_dir = None
        self.current_build_id = None
        self.current_build_zip = None

        self.lbl_project_path.config(text="No project selected")
        self.lbl_project_type.config(text="Framework Type: Unknown")
        self.btn_build.config(state='disabled')
        self.btn_download.config(state='disabled')

        self.local_url_var.set("Waiting for build...")
        self.lan_url_var.set("Waiting for build...")

        self.terminal.config(state='normal')
        self.terminal.delete(1.0, tk.END)
        self.terminal.config(state='disabled')

        self.progress_var.set(0)
        self.lbl_progress.config(text="0%")

    def detect_project_type(self, path):
        # Look for package.json in path or immediate subdirectory
        p_path = Path(path)
        pkg = p_path / 'package.json'
        
        if not pkg.exists():
            for sub in p_path.iterdir():
                if sub.is_dir() and (sub / 'package.json').exists():
                    p_path = sub
                    pkg = sub / 'package.json'
                    break

        if not pkg.exists():
            return None, None

        try:
            with open(pkg, 'r', encoding='utf-8') as f:
                data = json.load(f)
                deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
                
                if 'next' in deps:
                    return 'Next.js', p_path
                elif 'vite' in deps:
                    return 'Vite (React)', p_path
                elif 'react' in deps:
                    return 'React', p_path
                else:
                    return 'Node.js App', p_path
        except Exception as e:
            return None, None

    def load_project(self, path):
        ptype, actual_path = self.detect_project_type(path)
        if not ptype:
            messagebox.showerror(
                "Invalid Project",
                "Could not find a valid package.json in the selected directory or ZIP.\n"
                "Please verify that this is a React, Next.js, or Vite project."
            )
            return

        self.current_project_path = str(actual_path)
        self.current_project_type = ptype
        self.lbl_project_path.config(text=f"Selected: {self.current_project_path}")
        self.lbl_project_type.config(text=f"Framework Type: {self.current_project_type}")

        self.btn_build.config(state='normal')
        self.btn_download.config(state='disabled')

        self.local_url_var.set("Ready to build...")
        self.lan_url_var.set("Ready to build...")

        self.log_terminal(f"Loaded project: {self.current_project_path}", 'info')
        self.log_terminal(f"Framework: {self.current_project_type}", 'info')

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select Project Root Folder")
        if folder:
            self.load_project(folder)

    def select_zip(self):
        zip_path = filedialog.askopenfilename(
            title="Select Project ZIP Archive",
            filetypes=[("ZIP Archive", "*.zip")]
        )
        if zip_path:
            temp_extract = Path(self.settings['cache_dir']) / "extract_main"
            if temp_extract.exists():
                shutil.rmtree(temp_extract, ignore_errors=True)

            try:
                self.log_terminal("Extracting ZIP archive...", 'info')
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_extract)

                contents = list(temp_extract.iterdir())
                if len(contents) == 1 and contents[0].is_dir():
                    project_dir = contents[0]
                else:
                    project_dir = temp_extract

                self.load_project(project_dir)
            except Exception as e:
                messagebox.showerror("Extraction Error", f"Failed to extract ZIP: {e}")

    def update_progress(self, val):
        self.progress_var.set(val)
        self.lbl_progress.config(text=f"{int(val)}%")

    def stop_build(self):
        if self.is_building:
            self.stop_requested = True
            if self.build_process:
                try:
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.build_process.pid)], capture_output=True)
                    else:
                        self.build_process.terminate()
                except Exception as e:
                    self.log_terminal(f"Error terminating process: {e}", 'error')

            self.log_terminal("\n--- Build Cancelled by User ---", 'error')
            self.reset_build_state()

    def reset_build_state(self):
        self.is_building = False
        self.stop_requested = False
        self.build_process = None
        self.btn_build.config(state='normal')
        self.btn_stop.config(state='disabled')
        if hasattr(self, 'current_build_id') and self.current_build_id:
            self.btn_download.config(state='normal')
        self._cleanup_anim()

    def start_build(self):
        if not self.current_project_path:
            return
        if not self.node_version:
            if not self.node_check_done:
                messagebox.showinfo("Checking Environment", "Flash npmBuilder is currently detecting Node.js. Please wait a moment...")
                return
            messagebox.showerror("Node.js Required", "Node.js is not detected on your system. Please install Node.js from the Requirements tab first.")
            return

        self.is_building = True
        self.stop_requested = False
        self.btn_build.config(state='disabled')
        self.btn_stop.config(state='normal')
        self.btn_download.config(state='disabled')

        self.local_url_var.set("Building...")
        self.lan_url_var.set("Building...")

        self.terminal.config(state='normal')
        self.terminal.delete(1.0, tk.END)
        self.terminal.config(state='disabled')

        self.start_build_animation("main")
        threading.Thread(target=self.build_thread_func, daemon=True).start()

    def run_subprocess(self, cmd, cwd):
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        env = os.environ.copy()
        env['CI'] = 'true'
        env['FORCE_COLOR'] = '0'

        self.build_process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True,
            bufsize=1,
            universal_newlines=True,
            startupinfo=startupinfo,
            env=env
        )

        lines_count = 0
        for line in self.build_process.stdout:
            if self.stop_requested:
                break
            self.root.after(0, self.log_terminal, line.strip())
            lines_count += 1
            if lines_count % 10 == 0:
                curr = self.progress_var.get()
                if curr < 90:
                    self.root.after(0, self.update_progress, curr + 0.1)

        self.build_process.wait()
        return self.build_process.returncode

    def find_build_output(self, project_dir):
        common_dirs = ['out', 'dist', 'build', '.next', 'public']
        for d in common_dirs:
            p = project_dir / d
            if p.exists() and p.is_dir():
                return p

        for root, dirs, files in os.walk(project_dir):
            if 'node_modules' in root:
                continue
            if 'index.html' in files:
                return Path(root)

        return None

    def build_thread_func(self):
        work_dir = None
        try:
            self.root.after(0, self.update_progress, 5)
            self.root.after(0, self.log_terminal, "=== Flash npmBuilder: Starting Build ===", 'info')

            project_id = f"id-{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"
            project_name = Path(self.current_project_path).name

            projects_base = Path(self.settings['projects_dir'])
            projects_base.mkdir(parents=True, exist_ok=True)
            work_dir = projects_base / project_id

            # Step 1: Copy workspace
            self.root.after(0, self.log_terminal, f"Syncing project workspace into: {work_dir}")
            if work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)

            shutil.copytree(
                self.current_project_path,
                work_dir,
                ignore=shutil.ignore_patterns('node_modules', '.git', '.next', 'dist', 'build', 'out'),
                dirs_exist_ok=True
            )
            self.root.after(0, self.update_progress, 20)

            if self.stop_requested: return

            # Step 2: npm install
            self.root.after(0, self.log_terminal, "\n> npm install --legacy-peer-deps", 'info')
            npm_cmd = "npm.cmd" if os.name == 'nt' else "npm"
            ret = self.run_subprocess(f"{npm_cmd} install --legacy-peer-deps", str(work_dir))
            if self.stop_requested: return

            if ret != 0:
                self.root.after(0, self.log_terminal, "\nError occurred during package installation (npm install)", 'error')
                self.root.after(0, self.reset_build_state)
                return

            self.root.after(0, self.update_progress, 55)

            # Step 3: npm run build
            self.root.after(0, self.log_terminal, f"\n> {npm_cmd} run build", 'info')
            ret = self.run_subprocess(f"{npm_cmd} run build", str(work_dir))
            if self.stop_requested: return

            if ret != 0:
                self.root.after(0, self.log_terminal, "\nError occurred during compilation (npm run build)", 'error')
                self.root.after(0, self.reset_build_state)
                return

            self.root.after(0, self.update_progress, 85)

            # Step 4: Identify output
            self.root.after(0, self.log_terminal, "\nLocating compilation output directory...", 'info')
            output_dir = self.find_build_output(work_dir)

            if not output_dir or not output_dir.exists():
                self.root.after(0, self.log_terminal, "Failed to identify output folder (dist, out, build, etc.)", 'error')
                self.root.after(0, self.reset_build_state)
                return

            self.root.after(0, self.log_terminal, f"Identified build target: {output_dir.name}")

            builds_base = Path(self.settings['builds_dir'])
            builds_base.mkdir(parents=True, exist_ok=True)
            final_build_dir = builds_base / f"{project_name}_{project_id}"
            if final_build_dir.exists():
                shutil.rmtree(final_build_dir, ignore_errors=True)
            shutil.copytree(output_dir, final_build_dir, dirs_exist_ok=True)

            zip_path = Path(self.settings['builds_dir']) / f"{project_name}_{project_id}.zip"
            shutil.make_archive(str(zip_path.with_suffix('')), 'zip', final_build_dir)

            self.root.after(0, self.update_progress, 95)

            metadata = {
                "id": project_id,
                "name": project_name,
                "type": self.current_project_type,
                "path": str(final_build_dir),
                "zip_path": str(zip_path),
                "port": self.current_port,
                "status": "Ready",
                "project_id": project_id,
                "timestamp": time.time()
            }

            builds_json = Path(self.settings['builds_dir']) / 'builds.json'
            builds = []
            if builds_json.exists():
                try:
                    with open(builds_json, 'r', encoding='utf-8') as f:
                        builds = json.load(f)
                except Exception:
                    builds = []

            builds.append(metadata)
            with open(builds_json, 'w', encoding='utf-8') as f:
                json.dump(builds, f, indent=4)

            self.current_build_id = project_id
            self.current_build_zip = str(zip_path)
            self.current_build_dir = str(final_build_dir)

            self.root.after(0, self._cleanup_anim)
            self.root.after(0, self.update_progress, 100)
            self.root.after(0, self.log_terminal, "\n=== Build Completed Successfully! ===", 'success')

            local_url = f"http://localhost:{self.current_port}/{project_id}/"
            lan_url = f"http://{self.get_lan_ip()}:{self.current_port}/{project_id}/"
            self.root.after(0, self.local_url_var.set, local_url)
            self.root.after(0, self.lan_url_var.set, lan_url)

            self.root.after(0, self.refresh_builds_list)

        except Exception as e:
            self.root.after(0, self.log_terminal, f"\nUnexpected Build Failure: {e}", 'error')
        finally:
            self.root.after(0, self.reset_build_state)
            if work_dir and work_dir.exists():
                try:
                    shutil.rmtree(work_dir, ignore_errors=True)
                except Exception:
                    pass

    # ========================== TEMP BUILD LOGIC ==========================

    def log_temp_terminal(self, message, tag=None):
        self.temp_terminal.config(state='normal')
        try:
            if 'anim_mark' in self.temp_terminal.mark_names():
                self.temp_terminal.delete('anim_mark', 'end')
                self.temp_terminal.mark_unset('anim_mark')
            self.temp_terminal.insert('end', message + '\n', tag)
            self.temp_terminal.see('end')
        finally:
            self.temp_terminal.config(state='disabled')

    def select_temp_folder(self):
        folder = filedialog.askdirectory(title="Select Temp Project Folder")
        if folder:
            self.load_temp_project(folder)

    def select_temp_zip(self):
        zip_path = filedialog.askopenfilename(
            title="Select Temp Project ZIP",
            filetypes=[("ZIP Archive", "*.zip")]
        )
        if zip_path:
            temp_extract = Path(self.settings.get('cache_dir', str(self.app_data_root / 'cache'))) / "extract_temp"
            if temp_extract.exists():
                shutil.rmtree(temp_extract, ignore_errors=True)
            temp_extract.mkdir(parents=True, exist_ok=True)

            try:
                self.log_temp_terminal("Extracting Temp ZIP archive...", 'info')
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_extract)

                contents = [c for c in temp_extract.iterdir() if not c.name.startswith('.')]
                if len(contents) == 1 and contents[0].is_dir():
                    project_dir = contents[0]
                else:
                    project_dir = temp_extract

                self.load_temp_project(project_dir)
            except Exception as e:
                messagebox.showerror("Extraction Error", f"Failed to extract ZIP: {e}")

    def load_temp_project(self, path):
        ptype, actual_path = self.detect_project_type(path)
        if not ptype:
            messagebox.showerror(
                "Invalid Temp Project",
                "Could not find a valid package.json in the chosen temp project.\n"
                "Please verify that this is a React or Next.js app."
            )
            return

        self.temp_project_path = str(actual_path)
        self.temp_project_type = ptype
        self.lbl_temp_project_path.config(text=f"Selected Temp: {self.temp_project_path}")
        self.lbl_temp_project_type.config(text=f"Framework: {self.temp_project_type}")

        self.btn_temp_build.config(state='normal')
        self.temp_local_url_var.set("Ready for temp build...")
        self.temp_lan_url_var.set("Ready for temp build...")

        self.log_temp_terminal(f"Loaded temp target: {self.temp_project_path}", 'info')
        self.log_temp_terminal(f"Framework: {self.temp_project_type}", 'info')

    def update_temp_progress(self, val):
        self.temp_progress_var.set(val)
        self.lbl_temp_progress.config(text=f"{int(val)}%")

    def delete_current_temp_project(self, preserve_path=None):
        """Purges any existing temp project from AppData/temp."""
        temp_dir = Path(self.settings.get('temp_dir', str(self.app_data_root / 'temp')))
        temp_dir.mkdir(parents=True, exist_ok=True)
        try:
            preserve = None
            if preserve_path:
                try:
                    preserve = Path(preserve_path).resolve()
                except Exception:
                    preserve = None

            if temp_dir.exists():
                for item in temp_dir.iterdir():
                    try:
                        resolved_item = item.resolve()
                        if preserve and (resolved_item == preserve or resolved_item in preserve.parents):
                            continue
                        if item.is_dir():
                            shutil.rmtree(item, ignore_errors=True)
                        else:
                            try:
                                item.unlink()
                            except Exception:
                                pass
                    except Exception:
                        pass
            FlashNpmBuilderApp.ACTIVE_TEMP_PATH = None
            FlashNpmBuilderApp.ACTIVE_TEMP_ID = None
            self.temp_local_url_var.set("Waiting for temp build...")
            self.temp_lan_url_var.set("Waiting for temp build...")
            self.log_temp_terminal("Temp directory purged and wiped clean.", 'warn')
        except Exception as e:
            self.log_temp_terminal(f"Failed to clear temp: {e}", 'error')

    def stop_temp_build(self):
        if self.is_temp_building:
            self.stop_temp_requested = True
            if self.temp_build_process:
                try:
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.temp_build_process.pid)], capture_output=True)
                    else:
                        self.temp_build_process.terminate()
                except Exception as e:
                    self.log_temp_terminal(f"Error terminating temp process: {e}", 'error')

            self.log_temp_terminal("\n--- Temp Build Cancelled by User ---", 'error')
            self.reset_temp_build_state()

    def reset_temp_build_state(self):
        self.is_temp_building = False
        self.stop_temp_requested = False
        self.temp_build_process = None
        self.btn_temp_build.config(state='normal')
        self.btn_temp_stop.config(state='disabled')
        self._cleanup_anim()

    def start_temp_build(self):
        if not self.temp_project_path:
            return
        if not os.path.exists(self.temp_project_path):
            messagebox.showerror("Project Not Found", f"Temp project source path does not exist:\n{self.temp_project_path}")
            return
        if not self.node_version:
            if not self.node_check_done:
                messagebox.showinfo("Checking Environment", "Flash npmBuilder is currently detecting Node.js. Please wait a moment...")
                return
            messagebox.showerror("Node.js Required", "Node.js is not installed. Please check the Requirements tab first.")
            return

        # Before building, delete previous temp project preserving the current source path
        self.delete_current_temp_project(preserve_path=self.temp_project_path)

        self.is_temp_building = True
        self.stop_temp_requested = False
        self.btn_temp_build.config(state='disabled')
        self.btn_temp_stop.config(state='normal')

        self.temp_local_url_var.set("Building temp project...")
        self.temp_lan_url_var.set("Building temp project...")

        self.temp_terminal.config(state='normal')
        self.temp_terminal.delete(1.0, tk.END)
        self.temp_terminal.config(state='disabled')

        self.start_build_animation("temp")
        threading.Thread(target=self.temp_build_thread_func, daemon=True).start()

    def run_temp_subprocess(self, cmd, cwd):
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        env = os.environ.copy()
        env['CI'] = 'true'
        env['FORCE_COLOR'] = '0'

        self.temp_build_process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True,
            bufsize=1,
            universal_newlines=True,
            startupinfo=startupinfo,
            env=env
        )

        lines_count = 0
        for line in self.temp_build_process.stdout:
            if self.stop_temp_requested:
                break
            self.root.after(0, self.log_temp_terminal, line.strip())
            lines_count += 1
            if lines_count % 10 == 0:
                curr = self.temp_progress_var.get()
                if curr < 90:
                    self.root.after(0, self.update_temp_progress, curr + 0.1)

        self.temp_build_process.wait()
        return self.temp_build_process.returncode

    def temp_build_thread_func(self):
        work_dir = None
        try:
            self.root.after(0, self.update_temp_progress, 5)
            self.root.after(0, self.log_temp_terminal, "=== Starting Ephemeral Temp Build ===", 'info')

            if not os.path.exists(self.temp_project_path):
                raise FileNotFoundError(f"Source project path not found: {self.temp_project_path}")

            temp_id = f"temp_{''.join(random.choices(string.ascii_lowercase + string.digits, k=6))}"
            temp_base = Path(self.settings.get('temp_dir', str(self.app_data_root / 'temp')))
            temp_base.mkdir(parents=True, exist_ok=True)
            work_dir = temp_base / f"{temp_id}_workspace"
            if work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)

            # Step 1: Copy
            self.root.after(0, self.log_temp_terminal, f"Copying files into temp workspace: {work_dir}")
            shutil.copytree(
                self.temp_project_path,
                work_dir,
                ignore=shutil.ignore_patterns('node_modules', '.git', '.next', 'dist', 'build', 'out'),
                dirs_exist_ok=True
            )
            self.root.after(0, self.update_temp_progress, 20)

            if self.stop_temp_requested: return

            # Step 2: npm install
            npm_cmd = "npm.cmd" if os.name == 'nt' else "npm"
            self.root.after(0, self.log_temp_terminal, f"\n> {npm_cmd} install --legacy-peer-deps", 'info')
            ret = self.run_temp_subprocess(f"{npm_cmd} install --legacy-peer-deps", str(work_dir))
            if self.stop_temp_requested: return

            if ret != 0:
                self.root.after(0, self.log_temp_terminal, "\nTemp Build failed during npm install.", 'error')
                self.root.after(0, self.reset_temp_build_state)
                return

            self.root.after(0, self.update_temp_progress, 60)

            # Step 3: npm run build
            self.root.after(0, self.log_temp_terminal, f"\n> {npm_cmd} run build", 'info')
            ret = self.run_temp_subprocess(f"{npm_cmd} run build", str(work_dir))
            if self.stop_temp_requested: return

            if ret != 0:
                self.root.after(0, self.log_temp_terminal, "\nTemp Build failed during compilation.", 'error')
                self.root.after(0, self.reset_temp_build_state)
                return

            self.root.after(0, self.update_temp_progress, 85)

            # Step 4: Find Output
            output_dir = self.find_build_output(work_dir)
            if not output_dir or not output_dir.exists():
                self.root.after(0, self.log_temp_terminal, "Failed to identify output directory in temp build.", 'error')
                self.root.after(0, self.reset_temp_build_state)
                return

            final_temp_out = temp_base / f"{temp_id}_live"
            if final_temp_out.exists():
                shutil.rmtree(final_temp_out, ignore_errors=True)
            shutil.copytree(output_dir, final_temp_out, dirs_exist_ok=True)

            # Register globally so BuildHandler can route requests to /temp_id/
            FlashNpmBuilderApp.ACTIVE_TEMP_PATH = str(final_temp_out)
            FlashNpmBuilderApp.ACTIVE_TEMP_ID = temp_id

            self.root.after(0, self._cleanup_anim)
            self.root.after(0, self.update_temp_progress, 100)
            self.root.after(0, self.log_temp_terminal, "\n=== Temp Build Ready & Live ===", 'success')
            self.root.after(0, self.log_temp_terminal, f"Live folder: {final_temp_out}")

            local_url = f"http://localhost:{self.current_port}/{temp_id}/"
            lan_url = f"http://{self.get_lan_ip()}:{self.current_port}/{temp_id}/"
            self.root.after(0, self.temp_local_url_var.set, local_url)
            self.root.after(0, self.temp_lan_url_var.set, lan_url)

        except Exception as e:
            err_details = traceback.format_exc()
            self.root.after(0, self.log_temp_terminal, f"\nTemp Build Exception: {e}\n{err_details}", 'error')
        finally:
            self.root.after(0, self.reset_temp_build_state)
            # Remove intermediate uncompiled workspace to save disk space
            if work_dir and work_dir.exists():
                try:
                    shutil.rmtree(work_dir, ignore_errors=True)
                except Exception:
                    pass

    def open_temp_folder(self):
        temp_dir = self.settings.get('temp_dir', str(self.app_data_root / 'temp'))
        if os.path.exists(temp_dir):
            os.startfile(temp_dir)
        else:
            messagebox.showinfo("Temp Folder", f"Temp directory is located at:\n{temp_dir}")

    def scan_and_detect_restored_builds(self, show_dialog=True):
        """Scans the builds directory for any restored project folders or ZIP archives

        that were recovered from the Recycle Bin and restores them into builds.json.
        """
        builds_dir = Path(self.settings['builds_dir'])
        if not builds_dir.exists():
            if show_dialog:
                messagebox.showinfo("Detect Builds", "Builds directory does not exist yet.")
            return

        builds_json = builds_dir / 'builds.json'
        known_builds = []
        if builds_json.exists():
            try:
                with open(builds_json, 'r', encoding='utf-8') as f:
                    known_builds = json.load(f)
            except Exception:
                known_builds = []

        known_paths = {os.path.abspath(b.get('path', '')) for b in known_builds if b.get('path')}
        known_ids = {b.get('project_id', b.get('id', '')) for b in known_builds}

        newly_detected = 0

        # Scan for build folders inside builds_dir
        for item in builds_dir.iterdir():
            if item.is_dir():
                abs_path = os.path.abspath(str(item))
                if abs_path in known_paths:
                    continue

                folder_name = item.name
                # Check for project_id pattern like projectName_id-xxxxxxxx or id-xxxxxxxx
                match = re.search(r'(id-[a-z0-9]+)', folder_name)
                if match:
                    proj_id = match.group(1)
                    proj_name = folder_name.replace(f"_{proj_id}", "").replace(proj_id, "").strip("_-") or "Restored_Project"
                else:
                    proj_id = f"id-{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"
                    proj_name = folder_name

                # Look for matching zip archive if restored alongside
                zip_candidate = builds_dir / f"{folder_name}.zip"
                if not zip_candidate.exists():
                    zip_candidate = builds_dir / f"{proj_name}_{proj_id}.zip"

                # Detect framework if package.json or artifacts exist
                framework = "React / Web App"
                if (item / "server" / "pages").exists() or (item / "server" / "app").exists():
                    framework = "Next.js"
                elif (item / "assets").exists() or (item / "index.html").exists():
                    framework = "React / Vite"

                new_meta = {
                    "id": proj_id,
                    "name": proj_name,
                    "type": framework,
                    "path": str(item),
                    "zip_path": str(zip_candidate) if zip_candidate.exists() else "",
                    "port": self.current_port,
                    "status": "Ready",
                    "project_id": proj_id,
                    "timestamp": item.stat().st_mtime
                }
                known_builds.append(new_meta)
                known_paths.add(abs_path)
                known_ids.add(proj_id)
                newly_detected += 1

        # Save updated builds registry
        if newly_detected > 0:
            with open(builds_json, 'w', encoding='utf-8') as f:
                json.dump(known_builds, f, indent=4)

        self.refresh_builds_list()

        if show_dialog:
            if newly_detected > 0:
                messagebox.showinfo(
                    "Restored Builds Detected",
                    f"Successfully detected and restored {newly_detected} project(s) back into your Builds List!"
                )
            else:
                messagebox.showinfo(
                    "Scan Complete",
                    "No new or restored projects found in the builds directory.\n"
                    "If you restored files from the Recycle Bin, ensure they were restored to:\n"
                    f"{builds_dir}"
                )

    def refresh_builds_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        builds_json = Path(self.settings['builds_dir']) / 'builds.json'
        if builds_json.exists():
            try:
                with open(builds_json, 'r', encoding='utf-8') as f:
                    builds = json.load(f)

                lan_ip = self.get_lan_ip()
                for b in reversed(builds):
                    proj_id = b.get('project_id', b.get('id', ''))
                    local_url = f"http://localhost:{self.current_port}/{proj_id}/"
                    lan_url = f"http://{lan_ip}:{self.current_port}/{proj_id}/"
                    path_str = b.get('path', '')
                    
                    # Indicate if project folder exists on disk or is currently missing/deleted
                    exists = os.path.exists(path_str)
                    status_text = b.get('status', 'Ready') if exists else "Missing / In Bin"

                    self.tree.insert(
                        "",
                        "end",
                        iid=b['id'],
                        values=(b.get('name', 'App'), b.get('type', 'React'), status_text, local_url, lan_url, path_str)
                    )
            except Exception as e:
                print(f"Error loading builds: {e}")

    def on_tree_double_click(self, event):
        self.open_selected_build()

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def open_selected_build(self):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            url = item['values'][3]
            webbrowser.open(url)

    def open_selected_project_location(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select Build", "Please select a build from the list.")
            return

        project_id = selected[0]
        builds_json = Path(self.settings['builds_dir']) / 'builds.json'

        if builds_json.exists():
            try:
                with open(builds_json, 'r', encoding='utf-8') as f:
                    builds = json.load(f)

                for b in builds:
                    if b.get('id') == project_id:
                        p_path = b.get('path', '')
                        if os.path.exists(p_path):
                            os.startfile(p_path)
                            return
                        else:
                            # Parent directory
                            parent = str(Path(p_path).parent)
                            if os.path.exists(parent):
                                os.startfile(parent)
                                return
                messagebox.showwarning("Not Found", "Project path could not be located on disk.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open project location: {e}")

    def copy_selected_local_url(self):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            url = item['values'][3]
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            messagebox.showinfo("Copied", f"Local URL copied to clipboard:\n{url}")

    def copy_lan_url(self):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            url = item['values'][4]
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            messagebox.showinfo("Copied", f"LAN URL copied to clipboard:\n{url}")

    def download_current_build(self):
        if hasattr(self, 'current_build_zip') and self.current_build_zip and os.path.exists(self.current_build_zip):
            dest = filedialog.asksaveasfilename(
                defaultextension=".zip",
                filetypes=[("ZIP Archive", "*.zip")],
                initialfile=Path(self.current_build_zip).name
            )
            if dest:
                shutil.copy2(self.current_build_zip, dest)
                messagebox.showinfo("Saved", f"Build ZIP saved to:\n{dest}")

    def download_selected_build(self):
        selected = self.tree.selection()
        if not selected: return

        project_id = selected[0]
        builds_json = Path(self.settings['builds_dir']) / 'builds.json'

        try:
            with open(builds_json, 'r', encoding='utf-8') as f:
                builds = json.load(f)

            for b in builds:
                if b['id'] == project_id:
                    zip_path = b.get('zip_path', '')
                    if os.path.exists(zip_path):
                        dest = filedialog.asksaveasfilename(
                            defaultextension=".zip",
                            filetypes=[("ZIP Archive", "*.zip")],
                            initialfile=Path(zip_path).name
                        )
                        if dest:
                            shutil.copy2(zip_path, dest)
                            messagebox.showinfo("Saved", "Build ZIP downloaded successfully.")
                    else:
                        messagebox.showerror("Missing Archive", "ZIP archive for this build was not found on disk.")
                    break
        except Exception as e:
            messagebox.showerror("Error", f"Failed to download build: {e}")

    def delete_selected_build(self):
        selected = self.tree.selection()
        if not selected: return

        if not messagebox.askyesno(
            "Move to Recycle Bin",
            "Are you sure you want to delete this build?\n"
            "This will safely move the build files and archive to your Windows Recycle Bin."
        ):
            return

        project_id = selected[0]
        builds_json = Path(self.settings['builds_dir']) / 'builds.json'

        try:
            with open(builds_json, 'r', encoding='utf-8') as f:
                builds = json.load(f)

            updated_builds = []
            for b in builds:
                if b['id'] == project_id:
                    path = b.get('path', '')
                    zip_path = b.get('zip_path', '')

                    # Precise recycle bin deletion
                    if HAS_SEND2TRASH:
                        if os.path.exists(path):
                            send2trash(os.path.abspath(path))
                        if os.path.exists(zip_path):
                            send2trash(os.path.abspath(zip_path))
                    else:
                        # Fallback deletion if send2trash not present
                        if os.path.exists(path):
                            shutil.rmtree(path, ignore_errors=True)
                        if os.path.exists(zip_path):
                            try:
                                os.remove(zip_path)
                            except Exception:
                                pass
                else:
                    updated_builds.append(b)

            with open(builds_json, 'w', encoding='utf-8') as f:
                json.dump(updated_builds, f, indent=4)

            self.refresh_builds_list()
            messagebox.showinfo("Deleted", "Build has been removed and sent to the Recycle Bin.")

        except Exception as e:
            messagebox.showerror("Deletion Error", f"Failed to delete build: {e}")

    def open_all_projects_dir(self):
        p_dir = self.settings['projects_dir']
        if os.path.exists(p_dir):
            os.startfile(p_dir)
        else:
            Path(p_dir).mkdir(parents=True, exist_ok=True)
            os.startfile(p_dir)

    def open_all_builds_dir(self):
        b_dir = self.settings['builds_dir']
        if os.path.exists(b_dir):
            os.startfile(b_dir)
        else:
            Path(b_dir).mkdir(parents=True, exist_ok=True)
            os.startfile(b_dir)

    def open_appdata_root(self):
        root_dir = str(self.app_data_root)
        if os.path.exists(root_dir):
            os.startfile(root_dir)
        else:
            self.app_data_root.mkdir(parents=True, exist_ok=True)
            os.startfile(root_dir)


def main():
    root = tk.Tk()

    style = ttk.Style()
    if os.name == 'nt':
        try:
            style.theme_use('vista')
        except Exception:
            pass

    app = FlashNpmBuilderApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: on_closing(root, app))
    root.mainloop()


def on_closing(root, app):
    if app.is_building or app.is_temp_building:
        if not messagebox.askyesno("Quit", "A build process is currently running. Do you want to cancel and exit?"):
            return
        if app.is_building:
            app.stop_build()
        if app.is_temp_building:
            app.stop_temp_build()

    # Ephemeral Temp & Cache Cleanup on Closing the App
    try:
        app.delete_current_temp_project()
        cache_extract = Path(app.settings.get('cache_dir', str(app.app_data_root / 'cache'))) / "extract_temp"
        if cache_extract.exists():
            shutil.rmtree(cache_extract, ignore_errors=True)
    except Exception:
        pass

    if app.httpd:
        try:
            app.httpd.shutdown()
        except Exception:
            pass

    root.destroy()


if __name__ == "__main__":
    main()
