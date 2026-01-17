import customtkinter as ctk
import pyperclip
import keyboard
import threading
import sqlite3
import time
import pystray
from PIL import Image, ImageDraw
import sys
import os

# --- 1. SETUP DATA PATH (The Fix) ---
# We locate the authorized "AppData" folder for the user
APP_NAME = "SmartClipboardPro"
if os.name == 'nt':
    data_dir = os.path.join(os.getenv('APPDATA'), APP_NAME)
else:
    data_dir = os.path.join(os.path.expanduser("~"), ".local", "share", APP_NAME)

# Create the folder if it doesn't exist
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

DB_PATH = os.path.join(data_dir, "clipboard_history.db")

# --- 2. DATABASE ENGINE ---
class Database:
    def __init__(self):
        # We now connect to the DB in the safe folder
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT UNIQUE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def add_clip(self, text):
        try:
            self.cursor.execute("DELETE FROM history WHERE content = ?", (text,))
            self.cursor.execute("INSERT INTO history (content) VALUES (?)", (text,))
            self.conn.commit()
        except Exception as e:
            print(f"DB Error: {e}")

    def get_clips(self, search_query=""):
        if search_query:
            self.cursor.execute("SELECT content FROM history WHERE content LIKE ? ORDER BY id DESC LIMIT 50", ('%' + search_query + '%',))
        else:
            self.cursor.execute("SELECT content FROM history ORDER BY id DESC LIMIT 50")
        return [row[0] for row in self.cursor.fetchall()]

db = Database()

# --- 3. THE UI ---
class QuickPasteApp(ctk.CTkToplevel):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.overrideredirect(True) 
        self.attributes("-topmost", True)
        self.geometry("400x500")
        self.configure(fg_color="#1a1a1a")
        
        self.search_var = ctk.StringVar()
        self.search_var.trace("w", self.update_list)
        self.entry = ctk.CTkEntry(
            self, placeholder_text="Search clips...", 
            textvariable=self.search_var,
            font=("Segoe UI", 14), height=40, border_width=0, fg_color="#333"
        )
        self.entry.pack(fill="x", padx=5, pady=5)
        self.entry.bind("<Escape>", self.hide_window)

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        self.buttons = []
        self.refresh_ui()

    def show_window(self):
        try:
            x, y = self.winfo_pointerxy()
            self.geometry(f"+{x}+{y}")
        except:
            pass
        self.deiconify()
        self.entry.focus_set()
        self.entry.delete(0, 'end')
        self.refresh_ui()

    def hide_window(self, event=None):
        self.withdraw()

    def refresh_ui(self):
        for btn in self.buttons:
            btn.destroy()
        self.buttons = []

        query = self.search_var.get()
        clips = db.get_clips(query)

        for clip in clips:
            display_text = clip.replace("\n", " ")[:45] + "..." if len(clip) > 45 else clip
            btn = ctk.CTkButton(
                self.scroll_frame, 
                text=display_text, 
                anchor="w", 
                fg_color="transparent", 
                hover_color="#0078D7",
                height=35,
                command=lambda c=clip: self.paste_clip(c)
            )
            btn.pack(fill="x")
            self.buttons.append(btn)

    def update_list(self, *args):
        self.refresh_ui()

    def paste_clip(self, content):
        pyperclip.copy(content)
        self.hide_window()
        time.sleep(0.1)
        keyboard.send("ctrl+v")

# --- 4. BACKGROUND WORKER ---
def clipboard_monitor():
    last_text = ""
    while True:
        try:
            current_text = pyperclip.paste()
            if current_text and current_text != last_text:
                last_text = current_text
                db.add_clip(current_text)
        except:
            pass
        time.sleep(0.5)

# --- 5. TRAY ICON ---
def create_tray_icon(root):
    image = Image.new('RGB', (64, 64), color=(0, 120, 215))
    d = ImageDraw.Draw(image)
    d.rectangle([16, 16, 48, 48], fill="white")
    
    def quit_app(icon, item):
        icon.stop()
        root.quit()
        sys.exit()

    icon = pystray.Icon("DittoClone", image, "Smart Clipboard", menu=pystray.Menu(
        pystray.MenuItem("Exit", quit_app)
    ))
    return icon

if __name__ == "__main__":
    root = ctk.CTk()
    root.withdraw()
    app_window = QuickPasteApp()
    threading.Thread(target=clipboard_monitor, daemon=True).start()
    keyboard.add_hotkey("ctrl+shift+v", app_window.show_window)
    tray = create_tray_icon(root)
    threading.Thread(target=tray.run, daemon=True).start()
    root.mainloop()
