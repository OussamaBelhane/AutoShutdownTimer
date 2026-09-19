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
        self.root.geometry("480x720")
        self.root.resizable(False, False)
        
        self.bg = "#0B0F17"
        self.card = "#131B26"
        self.card_highlight = "#182232"
        self.border = "#1E2C3F"
        self.border_focus = "#388BFD"
        self.accent = "#388BFD"
        self.accent_glow = "#58A6FF"
        self.btn_green = "#238636"
        self.btn_green_hover = "#2EA043"
        self.btn_red = "#DA3633"
        self.btn_red_hover = "#F85149"
        self.fg = "#F0F6FC"
        self.fg_dim = "#7D8590"
        self.fg_sub = "#A0AEC0"
        self.input_bg = "#0D131C"
        self.chip_bg = "#1A2433"
        self.chip_hover = "#253347"
        
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
        
        self.updating_from_calc = False
        self.updating_from_inputs = False
        
        self.h_val = tk.StringVar(value="8")
        self.m_val = tk.StringVar(value="0")
        self.s_val = tk.StringVar(value="0")
        self.force_val = tk.BooleanVar(value=True)
        self.mode_val = tk.StringVar(value="shutdown")
        
        self.size_val = tk.StringVar(value="42.8")
        self.speed_val = tk.StringVar(value="2.0")
        self.buffer_val = tk.StringVar(value="+30 min")
        
        self.tray = None
        self.minimized = False

        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def make_card(self, parent, pady=(0, 10)):
        outer = tk.Frame(parent, bg=self.border, padx=1, pady=1)
        outer.pack(fill="x", padx=16, pady=pady)
        inner = tk.Frame(outer, bg=self.card, padx=14, pady=12)
        inner.pack(fill="both", expand=True)
        return inner

    def setup_ui(self):
        header = tk.Frame(self.root, bg=self.bg)
        header.pack(fill="x", padx=16, pady=(16, 10))

        title_row = tk.Frame(header, bg=self.bg)
        title_row.pack(anchor="w")

        tk.Label(title_row, text="⚡", font=("Segoe UI Emoji", 14), fg=self.accent_glow, bg=self.bg).pack(side="left", padx=(0, 6))
        tk.Label(title_row, text="Auto Shutdown", font=("Segoe UI", 15, "bold"), fg=self.fg, bg=self.bg).pack(side="left")
        
        tag = tk.Label(title_row, text="PRO", font=("Segoe UI", 7, "bold"), fg="#000000", bg=self.accent_glow, padx=5, pady=1)
        tag.pack(side="left", padx=8)

        tk.Label(header, text="High-precision system power scheduler & download manager", font=("Segoe UI", 8), fg=self.fg_dim, bg=self.bg).pack(anchor="w", pady=(2, 0))

        c_display = self.make_card(self.root, pady=(0, 10))

        status_bar = tk.Frame(c_display, bg=self.card)
        status_bar.pack(fill="x")

        pill = tk.Frame(status_bar, bg="#11271D", padx=8, pady=3, highlightbackground="#238636", highlightthickness=1)
        pill.pack(side="left")
        self.dot = tk.Label(pill, text="●", font=("Segoe UI", 8), fg="#3FB950", bg="#11271D")
        self.dot.pack(side="left", padx=(0, 4))
        self.status_txt = tk.Label(pill, text="READY TO SCHEDULE", font=("Segoe UI", 8, "bold"), fg="#3FB950", bg="#11271D")
        self.status_txt.pack(side="left")

        self.clock_lbl = tk.Label(c_display, text="08:00:00", font=("Consolas", 36, "bold"), fg=self.fg, bg=self.card)
        self.clock_lbl.pack(pady=(10, 2))

        eta_pill = tk.Frame(c_display, bg="#0D131C", padx=10, pady=3)
        eta_pill.pack(pady=(0, 2))
        self.eta_txt = tk.Label(eta_pill, text="Target: None", font=("Segoe UI", 8), fg=self.fg_sub, bg="#0D131C")
        self.eta_txt.pack()

        c_calc = self.make_card(self.root, pady=(0, 10))

        calc_head = tk.Frame(c_calc, bg=self.card)
        calc_head.pack(fill="x", pady=(0, 8))
        tk.Label(calc_head, text="📥  DOWNLOAD TIME CALCULATOR", font=("Segoe UI", 8, "bold"), fg=self.accent_glow, bg=self.card).pack(side="left")

        calc_grid = tk.Frame(c_calc, bg=self.card)
        calc_grid.pack(fill="x", pady=(0, 8))

        def create_input_cell(parent, var, title, unit):
            wrapper = tk.Frame(parent, bg=self.border, padx=1, pady=1)
            wrapper.pack(side="left", expand=True, fill="x", padx=3)
            cell = tk.Frame(wrapper, bg=self.input_bg, padx=6, pady=6)
            cell.pack(fill="both", expand=True)

            tk.Label(cell, text=title, font=("Segoe UI", 7, "bold"), fg=self.fg_dim, bg=self.input_bg).pack(anchor="w")
            
            row = tk.Frame(cell, bg=self.input_bg)
            row.pack(fill="x", pady=(2, 0))
            e = tk.Entry(row, textvariable=var, font=("Consolas", 12, "bold"), fg=self.fg, bg=self.input_bg, bd=0, insertbackground=self.fg, width=5)
            e.pack(side="left", fill="x", expand=True)
            tk.Label(row, text=unit, font=("Segoe UI", 8, "bold"), fg=self.accent, bg=self.input_bg).pack(side="right", padx=(2, 0))

            var.trace_add("write", lambda *_: self.calc_download_time())
            return e, wrapper

        self.ent_size, self.wrap_size = create_input_cell(calc_grid, self.size_val, "FILE SIZE", "GB")
        self.ent_speed, self.wrap_speed = create_input_cell(calc_grid, self.speed_val, "DOWNLOAD SPEED", "MB/s")

        buf_wrapper = tk.Frame(calc_grid, bg=self.border, padx=1, pady=1)
        buf_wrapper.pack(side="left", expand=True, fill="x", padx=3)
        buf_cell = tk.Frame(buf_wrapper, bg=self.input_bg, padx=6, pady=4)
        buf_cell.pack(fill="both", expand=True)

        tk.Label(buf_cell, text="SAFETY BUFFER", font=("Segoe UI", 7, "bold"), fg=self.fg_dim, bg=self.input_bg).pack(anchor="w")
        
        self.buf_menu = tk.OptionMenu(buf_cell, self.buffer_val, "+15 min", "+30 min", "+45 min", "+60 min", command=lambda *_: self.calc_download_time())
        self.buf_menu.config(font=("Segoe UI", 9, "bold"), fg=self.accent_glow, bg=self.input_bg, bd=0, highlightthickness=0, activebackground=self.input_bg, activeforeground=self.accent_glow, indicatoron=0, cursor="hand2")
        self.buf_menu["menu"].config(font=("Segoe UI", 9), bg=self.card, fg=self.fg, activebackground=self.accent, activeforeground="#FFFFFF", bd=1)
        self.buf_menu.pack(fill="x", pady=(2, 0))

        info_bar = tk.Frame(c_calc, bg="#0D131C", padx=8, pady=5)
        info_bar.pack(fill="x")
        self.calc_info_lbl = tk.Label(
            info_bar,
            text="Real time: 06h 04m  |  Auto-fills: 06h 34m (+30m buffer)",
            font=("Segoe UI", 8),
            fg=self.accent_glow,
            bg="#0D131C"
        )
        self.calc_info_lbl.pack()

        c_time = self.make_card(self.root, pady=(0, 10))

        time_head = tk.Frame(c_time, bg=self.card)
        time_head.pack(fill="x", pady=(0, 8))
        tk.Label(time_head, text="⏱  MANUAL DURATION & PRESETS", font=("Segoe UI", 8, "bold"), fg=self.fg_sub, bg=self.card).pack(side="left")

        inputs_wrap = tk.Frame(c_time, bg=self.card)
        inputs_wrap.pack(fill="x", pady=(0, 8))

        def create_time_spinner(parent, var, label):
            wrapper = tk.Frame(parent, bg=self.border, padx=1, pady=1)
            wrapper.pack(side="left", expand=True, fill="x", padx=3)
            cell = tk.Frame(wrapper, bg=self.input_bg, padx=4, pady=4)
            cell.pack(fill="both", expand=True)

            e = tk.Entry(cell, textvariable=var, font=("Consolas", 14, "bold"), fg=self.accent_glow, bg=self.input_bg, justify="center", bd=0, insertbackground=self.fg, width=3)
            e.pack()
            tk.Label(cell, text=label, font=("Segoe UI", 7, "bold"), fg=self.fg_dim, bg=self.input_bg).pack()

            var.trace_add("write", lambda *_: self.on_time_input_change())
            return e, wrapper

        self.ent_h, self.wrap_h = create_time_spinner(inputs_wrap, self.h_val, "HOURS")
        self.ent_m, self.wrap_m = create_time_spinner(inputs_wrap, self.m_val, "MINS")
        self.ent_s, self.wrap_s = create_time_spinner(inputs_wrap, self.s_val, "SECS")

        chips_wrap = tk.Frame(c_time, bg=self.card)
        chips_wrap.pack(fill="x")

        for text, h, m in [("30m", 0, 30), ("1h", 1, 0), ("2h", 2, 0), ("4h", 4, 0), ("8h", 8, 0), ("12h", 12, 0)]:
            btn = tk.Button(
                chips_wrap,
                text=text,
                font=("Segoe UI", 8, "bold"),
                fg=self.fg,
                bg=self.chip_bg,
                activebackground=self.chip_hover,
                activeforeground=self.fg,
                relief="flat",
                bd=0,
                pady=4,
                cursor="hand2",
                command=lambda hrs=h, mins=m: self.apply_preset(hrs, mins)
            )
            btn.pack(side="left", padx=2, expand=True, fill="x")

        c_opt = self.make_card(self.root, pady=(0, 12))

        opt_row = tk.Frame(c_opt, bg=self.card)
        opt_row.pack(fill="x")

        for text, val in [("Shutdown", "shutdown"), ("Restart", "restart"), ("Sleep", "sleep")]:
            rb = tk.Radiobutton(
                opt_row,
                text=text,
                value=val,
                variable=self.mode_val,
                font=("Segoe UI", 8, "bold"),
                fg=self.fg,
                bg=self.card,
                activebackground=self.card,
                activeforeground=self.accent,
                selectcolor=self.input_bg,
                cursor="hand2",
                command=self.update_display
            )
            rb.pack(side="left", padx=(0, 14))

        force_box = tk.Checkbutton(
            c_opt,
            text="⚡ Force close running applications without hanging prompts",
            variable=self.force_val,
            font=("Segoe UI", 8),
            fg="#F85149",
            bg=self.card,
            activebackground=self.card,
            activeforeground="#F85149",
            selectcolor=self.input_bg,
            cursor="hand2"
        )
        force_box.pack(anchor="w", pady=(6, 0))

        ctrl_frame = tk.Frame(self.root, bg=self.bg)
        ctrl_frame.pack(fill="x", padx=16, pady=(0, 14))

        self.btn_start = tk.Button(
            ctrl_frame,
            text="▶   START TIMER & SCHEDULE",
            font=("Segoe UI", 10, "bold"),
            fg="#FFFFFF",
            bg=self.btn_green,
            activebackground=self.btn_green_hover,
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            pady=10,
            cursor="hand2",
            command=self.start
        )
        self.btn_start.pack(fill="x", pady=(0, 6))

        row2 = tk.Frame(ctrl_frame, bg=self.bg)
        row2.pack(fill="x")

        self.btn_cancel = tk.Button(
            row2,
            text="✕  Cancel / Stop",
            font=("Segoe UI", 9, "bold"),
            fg=self.fg_dim,
            bg=self.card,
            activebackground=self.btn_red,
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            pady=7,
            state="disabled",
            cursor="hand2",
            command=self.cancel
        )
        self.btn_cancel.pack(side="left", expand=True, fill="x", padx=(0, 3))

        self.btn_tray = tk.Button(
            row2,
            text="🗕  Minimize to Tray",
            font=("Segoe UI", 9),
            fg=self.fg_sub,
            bg=self.card,
            activebackground=self.chip_hover,
            activeforeground=self.fg,
            relief="flat",
            bd=0,
            pady=7,
            cursor="hand2",
            command=self.to_tray
        )
        self.btn_tray.pack(side="right", expand=True, fill="x", padx=(3, 0))

        self.calc_download_time()

    def calc_download_time(self):
        if self.running or self.updating_from_inputs:
            return
        
        try:
            s_raw = self.size_val.get().strip().replace(",", ".")
            sp_raw = self.speed_val.get().strip().replace(",", ".")
            if not s_raw or not sp_raw:
                self.calc_info_lbl.config(text="Enter size (GB) and download speed (MB/s)")
                return

            size_gb = float(s_raw)
            speed_mb = float(sp_raw)
            if size_gb <= 0 or speed_mb <= 0:
                self.calc_info_lbl.config(text="Enter positive values for size and speed")
                return

            total_mb = size_gb * 1024.0
            real_secs = int(total_mb / speed_mb)
            
            rh = real_secs // 3600
            rm = (real_secs % 3600) // 60
            rs = real_secs % 60

            buf_str = self.buffer_val.get().replace("+", "").replace(" min", "").strip()
            buf_mins = int(buf_str) if buf_str.isdigit() else 30

            total_fill_secs = real_secs + (buf_mins * 60)
            th = total_fill_secs // 3600
            tm = (total_fill_secs % 3600) // 60
            ts = total_fill_secs % 60

            self.calc_info_lbl.config(
                text=f"Real time: {rh:02d}h {rm:02d}m {rs:02d}s  |  Timer filled: {th:02d}h {tm:02d}m (+{buf_mins}m buffer)"
            )

            self.updating_from_calc = True
            self.h_val.set(str(th))
            self.m_val.set(str(tm))
            self.s_val.set(str(ts))
            self.updating_from_calc = False
            
            self.update_display()
        except ValueError:
            self.calc_info_lbl.config(text="Enter valid numbers (e.g. 42.8 GB and 2.7 MB/s)")

    def on_time_input_change(self):
        if not self.running and not self.updating_from_calc:
            self.updating_from_inputs = True
            self.update_display()
            self.updating_from_inputs = False

    def parse_seconds(self):
        try:
            h = int(self.h_val.get().strip() or 0)
            m = int(self.m_val.get().strip() or 0)
            s = int(self.s_val.get().strip() or 0)
            return max(0, h * 3600 + m * 60 + s)
        except ValueError:
            return 0

    def apply_preset(self, h, m):
        if self.running:
            return
        self.updating_from_calc = True
        self.h_val.set(str(h))
        self.m_val.set(str(m))
        self.s_val.set("0")
        self.updating_from_calc = False
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

        self.btn_start.config(state="disabled", bg="#153621", text="⏳   COUNTDOWN IN PROGRESS...")
        self.btn_cancel.config(state="normal", bg=self.btn_red, fg="#FFFFFF")
        for ent in [self.ent_h, self.ent_m, self.ent_s, self.ent_size, self.ent_speed]:
            ent.config(state="disabled")
        self.buf_menu.config(state="disabled")

        self.dot.config(fg=self.accent_glow)
        self.status_txt.config(text="ACTIVE COUNTDOWN", fg=self.accent_glow)
        self.clock_lbl.config(fg=self.accent_glow)

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
        self.btn_start.config(state="normal", bg=self.btn_green, text="▶   START TIMER & SCHEDULE")
        self.btn_cancel.config(state="disabled", bg=self.card, fg=self.fg_dim)
        for ent in [self.ent_h, self.ent_m, self.ent_s, self.ent_size, self.ent_speed]:
            ent.config(state="normal")
        self.buf_menu.config(state="normal")
            
        self.dot.config(fg="#3FB950")
        self.status_txt.config(text="READY TO SCHEDULE", fg="#3FB950")
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
