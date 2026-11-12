#!/usr/bin/env python3
"""Kairos desktop agent. Supports Python 3.8+ on Linux and Windows."""
import argparse
import json
import logging
import os
import platform
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from PIL import ImageGrab

APP_NAME = "Kairos"
VERSION = "0.2.0"
ROOT = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share") / APP_NAME
CONFIG_PATH = ROOT / "config.dat"
PENDING = ROOT / "pending"
LOG = ROOT / "kairos.log"
_instance_handle = None
ROOT.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(LOG), level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")


def protect_config(raw):
    if sys.platform == "win32":
        import win32crypt
        return win32crypt.CryptProtectData(raw, APP_NAME, None, None, None, 0)
    return raw


def unprotect_config(raw):
    if sys.platform == "win32":
        import win32crypt
        return win32crypt.CryptUnprotectData(raw, None, None, None, 0)[1]
    return raw


def configure():
    import tkinter as tk
    from tkinter import messagebox
    ROOT.mkdir(parents=True, exist_ok=True)
    window = tk.Tk()
    window.title("Configurar Kairos")
    window.resizable(False, False)
    tk.Label(window, text="URL da API de programação").grid(row=0, column=0, padx=12, pady=(12, 2), sticky="w")
    api = tk.Entry(window, width=62)
    api.grid(row=1, column=0, padx=12)
    tk.Label(window, text="Token do computador (emitido pela intranet)").grid(row=2, column=0, padx=12, pady=(8, 2), sticky="w")
    token = tk.Entry(window, width=62, show="•")
    token.grid(row=3, column=0, padx=12)
    tk.Label(window, text="CA local do Olympus (opcional; ex.: /tmp/kairos-dev-root.crt)").grid(row=4, column=0, padx=12, pady=(8, 2), sticky="w")
    ca_bundle = tk.Entry(window, width=62)
    ca_bundle.grid(row=5, column=0, padx=12)

    def save():
        values = {"api_url": api.get().strip(), "token": token.get().strip(), "ca_bundle": ca_bundle.get().strip() or None}
        if not values["api_url"].startswith(("https://", "http://127.0.0.1", "http://localhost")) or not values["token"]:
            messagebox.showerror("Kairos", "Informe uma URL válida e o token.")
            return
        CONFIG_PATH.write_bytes(protect_config(json.dumps(values).encode("utf-8")))
        try:
            os.chmod(CONFIG_PATH, 0o600)
        except OSError:
            pass
        window.destroy()

    tk.Button(window, text="Salvar e iniciar", command=save).grid(row=4, column=0, padx=12, pady=12, sticky="e")
    window.mainloop()


def load_config():
    if not CONFIG_PATH.exists():
        return None
    return json.loads(unprotect_config(CONFIG_PATH.read_bytes()).decode("utf-8"))


