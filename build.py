import os
import sys
import subprocess

def build():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(root_dir, "app.py")
    ico = os.path.join(root_dir, "app_icon.ico")
    png = os.path.join(root_dir, "app_icon.png")

    args = [
        sys.executable,
        "-m", "PyInstaller",
        "--name=AutoShutdownTimer",
        "--onefile",
        "--noconsole",
        f"--icon={ico}",
        f"--add-data={ico};.",
        f"--add-data={png};.",
        "--clean",
        main_script
    ]

    ret = subprocess.run(args, cwd=root_dir)
    if ret.returncode == 0:
        out = os.path.join(root_dir, "dist", "AutoShutdownTimer.exe")
        print(f"\nCreated: {out}")

if __name__ == "__main__":
    build()
