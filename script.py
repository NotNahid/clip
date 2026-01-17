import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import time
import pyperclip
import os
import json
import datetime
import keyboard  # For Global Hotkeys
import subprocess

# --- 0. CONFIGURATION MANAGER (The Brain) ---
CONFIG_FILE = "app_config.json"
DEFAULT_CONFIG = {
    "save_path": os.path.expanduser("~/Documents"),
    "hotkey": "ctrl+shift+z",
    "clipboard_active": False
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return DEFAULT_CONFIG

def save_config(config_data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)

# Global Config Object
APP_CONFIG = load_config()

# --- 1. CLIPBOARD HISTORY WINDOW (The UI Popup) ---
class ClipboardUI(ctk.CTkToplevel):
    def __init__(self, history):
        super().__init__()
        self.title("Clipboard History")
        self.geometry("400x500")
        self.attributes("-topmost", True) # Keep window on top
        
        self.label = ctk.CTkLabel(self, text="Recent Clips", font=("Arial", 20, "bold"))
        self.label.pack(pady=10)

        # Scrollable list
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=380, height=450)
        self.scroll_frame.pack(padx=10, pady=10, fill="both", expand=True)

        for item in reversed(history):
            btn = ctk.CTkButton(
                self.scroll_frame, 
                text=item[:40] + "..." if len(item) > 40 else item, 
                command=lambda t=item: self.copy_to_clipboard(t),
                anchor="w",
                fg_color="#2B2B2B"
            )
            btn.pack(fill="x", pady=2)

    def copy_to_clipboard(self, text):
        pyperclip.copy(text)
        self.destroy() # Close window after selection

# --- 2. BACKEND MODULES ---
class ClipboardManager:
    def __init__(self):
        self.active = False
        self.thread = None
        self.last_text = ""
        self.history = []
        
        # Setup Hotkey Listener
        try:
            keyboard.add_hotkey(APP_CONFIG["hotkey"], self.open_history_ui)
        except:
            print("Could not register hotkey (requires Admin on some systems)")

    def start(self):
        if not self.active:
            self.active = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.active = False

    def open_history_ui(self):
        # Must run on main thread, usually tricky in Tkinter from background thread
        # For simplicity in this structure, we trigger it only if history exists
        if self.history:
            # Note: In a complex app, we'd use a queue. Here we assume thread safety works for simple UI spawn.
            ClipboardUI(self.history)

    def _run_loop(self):
        while self.active:
            try:
                current_text = pyperclip.paste()
                if current_text and current_text != self.last_text:
                    self.last_text = current_text
                    self.history.append(current_text)
                    self._save_to_file(current_text)
                    
                    if len(self.history) > 20: 
                        self.history.pop(0)
            except:
                pass
            time.sleep(1.0)

    def _save_to_file(self, text):
        folder = APP_CONFIG["save_path"]
        file_path = os.path.join(folder, "clipboard_history.txt")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}]\n{text}\n{'-'*30}\n")
        except Exception as e:
            print(f"Save Error: {e}")

# Initialize Engines
clipboard_engine = ClipboardManager()

# --- 3. FRONTEND DASHBOARD ---

class ProductivitySuite(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("Productivity Station Pro")
        self.geometry("900x600")
        ctk.set_appearance_mode("Dark")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo = ctk.CTkLabel(self.sidebar, text="⚡ PRO SUITE", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Main Area
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # CLIPBOARD CARD
        self.create_clipboard_card()

    def create_clipboard_card(self):
        card = ctk.CTkFrame(self.main_frame, height=150)
        card.pack(fill="x", pady=10)
        
        # Title
        lbl = ctk.CTkLabel(card, text="📋 Clipboard Manager", font=ctk.CTkFont(size=18, weight="bold"))
        lbl.pack(anchor="w", padx=20, pady=(15, 5))

        # Status Label
        self.lbl_path = ctk.CTkLabel(card, text=f"Saving to: {APP_CONFIG['save_path']}")
        self.lbl_path.pack(anchor="w", padx=20, pady=5)

        # Controls Row
        ctrl_frame = ctk.CTkFrame(card, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=10, pady=10)

        # 1. Change Folder Button
        btn_folder = ctk.CTkButton(ctrl_frame, text="📂 Set Folder", width=100, command=self.change_folder)
        btn_folder.pack(side="left", padx=10)

        # 2. Open Text File Button
        btn_open = ctk.CTkButton(ctrl_frame, text="📄 Open Log", width=100, fg_color="#555", command=self.open_log_file)
        btn_open.pack(side="left", padx=10)

        # 3. Toggle Switch
        self.switch_var = ctk.StringVar(value="on" if APP_CONFIG["clipboard_active"] else "off")
        self.switch = ctk.CTkSwitch(ctrl_frame, text="Active", command=self.toggle_clipboard, variable=self.switch_var, onvalue="on", offvalue="off")
        self.switch.pack(side="right", padx=20)
        
        # Auto-start if it was on previously
        if APP_CONFIG["clipboard_active"]:
            self.switch.select()
            clipboard_engine.start()

    def change_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            APP_CONFIG["save_path"] = folder
            save_config(APP_CONFIG)
            self.lbl_path.configure(text=f"Saving to: {folder}")

    def open_log_file(self):
        file_path = os.path.join(APP_CONFIG["save_path"], "clipboard_history.txt")
        if os.path.exists(file_path):
            os.startfile(file_path) # Windows only command
        else:
            messagebox.showinfo("Info", "No history file created yet.")

    def toggle_clipboard(self):
        if self.switch.get() == "on":
            APP_CONFIG["clipboard_active"] = True
            clipboard_engine.start()
        else:
            APP_CONFIG["clipboard_active"] = False
            clipboard_engine.stop()
        save_config(APP_CONFIG)

if __name__ == "__main__":
    app = ProductivitySuite()
    app.mainloop()