def install_startup():
    if sys.platform == "win32":
        import winreg
        command = '"{}"'.format(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
    elif sys.platform == "linux":
        autostart = Path.home() / ".config" / "autostart"
        autostart.mkdir(parents=True, exist_ok=True)
        command = '"{}"'.format(sys.executable) if getattr(sys, "frozen", False) else '"{}" "{}"'.format(sys.executable, os.path.abspath(__file__))
        entry = "[Desktop Entry]\nType=Application\nName=Kairos\nExec={}".format(command)
        (autostart / "kairos.desktop").write_text(entry, encoding="utf-8")


def acquire_instance_lock():
    global _instance_handle
    if sys.platform == "win32":
        import ctypes
        kernel = ctypes.windll.kernel32
        _instance_handle = kernel.CreateMutexW(None, True, "Local\\KairosAgent")
        return _instance_handle and kernel.GetLastError() != 183
    try:
        import fcntl
        _instance_handle = open(ROOT / "agent.lock", "w")
        fcntl.flock(_instance_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except (IOError, OSError):
        return False


class Agent:
    def __init__(self, config):
        self.config = config
        self.stop_event = threading.Event()
        self.status_lock = threading.Lock()
        self.status = "Iniciando"
        ROOT.mkdir(parents=True, exist_ok=True)
        PENDING.mkdir(parents=True, exist_ok=True)

    def set_status(self, value):
        with self.status_lock:
            self.status = value

    def capture(self, occurrence):
        key = "{}-{}".format(occurrence["schedule_id"], occurrence["occurrence_on"])
        image_path = PENDING / (key + ".png")
        meta_path = PENDING / (key + ".json")
        if image_path.exists():
            return
        image = ImageGrab.grab(all_screens=True)
        temp_path = image_path.with_suffix(".tmp")
        image.save(str(temp_path), format="PNG")
        os.replace(str(temp_path), str(image_path))
        metadata = {"occurrence": occurrence, "captured_at": datetime.now(timezone.utc).isoformat(),
                    "computer_name": platform.node(), "agent_version": VERSION}
        meta_path.write_text(json.dumps(metadata), encoding="utf-8")
        logging.info("Captured occurrence %s", key)

    def send_pending(self, session):
        for meta_path in PENDING.glob("*.json"):
            image_path = meta_path.with_suffix(".png")
            if not image_path.exists():
                continue
            try:
                metadata = json.loads(meta_path.read_text(encoding="utf-8"))
                occurrence = metadata["occurrence"]
                upload_url = self.config["api_url"].rsplit("/", 1)[0] + "/submissions"
                with image_path.open("rb") as image_file:
                    response = session.post(upload_url, data={
                        "schedule_id": occurrence["schedule_id"],
                        "occurrence_on": occurrence["occurrence_on"],
                        "captured_at": metadata["captured_at"],
                        "computer_name": metadata["computer_name"],
                        "agent_version": metadata["agent_version"],
                    }, files={"image": (image_path.name, image_file, "image/png")}, timeout=60)
                response.raise_for_status()
                (PENDING / (image_path.stem + ".sent")).write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
                logging.info("Submission accepted: %s", image_path.stem)
            except Exception:
                logging.exception("Pending upload failed: %s", image_path.name)

    def run(self):
        install_startup()
        session = requests.Session()
        session.headers["Authorization"] = "Bearer " + self.config["token"]
        session.verify = self.config.get("ca_bundle") or True
        next_poll = 0
        occurrences = []
        captured = set()
        while not self.stop_event.is_set():
            now = time.time()
            if now >= next_poll:
                try:
                    response = session.get(self.config["api_url"], timeout=20)
                    response.raise_for_status()
                    payload = response.json()
                    occurrences = payload.get("occurrences", [])
                    next_poll = now + int(payload.get("poll_interval_seconds", 1800))
                    self.set_status("Sincronizado às " + datetime.now().strftime("%H:%M"))
                except Exception:
                    logging.exception("Schedule poll failed")
                    next_poll = now + 60
                    self.set_status("Sem conexão; nova tentativa em 1 min")
            self.send_pending(session)
            for occurrence in occurrences:
                key = (occurrence["schedule_id"], occurrence["occurrence_on"])
                at = datetime.fromisoformat(occurrence["scheduled_at"].replace("Z", "+00:00")).timestamp()
                if key not in captured and at <= time.time() <= at + 90:
                    try:
                        self.capture(occurrence)
                        captured.add(key)
                        self.send_pending(session)
                    except Exception:
                        logging.exception("Capture failed for %s", key)
                        self.set_status("Falha na captura; consulte o log")
            self.stop_event.wait(5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--configure", action="store_true")
    parser.add_argument("--background", action="store_true")
    args = parser.parse_args()
    if args.configure or not CONFIG_PATH.exists():
        configure()
    config = load_config()
    if not config:
        return 2
    if not acquire_instance_lock():
        return 0
    agent = Agent(config)
    if args.background:
        agent.run()
        return 0
    try:
        import pystray
        from PIL import Image, ImageDraw
        icon_image = Image.new("RGB", (64, 64), "#254f76")
        draw = ImageDraw.Draw(icon_image)
        draw.text((15, 18), "K", fill="white")
        threading.Thread(target=agent.run, daemon=True).start()
        icon = pystray.Icon(APP_NAME, icon_image, APP_NAME, menu=pystray.Menu(
            pystray.MenuItem("Abrir pasta de capturas", lambda: os.startfile(str(PENDING)) if os.name == "nt" else None),
            pystray.MenuItem("Configurar", lambda: configure()),
            pystray.MenuItem("Sair", lambda: icon.stop())))
        icon.run()
    except ImportError:
        agent.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
