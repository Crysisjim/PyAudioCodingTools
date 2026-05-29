# main.py - PyAudioCodingTools v2.4
import customtkinter as ctk
import traceback
import sys
import os
import datetime

try:
    from tkinterdnd2 import TkinterDnD
except ImportError:
    TkinterDnD = None

from gui import PyAudioCodingTools

CRASH_LOG_FILE = "pyaudiocodingtools_crash.log"

def write_crash_log(exc_type, exc_value, exc_tb):
    """Écrit un crash log détaillé à côté de l'exécutable."""
    try:
        # Déterminer le dossier de l'exe ou du script
        if getattr(sys, 'frozen', False):
            log_dir = os.path.dirname(sys.executable)
        else:
            log_dir = os.path.dirname(os.path.abspath(__file__))
        
        log_path = os.path.join(log_dir, CRASH_LOG_FILE)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tb_text = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        
        # Infos système
        import platform
        sys_info = (
            f"Python: {sys.version}\n"
            f"OS: {platform.system()} {platform.release()} ({platform.version()})\n"
            f"Architecture: {platform.machine()}\n"
            f"Executable: {sys.executable}\n"
        )
        
        # Ajouter au log (append, pas écraser — garder l'historique)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*70}\n")
            f.write(f"CRASH REPORT — {timestamp}\n")
            f.write(f"{'='*70}\n\n")
            f.write(f"--- Système ---\n{sys_info}\n")
            f.write(f"--- Exception ---\n{tb_text}\n")
            
            # État du recovery file si présent
            try:
                import json
                recovery_path = os.path.join(log_dir, "pyaudiocodingtools_recovery.json")
                if os.path.exists(recovery_path):
                    with open(recovery_path, 'r', encoding='utf-8') as rf:
                        recovery = json.load(rf)
                    total = len(recovery.get('files', []))
                    done = len(recovery.get('completed', []))
                    failed = len(recovery.get('failed', []))
                    f.write(f"--- État du batch ---\n")
                    f.write(f"Fichiers total: {total}, Terminés: {done}, Échoués: {failed}, Restants: {total-done-failed}\n\n")
            except: pass
        
        print(f"Crash log écrit dans : {log_path}")
    except Exception as log_error:
        print(f"Impossible d'écrire le crash log : {log_error}")

sys.excepthook = write_crash_log

if __name__ == "__main__":
    # Set AppUserModelID BEFORE creating window — fixes taskbar icon on Windows
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Crysisjim.PyAudioCodingTools.2.4')
    except Exception:
        pass

    try:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        if TkinterDnD is not None:
            root = TkinterDnD.Tk()
        else:
            root = ctk.CTk()
            
        app = PyAudioCodingTools(root)
        root.mainloop()
        
    except Exception as e:
        write_crash_log(type(e), e, e.__traceback__)
        print(f"Erreur fatale : {e}\nDétails dans {CRASH_LOG_FILE}")
        sys.exit(1)
