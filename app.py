import os
import sys
import time
import subprocess
import threading
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox
from PIL import Image

try:
    import pystray
    TRAY_OK = True
except ImportError:
    TRAY_OK = False

try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

class ShutdownTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Shutdown Timer")
        self.root.geometry("450x620")
        self.root.resizable(False, False)
        
        self.bg = "#121418"
        self.card = "#1c2128"
        self.border = "#2d333b"
        self.accent = "#58a6ff"
        self.btn_green = "#238636"
        self.btn_red = "#da3633"
        self.fg = "#f0f6fc"
        self.fg_dim = "#8b949e"
        self.input_bg = "#22272e"
        
        self.root.configure(bg=self.bg)
        
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "app_icon.ico")
        self.png_path = os.path.join(base_dir, "app_icon.png")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        self.running = False
        self.total_secs = 0
        self.target_dt = None
        self.worker = None
        self.stop_flag = threading.Event()
        
        self.h_val = tk.StringVar(value="8")
        self.m_val = tk.StringVar(value="0")
        self.s_val = tk.StringVar(value="0")
        self.force_val = tk.BooleanVar(value=True)
        self.mode_val = tk.StringVar(value="shutdown")
        
        self.tray = None
        self.minimized = False

        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        top = tk.Frame(self.root, bg=self.bg)
        top.pack(fill="x", padx=20, pady=(18, 8))

        lbl_title = tk.Label(top, text="⚡ Auto Shutdown", font=("Segoe UI", 16, "bold"), fg=self.fg, bg=self.bg)
        lbl_title.pack(anchor="w")
        lbl_sub = tk.Label(top, text="Simple, lightweight power scheduler", font=("Segoe UI", 9), fg=self.fg_dim, bg=self.bg)
        lbl_sub.pack(anchor="w", pady=(2, 0))

        display_box = tk.Frame(self.root, bg=self.card, highlightbackground=self.border, highlightthickness=1)
        display_box.pack(fill="x", padx=20, pady=8)

        badge = tk.Frame(display_box, bg=self.card)
        badge.pack(fill="x", padx=15, pady=(12, 0))

        self.dot = tk.Label(badge, text="●", font=("Segoe UI", 9), fg="#3fb950", bg=self.card)
        self.dot.pack(side="left")
        self.status_txt = tk.Label(badge, text="READY", font=("Segoe UI", 9, "bold"), fg="#3fb950", bg=self.card)
        self.status_txt.pack(side="left", padx=5)

        self.clock_lbl = tk.Label(display_box, text="08:00:00", font=("Consolas", 34, "bold"), fg=self.fg, bg=self.card)
        self.clock_lbl.pack(pady=(6, 2))

        self.eta_txt = tk.Label(display_box, text="Target: None", font=("Segoe UI", 9), fg=self.fg_dim, bg=self.card)
        self.eta_txt.pack(pady=(0, 12))

        time_card = tk.Frame(self.root, bg=self.card, highlightbackground=self.border, highlightthickness=1)
        time_card.pack(fill="x", padx=20, pady=8)

        tk.Label(time_card, text="DURATION", font=("Segoe UI", 9, "bold"), fg=self.fg_dim, bg=self.card).pack(anchor="w", padx=15, pady=(10, 5))

        inputs_wrap = tk.Frame(time_card, bg=self.card)
        inputs_wrap.pack(fill="x", padx=15, pady=(0, 10))

        def make_box(parent, var, label):
            box = tk.Frame(parent, bg=self.input_bg, highlightbackground=self.border, highlightthickness=1, padx=4, pady=4)
            box.pack(side="left", expand=True, fill="x", padx=3)
            
            e = tk.Entry(box, textvariable=var, font=("Consolas", 14, "bold"), fg=self.accent, bg=self.input_bg, justify="center", bd=0, width=3)
            e.pack()
            tk.Label(box, text=label, font=("Segoe UI", 8), fg=self.fg_dim, bg=self.input_bg).pack()
            
            var.trace_add("write", lambda *_: self.update_display())
            return e

        self.ent_h = make_box(inputs_wrap, self.h_val, "HOURS")
        self.ent_m = make_box(inputs_wrap, self.m_val, "MINS")
        self.ent_s = make_box(inputs_wrap, self.s_val, "SECS")

        chips_wrap = tk.Frame(time_card, bg=self.card)
        chips_wrap.pack(fill="x", padx=15, pady=(0, 12))

        for text, h, m in [("30m", 0, 30), ("1h", 1, 0), ("2h", 2, 0), ("4h", 4, 0), ("8h", 8, 0), ("12h", 12, 0)]:
            btn = tk.Button(
                chips_wrap,
                text=text,
                font=("Segoe UI", 8, "bold"),
                fg=self.fg,
                bg="#252c35",
                activebackground="#313a46",
                activeforeground=self.fg,
                relief="flat",
                bd=0,
                pady=4,
                cursor="hand2",
                command=lambda hrs=h, mins=m: self.apply_preset(hrs, mins)
            )
            btn.pack(side="left", padx=2, expand=True, fill="x")

        cfg_card = tk.Frame(self.root, bg=self.card, highlightbackground=self.border, highlightthickness=1)
        cfg_card.pack(fill="x", padx=20, pady=8)

        tk.Label(cfg_card, text="OPTIONS", font=("Segoe UI", 9, "bold"), fg=self.fg_dim, bg=self.card).pack(anchor="w", padx=15, pady=(8, 4))

        modes_row = tk.Frame(cfg_card, bg=self.card)
        modes_row.pack(fill="x", padx=15, pady=(0, 4))

        for text, val in [("Shutdown", "shutdown"), ("Restart", "restart"), ("Sleep", "sleep")]:
            rb = tk.Radiobutton(
                modes_row,
                text=text,
                value=val,
                variable=self.mode_val,
                font=("Segoe UI", 9),
                fg=self.fg,
                bg=self.card,
                activebackground=self.card,
                activeforeground=self.accent,
                selectcolor=self.input_bg,
                cursor="hand2"
            )
            rb.pack(side="left", padx=(0, 12))

        force_box = tk.Checkbutton(
            cfg_card,
            text="Force close running apps without prompting",
            variable=self.force_val,
            font=("Segoe UI", 8),
            fg="#f85149",
            bg=self.card,
            activebackground=self.card,
            activeforeground="#f85149",
            selectcolor=self.input_bg,
            cursor="hand2"
        )
        force_box.pack(anchor="w", padx=15, pady=(0, 8))

        ctrl_frame = tk.Frame(self.root, bg=self.bg)
        ctrl_frame.pack(fill="x", padx=20, pady=(10, 10))

        self.btn_start = tk.Button(
            ctrl_frame,
            text="START TIMER",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg=self.btn_green,
            activebackground="#2ea043",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            pady=9,
            cursor="hand2",
            command=self.start
        )
        self.btn_start.pack(fill="x", pady=(0, 5))

        row2 = tk.Frame(ctrl_frame, bg=self.bg)
        row2.pack(fill="x")

        self.btn_cancel = tk.Button(
            row2,
            text="Cancel / Stop",
            font=("Segoe UI", 9),
            fg=self.fg,
            bg=self.card,
            activebackground=self.btn_red,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            pady=6,
            state="disabled",
            cursor="hand2",
            command=self.cancel
        )
        self.btn_cancel.pack(side="left", expand=True, fill="x", padx=(0, 3))

        self.btn_tray = tk.Button(
            row2,
            text="Minimize to Tray",
            font=("Segoe UI", 9),
            fg=self.fg_dim,
            bg=self.card,
            activebackground=self.input_bg,
            activeforeground=self.fg,
            relief="flat",
            bd=0,
            pady=6,
            cursor="hand2",
            command=self.to_tray
        )
        self.btn_tray.pack(side="right", expand=True, fill="x", padx=(3, 0))

        self.update_display()

    def parse_seconds(self):
        try:
            h = int(self.h_val.get() or 0)
            m = int(self.m_val.get() or 0)
            s = int(self.s_val.get() or 0)
            return max(0, h * 3600 + m * 60 + s)
        except ValueError:
            return 0

    def apply_preset(self, h, m):
        if self.running:
            return
        self.h_val.set(str(h))
        self.m_val.set(str(m))
        self.s_val.set("0")
        self.update_display()

    def update_display(self):
        if self.running:
            return
        total = self.parse_seconds()
        h, m, s = total // 3600, (total % 3600) // 60, total % 60
        self.clock_lbl.config(text=f"{h:02d}:{m:02d}:{s:02d}")
        
        if total > 0:
            target = datetime.now() + timedelta(seconds=total)
            action = self.mode_val.get().capitalize()
            self.eta_txt.config(text=f"Will {action} at: {target.strftime('%I:%M:%S %p (%b %d)')}")
        else:
            self.eta_txt.config(text="Target: None")

    def start(self):
        secs = self.parse_seconds()
        if secs <= 0:
            messagebox.showwarning("Warning", "Please set a duration greater than 0.")
            return

        self.total_secs = secs
        self.target_dt = datetime.now() + timedelta(seconds=secs)
        self.running = True
        self.stop_flag.clear()

        self.btn_start.config(state="disabled", bg="#1b4728", text="RUNNING...")
        self.btn_cancel.config(state="normal", bg=self.btn_red, fg="#ffffff")
        for ent in [self.ent_h, self.ent_m, self.ent_s]:
            ent.config(state="disabled")

        self.dot.config(fg=self.accent)
        self.status_txt.config(text="COUNTING DOWN", fg=self.accent)
        self.clock_lbl.config(fg=self.accent)

        self.worker = threading.Thread(target=self.tick_loop, daemon=True)
        self.worker.start()

    def tick_loop(self):
        t0 = time.time()
        while not self.stop_flag.is_set():
            passed = int(time.time() - t0)
            left = max(0, self.total_secs - passed)

            self.root.after(0, self.render_tick, left)
            if left <= 0:
                self.root.after(0, self.trigger_action)
                break
            time.sleep(0.5)

    def render_tick(self, left):
        if not self.running:
            return
        h, m, s = left // 3600, (left % 3600) // 60, left % 60
        self.clock_lbl.config(text=f"{h:02d}:{m:02d}:{s:02d}")
        if self.target_dt:
            self.eta_txt.config(text=f"Target: {self.target_dt.strftime('%I:%M:%S %p')}")

        if self.tray and self.minimized:
            self.tray.title = f"Shutdown in {h:02d}:{m:02d}:{s:02d}"

    def trigger_action(self):
        self.running = False
        mode = self.mode_val.get()
        force = self.force_val.get()

        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        try:
            if mode == "shutdown":
                cmd = ["shutdown", "/s"]
                if force:
                    cmd.append("/f")
                cmd.extend(["/t", "0"])
                subprocess.run(cmd, creationflags=flags)
            elif mode == "restart":
                cmd = ["shutdown", "/r"]
                if force:
                    cmd.append("/f")
                cmd.extend(["/t", "0"])
                subprocess.run(cmd, creationflags=flags)
            elif mode == "sleep":
                subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], creationflags=flags)
        except Exception as err:
            messagebox.showerror("Error", f"Could not execute {mode}: {err}")

        self.reset_state()

    def cancel(self):
        if self.running:
            self.stop_flag.set()
            self.running = False

        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            subprocess.run(["shutdown", "/a"], creationflags=flags, capture_output=True)
        except Exception:
            pass

        self.reset_state()
        messagebox.showinfo("Stopped", "Scheduled power action has been cancelled.")

    def reset_state(self):
        self.running = False
        self.btn_start.config(state="normal", bg=self.btn_green, text="START TIMER")
        self.btn_cancel.config(state="disabled", bg=self.card, fg=self.fg)
        for ent in [self.ent_h, self.ent_m, self.ent_s]:
            ent.config(state="normal")
            
        self.dot.config(fg="#3fb950")
        self.status_txt.config(text="READY", fg="#3fb950")
        self.clock_lbl.config(fg=self.fg)
        self.update_display()

    def to_tray(self):
        if not TRAY_OK:
            self.root.iconify()
            return
        
        self.root.withdraw()
        self.minimized = True

        img = None
        if os.path.exists(self.png_path):
            try:
                img = Image.open(self.png_path)
            except Exception:
                pass
        if not img:
            img = Image.new('RGB', (64, 64), color=(35, 134, 54))

        menu = pystray.Menu(
            pystray.MenuItem("Show Window", self.from_tray, default=True),
            pystray.MenuItem("Cancel Shutdown", self.cancel),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self.quit_all)
        )

        self.tray = pystray.Icon("ShutdownTimer", img, "Auto Shutdown Timer", menu)
        threading.Thread(target=self.tray.run, daemon=True).start()

    def from_tray(self, icon=None, item=None):
        if self.tray:
            self.tray.stop()
            self.tray = None
        self.minimized = False
        self.root.after(0, self.root.deiconify)

    def quit_all(self, icon=None, item=None):
        if self.tray:
            self.tray.stop()
        if self.running:
            self.cancel()
        self.root.destroy()
        sys.exit(0)

    def on_close(self):
        if self.running:
            ans = messagebox.askyesno(
                "Timer Active",
                "A countdown is currently active.\n\nMinimize to tray instead of stopping?"
            )
            if ans:
                self.to_tray()
                return
            self.cancel()
        self.quit_all()

if __name__ == "__main__":
    root = tk.Tk()
    app = ShutdownTimer(root)
    root.mainloop()
