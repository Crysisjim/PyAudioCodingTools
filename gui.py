# gui.py - v2.4 (Toast + FFmpeg Full Build Update + Crash Recovery + Validation + Infobulles détaillées)
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os, sys, json, time, threading, queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageTk, ImageDraw
from audio_utils import (
    get_ffmpeg_codecs, is_audio_file, validate_file_codec, get_duration, get_bitrate,
    show_audio_spectrum, process_file, show_audio_spectrum_comparison,
    get_audio_tracks, LOUDNORM_CODECS, MAX_CHANNELS, AC_MAP
)
from taskbar_utils import TaskbarController
from strings import T, set_lang, get_lang

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
except ImportError:
    TkinterDnD = None; DND_FILES = None

try:
    import pygame; pygame.mixer.init(); HAS_AUDIO = True
except (ImportError, Exception) as e:
    HAS_AUDIO = False; print(f"Info: Audio désactivé ({e})")

import shutil, glob, multiprocessing, re, subprocess
try: import requests
except ImportError: requests = None
import webbrowser

HAS_TOAST = False
_TOAST_LIB = None  # 'win11toast' or 'windows_toasts'
try:
    from win11toast import toast as _win11_toast_fn; HAS_TOAST = True; _TOAST_LIB = 'win11toast'
except ImportError:
    try:
        from windows_toasts import Toast as _WTToast, WindowsToaster as _WTToaster; HAS_TOAST = True; _TOAST_LIB = 'windows_toasts'
    except ImportError: pass

CRASH_RECOVERY_FILE = "pyaudiocodingtools_recovery.json"

def resource_path(rp):
    try: bp = sys._MEIPASS
    except: bp = os.path.abspath(".")
    return os.path.join(bp, rp)

class ToolTip:
    _all_tips = []  # Registre global pour pouvoir tout fermer
    
    def __init__(self, w, text):
        self.widget=w; self.text=text; self.tw=None; self.id=None; self.auto_hide_id=None
        w.bind("<Enter>", self._sched)
        w.bind("<Leave>", self._hide)
        w.bind("<Button-1>", self._hide)  # Clic = fermer
        # Surveiller la destruction ou le masquage du widget
        w.bind("<Unmap>", self._hide)     # Widget devient invisible (changement d'onglet)
        ToolTip._all_tips.append(self)
    
    def _sched(self, e=None):
        self._cancel()
        self.id = self.widget.after(600, self._show)
    
    def _show(self):
        self.id = None
        if self.tw: return
        # Vérifier que le widget est encore visible et que la souris est dessus
        try:
            if not self.widget.winfo_ismapped(): return
            # Vérifier position souris par rapport au widget
            mx = self.widget.winfo_pointerx(); my = self.widget.winfo_pointery()
            wx = self.widget.winfo_rootx(); wy = self.widget.winfo_rooty()
            ww = self.widget.winfo_width(); wh = self.widget.winfo_height()
            if not (wx <= mx <= wx+ww and wy <= my <= wy+wh): return
        except: return
        
        x=self.widget.winfo_rootx()+25; y=self.widget.winfo_rooty()+25
        self.tw = t = ctk.CTkToplevel(self.widget); t.wm_overrideredirect(True); t.wm_geometry(f"+{x}+{y}"); t.attributes("-topmost",True)
        ctk.CTkLabel(t, text=self.text, justify='left', fg_color='#1a1a1a', text_color='#f0f0f0', corner_radius=6, font=("Segoe UI",11), wraplength=450).pack(padx=10, pady=6)
        # Auto-disparition après 12 secondes max
        self.auto_hide_id = self.widget.after(12000, self._force_hide)
    
    def _hide(self, e=None):
        self._cancel()
        if self.tw:
            try: self.tw.destroy()
            except: pass
            self.tw=None
    
    def _force_hide(self):
        """Ferme l'infobulle même si Leave n'a pas été déclenché."""
        self.auto_hide_id = None
        if self.tw:
            try: self.tw.destroy()
            except: pass
            self.tw = None
    
    def _cancel(self):
        if self.id:
            try: self.widget.after_cancel(self.id)
            except: pass
            self.id=None
        if self.auto_hide_id:
            try: self.widget.after_cancel(self.auto_hide_id)
            except: pass
            self.auto_hide_id=None
    
    @classmethod
    def hide_all(cls):
        """Ferme toutes les infobulles actives."""
        for tip in cls._all_tips:
            tip._hide()

class PyAudioCodingTools:
    VERSION = "2.4"
    
    def __init__(self, root):
        self.root = root
        self.root.title(T('window_title', version=self.VERSION))
        self.root.update_idletasks()
        self.taskbar = TaskbarController(self.root)
        ctk.deactivate_automatic_dpi_awareness()
        self.data_lock = threading.Lock()
        self.spectrum_queue = queue.Queue()
        self.update_queue = queue.Queue(maxsize=2000)
        threading.Thread(target=self.process_spectrum_queue, daemon=True).start()
        self.check_update_queue()
        try:
            ip = resource_path(os.path.join("Assets","vivi.ico"))
            if os.path.exists(ip):
                self.root.iconbitmap(ip)  # proper Windows taskbar icon
                self.root.iconphoto(True, ImageTk.PhotoImage(Image.open(ip)))  # title bar
        except Exception as e: print(f"Icône: {e}")

        self.settings_file = "pyaudiocodingtools_settings.json"
        self.presets_file = "pyaudiocodingtools_presets.json"
        self.codec_display_map = {'aac':'AAC','ac3':'Dolby Digital','alac':'ALAC','flac':'FLAC','libmp3lame':'MP3','libopus':'Opus','pcm_s16le':'PCM 16-bit','wmav2':'WMA v2','eac3':'Dolby Digital Plus','dts':'DTS','libvorbis':'Vorbis'}
        self.codec_reverse_map = {v:k for k,v in self.codec_display_map.items()}
        self.settings = self.load_settings(); self.presets = self.load_presets()
        set_lang(self.settings.get('language', 'fr'))
        self.window_width = self.settings.get('window_width',1385); self.window_height = self.settings.get('window_height',885)
        self.root.geometry(f"{self.window_width}x{self.window_height}")
        self.theme = self.settings.get('theme','dark'); ctk.set_appearance_mode(self.theme)
        self.color_theme = self.settings.get('color_theme','green'); self.apply_safe_theme(self.color_theme)

        self.theme_var = ctk.StringVar(value=self.theme)
        self.detailed_output_var = ctk.BooleanVar(value=self.settings.get('detailed_output',False))
        self.copy_metadata_var = ctk.BooleanVar(value=self.settings.get('copy_metadata',False))
        self.loudnorm_var = ctk.BooleanVar(value=self.settings.get('loudnorm',True))
        self.dialnorm_var = ctk.BooleanVar(value=self.settings.get('dialnorm',True))
        self.compare_spectrum_var = ctk.BooleanVar(value=self.settings.get('compare_spectrum',False))
        self.mka_output_var = ctk.BooleanVar(value=self.settings.get('mka_output',True))
        self.preferred_language = self.settings.get('preferred_language', 'fre')  # Langue auto-cochée dans les sélecteurs
        self.parallel_processing_var = ctk.BooleanVar(value=self.settings.get('parallel_processing',True))
        self.surround_mode_var = ctk.StringVar(value="same")
        self.codec_var = ctk.StringVar(value=self.settings.get('codec','Dolby Digital Plus'))
        self.enable_sounds_var = ctk.BooleanVar(value=self.settings.get('enable_sounds',True))
        self.sound_volume_var = ctk.DoubleVar(value=self.settings.get('sound_volume',0.5))
        self.enable_toast_var = ctk.BooleanVar(value=self.settings.get('enable_toast', True))

        self._cancel_event = threading.Event()
        self.pause_processing = False; self.pause_event = threading.Event(); self.pause_event.set()
        self.file_queue = queue.Queue()
        self.progress_bars={}; self.progress_values={}; self.speeds={}; self.bitrates={}
        self.target_bitrates={}; self.real_bitrates={}; self.current_steps={}; self.file_indices={}; self.codec_params={}
        self.analyze_duration_combo=None; self.probe_size_combo=None; self.async_combo=None
        self.min_hard_comp_entry=None; self.first_pts_entry=None; self.resampler_combo=None
        self.loudness_params_frame=None; self.validation_label=None

        self._about_sound_played = False

        self.notebook = ctk.CTkTabview(self.root, height=50, command=lambda: ToolTip.hide_all())
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        self.ffmpeg_path_entry = ctk.CTkEntry(self.root)
        self.ffmpeg_path_entry.insert(0, self.settings.get('ffmpeg_path', self.find_executable('ffmpeg') or 'ffmpeg'))
        self.ffprobe_path_entry = ctk.CTkEntry(self.root)
        self.ffprobe_path_entry.insert(0, self.settings.get('ffprobe_path', self.find_executable('ffprobe') or 'ffprobe'))
        self.codec_list = get_ffmpeg_codecs(self)
        self.codec_display_list = [self.codec_display_map.get(c,c) for c in self.codec_list]
        self.create_tabs()
        if DND_FILES: self.file_list.drop_target_register(DND_FILES); self.file_list.dnd_bind('<<Drop>>', self.drop_files)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        threading.Thread(target=self.check_ffmpeg_version_on_startup, daemon=True).start()
        self.resize_after_id = None; self.last_width = self.root.winfo_width()
        self.root.after(100, self.change_theme)
        self.root.after(500, self.check_crash_recovery)

    @property
    def cancel_processing(self): return self._cancel_event.is_set()
    @cancel_processing.setter
    def cancel_processing(self, v):
        if v: self._cancel_event.set()
        else: self._cancel_event.clear()

    # ===================== TOAST =====================
    def send_toast(self, title, msg):
        if not HAS_TOAST or not self.enable_toast_var.get(): return
        def _send():
            try:
                if _TOAST_LIB == 'win11toast':
                    _win11_toast_fn(title, msg, app_id='PyAudioCodingTools')
                elif _TOAST_LIB == 'windows_toasts':
                    t = _WTToast(); t.text_fields = [title, msg]
                    _WTToaster('PyAudioCodingTools').show_toast(t)
            except Exception as e: print(f"Toast: {e}")
        threading.Thread(target=_send, daemon=True).start()

    # ===================== CRASH RECOVERY =====================
    def save_crash_recovery(self, files, params):
        try:
            with open(CRASH_RECOVERY_FILE,'w',encoding='utf-8') as f:
                json.dump({'timestamp':time.time(),'files':files,'params':params,'completed':[],'failed':[]}, f, indent=2)
        except Exception as e: print(f"Recovery save: {e}")
    def update_crash_recovery(self, completed=None, failed=None):
        try:
            if not os.path.exists(CRASH_RECOVERY_FILE): return
            with open(CRASH_RECOVERY_FILE,'r',encoding='utf-8') as f: r = json.load(f)
            if completed: r.setdefault('completed',[]).append(completed)
            if failed: r.setdefault('failed',[]).append(failed)
            with open(CRASH_RECOVERY_FILE,'w',encoding='utf-8') as f: json.dump(r,f,indent=2)
        except Exception as e: print(f"Recovery update: {e}")
    def clear_crash_recovery(self):
        try:
            if os.path.exists(CRASH_RECOVERY_FILE): os.remove(CRASH_RECOVERY_FILE)
        except: pass
    def check_crash_recovery(self):
        if not os.path.exists(CRASH_RECOVERY_FILE): return
        try:
            with open(CRASH_RECOVERY_FILE,'r',encoding='utf-8') as f: r = json.load(f)
            done = set(r.get('completed',[])); fail = set(r.get('failed',[]))
            remaining = [f for f in r.get('files',[]) if f not in done and f not in fail]
            if not remaining: self.clear_crash_recovery(); return
            age = int((time.time()-r.get('timestamp',0))/60)
            
            # Vérifier que les fichiers existent encore
            existing = [f for f in remaining if os.path.exists(f.split('|track:')[0] if '|track:' in f else f)]
            missing = len(remaining) - len(existing)
            
            msg = (f"Un batch interrompu a été détecté !\n\n"
                   f"• {len(existing)} fichier(s) restant(s) sur {len(r.get('files',[]))}\n"
                   f"• {len(done)} déjà terminé(s), {len(fail)} en erreur\n"
                   f"• Interrompu il y a environ {age} minute(s)\n")
            if missing > 0:
                msg += f"• ⚠ {missing} fichier(s) introuvable(s) (ignorés)\n"
            msg += (f"\nOui = Reprendre automatiquement l'encodage\n"
                    f"Non = Abandonner et supprimer la sauvegarde\n"
                    f"Annuler = Ne rien faire (on redemandera au prochain lancement)")
            
            res = messagebox.askyesnocancel("Reprise après interruption", msg)
            if res is True:
                self.file_list.delete(0,tk.END)
                for f in existing:
                    self.file_list.insert(tk.END, f)
                p = r.get('params',{})
                if p.get('codec'): self.codec_var.set(p['codec']); self.update_codec_params()
                if p.get('bitrate'): self.bitrate_combo.set(p['bitrate'])
                if p.get('sample_rate'): self.sample_rate_combo.set(p['sample_rate'])
                self.clear_crash_recovery()  # Effacer l'ancien recovery avant de relancer
                # Relancer l'encodage automatiquement après un court délai
                # (laisse le temps à l'UI de se mettre à jour)
                self.root.after(500, self.start_processing)
            elif res is False: self.clear_crash_recovery()
        except Exception as e: print(f"Recovery check: {e}"); self.clear_crash_recovery()

    # ===================== VALIDATION TEMPS RÉEL =====================
    def validate_params_realtime(self, *args):
        if not self.validation_label: return
        w = []; cd = self.codec_var.get(); ck = self.codec_reverse_map.get(cd, cd)
        try:
            br = int(self.bitrate_combo.get())
            if ck=='libopus' and br>256: w.append(T('val_opus_max'))
            if ck=='ac3' and br>640: w.append(T('val_ac3_max'))
            if ck in ('aac','libmp3lame') and br>320: w.append(T('val_br_max', codec=cd))
        except: pass
        sm = self.surround_mode_var.get()
        if sm != 'same':
            mx = MAX_CHANNELS.get(ck,8); req = int(AC_MAP.get(sm,'6'))
            if req > mx: w.append(T('val_ch_max', codec=cd, max=mx, req=sm))
        if self.loudnorm_var.get() and ck not in LOUDNORM_CODECS: w.append(T('val_loudnorm_incompat', codec=cd))
        if self.dialnorm_var.get() and ck != 'eac3': w.append(T('val_dialnorm_only'))
        if w: self.validation_label.configure(text="⚠ "+" | ".join(w), text_color="#FFA500")
        else: self.validation_label.configure(text=T('valid_ok'), text_color="#00CC00")

    # ===================== FFMPEG UPDATE =====================
    def update_ffmpeg(self):
        cw = ctk.CTkToplevel(self.root); cw.title("Installation / Mise à jour FFmpeg")
        self.center_toplevel(cw, 600, 350); cw.attributes("-topmost", True); cw.grab_set()
        ctk.CTkLabel(cw, text="Quelle version de FFmpeg voulez-vous installer ?", font=("Arial",14,"bold")).pack(pady=12)
        ctk.CTkLabel(cw, text=(
            "📦 Release Full (WinGet) = Version stable avec TOUS les codecs.\n"
            "     Installée via WinGet. Recommandée pour la plupart des utilisateurs.\n\n"
            "📦 Release Essentials (WinGet) = Version allégée, sans soxr.\n"
            "     ⚠ Le resampler haute qualité (soxr) ne sera PAS disponible.\n\n"
            "🔧 Git Master Full (Téléchargement) = Toute dernière version compilée.\n"
            "     Téléchargée directement depuis gyan.dev (fichier .7z).\n"
            "     Plus récente que la Release, mais potentiellement instable."),
            font=("Arial",10), text_color="gray", justify="left").pack(padx=20, pady=5)
        bf = ctk.CTkFrame(cw, fg_color="transparent"); bf.pack(pady=12)
        ctk.CTkButton(bf, text="📦 Release Full (WinGet)", width=190,
            command=lambda: (cw.destroy(), self._do_ffmpeg_winget("Gyan.FFmpeg", "Full")),
            fg_color='#008000').pack(side="left", padx=5)
        ctk.CTkButton(bf, text="📦 Essentials (WinGet)", width=160,
            command=lambda: (cw.destroy(), self._do_ffmpeg_winget("Gyan.FFmpeg.Essentials", "Essentials")),
            fg_color='#0066ff').pack(side="left", padx=5)
        ctk.CTkButton(bf, text="🔧 Git Master Full", width=150,
            command=lambda: (cw.destroy(), self._do_ffmpeg_git_download()),
            fg_color='#FFA500').pack(side="left", padx=5)
        ctk.CTkButton(cw, text="Annuler", command=cw.destroy, fg_color='#FF4500', width=100).pack(pady=10)

    def _create_winget_symlinks(self, ffmpeg_path, ffprobe_path):
        """Crée les symlinks dans le dossier WinGet Links pour que ffmpeg/ffprobe soient accessibles partout.
        Corrige le bug WinGet qui ne recrée pas toujours les Links."""
        localappdata = os.environ.get('LOCALAPPDATA', '')
        links_dir = os.path.join(localappdata, "Microsoft", "WinGet", "Links")
        if not os.path.isdir(links_dir):
            try: os.makedirs(links_dir, exist_ok=True)
            except: return
        
        created = []
        for src, name in [(ffmpeg_path, "ffmpeg.exe"), (ffprobe_path, "ffprobe.exe")]:
            if not src or not os.path.isfile(src): continue
            link = os.path.join(links_dir, name)
            try:
                # Supprimer l'ancien lien/fichier s'il existe
                if os.path.exists(link) or os.path.islink(link):
                    os.remove(link)
                # Créer le symlink (ou copier si les symlinks nécessitent admin)
                try:
                    os.symlink(src, link)
                    created.append(name)
                except OSError:
                    # Symlink peut nécessiter des droits admin — fallback: copie dure
                    shutil.copy2(src, link)
                    created.append(f"{name} (copie)")
            except Exception as e:
                print(f"Symlink {name}: {e}")
        
        # Aussi ffplay si présent
        ffplay_src = os.path.join(os.path.dirname(ffmpeg_path), "ffplay.exe")
        if os.path.isfile(ffplay_src):
            link = os.path.join(links_dir, "ffplay.exe")
            try:
                if os.path.exists(link): os.remove(link)
                try: os.symlink(ffplay_src, link)
                except OSError: shutil.copy2(ffplay_src, link)
                created.append("ffplay.exe")
            except: pass
        
        if created:
            print(f"Symlinks créés dans {links_dir}: {', '.join(created)}")
        
        # Ajouter le dossier Links au PATH utilisateur s'il n'y est pas déjà
        self._ensure_path_contains(links_dir)
        
        return len(created) > 0

    def _ensure_path_contains(self, directory):
        """Ajoute un dossier au PATH utilisateur Windows s'il n'y est pas déjà."""
        if os.name != 'nt': return
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE)
            try:
                current_path, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                current_path = ""
            
            # Vérifier si le dossier est déjà dans le PATH (insensible à la casse)
            paths = [p.strip().rstrip('\\') for p in current_path.split(';') if p.strip()]
            dir_normalized = directory.strip().rstrip('\\')
            
            if dir_normalized.lower() not in [p.lower() for p in paths]:
                new_path = current_path.rstrip(';') + ';' + directory
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                print(f"PATH utilisateur mis à jour : ajout de {directory}")
                
                # Notifier Windows du changement de variable d'environnement
                try:
                    import ctypes
                    HWND_BROADCAST = 0xFFFF
                    WM_SETTINGCHANGE = 0x001A
                    ctypes.windll.user32.SendMessageTimeoutW(
                        HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment", 0x0002, 5000, ctypes.byref(ctypes.c_long()))
                except: pass
                
                # Aussi mettre à jour le PATH du process courant
                os.environ["PATH"] = os.environ.get("PATH", "") + ";" + directory
            else:
                print(f"PATH utilisateur contient déjà {directory}")
            
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Erreur mise à jour PATH: {e}")

    def _do_ffmpeg_git_download(self):
        """Télécharge ffmpeg-git-full.7z depuis gyan.dev et extrait avec WinRAR/7-Zip/Windows natif."""
        if not requests:
            messagebox.showerror("Erreur", "Le module 'requests' est requis."); return
        uw = ctk.CTkToplevel(self.root); uw.title("Téléchargement FFmpeg (Git Master Full)")
        self.center_toplevel(uw, 550, 250); uw.attributes("-topmost", True); uw.grab_set()
        sl = ctk.CTkLabel(uw, text="Préparation...", font=("Arial",12), wraplength=480); sl.pack(pady=20)
        pb = ctk.CTkProgressBar(uw, width=400, mode='indeterminate'); pb.pack(pady=10); pb.start()
        close_btn = ctk.CTkButton(uw, text="Fermer", command=uw.destroy, fg_color='#FF4500'); close_btn.pack(pady=10)
        
        def _dl():
            try:
                import tempfile as _tmp
                url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z"
                
                # Dossier d'installation : à côté des packages WinGet ou dans un dossier dédié
                localappdata = os.environ.get('LOCALAPPDATA', '')
                install_dir = os.path.join(localappdata, "Microsoft", "WinGet", "Packages", "FFmpeg_Git_Full")
                os.makedirs(install_dir, exist_ok=True)
                
                # Téléchargement
                self.update_queue.put(lambda: sl.configure(text="Téléchargement de ffmpeg-git-full.7z...\n(~200 Mo, soyez patient)"))
                tmp_file = os.path.join(_tmp.gettempdir(), "ffmpeg-git-full.7z")
                r = requests.get(url, stream=True, timeout=60); r.raise_for_status()
                total = int(r.headers.get('content-length', 0)); dl = 0
                with open(tmp_file, 'wb') as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk); dl += len(chunk)
                        if total > 0:
                            pct = int(dl/total*100); mb = dl//(1024*1024); tmb = total//(1024*1024)
                            self.update_queue.put(lambda p=pct, m=mb, t=tmb: sl.configure(text=f"Téléchargement... {p}% ({m}/{t} Mo)"))
                
                # Nettoyage des anciennes versions avant extraction
                self.update_queue.put(lambda: sl.configure(text="Nettoyage ancienne version..."))
                for _item in os.listdir(install_dir):
                    _p = os.path.join(install_dir, _item)
                    try:
                        if os.path.isdir(_p): shutil.rmtree(_p)
                        else: os.remove(_p)
                    except Exception as _ce: print(f"Cleanup: {_ce}")

                # Extraction — essayer dans l'ordre : WinRAR, 7-Zip
                self.update_queue.put(lambda: sl.configure(text="Extraction en cours..."))
                extract_ok = False
                
                # 1. WinRAR
                winrar = None
                for p in [r"C:\Program Files\WinRAR\WinRAR.exe", r"C:\Program Files (x86)\WinRAR\WinRAR.exe"]:
                    if os.path.exists(p): winrar = p; break
                if not winrar: winrar = shutil.which("WinRAR")
                
                if winrar:
                    self.update_queue.put(lambda: sl.configure(text="Extraction avec WinRAR..."))
                    result = subprocess.run([winrar, "x", "-y", tmp_file, install_dir],
                        capture_output=True, timeout=300, creationflags=0x08000000)
                    extract_ok = result.returncode == 0
                
                # 2. 7-Zip
                if not extract_ok:
                    sz = None
                    for p in [r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe"]:
                        if os.path.exists(p): sz = p; break
                    if not sz: sz = shutil.which("7z")
                    if sz:
                        self.update_queue.put(lambda: sl.configure(text="Extraction avec 7-Zip..."))
                        result = subprocess.run([sz, "x", tmp_file, f"-o{install_dir}", "-y"],
                            capture_output=True, timeout=300, creationflags=0x08000000)
                        extract_ok = result.returncode == 0
                
                if not extract_ok:
                    self.update_queue.put(lambda: sl.configure(
                        text="Impossible d'extraire le fichier .7z !\n\n"
                             "Installez un de ces outils :\n"
                             "• WinRAR : https://www.win-rar.com/\n"
                             "• 7-Zip : https://www.7-zip.org/", text_color="#FF0000"))
                    self.update_queue.put(lambda: pb.stop()); return
                
                # Trouver ffmpeg.exe — chercher TOUS les candidats, garder le plus récent
                ff_candidates = []
                for root_dir, dirs, files_list in os.walk(install_dir):
                    for fname in files_list:
                        if fname.lower() == 'ffmpeg.exe':
                            fp_cand = os.path.join(root_dir, 'ffprobe.exe')
                            if not os.path.exists(fp_cand):
                                fp_cand = os.path.join(root_dir, 'ffprobe.EXE')
                            if os.path.exists(fp_cand):
                                ff_path = os.path.join(root_dir, fname)
                                ff_candidates.append((os.path.getmtime(ff_path), ff_path, fp_cand))
                new_ff = None; new_fp = None
                if ff_candidates:
                    ff_candidates.sort(reverse=True)  # plus récent en premier
                    _, new_ff, new_fp = ff_candidates[0]
                
                if new_ff and new_fp:
                    # Créer les symlinks dans WinGet/Links
                    self._create_winget_symlinks(new_ff, new_fp)
                    def _ok(ff=new_ff, fp=new_fp):
                        self.ffmpeg_path_entry.delete(0, tk.END); self.ffmpeg_path_entry.insert(0, ff)
                        self.ffprobe_path_entry.delete(0, tk.END); self.ffprobe_path_entry.insert(0, fp)
                        sl.configure(text=f"✓ Git Master Full installé !\n\n"
                                         f"FFmpeg :  {ff}\n"
                                         f"FFprobe : {fp}\n\n"
                                         f"Symlinks créés dans WinGet/Links ✓", text_color="#00CC00")
                        pb.stop(); pb.configure(mode='determinate'); pb.set(1.0)
                        close_btn.configure(fg_color='#008000')
                    self.update_queue.put(_ok)
                    self.send_toast("FFmpeg mis à jour", "Git Master Full installé")
                else:
                    self.update_queue.put(lambda: sl.configure(
                        text="Extraction réussie mais ffmpeg.exe non trouvé.\n"
                             f"Vérifiez manuellement : {install_dir}", text_color="#FF0000"))
                    self.update_queue.put(lambda: pb.stop())
                
                try: os.remove(tmp_file)
                except: pass
            except Exception as e:
                self.update_queue.put(lambda e=str(e): sl.configure(text=f"Erreur : {e}", text_color="#FF0000"))
                self.update_queue.put(lambda: pb.stop())
        
        threading.Thread(target=_dl, daemon=True).start()

    def _do_ffmpeg_winget(self, winget_id, label):
        """Installe/met à jour FFmpeg via winget."""
        uw = ctk.CTkToplevel(self.root); uw.title(f"Installation FFmpeg ({label})")
        self.center_toplevel(uw, 550, 250); uw.attributes("-topmost", True); uw.grab_set()
        sl = ctk.CTkLabel(uw, text="Vérification de WinGet...", font=("Arial",12), wraplength=480); sl.pack(pady=20)
        pb = ctk.CTkProgressBar(uw, width=400, mode='indeterminate'); pb.pack(pady=10); pb.start()
        close_btn = ctk.CTkButton(uw, text="Fermer", command=uw.destroy, fg_color='#FF4500')
        close_btn.pack(pady=10)
        
        def _install():
            try:
                # Vérifier winget
                try:
                    subprocess.run(["winget", "--version"], capture_output=True, check=True, creationflags=0x08000000)
                except (FileNotFoundError, subprocess.CalledProcessError):
                    self.update_queue.put(lambda: sl.configure(
                        text="WinGet n'est pas disponible sur ce système.\n\n"
                             "WinGet est inclus dans Windows 10/11 récent.\n"
                             "Installez 'App Installer' depuis le Microsoft Store.", text_color="#FF0000"))
                    self.update_queue.put(lambda: pb.stop()); return
                
                # winget install gère à la fois l'installation et la mise à jour
                self.update_queue.put(lambda wid=winget_id: sl.configure(
                    text=f"Installation/mise à jour via WinGet...\n\nwinget install --id {wid}\n\n"
                         f"(Cela peut prendre 1-2 minutes)"))
                
                result = subprocess.run(
                    ["winget", "install", "--id", winget_id,
                     "--accept-package-agreements", "--accept-source-agreements",
                     "--force"],
                    capture_output=True, text=True, timeout=600, creationflags=0x08000000
                )
                
                combined = result.stdout + result.stderr
                
                # Chercher ffmpeg dans les emplacements WinGet connus
                localappdata = os.environ.get('LOCALAPPDATA', '')
                winget_links = os.path.join(localappdata, "Microsoft", "WinGet", "Links")
                winget_pkgs = os.path.join(localappdata, "Microsoft", "WinGet", "Packages")
                
                new_ff = None; new_fp = None
                
                # 1. Scanner Packages d'abord (chemin réel, plus fiable)
                if os.path.isdir(winget_pkgs):
                    for root_dir, dirs, files_list in os.walk(winget_pkgs):
                        for fname in files_list:
                            if fname.lower() == 'ffmpeg.exe':
                                candidate = os.path.join(root_dir, fname)
                                fp_candidate = os.path.join(root_dir, 'ffprobe.exe')
                                # Vérifier aussi avec la casse originale
                                if not os.path.exists(fp_candidate):
                                    fp_candidate = os.path.join(root_dir, 'ffprobe.EXE')
                                if os.path.isfile(candidate) and os.path.isfile(fp_candidate):
                                    new_ff = candidate; new_fp = fp_candidate; break
                        if new_ff: break
                
                # 2. Si pas trouvé dans Packages, essayer Links
                if not new_ff:
                    for name_ff, name_fp in [('ffmpeg.exe','ffprobe.exe'), ('ffmpeg.EXE','ffprobe.EXE')]:
                        lf = os.path.join(winget_links, name_ff)
                        lp = os.path.join(winget_links, name_fp)
                        if os.path.isfile(lf) and os.path.isfile(lp):
                            new_ff = lf; new_fp = lp; break
                
                # 3. Dernier recours : shutil.which
                if not new_ff:
                    new_ff = shutil.which("ffmpeg")
                    new_fp = shutil.which("ffprobe")
                
                if new_ff and new_fp:
                    # Créer/recréer les symlinks dans WinGet/Links
                    self._create_winget_symlinks(new_ff, new_fp)
                    def _ok(ff=new_ff, fp=new_fp):
                        self.ffmpeg_path_entry.delete(0, tk.END); self.ffmpeg_path_entry.insert(0, ff)
                        self.ffprobe_path_entry.delete(0, tk.END); self.ffprobe_path_entry.insert(0, fp)
                        sl.configure(text=f"✓ FFmpeg ({label}) installé avec succès !\n\n"
                                         f"FFmpeg :  {ff}\n"
                                         f"FFprobe : {fp}\n\n"
                                         f"Symlinks créés dans WinGet/Links ✓", text_color="#00CC00")
                        pb.stop(); pb.configure(mode='determinate'); pb.set(1.0)
                        close_btn.configure(fg_color='#008000')
                    self.update_queue.put(_ok)
                    self.send_toast("FFmpeg mis à jour", f"FFmpeg ({label}) installé via WinGet")
                elif result.returncode == 0 or "No applicable update" in combined or "successfully" in combined.lower():
                    self.update_queue.put(lambda: sl.configure(
                        text=f"✓ WinGet a terminé, mais les chemins n'ont pas pu\n"
                             f"être détectés automatiquement.\n\n"
                             f"Fermez et relancez l'application, puis vérifiez\n"
                             f"les chemins avec le bouton 'Test'.\n\n"
                             f"Ou cherchez manuellement ffmpeg.exe dans :\n"
                             f"{winget_links}", text_color="#FFA500"))
                    self.update_queue.put(lambda: pb.stop())
                else:
                    short = combined[:600] if combined else "Aucune sortie"
                    self.update_queue.put(lambda s=short, rc=result.returncode: sl.configure(
                        text=f"WinGet a terminé avec le code {rc}.\n\n{s}", text_color="#FF0000"))
                    self.update_queue.put(lambda: pb.stop())
                    
            except subprocess.TimeoutExpired:
                self.update_queue.put(lambda: sl.configure(
                    text="Timeout : l'installation a pris trop de temps.\n\n"
                         f"Essayez manuellement :\nwinget install --id {winget_id}", text_color="#FF0000"))
                self.update_queue.put(lambda: pb.stop())
            except Exception as e:
                self.update_queue.put(lambda e=str(e): sl.configure(text=f"Erreur : {e}", text_color="#FF0000"))
                self.update_queue.put(lambda: pb.stop())
        
        threading.Thread(target=_install, daemon=True).start()

    # ===================== MÉTHODES DE BASE =====================
    def apply_safe_theme(self, tn):
        if tn in ['green','blue','dark-blue']:
            try: ctk.set_default_color_theme(tn); return
            except: pass
        for p in [resource_path(os.path.join("Assets",f"{tn}.json")), resource_path(f"{tn}.json")]:
            if os.path.exists(p):
                try:
                    with open(p,"r") as f: ct = json.load(f)
                    bt = ctk.ThemeManager.theme
                    for s,v in ct.items():
                        if s in bt:
                            if isinstance(bt[s],dict) and isinstance(v,dict): bt[s].update(v)
                            else: bt[s]=v
                    return
                except Exception as e: print(f"Thème {tn}: {e}")
        try: ctk.set_default_color_theme("green")
        except: pass

    def check_ffmpeg_version_on_startup(self): self.test_ffmpeg_ffprobe(silent=True)
    def center_toplevel(self, w, wi, h):
        mx=self.root.winfo_x(); my=self.root.winfo_y(); mw=self.root.winfo_width(); mh=self.root.winfo_height()
        w.geometry(f"{wi}x{h}+{mx+mw//2-wi//2}+{my+mh//2-h//2}")

    def test_ffmpeg_ffprobe(self, silent=False):
        ff=self.ffmpeg_path_entry.get(); fp=self.ffprobe_path_entry.get()
        try:
            fo=subprocess.check_output([ff,"-version"],stderr=subprocess.STDOUT,universal_newlines=True)
            po=subprocess.check_output([fp,"-version"],stderr=subprocess.STDOUT,universal_newlines=True)
            fv=re.search(r'ffmpeg version (\S+)',fo).group(1)
            pv=re.search(r'ffprobe version (\S+)',po).group(1)
            msg=f"FFmpeg local : {fv}\nFFprobe local : {pv}"
            online_rel="?"; online_git="?"; outdated=False
            if requests:
                try:
                    r=requests.get("https://www.gyan.dev/ffmpeg/builds/release-version",timeout=3)
                    if r.status_code==200: online_rel=r.text.strip()
                    r2=requests.get("https://www.gyan.dev/ffmpeg/builds/git-version",timeout=3)
                    if r2.status_code==200: online_git=r2.text.strip()
                    msg+=f"\n\nDernière Release stable : {online_rel}\nDernière Git Master : {online_git}"
                    try:
                        lm = float(fv.split('.')[0]+'.'+fv.split('.')[1]) if '.' in fv else 0
                        rm = float(online_rel.split('.')[0]+'.'+online_rel.split('.')[1]) if '.' in online_rel else 0
                        if lm < rm: outdated=True; msg+="\n\n⚠ Une mise à jour est disponible !"
                    except: pass
                except Exception as e: print(f"Version check: {e}")
            if not silent:
                tw=ctk.CTkToplevel(self.root,fg_color="#2b3e50"); tw.title("Test FFmpeg / FFprobe"); self.center_toplevel(tw,520,400)
                tw.attributes("-topmost",True); tw.grab_set()
                c=ctk.CTkFrame(tw,fg_color="transparent"); c.pack(expand=True,fill="both",padx=20,pady=20)
                ctk.CTkLabel(c,text=msg,font=("Arial",13),justify="center",text_color="#ffffff").pack(pady=15,expand=True)
                bf=ctk.CTkFrame(c,fg_color="transparent"); bf.pack(pady=5)
                b1=ctk.CTkButton(bf,text="📥 Mise à jour",command=lambda:(tw.destroy(),self.update_ffmpeg()),fg_color="#FFA500",width=120)
                b1.pack(side="left",padx=4)
                ToolTip(b1,"Ouvre le menu d'installation/mise à jour.\nRelease Full (WinGet), Essentials (WinGet) ou Git Master Full (téléchargement).")
                b2=ctk.CTkButton(bf,text="🔧 Git Master",command=lambda:(tw.destroy(),self._do_ffmpeg_git_download()),fg_color="#FF6600",width=120)
                b2.pack(side="left",padx=4)
                ToolTip(b2,"Télécharge et installe directement la dernière build\nGit Master Full depuis gyan.dev.")
                ctk.CTkButton(bf,text="🌐 gyan.dev",command=lambda:webbrowser.open('https://www.gyan.dev/ffmpeg/builds/'),fg_color="#0066ff",width=100).pack(side="left",padx=4)
                ctk.CTkButton(c,text="Fermer",command=tw.destroy,width=100).pack(pady=10,side="bottom")
        except Exception as e:
            if not silent: messagebox.showerror("Erreur",f"Impossible de tester FFmpeg/FFprobe :\n{e}")

    def process_spectrum_queue(self):
        while True:
            try: i,o = self.spectrum_queue.get(); show_audio_spectrum_comparison(self,i,o)
            except Exception as e: print(f"Spectre: {e}")

    def _ensure_winget_links(self, ffmpeg_path, ffprobe_path):
        """Alias pour _create_winget_symlinks (rétro-compatibilité)."""
        return self._create_winget_symlinks(ffmpeg_path, ffprobe_path)
    def check_update_queue(self):
        n=0
        try:
            while n<20 and not self.update_queue.empty():
                try:
                    callback = self.update_queue.get_nowait()
                    callback()
                except Exception as e:
                    print(f"Queue callback error: {e}")
                n+=1
        except Exception as e: print(f"Queue: {e}")
        # Si la queue est trop grosse (>500), vider les plus anciens pour éviter le freeze
        try:
            qsize = self.update_queue.qsize()
            if qsize > 500:
                dropped = 0
                while self.update_queue.qsize() > 100:
                    try: self.update_queue.get_nowait(); dropped += 1
                    except: break
                if dropped: print(f"Queue saturée: {dropped} éléments supprimés (restait {qsize})")
        except: pass
        self.root.after(15 if n>=20 else 50, self.check_update_queue)

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file,'r',encoding='utf-8') as f:
                    s=json.load(f)
                    if 'codec_params' in s: s['codec_params']={k:v for k,v in s['codec_params'].items() if k in self.codec_display_map.values()}
                    return s
            except: return {}
        return {}
    def load_presets(self):
        if os.path.exists(self.presets_file):
            try:
                with open(self.presets_file,'r',encoding='utf-8') as f: return json.load(f)
            except: return {}
        return {}
    def save_settings(self):
        ccp={}
        for dk,p in self.codec_params.items():
            cp={k:v.get() if isinstance(v,ctk.StringVar) else v for k,v in p.items()}; cp['surround_mode']=self.surround_mode_var.get(); ccp[dk]=cp
        s={'ffmpeg_path':self.ffmpeg_path_entry.get(),'ffprobe_path':self.ffprobe_path_entry.get(),
           'output_dir':self.output_dir_entry.get(),'max_workers':self.max_workers_entry.get(),
           'codec':self.codec_var.get(),'bitrate':self.bitrate_combo.get(),'sample_rate':self.sample_rate_combo.get(),
           'loudnorm_i':self.loudnorm_i_combo.get(),'loudnorm_lra':self.loudnorm_lra_combo.get(),'loudnorm_tp':self.loudnorm_tp_combo.get(),
           'copy_metadata':self.copy_metadata_var.get(),'loudnorm':self.loudnorm_var.get(),'dialnorm':self.dialnorm_var.get(),
           'compare_spectrum':self.compare_spectrum_var.get(),'parallel_processing':self.parallel_processing_var.get(),
           'mka_output':self.mka_output_var.get(),
           'preferred_language':self.preferred_language,
           'codec_params':ccp,'window_width':self.root.winfo_width(),'window_height':self.root.winfo_height(),
           'theme':self.theme,'color_theme':self.color_theme_combo.get(),
           'detailed_output':self.detailed_output_var.get(),'enable_sounds':self.enable_sounds_var.get(),
           'sound_volume':self.sound_volume_var.get(),'enable_toast':self.enable_toast_var.get(),
           'analyze_duration':self.analyze_duration_combo.get() if self.analyze_duration_combo else '80M',
           'probe_size':self.probe_size_combo.get() if self.probe_size_combo else '60M',
           'async':self.async_combo.get() if self.async_combo else 'On',
           'min_hard_comp':self.min_hard_comp_entry.get() if self.min_hard_comp_entry else '0.100000',
           'first_pts':self.first_pts_entry.get() if self.first_pts_entry else '0',
           'resampler':self.resampler_combo.get() if self.resampler_combo else 'soxr',
           'language':get_lang()}
        try:
            with open(self.settings_file,'w',encoding='utf-8') as f: json.dump(s,f,indent=4)
        except Exception as e: messagebox.showerror("Erreur",f"Sauvegarde impossible : {e}")

    def _apply_builtin_preset(self, params, name):
        """Applique un preset intégré (codec, bitrate, surround, loudnorm, dialnorm)."""
        self.codec_var.set(params['codec'])
        self.update_codec_params()
        self.bitrate_combo.set(params['bitrate'])
        self.sample_rate_combo.set(params['sample_rate'])
        self.surround_mode_var.set(params['surround_mode'])
        self.loudnorm_var.set(params['loudnorm'])
        self.dialnorm_var.set(params['dialnorm'])
        # Ajuster loudnorm cible selon usage
        if params['loudnorm']:
            if 'Série' in name or 'VO' in name:
                self.loudnorm_i_combo.set('-23')  # Broadcast TV
            elif 'Web' in name or 'Podcast' in name:
                self.loudnorm_i_combo.set('-16')  # Streaming
            else:
                self.loudnorm_i_combo.set('-18')  # Défaut
        self.toggle_loudness_visibility()
        self.validate_params_realtime()
        # Feedback visuel
        messagebox.showinfo("Préréglage appliqué", f"✓ {name} appliqué.\n\n"
            f"Codec : {params['codec']}\n"
            f"Bitrate : {params['bitrate']} kbps\n"
            f"Canaux : {params['surround_mode']}\n"
            f"Loudnorm : {'✓' if params['loudnorm'] else '✗'}\n"
            f"Dialnorm : {'✓' if params['dialnorm'] else '✗'}")

    def save_preset(self):
        n=self.preset_name_entry.get().strip()
        if not n: messagebox.showwarning("Attention","Veuillez entrer un nom de préréglage."); return
        cp={k:v.get() if isinstance(v,ctk.StringVar) else v for k,v in self.codec_params.get(self.codec_var.get(),{}).items()}
        cp['surround_mode']=self.surround_mode_var.get()
        d={'codec':self.codec_var.get(),'bitrate':self.bitrate_combo.get(),'sample_rate':self.sample_rate_combo.get(),
           'loudnorm_i':self.loudnorm_i_combo.get(),'loudnorm_lra':self.loudnorm_lra_combo.get(),'loudnorm_tp':self.loudnorm_tp_combo.get(),
           'copy_metadata':self.copy_metadata_var.get(),'loudnorm':self.loudnorm_var.get(),'dialnorm':self.dialnorm_var.get(),
           'codec_params':cp,'analyze_duration':self.analyze_duration_combo.get(),'probe_size':self.probe_size_combo.get(),
           'async':self.async_combo.get(),'min_hard_comp':self.min_hard_comp_entry.get(),'first_pts':self.first_pts_entry.get(),'resampler':self.resampler_combo.get()}
        self.presets[n]=d
        with open(self.presets_file,'w',encoding='utf-8') as f: json.dump(self.presets,f,indent=4)
        self.preset_combo.configure(values=list(self.presets.keys())); self.preset_combo.set(n)
        messagebox.showinfo("Succès",f"Préréglage '{n}' sauvegardé !")
    def load_preset(self):
        n=self.preset_combo.get()
        if not n or n not in self.presets: messagebox.showwarning("Attention","Sélectionnez un préréglage valide dans la liste."); return
        d=self.presets[n]; self.codec_var.set(d.get('codec','Dolby Digital Plus')); self.update_codec_params()
        for k,w in [('bitrate',self.bitrate_combo),('sample_rate',self.sample_rate_combo),('loudnorm_i',self.loudnorm_i_combo),('loudnorm_lra',self.loudnorm_lra_combo),('loudnorm_tp',self.loudnorm_tp_combo)]:
            if d.get(k): w.set(d[k])
        self.copy_metadata_var.set(d.get('copy_metadata',False)); self.loudnorm_var.set(d.get('loudnorm',True)); self.dialnorm_var.set(d.get('dialnorm',True))
        if self.analyze_duration_combo and d.get('analyze_duration'): self.analyze_duration_combo.set(d['analyze_duration'])
        if self.probe_size_combo and d.get('probe_size'): self.probe_size_combo.set(d['probe_size'])
        if self.async_combo and d.get('async'): self.async_combo.set(d['async'])
        if self.min_hard_comp_entry and d.get('min_hard_comp'): self.min_hard_comp_entry.delete(0,tk.END); self.min_hard_comp_entry.insert(0,d['min_hard_comp'])
        if self.first_pts_entry and d.get('first_pts'): self.first_pts_entry.delete(0,tk.END); self.first_pts_entry.insert(0,d['first_pts'])
        if self.resampler_combo and d.get('resampler'): self.resampler_combo.set(d['resampler'])
        self.update_codec_specific_frame(); self.toggle_loudness_visibility()
        messagebox.showinfo("Succès",f"Préréglage '{n}' chargé !")
    def delete_preset(self):
        n=self.preset_combo.get()
        if n and n in self.presets:
            del self.presets[n]
            with open(self.presets_file,'w',encoding='utf-8') as f: json.dump(self.presets,f,indent=4)
            self.preset_combo.configure(values=list(self.presets.keys())); self.preset_combo.set('')
            messagebox.showinfo("Succès","Préréglage supprimé !")

    # ===================== TABS =====================
    def create_tabs(self):
        # INPUT
        self.input_tab=self.notebook.add(T('tab_input')); lf=ctk.CTkFrame(self.input_tab); lf.pack(fill='both',expand=True,pady=5,padx=5)
        self.file_list=tk.Listbox(lf,selectmode=tk.MULTIPLE,height=10,bg='#333333',fg='white',borderwidth=0,highlightthickness=0)
        self.input_scrollbar=ctk.CTkScrollbar(lf,command=self.file_list.yview); self.file_list.configure(yscrollcommand=self.input_scrollbar.set)
        self.file_list.pack(side="left",fill='both',expand=True); self.input_scrollbar.pack(side="right",fill="y")
        bf=ctk.CTkFrame(self.input_tab,fg_color="transparent"); bf.pack(side="bottom",anchor='center',pady=6)
        b1=ctk.CTkButton(bf,text=T('btn_add_files'),command=self.add_files,fg_color='#ADD8E6',text_color='#000000'); b1.pack(side=tk.LEFT,padx=3)
        ToolTip(b1,"Ouvrir une fenêtre pour sélectionner un ou plusieurs fichiers audio.\nFormats acceptés : FLAC, WAV, MP3, AAC, OGG, M4A, DTS, THD.\nLes fichiers seront ajoutés à la liste ci-dessus.")
        b2=ctk.CTkButton(bf,text=T('btn_add_folder'),command=self.add_folder,fg_color='#800080',text_color='white'); b2.pack(side=tk.LEFT,padx=3)
        ToolTip(b2,"Scanner un dossier entier (y compris tous les sous-dossiers)\net ajouter automatiquement tous les fichiers audio trouvés.\nIdéal pour traiter une discothèque ou une saison de série d'un coup.")
        b3=ctk.CTkButton(bf,text=T('btn_remove_sel'),command=self.remove_selected,fg_color='#FF4500',text_color='white'); b3.pack(side=tk.LEFT,padx=3)
        ToolTip(b3,"Retire de la liste les fichiers que vous avez sélectionnés (surlignés en bleu).\nPour sélectionner plusieurs fichiers : maintenez Ctrl en cliquant.\nLes fichiers originaux ne sont PAS supprimés du disque.")
        b4=ctk.CTkButton(bf,text=T('btn_clear_all'),command=self.clear_files,fg_color='#FF0000',text_color='white'); b4.pack(side=tk.LEFT,padx=3)
        ToolTip(b4,"Vide entièrement la liste des fichiers à traiter.\nAucun fichier n'est supprimé de votre disque,\nil sont simplement retirés de la file d'attente.")
        b5=ctk.CTkButton(bf,text=T('btn_move_up'),command=self.move_file_up,fg_color='#0066ff',text_color='white',width=70); b5.pack(side=tk.LEFT,padx=3)
        ToolTip(b5,"Déplace le fichier sélectionné vers le haut dans la liste.\nCela change l'ordre dans lequel les fichiers seront traités.")
        b6=ctk.CTkButton(bf,text=T('btn_move_down'),command=self.move_file_down,fg_color='#0066ff',text_color='white',width=70); b6.pack(side=tk.LEFT,padx=3)
        ToolTip(b6,"Déplace le fichier sélectionné vers le bas dans la liste.\nCela change l'ordre dans lequel les fichiers seront traités.")
        b7=ctk.CTkButton(bf,text=T('btn_open_output'),command=self._open_output_folder,fg_color='#FFA500',text_color='white',width=130); b7.pack(side=tk.LEFT,padx=3)
        ToolTip(b7,"Ouvre le dossier de sortie dans l'explorateur Windows.\n\n"
                   "Si le champ 'Dossier de sortie' (onglet Options) est rempli,\nouvre ce dossier.\n\n"
                   "Sinon, ouvre le dossier du premier fichier de la liste\n(les fichiers convertis sont créés à côté des originaux).")

        # OUTPUT
        self.output_tab=self.notebook.add(T('tab_output')); ocf=ctk.CTkFrame(self.output_tab); ocf.pack(fill='x',pady=5)
        dc=ctk.CTkCheckBox(ocf,text=T('chk_detailed'),variable=self.detailed_output_var); dc.pack(side=tk.LEFT,padx=5)
        ToolTip(dc,"ACTIVÉ : Affiche les commandes FFmpeg complètes, la sortie brute du terminal,\net toutes les informations techniques de chaque étape.\nTrès utile pour comprendre pourquoi un fichier échoue.\n\nDÉSACTIVÉ : Affichage simplifié, une ligne par fichier.\nRecommandé pour un usage normal.")
        slb=ctk.CTkButton(ocf,text=T('btn_save_log'),command=self.save_log,fg_color='#008000'); slb.pack(side=tk.RIGHT,padx=5)
        ToolTip(slb,"Enregistre tout le texte de la console de sortie dans un fichier .txt.\nUtile pour garder une trace ou envoyer un rapport de bug.")
        clb=ctk.CTkButton(ocf,text=T('btn_clear_log'),command=self.clear_log_and_jobs,fg_color='#FF4500'); clb.pack(side=tk.RIGHT,padx=5)
        ToolTip(clb,"Efface le texte du log ET supprime la liste des tâches\n(barres de progression en bas).\nPermet de repartir à zéro sans relancer l'application.")
        self.paned_window=tk.PanedWindow(self.output_tab,orient='vertical',sashrelief='flat',sashwidth=4,bg='#2b2b2b'); self.paned_window.pack(fill='both',expand=True,padx=5,pady=5)
        self.log_frame=tk.Frame(self.paned_window,bg='#2b2b2b'); self.paned_window.add(self.log_frame)
        self.output_text=tk.Text(self.log_frame,height=10,bg='#333333',fg='white',borderwidth=0); self.output_text.pack(side="left",fill="both",expand=True)
        sb=tk.Scrollbar(self.log_frame,command=self.output_text.yview,bg='#333333'); sb.pack(side="right",fill="y"); self.output_text.configure(yscrollcommand=sb.set)
        self.progress_container=tk.Frame(self.paned_window,bg='#2b2b2b'); self.paned_window.add(self.progress_container)
        self.progress_pane=ctk.CTkScrollableFrame(self.progress_container,label_text=T('tasks_label')); self.progress_pane.pack(fill='both',expand=True)
        for t,c in [("success","#00ff00"),("error","#ff0000"),("info","#00ccff")]: self.output_text.tag_configure(t,foreground=c)

        # PARAMS
        self.encode_params_tab=self.notebook.add(T('tab_params')); mpf=ctk.CTkFrame(self.encode_params_tab,fg_color="transparent"); mpf.pack(fill='both',expand=True,padx=20,pady=10)
        ff=ctk.CTkFrame(mpf); ff.pack(fill='x',pady=(0,10)); ff.grid_columnconfigure(tuple(range(8)),weight=1)
        ctk.CTkLabel(ff,text=T('lbl_codec')).grid(row=0,column=0,padx=5,pady=10,sticky="e")
        cc=ctk.CTkOptionMenu(ff,variable=self.codec_var,values=self.codec_display_list,command=self.update_codec_params); cc.grid(row=0,column=1,padx=5,pady=10,sticky="w")
        ToolTip(cc,"Le format audio dans lequel vos fichiers seront convertis.\n\n"
                   "• AAC : Le plus compatible (smartphones, TV, streaming). Bonne qualité.\n"
                   "• Dolby Digital (AC3) : Standard home-cinéma 5.1. Compatible partout.\n"
                   "• Dolby Digital Plus (E-AC3) : Version améliorée du AC3. Meilleur son à même bitrate.\n"
                   "• FLAC : Sans perte (lossless). Fichier plus gros mais qualité parfaite.\n"
                   "• MP3 : Universel mais qualité inférieure. Pour la compatibilité maximale.\n"
                   "• Opus : Excellent rapport qualité/taille. Idéal pour le streaming/web.\n"
                   "• DTS : Standard cinéma. Bonne qualité surround.\n"
                   "• ALAC : Sans perte Apple. Pour iTunes/iPhone.\n"
                   "• PCM 16-bit : Audio brut non compressé (WAV).\n"
                   "• Vorbis : Alternative libre au MP3. Bonne qualité.")
        ctk.CTkLabel(ff,text=T('lbl_bitrate')).grid(row=0,column=2,padx=5,pady=10,sticky="e")
        self.bitrate_combo=ctk.CTkOptionMenu(ff,values=[]); self.bitrate_combo.grid(row=0,column=3,padx=5,pady=10,sticky="w")
        ToolTip(self.bitrate_combo,"La qualité du son encodé, mesurée en kilobits par seconde (kbps).\n\n"
                "AUGMENTER le bitrate = Meilleure qualité audio, fichier plus volumineux.\n"
                "RÉDUIRE le bitrate = Qualité moindre, fichier plus petit.\n\n"
                "Recommandations :\n"
                "• 128 kbps : Acceptable pour la voix/podcast\n"
                "• 192 kbps : Bonne qualité pour la musique stéréo\n"
                "• 320 kbps : Très bonne qualité stéréo (quasi transparent)\n"
                "• 448 kbps : Standard pour le surround 5.1 (DVD)\n"
                "• 640 kbps : Haute qualité surround 5.1/7.1")
        ctk.CTkLabel(ff,text=T('lbl_samplerate')).grid(row=0,column=4,padx=5,pady=10,sticky="e")
        self.sample_rate_combo=ctk.CTkOptionMenu(ff,values=[]); self.sample_rate_combo.grid(row=0,column=5,padx=5,pady=10,sticky="w")
        ToolTip(self.sample_rate_combo,"La fréquence d'échantillonnage : combien de fois par seconde le son est mesuré.\n\n"
                "AUGMENTER = Plus de détail dans les hautes fréquences.\n"
                "RÉDUIRE = Fichier plus petit, fréquences aiguës coupées.\n\n"
                "• 44100 Hz : Standard CD audio. Suffisant pour la musique.\n"
                "• 48000 Hz : Standard vidéo/film/TV. RECOMMANDÉ pour la plupart des usages.\n"
                "• 96000 Hz : Haute résolution. Seulement si votre source est en Hi-Res.\n"
                "• 22050 Hz ou moins : Qualité téléphone. Déconseillé.")
        ctk.CTkLabel(ff,text=T('lbl_channels')).grid(row=0,column=6,padx=5,pady=10,sticky="e")
        self.channels_combo=ctk.CTkOptionMenu(ff,variable=self.surround_mode_var,values=[]); self.channels_combo.grid(row=0,column=7,padx=5,pady=10,sticky="w")
        ToolTip(self.channels_combo,"Le nombre de canaux audio (haut-parleurs) du fichier de sortie.\n\n"
                "• Same : Garde le même nombre de canaux que le fichier original.\n"
                "            C'est le choix le plus sûr si vous ne savez pas.\n"
                "• 2.0 (Stéréo) : 2 canaux — gauche et droite.\n"
                "            Pour écouter au casque ou sur des enceintes simples.\n"
                "• 5.1 (Surround) : 6 canaux — avant G/D/C + arrière G/D + caisson de basses.\n"
                "            Pour les systèmes home-cinéma.\n"
                "• 7.1 (Surround étendu) : 8 canaux — comme le 5.1 + 2 canaux latéraux.\n"
                "            Pour les installations home-cinéma haut de gamme.")

        # Validation indicator
        self.validation_label=ctk.CTkLabel(mpf,text=T('valid_ok'),text_color="#00CC00",font=("Arial",11,"bold")); self.validation_label.pack(fill='x',pady=(0,5))
        self.codec_var.trace_add('write',self.validate_params_realtime); self.surround_mode_var.trace_add('write',self.validate_params_realtime)
        self.loudnorm_var.trace_add('write',self.validate_params_realtime); self.dialnorm_var.trace_add('write',self.validate_params_realtime)

        of=ctk.CTkFrame(mpf); of.pack(fill='x',pady=5); ci=ctk.CTkFrame(of,fg_color="transparent"); ci.pack(pady=10)
        c1=ctk.CTkCheckBox(ci,text=T('chk_copy_meta'),variable=self.copy_metadata_var); c1.pack(side=tk.LEFT,padx=10)
        ToolTip(c1,"ACTIVÉ : Le fichier converti conservera les informations du fichier original :\n"
                   "titre, artiste, album, année, pochette, et les chapitres (si présents).\n"
                   "Utile pour garder les infos de vos fichiers musicaux ou films.\n\n"
                   "DÉSACTIVÉ : Le fichier converti sera 'vierge' sans métadonnées.")
        c2=ctk.CTkCheckBox(ci,text=T('chk_loudnorm'),variable=self.loudnorm_var,command=self.toggle_loudness_visibility); c2.pack(side=tk.LEFT,padx=10)
        ToolTip(c2,"ACTIVÉ : Ajuste automatiquement le volume de vos fichiers selon la norme EBU R128.\n"
                   "Cela signifie que tous vos fichiers auront le même volume perçu.\n"
                   "Très utile si vous en avez marre de monter/baisser le son entre chaque épisode ou chanson.\n"
                   "Le traitement se fait en 2 passes : analyse du volume → correction intelligente.\n\n"
                   "DÉSACTIVÉ : Le volume du fichier original est conservé tel quel.\n\n"
                   "Note : Compatible avec AAC, AC3, E-AC3, MP3, Opus, WMA et Vorbis.\n"
                   "Non compatible avec FLAC, ALAC, PCM et DTS (ces codecs encodent sans filtre audio).")
        c3=ctk.CTkCheckBox(ci,text=T('chk_dialnorm'),variable=self.dialnorm_var); c3.pack(side=tk.LEFT,padx=10)
        ToolTip(c3,"ACTIVÉ : Ajoute une métadonnée 'dialogue normalization' au fichier Dolby Digital Plus.\n"
                   "Valeur -31 dB = indique au décodeur Dolby de ne PAS modifier le volume.\n"
                   "C'est le réglage standard pour la compatibilité avec les amplis home-cinéma.\n\n"
                   "DÉSACTIVÉ : Pas de métadonnée dialnorm ajoutée.\n\n"
                   "Note : Cette option n'a d'effet que si le codec est Dolby Digital Plus (E-AC3).\n"
                   "Pour tous les autres codecs, elle est ignorée.")
        c4=ctk.CTkCheckBox(ci,text=T('chk_spectrum'),variable=self.compare_spectrum_var); c4.pack(side=tk.LEFT,padx=10)
        ToolTip(c4,"ACTIVÉ : Après chaque encodage, ouvre une fenêtre de comparaison visuelle avec 4 graphiques :\n"
                   "• En haut : Forme d'onde du fichier source vs fichier encodé\n"
                   "• En bas : Spectrogramme FFT (analyse fréquentielle) source vs encodé\n\n"
                   "Le spectrogramme permet de voir visuellement les fréquences coupées par le codec.\n"
                   "Les couleurs chaudes = beaucoup d'énergie. Les couleurs froides = peu d'énergie.\n"
                   "Un bon encodage garde un spectrogramme similaire à l'original.\n\n"
                   "DÉSACTIVÉ : Pas de fenêtre de comparaison (encodage plus rapide).")
        c5=ctk.CTkCheckBox(ci,text=T('chk_mka'),variable=self.mka_output_var); c5.pack(side=tk.LEFT,padx=10)
        ToolTip(c5,"Concerne les formats bruts : EAC3, AC3, DTS, WAV, WMA, AAC.\n\n"
                   "ACTIVÉ : Le fichier encodé est enveloppé dans un conteneur Matroska Audio (.mka).\n"
                   "Le .mka préserve les métadonnées de la piste source (langue, titre).\n"
                   "Quand vous importerez le fichier dans MKVMerge, le tag de langue\n"
                   "(ex: FRE, ENG, JPN) sera automatiquement reconnu.\n"
                   "C'est exactement un MKV mais qui ne contient que de l'audio.\n"
                   "Compatibilité : MKVMerge, VLC, Kodi, MPV, ffmpeg — tous le lisent.\n\n"
                   "DÉSACTIVÉ : Le fichier est écrit en format brut (.eac3, .ac3, .dts, etc.).\n"
                   "Les métadonnées de langue/titre sont PERDUES.\n"
                   "Dans MKVMerge, la piste apparaîtra comme 'und' (indéterminé).\n"
                   "Vous devrez définir la langue manuellement dans MKVMerge.\n\n"
                   "Note : Pour FLAC, MP3, Opus, Vorbis et M4A, cette option n'a pas d'effet\n"
                   "car ces formats supportent déjà les métadonnées nativement.")

        self.loudness_params_frame=ctk.CTkFrame(mpf)
        ctk.CTkLabel(self.loudness_params_frame,text=T('loudnorm_title'),font=("Arial",11,"bold")).pack(pady=5)
        li=ctk.CTkFrame(self.loudness_params_frame,fg_color="transparent"); li.pack(pady=5)
        ctk.CTkLabel(li,text=T('lbl_target_i')).pack(side="left",padx=5); self.loudnorm_i_combo=ctk.CTkOptionMenu(li,values=[],width=80); self.loudnorm_i_combo.pack(side="left",padx=5)
        ToolTip(self.loudnorm_i_combo,"Le volume moyen cible de votre fichier (Integrated Loudness), en LUFS.\n\n"
                "AUGMENTER (vers 0) = Son plus fort.\n"
                "RÉDUIRE (vers -70) = Son plus faible.\n\n"
                "Recommandations :\n"
                "• -24 LUFS : Standard broadcast TV/Radio (Europe)\n"
                "• -23 LUFS : Standard EBU R128 strict\n"
                "• -18 LUFS : Bon compromis pour le web et les séries\n"
                "• -16 LUFS : Standard streaming (Spotify, YouTube)\n"
                "• -14 LUFS : Fort, pour les podcasts très dynamiques")
        ctk.CTkLabel(li,text=T('lbl_lra')).pack(side="left",padx=5); self.loudnorm_lra_combo=ctk.CTkOptionMenu(li,values=[],width=80); self.loudnorm_lra_combo.pack(side="left",padx=5)
        ToolTip(self.loudnorm_lra_combo,"L'écart autorisé entre les passages les plus calmes et les plus forts (Loudness Range).\n\n"
                "AUGMENTER = Plus de dynamique. Les passages calmes restent calmes,\nles passages forts restent forts (effet cinéma).\n"
                "RÉDUIRE = Son plus uniforme. Tout est au même niveau\n(effet radio/podcast).\n\n"
                "Recommandations :\n"
                "• 5-7 LU : Radio, podcast — tout est bien nivelé\n"
                "• 11 LU : Standard TV — bon équilibre (RECOMMANDÉ)\n"
                "• 15-20 LU : Film/cinéma — gros écarts voulus")
        ctk.CTkLabel(li,text=T('lbl_truepeak')).pack(side="left",padx=5); self.loudnorm_tp_combo=ctk.CTkOptionMenu(li,values=[],width=80); self.loudnorm_tp_combo.pack(side="left",padx=5)
        ToolTip(self.loudnorm_tp_combo,"Le niveau maximal absolu que le son ne doit JAMAIS dépasser (True Peak).\n\n"
                "AUGMENTER (vers 0) = Autorise des pics plus forts.\nRisque de distorsion/grésillement (clipping).\n"
                "RÉDUIRE (vers -9) = Plus de marge de sécurité.\nSon un peu moins fort mais garanti sans distorsion.\n\n"
                "Recommandations :\n"
                "• -1.0 dB : Standard broadcast — bon compromis (RECOMMANDÉ)\n"
                "• -2.0 dB : Extra sécurité, idéal pour les amplis sensibles\n"
                "• 0.0 dB : Aucune marge — déconseillé (risque de clipping)")

        af=ctk.CTkFrame(mpf); af.pack(fill='x',pady=10); ctk.CTkLabel(af,text=T('adv_title'),font=("Arial",11,"bold")).pack(pady=5)
        ti=ctk.CTkFrame(af,fg_color="transparent"); ti.pack(pady=5)
        ctk.CTkLabel(ti,text=T('lbl_analyze_dur')).grid(row=0,column=0,padx=2,sticky="e")
        self.analyze_duration_combo=ctk.CTkOptionMenu(ti,values=['10M','20M','50M','80M','100M','200M'],width=90)
        self.analyze_duration_combo.set(self.settings.get('analyze_duration','80M')); self.analyze_duration_combo.grid(row=0,column=1,padx=2)
        ToolTip(self.analyze_duration_combo,"Combien de temps (en octets) FFmpeg analyse le fichier pour détecter son format.\n\n"
                "AUGMENTER = FFmpeg lit plus de données avant de commencer.\nCorrige les erreurs 'Format not found' ou 'Invalid data'.\n"
                "RÉDUIRE = Démarrage plus rapide mais risque d'erreur sur certains fichiers.\n\n"
                "80M convient à 99% des fichiers. Montez à 200M si vous avez des fichiers exotiques.")
        ctk.CTkLabel(ti,text=T('lbl_probe_size')).grid(row=0,column=2,padx=2,sticky="e")
        self.probe_size_combo=ctk.CTkOptionMenu(ti,values=['10M','20M','50M','60M','80M','100M'],width=90)
        self.probe_size_combo.set(self.settings.get('probe_size','60M')); self.probe_size_combo.grid(row=0,column=3,padx=2)
        ToolTip(self.probe_size_combo,"Quantité de données que FFmpeg lit au début du fichier pour en comprendre la structure.\n\n"
                "AUGMENTER = Meilleure détection du format, mais plus lent au démarrage.\n"
                "RÉDUIRE = Plus rapide, mais peut échouer sur des fichiers mal formés.\n\n"
                "60M est un bon défaut. Augmentez si vous avez des erreurs au lancement du traitement.")
        ctk.CTkLabel(ti,text=T('lbl_async')).grid(row=0,column=4,padx=2,sticky="e")
        self.async_combo=ctk.CTkOptionMenu(ti,values=['On','Off'],width=90); self.async_combo.grid(row=0,column=5,padx=2)
        ToolTip(self.async_combo,"Corrige automatiquement les petits décalages entre l'audio et la vidéo.\n\n"
                "ON : FFmpeg étire ou compresse très légèrement le son pour le recaler.\n"
                "     Recommandé si vos fichiers viennent de rips DVD/Blu-ray.\n\n"
                "OFF : Aucune correction. Le son est copié tel quel.\n"
                "     Utilisez OFF si vous traitez de la musique pure (pas de vidéo).")
        ctk.CTkLabel(ti,text=T('lbl_resampler')).grid(row=0,column=6,padx=2,sticky="e")
        self.resampler_combo=ctk.CTkOptionMenu(ti,values=['soxr','swr'],width=90); self.resampler_combo.grid(row=0,column=7,padx=2)
        ToolTip(self.resampler_combo,"Le moteur utilisé pour convertir la fréquence d'échantillonnage du son.\n\n"
                "• soxr : Haute qualité (SoX Resampler). Produit un son plus propre\n"
                "          et plus fidèle à l'original. RECOMMANDÉ.\n"
                "          ⚠ Nécessite la build FFmpeg 'Full' (pas la version 'essentials').\n\n"
                "• swr : Le resampler standard de FFmpeg (Software Resampler).\n"
                "        Un peu moins précis mais fonctionne avec toutes les builds FFmpeg.\n"
                "        Utilisez swr si soxr provoque une erreur.")
        ctk.CTkLabel(ti,text=T('lbl_min_comp')).grid(row=0,column=8,padx=2,sticky="e")
        self.min_hard_comp_entry=ctk.CTkEntry(ti,width=80); self.min_hard_comp_entry.insert(0,self.settings.get('min_hard_comp','0.100000')); self.min_hard_comp_entry.grid(row=0,column=9,padx=2)
        ToolTip(self.min_hard_comp_entry,"Seuil à partir duquel FFmpeg applique une correction 'dure' de la synchronisation.\n\n"
                "Valeur par défaut : 0.100000 (100 ms)\n"
                "En dessous de ce seuil, FFmpeg étire doucement le son.\n"
                "Au-dessus, il coupe ou insère du silence pour recaler.\n\n"
                "⚠ Ne modifiez cette valeur que si vous avez des problèmes\nde décalage audio/vidéo persistants.")
        ctk.CTkLabel(ti,text=T('lbl_first_pts')).grid(row=0,column=10,padx=2,sticky="e")
        self.first_pts_entry=ctk.CTkEntry(ti,width=80); self.first_pts_entry.insert(0,self.settings.get('first_pts','0')); self.first_pts_entry.grid(row=0,column=11,padx=2)
        ToolTip(self.first_pts_entry,"Force le timestamp de début du son à la valeur indiquée.\n\n"
                "Valeur par défaut : 0 (le son commence au tout début)\n\n"
                "Utile si le son de votre fichier ne démarre pas à 0 seconde\n"
                "(fréquent avec les pistes audio extraites de fichiers MKV ou MP4).\n"
                "Dans la plupart des cas, laissez 0.")

        ctk.CTkLabel(mpf,text=T('lbl_custom_params')).pack(pady=(10,0))
        self.custom_params_entry=ctk.CTkEntry(mpf,width=500,placeholder_text=T('custom_params_ph')); self.custom_params_entry.pack(pady=5)
        ToolTip(self.custom_params_entry,"Zone réservée aux utilisateurs avancés.\n\n"
                "Permet d'ajouter des arguments FFmpeg personnalisés qui seront\n"
                "ajoutés à la commande d'encodage.\n\n"
                "Exemples :\n"
                "• -af 'bass=g=5' : Augmente les basses de 5 dB\n"
                "• -af 'highpass=f=200' : Coupe les fréquences en dessous de 200 Hz\n"
                "• -ac 2 : Force la sortie en stéréo\n"
                "• -map 0:a:1 : Sélectionne la 2ème piste audio\n\n"
                "Laissez vide si vous ne savez pas ce que c'est.")
        self.codec_specific_frame=ctk.CTkFrame(mpf); self.codec_specific_frame.pack(fill='x',pady=10)
        self.update_codec_params(); self.toggle_loudness_visibility()

        # PRESETS
        self.presets_tab=self.notebook.add(T('tab_presets'))
        
        # Presets intégrés (rapides, one-click)
        bif = ctk.CTkFrame(self.presets_tab); bif.pack(fill="x", pady=10, padx=20)
        ctk.CTkLabel(bif, text=T('presets_builtin_title'), font=("Arial", 12, "bold")).pack(pady=5)
        
        BUILT_IN_PRESETS = {
            "🎬 Série 5.1 (EAC3 640k)": {
                'codec': 'Dolby Digital Plus', 'bitrate': '640', 'sample_rate': '48000',
                'surround_mode': '5.1', 'loudnorm': True, 'dialnorm': True,
                'desc': 'Idéal pour les séries/films en 5.1 : EAC3 à 640k (Dolby Digital Plus), dialnorm -31dB, loudnorm EBU R128.'
            },
            "🎬 Série 2.0 (EAC3 256k)": {
                'codec': 'Dolby Digital Plus', 'bitrate': '256', 'sample_rate': '48000',
                'surround_mode': '2.0', 'loudnorm': True, 'dialnorm': True,
                'desc': 'Série ou film en stéréo : EAC3 256k, dialnorm -31dB, loudnorm EBU R128. Bon compromis qualité/taille.'
            },
            "🎙️ Podcast/VO (AAC 192k)": {
                'codec': 'AAC', 'bitrate': '192', 'sample_rate': '48000',
                'surround_mode': '2.0', 'loudnorm': True, 'dialnorm': False,
                'desc': 'Podcast ou version originale : AAC 192k stéréo, loudnorm -16 LUFS (standard streaming). Compatible partout.'
            },
            "🎵 Musique HQ (Opus 256k)": {
                'codec': 'Opus', 'bitrate': '256', 'sample_rate': '48000',
                'surround_mode': '2.0', 'loudnorm': False, 'dialnorm': False,
                'desc': 'Musique haute qualité en Opus 256k stéréo. Excellent rapport qualité/taille, supérieur à MP3 320k.'
            },
            "🌐 Web léger (Opus 128k)": {
                'codec': 'Opus', 'bitrate': '128', 'sample_rate': '48000',
                'surround_mode': '2.0', 'loudnorm': True, 'dialnorm': False,
                'desc': 'Audio pour le web : Opus 128k stéréo, loudnorm -16 LUFS. Fichiers petits, qualité excellente.'
            },
            "🎼 Archive FLAC (sans perte)": {
                'codec': 'FLAC', 'bitrate': '192', 'sample_rate': '48000',
                'surround_mode': 'same', 'loudnorm': False, 'dialnorm': False,
                'desc': 'Archivage sans perte : FLAC à la même config que la source. Aucune dégradation, fichier plus gros.'
            },
        }
        
        # Afficher les presets en grille 2 colonnes
        grid = ctk.CTkFrame(bif, fg_color="transparent"); grid.pack(pady=5)
        for i, (name, params) in enumerate(BUILT_IN_PRESETS.items()):
            btn = ctk.CTkButton(grid, text=name, width=260, height=32,
                command=lambda p=params, n=name: self._apply_builtin_preset(p, n),
                fg_color='#0066ff' if i%2==0 else '#008000')
            btn.grid(row=i//2, column=i%2, padx=6, pady=3)
            ToolTip(btn, params['desc'])
        
        # Presets personnels (existants)
        pf=ctk.CTkFrame(self.presets_tab,fg_color="transparent"); pf.pack(expand=True, pady=10)
        ctk.CTkLabel(pf,text=T('presets_custom_title'), font=("Arial", 12, "bold")).pack(pady=5)
        ctk.CTkLabel(pf,text=T('lbl_preset_name')).pack(pady=5); self.preset_name_entry=ctk.CTkEntry(pf,width=200); self.preset_name_entry.pack(pady=5)
        ToolTip(self.preset_name_entry,"Donnez un nom à votre configuration actuelle pour la retrouver facilement.\nExemple : 'Série TV - AC3 448k 5.1' ou 'Podcast - AAC 128k Stéréo'")
        self.preset_combo=ctk.CTkOptionMenu(pf,values=list(self.presets.keys()) or ["Aucun"],width=200); self.preset_combo.pack(pady=10)
        ToolTip(self.preset_combo,"Liste de vos préréglages sauvegardés.\nSélectionnez-en un puis cliquez 'Charger' pour restaurer ses paramètres.")
        pbf=ctk.CTkFrame(pf,fg_color="transparent"); pbf.pack(pady=10)
        svb=ctk.CTkButton(pbf,text=T('btn_preset_save'),command=self.save_preset,fg_color='#0066ff'); svb.pack(side="left",padx=5)
        ToolTip(svb,"Enregistre TOUS les paramètres actuels (codec, bitrate, loudnorm, etc.)\nsous le nom que vous avez tapé ci-dessus.")
        ldb=ctk.CTkButton(pbf,text=T('btn_preset_load'),command=self.load_preset,fg_color='#008000'); ldb.pack(side="left",padx=5)
        ToolTip(ldb,"Restaure les paramètres du préréglage sélectionné dans la liste.\nTous les réglages de l'onglet 'Paramètres d'encodage' seront remplacés.")
        deb=ctk.CTkButton(pbf,text=T('btn_preset_delete'),command=self.delete_preset,fg_color='#FF0000'); deb.pack(side="left",padx=5)
        ToolTip(deb,"Supprime définitivement le préréglage sélectionné de la liste.")

        # OPTIONS
        self.options_tab=self.notebook.add("Options"); oframe=ctk.CTkFrame(self.options_tab,fg_color="transparent"); oframe.pack(expand=True,fill="both",padx=50)
        ctk.CTkLabel(oframe,text=T('lbl_ffmpeg_path')).pack(anchor="w")
        fff=ctk.CTkFrame(oframe,fg_color="transparent"); fff.pack(fill="x",pady=5)
        self.ffmpeg_path_entry=ctk.CTkEntry(fff); self.ffmpeg_path_entry.pack(side="left",fill="x",expand=True)
        self.ffmpeg_path_entry.insert(0,self.settings.get('ffmpeg_path',self.find_executable('ffmpeg') or 'ffmpeg'))
        ToolTip(self.ffmpeg_path_entry,"Le chemin complet vers le fichier ffmpeg.exe sur votre ordinateur.\n\n"
                "FFmpeg est le moteur qui effectue toutes les conversions audio.\n"
                "Si FFmpeg est dans le PATH de Windows, vous pouvez juste écrire 'ffmpeg'.\n"
                "Sinon, cliquez '...' pour naviguer jusqu'au fichier.")
        ctk.CTkButton(fff,text="...",width=40,command=self.browse_ffmpeg,fg_color='#008000').pack(side="left",padx=3)
        tb=ctk.CTkButton(fff,text="Test",width=50,command=self.test_ffmpeg_ffprobe,fg_color='#0066ff'); tb.pack(side="left",padx=3)
        ToolTip(tb,"Vérifie que FFmpeg et FFprobe fonctionnent correctement\net affiche les versions installées et disponibles en ligne.")
        ub=ctk.CTkButton(fff,text="📥 Mise à jour",width=90,command=self.update_ffmpeg,fg_color='#FFA500'); ub.pack(side="left",padx=3)
        ToolTip(ub,"Installe ou met à jour FFmpeg.\n\n"
                "3 options disponibles :\n"
                "• Release Full (WinGet) : Stable, tous les codecs — RECOMMANDÉ\n"
                "• Essentials (WinGet) : Allégée, sans soxr\n"
                "• Git Master Full (Téléchargement) : Dernière version, tous les codecs\n"
                "   Téléchargée depuis gyan.dev, extraite avec WinRAR/7-Zip/Win11")

        ctk.CTkLabel(oframe,text=T('lbl_ffprobe_path')).pack(anchor="w")
        fpf=ctk.CTkFrame(oframe,fg_color="transparent"); fpf.pack(fill="x",pady=5)
        self.ffprobe_path_entry=ctk.CTkEntry(fpf); self.ffprobe_path_entry.pack(side="left",fill="x",expand=True)
        self.ffprobe_path_entry.insert(0,self.settings.get('ffprobe_path',self.find_executable('ffprobe') or 'ffprobe'))
        ToolTip(self.ffprobe_path_entry,"Le chemin vers ffprobe.exe — un outil compagnon de FFmpeg\nqui analyse les fichiers audio/vidéo pour en extraire les informations\n(durée, codec, bitrate, nombre de canaux, etc.).\n\nIl est toujours fourni avec FFmpeg dans le même dossier.")
        ctk.CTkButton(fpf,text="...",width=40,command=self.browse_ffprobe,fg_color='#008000').pack(side="left",padx=3)

        ctk.CTkLabel(oframe,text=T('lbl_output_dir')).pack(anchor="w")
        odf=ctk.CTkFrame(oframe,fg_color="transparent"); odf.pack(fill="x",pady=5)
        self.output_dir_entry=ctk.CTkEntry(odf); self.output_dir_entry.pack(side="left",fill="x",expand=True)
        self.output_dir_entry.insert(0,self.settings.get('output_dir',''))
        ToolTip(self.output_dir_entry,"Le dossier où seront enregistrés les fichiers convertis.\n\n"
                "Si vous laissez ce champ VIDE : les fichiers convertis seront créés\nà côté des fichiers originaux (dans le même dossier).\n\n"
                "Si vous spécifiez un dossier : TOUS les fichiers convertis iront dedans,\nquel que soit l'emplacement des originaux.")
        ctk.CTkButton(odf,text="...",width=40,command=self.browse_output_dir,fg_color='#008000').pack(side="left",padx=3)

        opts=ctk.CTkFrame(oframe,fg_color="transparent"); opts.pack(fill="x",pady=15)
        ctk.CTkLabel(opts,text=T('lbl_cpu_cores')).pack(side=tk.LEFT,padx=(0,3))
        self.max_workers_entry=ctk.CTkEntry(opts,width=35); self.max_workers_entry.insert(0,self.settings.get('max_workers','12')); self.max_workers_entry.pack(side=tk.LEFT,padx=3)
        ToolTip(self.max_workers_entry,"Le nombre de fichiers qui seront convertis en même temps.\n\nAUGMENTER = Plus rapide mais utilise plus de CPU/RAM.\nRÉDUIRE = Plus lent mais moins gourmand.\n\nRecommandation : moitié du nombre de cœurs CPU. Max: 32.")
        pp=ctk.CTkCheckBox(opts,text=T('chk_parallel'),variable=self.parallel_processing_var,width=130); pp.pack(side=tk.LEFT,padx=6)
        ToolTip(pp,"ACTIVÉ : Convertit plusieurs fichiers en même temps (rapide).\nLe nombre est défini par 'Cœurs CPU' ci-dessus.\n\nDÉSACTIVÉ : Convertit un par un, dans l'ordre (plus stable, logs lisibles).")
        ctk.CTkLabel(opts,text=T('lbl_accent_color')).pack(side=tk.LEFT,padx=3)
        self.color_theme_combo=ctk.CTkOptionMenu(opts,values=['red','pink','autumn','yellow','lavender','orange','cherry','violet','green','blue','dark-blue'],command=self.change_color_theme,width=95)
        self.color_theme_combo.set(self.color_theme); self.color_theme_combo.pack(side=tk.LEFT,padx=3)
        ToolTip(self.color_theme_combo,"Change la couleur des boutons et barres de progression.\n11 thèmes : 8 custom + 3 intégrés (green, blue, dark-blue).")
        tc=ctk.CTkCheckBox(opts,text=T('chk_light_mode'),variable=self.theme_var,onvalue="light",offvalue="dark",command=self.change_theme,width=80); tc.pack(side=tk.LEFT,padx=6)
        ToolTip(tc,"ACTIVÉ : Mode clair (fond blanc).\nDÉSACTIVÉ : Mode sombre (fond noir).")
        sc=ctk.CTkCheckBox(opts,text=T('chk_sounds'),variable=self.enable_sounds_var,width=50); sc.pack(side=tk.LEFT,padx=6)
        ToolTip(sc,"ACTIVÉ : Joue un son en fin de batch :\n• Succès = tout OK\n• Avertissement = certains ont échoué\n• Erreur = tous ont échoué\n\nDÉSACTIVÉ : Aucun son.")
        ctk.CTkLabel(opts,text="Volume :").pack(side=tk.LEFT,padx=2)
        vs=ctk.CTkSlider(opts,from_=0.0,to=1.0,variable=self.sound_volume_var,width=70,command=lambda v:None); vs.pack(side=tk.LEFT,padx=2)
        ToolTip(vs,"Volume des sons de notification.\nGlissez à droite pour augmenter.")
        tsb=ctk.CTkButton(opts,text="🔊 Test",width=50,command=lambda:self.play_sound("success"),fg_color="gray"); tsb.pack(side=tk.LEFT,padx=2)
        ToolTip(tsb,"Joue le son de succès pour tester le volume.")
        tch=ctk.CTkCheckBox(opts,text=T('chk_toast'),variable=self.enable_toast_var,width=200); tch.pack(side=tk.LEFT,padx=6)

        # Language selector
        opts2=ctk.CTkFrame(oframe,fg_color="transparent"); opts2.pack(fill="x",pady=(0,10))
        ctk.CTkLabel(opts2,text=T('lbl_language')).pack(side=tk.LEFT,padx=(0,5))
        self.language_combo=ctk.CTkOptionMenu(opts2,values=['Français (fr)','English (en)'],width=150,
            command=self._on_language_change)
        self.language_combo.set('English (en)' if get_lang()=='en' else 'Français (fr)')
        self.language_combo.pack(side=tk.LEFT,padx=3)
        ToolTip(tch,"ACTIVÉ : Notification Windows (bulle en bas à droite)\nquand un batch se termine.\nPrévient même si l'app est en arrière-plan.\n\nDÉSACTIVÉ : Pas de notification Windows.\n\n⚠ Nécessite : pip install windows-toasts")

        # ABOUT
        self.about_tab=self.notebook.add(T('tab_about'))
        self.about_canvas=ctk.CTkCanvas(self.about_tab,highlightthickness=0); self.about_canvas.pack(fill='both',expand=True)
        self.about_canvas.bind("<Configure>",self.resize_about_image)

        # BOTTOM BAR
        self.progress_frame=ctk.CTkFrame(self.root,width=800,height=70); self.progress_frame.pack(fill='x',side='bottom',pady=(5,15),padx=20); self.progress_frame.pack_propagate(False)
        self.global_progress=ctk.CTkProgressBar(self.progress_frame,width=300,progress_color='green',mode='determinate')
        self.global_progress.pack(side=tk.LEFT,padx=15,fill='x',expand=True); self.global_progress.set(0)
        lf2=ctk.CTkFrame(self.progress_frame,width=450,height=30,fg_color="transparent"); lf2.pack(side=tk.LEFT,padx=5); lf2.pack_propagate(False)
        self.global_progress_label=ctk.CTkLabel(lf2,text=T('status_waiting'),anchor="w"); self.global_progress_label.pack(fill='both',expand=True)
        lb=ctk.CTkButton(self.progress_frame,text=T('btn_start'),command=self.start_processing,fg_color='#00DC59',text_color='#333333',width=140); lb.pack(side=tk.LEFT,padx=8)
        ToolTip(lb,"Lance la conversion de TOUS les fichiers présents dans la liste d'entrée (onglet Input).\n\n"
                   "Avant de cliquer, vérifiez :\n"
                   "• Que la liste contient bien vos fichiers\n"
                   "• Que les paramètres d'encodage sont corrects (onglet Paramètres)\n"
                   "• Que l'indicateur de validation est vert (✓)\n\n"
                   "La progression s'affiche dans la barre ci-dessus\net dans la barre des tâches Windows.")
        self.pause_btn=ctk.CTkButton(self.progress_frame,text=T('btn_pause'),command=self.toggle_pause,fg_color='#FFA500',text_color='white',width=90); self.pause_btn.pack(side=tk.LEFT,padx=8)
        ToolTip(self.pause_btn,"Met le traitement en pause.\n\n"
                "Le fichier actuellement en cours de conversion finira d'abord,\npuis aucun nouveau fichier ne sera lancé jusqu'à ce que vous cliquiez 'Reprendre'.\n\n"
                "La barre des tâches Windows passera en jaune (pause).")
        sb2=ctk.CTkButton(self.progress_frame,text=T('btn_stop'),command=self.cancel_process,fg_color='#FF0000',text_color='white',width=100); sb2.pack(side=tk.LEFT,padx=8)
        ToolTip(sb2,"Annule IMMÉDIATEMENT tous les traitements en cours.\n\n"
                "Les fichiers en cours d'encodage seront interrompus.\n"
                "Les fichiers déjà terminés ne sont pas affectés.\n"
                "Les fichiers temporaires (.wav) seront nettoyés.\n\n"
                "La barre des tâches Windows passera en rouge (erreur).\n"
                "Les fichiers restants pourront être repris au prochain lancement\ngrâce à la fonction de reprise après crash.")
        self.root.bind("<Configure>",self.debounced_update_progress_width)

    # ===================== ACTIONS =====================
    def play_sound(self, t):
        if not HAS_AUDIO or not self.enable_sounds_var.get(): return
        try:
            sf=resource_path(os.path.join("Assets",f"{t}.wav"))
            if os.path.exists(sf): s=pygame.mixer.Sound(sf); s.set_volume(self.sound_volume_var.get()); s.play()
        except Exception as e: print(f"Son: {e}")
    def browse_ffmpeg(self):
        p=filedialog.askopenfilename(title="Sélectionner ffmpeg.exe",filetypes=[("Exécutable","*.exe"),("Tous","*.*")])
        if p: self.ffmpeg_path_entry.delete(0,tk.END); self.ffmpeg_path_entry.insert(0,p)
    def browse_ffprobe(self):
        p=filedialog.askopenfilename(title="Sélectionner ffprobe.exe",filetypes=[("Exécutable","*.exe"),("Tous","*.*")])
        if p: self.ffprobe_path_entry.delete(0,tk.END); self.ffprobe_path_entry.insert(0,p)
    def browse_output_dir(self):
        p=filedialog.askdirectory(title="Sélectionner le dossier de sortie")
        if p: self.output_dir_entry.delete(0,tk.END); self.output_dir_entry.insert(0,p)
    def add_files(self):
        files = list(filedialog.askopenfilenames(title="Sélectionner des fichiers audio ou vidéo",
            filetypes=[("Fichiers audio/vidéo","*.flac *.wav *.mp3 *.aac *.ogg *.m4a *.thd *.dts *.mkv *.mp4 *.avi *.ts"),("Tous les fichiers","*.*")]))
        if not files: return
        
        # Séparer conteneurs multi-pistes des fichiers audio simples
        container_exts = {'.mkv', '.mp4', '.avi', '.ts', '.m2ts'}
        containers = [f for f in files if os.path.splitext(f)[1].lower() in container_exts]
        audio_files = [f for f in files if os.path.splitext(f)[1].lower() not in container_exts]
        
        # Ajouter les fichiers audio simples directement
        for f in audio_files:
            if is_audio_file(self, f): self.file_list.insert(tk.END, f)
        
        # Traiter les conteneurs
        if not containers: return
        
        # Analyser le premier conteneur pour voir s'il a plusieurs pistes
        first_tracks = get_audio_tracks(self, containers[0])
        
        if len(containers) == 1:
            # Un seul conteneur : sélecteur classique
            if len(first_tracks) > 1:
                self._show_track_picker(containers[0], first_tracks)
            elif len(first_tracks) == 1:
                self.file_list.insert(tk.END, containers[0])
            else:
                messagebox.showinfo("Information", f"Aucune piste audio dans :\n{os.path.basename(containers[0])}")
        else:
            # Plusieurs conteneurs : proposer le mode batch
            if len(first_tracks) > 1:
                self._show_batch_track_picker(containers, first_tracks)
            else:
                # Tous avec une seule piste ou sans piste : ajout direct
                for f in containers:
                    tracks = get_audio_tracks(self, f)
                    if tracks: self.file_list.insert(tk.END, f)

    def _show_track_picker(self, filepath, tracks):
        """Sélection de pistes pour UN SEUL fichier."""
        pw = ctk.CTkToplevel(self.root); pw.title(f"Pistes audio — {os.path.basename(filepath)}")
        self.center_toplevel(pw, 800, 560); pw.attributes("-topmost", True); pw.grab_set()
        
        ctk.CTkLabel(pw, text=f"Le fichier contient {len(tracks)} piste(s) audio.\nCochez celles que vous souhaitez encoder :",
                     font=("Arial", 13, "bold"), justify="left").pack(padx=20, pady=10)
        
        # Détermine quelles pistes auto-cocher basé sur la langue préférée
        preferred = self.preferred_language.lower() if self.preferred_language else ''
        has_preferred = any(t.get('language','').lower() == preferred for t in tracks)
        
        sf = ctk.CTkScrollableFrame(pw, height=200); sf.pack(fill="both", expand=True, padx=20, pady=5)
        track_vars = []
        for t in tracks:
            # Si une piste correspond à la langue préférée, seule celle-ci est cochée
            # Sinon, toutes sont cochées (comportement par défaut)
            default_checked = (t.get('language','').lower() == preferred) if has_preferred else True
            var = ctk.BooleanVar(value=default_checked)
            label = self._format_track_label(t)
            if default_checked and has_preferred:
                label += "  ⭐"  # Marqueur visuel
            ctk.CTkCheckBox(sf, text=label, variable=var, font=("Consolas", 11)).pack(fill="x", padx=5, pady=3)
            track_vars.append((var, t))
        
        # Sélecteur de langue préférée
        lf = ctk.CTkFrame(pw, fg_color="transparent"); lf.pack(pady=5)
        ctk.CTkLabel(lf, text="🌐 Langue préférée (pré-cochée automatiquement) :", font=("Arial", 10)).pack(side="left", padx=5)
        lang_var = ctk.StringVar(value=self.preferred_language or 'fre')
        lang_options = ['fre', 'eng', 'jpn', 'ger', 'spa', 'ita', 'por', 'rus', 'kor', 'chi', '(aucune)']
        lc = ctk.CTkOptionMenu(lf, variable=lang_var, values=lang_options, width=90); lc.pack(side="left", padx=5)
        ToolTip(lc, "La langue cochée par défaut dans ce sélecteur.\nMémorisée entre les sessions.\nCodes ISO 639-2 : fre=Français, eng=Anglais, jpn=Japonais, etc.")
        
        ctk.CTkLabel(pw, text="Chaque piste cochée sera extraite puis encodée individuellement.",
                     font=("Arial", 10), text_color="gray").pack(padx=20, pady=5)
        bf = ctk.CTkFrame(pw, fg_color="transparent"); bf.pack(pady=10)
        
        def _add():
            # Mémoriser la langue préférée choisie
            chosen = lang_var.get()
            self.preferred_language = '' if chosen == '(aucune)' else chosen
            for var, t in track_vars:
                if var.get(): self.file_list.insert(tk.END, f"{filepath}|track:{t['index']}")
            pw.destroy()
        
        ctk.CTkButton(bf, text="Tout cocher", command=lambda: [v.set(True) for v,_ in track_vars], width=100, fg_color='#0066ff').pack(side="left", padx=5)
        ctk.CTkButton(bf, text="Tout décocher", command=lambda: [v.set(False) for v,_ in track_vars], width=100, fg_color='gray').pack(side="left", padx=5)
        ctk.CTkButton(bf, text="Ajouter les pistes cochées ✓", command=_add, width=200, fg_color='#008000').pack(side="left", padx=5)
        ctk.CTkButton(bf, text="Annuler", command=pw.destroy, width=80, fg_color='#FF4500').pack(side="left", padx=5)

    def _show_batch_track_picker(self, filepaths, reference_tracks):
        """Sélection de pistes pour PLUSIEURS fichiers d'un coup (ex: tous les épisodes d'une série).
        Analyse le premier fichier et propose d'appliquer la même sélection à tous.
        La langue préférée (ex: FR) est pré-cochée automatiquement."""
        pw = ctk.CTkToplevel(self.root); pw.title(f"Sélection de pistes — {len(filepaths)} fichiers")
        self.center_toplevel(pw, 850, 700); pw.attributes("-topmost", True); pw.grab_set()
        
        ctk.CTkLabel(pw, text=f"Vous avez sélectionné {len(filepaths)} fichiers conteneurs.\n"
                     f"Voici les pistes audio du premier fichier ({os.path.basename(filepaths[0])}).\n\n"
                     f"La même sélection sera appliquée à TOUS les fichiers :",
                     font=("Arial", 13, "bold"), justify="left").pack(padx=20, pady=10)
        
        # Auto-sélection basée sur la langue préférée
        preferred = self.preferred_language.lower() if self.preferred_language else ''
        has_preferred = any(t.get('language','').lower() == preferred for t in reference_tracks)
        
        sf = ctk.CTkScrollableFrame(pw, height=180); sf.pack(fill="both", expand=True, padx=20, pady=5)
        track_vars = []
        for t in reference_tracks:
            default_checked = (t.get('language','').lower() == preferred) if has_preferred else True
            var = ctk.BooleanVar(value=default_checked)
            label = self._format_track_label(t)
            if default_checked and has_preferred:
                label += "  ⭐"
            ctk.CTkCheckBox(sf, text=label, variable=var, font=("Consolas", 11)).pack(fill="x", padx=5, pady=3)
            track_vars.append((var, t))
        
        # Sélecteur de langue préférée
        lf = ctk.CTkFrame(pw, fg_color="transparent"); lf.pack(pady=5)
        ctk.CTkLabel(lf, text="🌐 Langue préférée (pré-cochée automatiquement) :", font=("Arial", 10)).pack(side="left", padx=5)
        lang_var = ctk.StringVar(value=self.preferred_language or 'fre')
        lang_options = ['fre', 'eng', 'jpn', 'ger', 'spa', 'ita', 'por', 'rus', 'kor', 'chi', '(aucune)']
        lc = ctk.CTkOptionMenu(lf, variable=lang_var, values=lang_options, width=90); lc.pack(side="left", padx=5)
        ToolTip(lc, "La langue cochée par défaut dans ce sélecteur.\nMémorisée entre les sessions.\nCodes ISO 639-2 : fre=Français, eng=Anglais, jpn=Japonais, etc.")
        
        # Liste des fichiers concernés
        ff = ctk.CTkFrame(pw); ff.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(ff, text="Fichiers concernés :", font=("Arial", 11, "bold")).pack(anchor="w", padx=5)
        fl = ctk.CTkScrollableFrame(ff, height=80); fl.pack(fill="x", padx=5, pady=3)
        for f in filepaths:
            ctk.CTkLabel(fl, text=f"  • {os.path.basename(f)}", font=("Arial", 10), anchor="w").pack(fill="x")
        
        ctk.CTkLabel(pw, text="⚠ Si un fichier n'a pas la piste demandée, il sera ignoré pour cette piste.",
                     font=("Arial", 10), text_color="#FFA500").pack(padx=20, pady=3)
        
        bf = ctk.CTkFrame(pw, fg_color="transparent"); bf.pack(pady=10)
        
        def _add_batch():
            chosen = lang_var.get()
            self.preferred_language = '' if chosen == '(aucune)' else chosen
            selected_indices = [t['index'] for var, t in track_vars if var.get()]
            count = 0
            for fp in filepaths:
                fp_tracks = get_audio_tracks(self, fp)
                fp_indices = {t['index'] for t in fp_tracks}
                for idx in selected_indices:
                    if idx in fp_indices:
                        self.file_list.insert(tk.END, f"{fp}|track:{idx}")
                        count += 1
            pw.destroy()
            if count > 0:
                messagebox.showinfo("Pistes ajoutées", 
                    f"{count} piste(s) ajoutée(s) à la file d'attente\n"
                    f"pour {len(filepaths)} fichier(s).")
        
        ctk.CTkButton(bf, text="Tout cocher", command=lambda: [v.set(True) for v,_ in track_vars], width=100, fg_color='#0066ff').pack(side="left", padx=5)
        ctk.CTkButton(bf, text="Tout décocher", command=lambda: [v.set(False) for v,_ in track_vars], width=100, fg_color='gray').pack(side="left", padx=5)
        ctk.CTkButton(bf, text=f"Appliquer à {len(filepaths)} fichiers ✓", command=_add_batch, width=220, fg_color='#008000').pack(side="left", padx=5)
        ctk.CTkButton(bf, text="Annuler", command=pw.destroy, width=80, fg_color='#FF4500').pack(side="left", padx=5)

    def _format_track_label(self, t):
        """Formate le label d'une piste audio pour l'affichage."""
        ch_str = f"{t['channels']}ch" if t['channels'] else "?"
        layout = f" ({t['channel_layout']})" if t['channel_layout'] else ""
        label = (f"Piste #{t['index']}  —  [{t['language'].upper()}]  "
                 f"{t['codec'].upper()} {ch_str}{layout}  "
                 f"@ {t['bitrate']}  {t['sample_rate']} Hz")
        if t['title']:
            label += f'  — "{t["title"]}"'
        return label

    def add_folder(self):
        d=filedialog.askdirectory(title="Sélectionner un dossier contenant des fichiers audio")
        if d:
            count=0
            for f in glob.glob(os.path.join(d,"**/*.*"),recursive=True):
                if is_audio_file(self,f): self.file_list.insert(tk.END,f); count+=1
            if count==0: messagebox.showinfo("Information",f"Aucun fichier audio trouvé dans :\n{d}")
    def remove_selected(self):
        for i in self.file_list.curselection()[::-1]: self.file_list.delete(i)
    def clear_files(self): self.file_list.delete(0,tk.END)
    def move_file_up(self):
        for i in (self.file_list.curselection() or []):
            if i==0: continue
            t=self.file_list.get(i); self.file_list.delete(i); self.file_list.insert(i-1,t); self.file_list.select_set(i-1)
    def move_file_down(self):
        for i in reversed(self.file_list.curselection() or []):
            if i==self.file_list.size()-1: continue
            t=self.file_list.get(i); self.file_list.delete(i); self.file_list.insert(i+1,t); self.file_list.select_set(i+1)
    def validate_parameters(self):
        try:
            mw=int(self.max_workers_entry.get())
            if mw<1 or mw>32: raise ValueError("Le nombre de cœurs CPU doit être entre 1 et 32.")
            ff=self.ffmpeg_path_entry.get(); fp=self.ffprobe_path_entry.get()
            if not os.path.exists(ff) and not shutil.which(ff): raise FileNotFoundError("FFmpeg introuvable ! Vérifiez le chemin dans l'onglet Options.")
            if not os.path.exists(fp) and not shutil.which(fp): raise FileNotFoundError("FFprobe introuvable ! Vérifiez le chemin dans l'onglet Options.")
            return True
        except Exception as e: messagebox.showerror("Erreur de configuration",str(e)); return False

    def start_processing(self):
        if not self.validate_parameters(): return
        files=list(self.file_list.get(0,tk.END))
        if not files: messagebox.showwarning("Attention","La liste de fichiers est vide !\nAjoutez des fichiers dans l'onglet Input avant de lancer."); return
        self.output_text.delete(1.0,"end"); self.global_progress.set(0); self.cancel_processing=False
        self.taskbar.set_state_normal(); self.taskbar.set_progress(0,100)
        self.save_crash_recovery(files,{'codec':self.codec_var.get(),'bitrate':self.bitrate_combo.get(),'sample_rate':self.sample_rate_combo.get()})
        for f in files: self.output_text.insert("end",f"{os.path.basename(f)} : En attente...\n")
        with self.data_lock:
            self.progress_values={f:0 for f in files}; self.speeds={f:'N/A' for f in files}
            self.target_bitrates={f:f"{self.bitrate_combo.get()} kbps" for f in files}; self.real_bitrates={f:"N/A" for f in files}
            self.bitrates={f:f"Cible: {self.bitrate_combo.get()} kbps" for f in files}
            self.current_steps={f:"Préparation" for f in files}; self.file_indices={f:i+1 for i,f in enumerate(files)}
        self.start_time=time.time()
        for w in self.progress_pane.winfo_children(): w.destroy()
        self.progress_bars.clear()
        for f in files:
            l=ctk.CTkLabel(self.progress_pane,text=f"{os.path.basename(f)} - 0%",anchor="w"); l.pack(fill='x',padx=5,pady=(5,0))
            pb=ctk.CTkProgressBar(self.progress_pane,width=450,progress_color='blue'); pb.pack(fill='x',padx=5,pady=(0,5))
            self.progress_bars[f]=(pb,l); self.file_queue.put(f)
        threading.Thread(target=self.process_queue,daemon=True).start()

    def process_queue(self):
        mw=min(int(self.max_workers_entry.get() or 12),multiprocessing.cpu_count())
        ok,err,files=[],[],[]
        while not self.file_queue.empty(): files.append(self.file_queue.get())
        if self.parallel_processing_var.get():
            with ThreadPoolExecutor(max_workers=mw) as ex:
                fut=[ex.submit(process_file,self,x,*self.progress_bars[x]) for x in files]
                for ft in as_completed(fut):
                    if self.cancel_processing: break
                    fi,o,s=ft.result()
                    if s: ok.append(fi); self.update_crash_recovery(completed=fi)
                    else: err.append(fi); self.update_crash_recovery(failed=fi)
                    self.update_queue.put(lambda o=o,s=s: self.output_text.insert("end",o,"success" if s else "error"))
        else:
            for x in files:
                if self.cancel_processing: break
                self.pause_event.wait()
                try:
                    _,o,s=process_file(self,x,*self.progress_bars[x])
                    if s: ok.append(x); self.update_crash_recovery(completed=x)
                    else: err.append(x); self.update_crash_recovery(failed=x)
                    self.update_queue.put(lambda o=o,s=s: self.output_text.insert("end",o,"success" if s else "error"))
                except Exception as e: err.append(x); self.update_crash_recovery(failed=x)
        if self.cancel_processing: self.update_queue.put(self.taskbar.set_state_off)
        else: self.clear_crash_recovery()
        # Reset titre
        self.update_queue.put(lambda: self.root.title(T('window_title', version=self.VERSION)))
        t=len(ok)+len(err)
        if err: self.send_toast("Encodage terminé",f"{len(ok)}/{t} fichiers réussis, {len(err)} en erreur")
        else: self.send_toast("Encodage terminé ✓",f"Les {t} fichiers ont été encodés avec succès !")
        self.update_queue.put(lambda s=ok,e=err: self.show_summary_window(s,e,time.time()-self.start_time))
        if not self.cancel_processing:
            total=len(ok)+len(err); elapsed=time.time()-self.start_time
            def _final_progress(t=total, el=elapsed, nok=len(ok), nerr=len(err)):
                self.global_progress.set(1.0)
                self.taskbar.set_progress(100,100)
                status = T('status_ok') if nerr==0 else T('status_partial', ok=nok, total=t)
                self.global_progress_label.configure(
                    text=T('progress_final', done=t, total=t, status=status, elapsed=self.format_time(el)))
                self.root.title(T('window_title_done', version=self.VERSION))
            self.update_queue.put(_final_progress)

    def update_global_progress(self, total):
        with self.data_lock:
            done=sum(1 for v in self.progress_values.values() if v>=100)
            pct=(sum(self.progress_values.values())/(total*100))*100 if total>0 else 0
            if done==total: pct=100
            el=time.time()-self.start_time; rem=(el/pct*100-el) if pct>0 else 0
            ss=0;vn=0
            for f in self.progress_values:
                sp=self.speeds.get(f,'N/A')
                if sp!='N/A':
                    try: ss+=float(sp.replace('x','')); vn+=1
                    except: pass
            avg=ss/vn if vn>0 else 0
        txt=T('progress_txt', done=done, total=total, pct=int(pct), avg=avg, elapsed=self.format_time(el), rem=self.format_time(rem))
        title_pct = int(pct)
        self.update_queue.put(lambda p=pct:self.global_progress.set(p/100))
        self.update_queue.put(lambda p=pct:self.taskbar.set_progress(p,100))
        self.update_queue.put(lambda t=txt:self.global_progress_label.configure(text=t))
        self.update_queue.put(lambda tp=title_pct: self.root.title(
            T('window_title_pct', pct=tp, version=self.VERSION) if tp < 100
            else T('window_title_done', version=self.VERSION)))

    def _on_language_change(self, choice):
        lang = 'en' if choice.startswith('English') else 'fr'
        if lang != get_lang():
            import tkinter.messagebox as mb
            mb.showinfo("Language / Langue", T('lang_restart_msg'))
            set_lang(lang)
            self.settings['language'] = lang
            self.save_settings()

    def toggle_pause(self):
        self.pause_processing=not self.pause_processing
        if self.pause_processing: self.pause_event.clear(); self.pause_btn.configure(text=T('btn_resume')); self.taskbar.set_state_paused()
        else: self.pause_event.set(); self.pause_btn.configure(text=T('btn_pause')); self.taskbar.set_state_normal()
    def cancel_process(self):
        self.cancel_processing=True; self.pause_event.set()
        self.update_queue.put(lambda:self.output_text.insert("end",T('cancel_msg'),"error")); self.taskbar.set_state_error()
    def clear_log_and_jobs(self):
        self.output_text.delete(1.0,"end")
        for w in self.progress_pane.winfo_children(): w.destroy()
        self.progress_bars.clear(); self.global_progress.set(0); self.global_progress_label.configure(text=T('status_waiting')); self.taskbar.set_state_off()
    def save_log(self):
        p=filedialog.asksaveasfilename(defaultextension=".txt",title="Enregistrer le log sous...",filetypes=[("Fichier texte","*.txt")])
        if p:
            with open(p,'w',encoding='utf-8') as f: f.write(self.output_text.get(1.0,"end"))
            messagebox.showinfo("Succès",f"Log sauvegardé dans :\n{p}")
    def format_time(self, s): return f"{int(s//60):02d}m {int(s%60):02d}s"
    def show_summary_window(self, s, e, t):
        if e: self.taskbar.set_state_error()
        else: self.taskbar.set_state_normal()
        # Déterminer le dossier de sortie (pour le bouton "Ouvrir le dossier")
        output_dir = self.output_dir_entry.get().strip()
        if not output_dir and s:
            # Si pas de dossier de sortie défini, prendre celui du premier fichier réussi
            first = s[0].split('|track:')[0] if '|track:' in s[0] else s[0]
            output_dir = os.path.dirname(first)
        w=ctk.CTkToplevel(self.root); w.title("Résumé de l'encodage"); w.attributes("-topmost",True); self.center_toplevel(w,500,400)
        c=ctk.CTkCanvas(w,highlightthickness=0); c.pack(fill='both',expand=True)
        c.bind("<Configure>",lambda ev,ca=c,er=e,su=s,od=output_dir:self.resize_summary_image(ev,ca,er,su,od))
        w.protocol("WM_DELETE_WINDOW",lambda:(self.taskbar.set_state_off(),w.destroy()))
    
    def _open_output_folder(self):
        """Ouvre le dossier de sortie configuré, ou le dossier du premier fichier de la liste."""
        od = self.output_dir_entry.get().strip()
        if od and os.path.isdir(od):
            self.open_folder(od); return
        # Fallback: prendre le dossier du premier fichier de la liste
        try:
            first = self.file_list.get(0)
            if first:
                # Gérer le format "filepath|track:N"
                actual = first.split('|track:')[0] if '|track:' in first else first
                folder = os.path.dirname(actual)
                if folder and os.path.isdir(folder):
                    self.open_folder(folder); return
        except: pass
        messagebox.showinfo("Aucun dossier à ouvrir",
            "Aucun dossier de sortie défini et aucun fichier dans la liste.\n\n"
            "Configurez le dossier de sortie dans l'onglet Options,\nou ajoutez des fichiers à traiter.")
    
    def open_folder(self, path):
        """Ouvre le dossier spécifié dans l'explorateur de fichiers."""
        if not path or not os.path.isdir(path):
            messagebox.showwarning("Attention", f"Dossier introuvable :\n{path}")
            return
        try:
            if os.name == 'nt':
                os.startfile(path)
            elif os.name == 'posix':
                subprocess.run(['xdg-open', path])
        except Exception as ex:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir le dossier :\n{ex}")
    def debounced_update_progress_width(self, event=None):
        if self.resize_after_id: self.root.after_cancel(self.resize_after_id)
        self.resize_after_id=self.root.after(200,self.update_progress_width,event)
    def change_theme(self):
        try:
            self.theme=self.theme_var.get(); ctk.set_appearance_mode(self.theme)
            bg='#ffffff' if self.theme=='light' else '#2b2b2b'; fg='#000000' if self.theme=='light' else '#ffffff'; lbg='#f0f0f0' if self.theme=='light' else '#333333'
            self.root.configure(bg=bg); self.file_list.configure(bg=lbg,fg=fg); self.output_text.configure(bg=lbg,fg=fg)
            self.notebook.configure(fg_color=bg); self.paned_window.configure(bg=bg); self.log_frame.configure(bg=bg)
            self.progress_pane.configure(fg_color=bg); self.about_canvas.configure(bg=lbg)
            for tab in [self.input_tab,self.output_tab,self.encode_params_tab,self.presets_tab,self.options_tab,self.about_tab]: tab.configure(fg_color=bg)
            self.global_progress_label.configure(text_color=fg)
            self.output_text.tag_configure("success",foreground='#006400' if self.theme=='light' else '#00ff00')
            self.resize_about_image(); self.root.update()
        except Exception as e: print(f"Thème: {e}")
    def change_color_theme(self, t): self.color_theme=t; self.apply_safe_theme(t); self.root.update()
    def resize_about_image(self, event=None):
        try:
            p=resource_path(os.path.join("Assets","backroom.jpg"))
            if os.path.exists(p):
                img=Image.open(p); w=max(1,self.about_canvas.winfo_width()); h=max(1,self.about_canvas.winfo_height())
                img=Image.alpha_composite(img.resize((w,h),Image.Resampling.LANCZOS).convert("RGBA"),
                    Image.new('RGBA',(w,h),(255,255,255,120) if self.theme=='light' else (0,0,0,80)))
                self.about_image=ImageTk.PhotoImage(img)
                self.about_canvas.create_image(w//2,h//2,image=self.about_image,anchor='center')
        except: pass
        txt=(f"PyAudioCodingTools v{self.VERSION} — 2026\n\n"
             "Développé par Crysisjim\n\n"
             "Crédits :\n"
             "• Code & Architecture initiale : Grok 4 (xAI) — 20%\n"
             "• Optimisation & Finitions : Gemini 3 Pro Thinking (Google) — 20%\n"
             "• Refactoring, corrections & features v2.1–2.4 : Claude Opus 4.6 (Anthropic) — 20%\n"
             "• Direction, tests & intégration : Crysisjim — 40%\n\n"
             "Bibliothèques & Remerciements :\n"
             "• Python (Python Software Foundation)\n"
             "• CustomTkinter (Tom Schimansky)\n"
             "• FFmpeg (Fabrice Bellard & Team)\n"
             "• Pygame (Pour la gestion audio)\n"
             "• Matplotlib & Numpy (Pour les spectres & spectrogrammes FFT)\n\n"
             "Nouveautés v2.4 :\n"
             "• Préréglages intégrés one-click (Série, Podcast, Musique, Web, FLAC)\n"
             "• Auto-sélection de la piste préférée (ex: FR) dans les sélecteurs\n"
             "• Bouton 'Ouvrir le dossier de sortie' (Input tab + résumé)\n"
             "• Timeout WAV adaptatif (gros PCM Blu-ray)\n"
             "• Reprise après crash avec relance auto de l'encodage\n"
             "• Crash log détaillé (pyaudiocodingtools_crash.log)\n\n"
             "Fonctionnalités :\n"
             "• Encodage batch multi-codec via FFmpeg\n"
             "• Normalisation EBU R128 (Loudnorm) en 2 passes\n"
             "• Sélection de pistes audio MKV/MP4 (unitaire & batch)\n"
             "• Sortie MKA avec préservation des tags langue/titre\n"
             "• Comparaison visuelle : Forme d'onde + Spectrogramme FFT\n"
             "• Mise à jour FFmpeg intégrée (WinGet / Git Master Full)\n"
             "• Notifications Windows Toast (win11toast)\n"
             "• Progression dans la barre des tâches & titre de fenêtre\n"
             "• Préréglages intégrés + personnels illimités\n"
             "• Drag & drop avec détection multi-pistes\n"
             "• Création automatique des symlinks WinGet + PATH\n\n"
             "Merci d'utiliser cet outil !")
        self.about_canvas.delete("txt")
        self.about_canvas.create_text(20,20,text=txt,justify=tk.LEFT,font=("Arial",12,"bold"),anchor='nw',
                                       fill='#000000' if self.theme=='light' else '#ffffff',tags="txt")
        if event and self.notebook.get()==T('tab_about') and not self._about_sound_played:
            self._about_sound_played = True
            self.play_sound("about")
    def update_progress_width(self, event=None):
        try:
            ww=self.progress_pane.winfo_width()
            if ww>50:
                for c in self.progress_pane.winfo_children():
                    if isinstance(c,ctk.CTkProgressBar): c.configure(width=int(ww*0.8))
        except: pass
    def resize_summary_image(self, event, canvas, errors, successes, output_dir=None):
        try:
            ww=event.width; wh=event.height
            n="success.jpg" if not errors else "warning.jpg" if successes else "failure.jpg"
            p=resource_path(os.path.join("Assets",n))
            if os.path.exists(p):
                i=Image.alpha_composite(Image.open(p).resize((ww,wh),Image.Resampling.LANCZOS).convert("RGBA"),
                    Image.new('RGBA',(ww,wh),(255,255,255,120) if self.theme=='light' else (0,0,0,80)))
                self.summary_image=ImageTk.PhotoImage(i)
                canvas.create_image(ww//2,wh//2,image=self.summary_image,anchor='center')
        except: pass
        y=20; c='#000000' if self.theme=='light' else '#ffffff'
        canvas.create_text(ww//2,y,text="Résumé de l'encodage",font=("Arial",14,"bold"),anchor='center',fill=c); y+=40
        canvas.create_text(ww//2,y,text=f"Fichiers réussis : {len(successes)}",font=("Arial",12,"bold"),anchor='center',fill='#006400' if self.theme=='light' else '#00FF00'); y+=25
        canvas.create_text(ww//2,y,text=f"Fichiers en erreur : {len(errors)}",font=("Arial",12,"bold"),anchor='center',fill='#FF0000'); y+=25
        canvas.create_text(ww//2,y,text=f"Temps total : {self.format_time(time.time()-self.start_time)}",font=("Arial",12,"italic"),anchor='center',fill=c); y+=45
        
        # Bouton "Ouvrir le dossier de sortie" si on a au moins un succès
        if successes and output_dir:
            canvas.create_window(ww//2, y, window=ctk.CTkButton(canvas.master,
                text="📂 Ouvrir le dossier de sortie", width=240,
                command=lambda od=output_dir: self.open_folder(od),
                fg_color='#0066ff'), anchor='center'); y += 40
        
        if errors:
            self.play_sound("warning" if successes else "error")
            def _err():
                ew=ctk.CTkToplevel(canvas.master); ew.title("Détails des erreurs"); self.center_toplevel(ew,800,400)
                t=tk.Text(ew); t.pack(fill='both',expand=True)
                for f in errors: t.insert("end",f+"\n")
            canvas.create_window(ww//2,y,window=ctk.CTkButton(canvas.master,text="Voir les détails des erreurs",command=_err,fg_color='#FF4500'),anchor='center'); y+=40
        else: self.play_sound("success")
        canvas.create_window(ww//2,y+20,window=ctk.CTkButton(canvas.master,text="Fermer",command=lambda:(self.taskbar.set_state_off(),canvas.master.destroy()),fg_color='#008000',width=100),anchor='center')
    def find_executable(self, name):
        """Cherche un exécutable dans le PATH, WinGet Links, et les packages WinGet."""
        try:
            # 1. shutil.which (PATH standard)
            p=shutil.which(name)
            if p and os.path.exists(p): return p
            
            # 2. where.exe (Windows)
            if os.name=='nt':
                try:
                    r=subprocess.check_output(['where.exe',name],universal_newlines=True,creationflags=0x08000000).strip()
                    if r and os.path.exists(r.split('\n')[0]): return r.split('\n')[0]
                except: pass
            
            # 3. WinGet Links (symlinks créés par winget)
            if os.name=='nt':
                winget_links = os.path.join(os.environ.get('LOCALAPPDATA',''), "Microsoft", "WinGet", "Links")
                candidate = os.path.join(winget_links, f"{name}.exe")
                if os.path.exists(candidate): return candidate
                # Aussi en majuscules (ffmpeg.EXE)
                candidate_upper = os.path.join(winget_links, f"{name}.EXE")
                if os.path.exists(candidate_upper): return candidate_upper
            
            # 4. Scanner les packages WinGet (chemin profond)
            if os.name=='nt':
                winget_pkgs = os.path.join(os.environ.get('LOCALAPPDATA',''), "Microsoft", "WinGet", "Packages")
                if os.path.isdir(winget_pkgs):
                    for root_dir, dirs, files in os.walk(winget_pkgs):
                        for fname in files:
                            if fname.lower() == f"{name}.exe":
                                return os.path.join(root_dir, fname)
        except Exception as e:
            print(f"find_executable({name}): {e}")
        return None
    def drop_files(self, event):
        files = list(self.root.tk.splitlist(event.data))
        container_exts = {'.mkv', '.mp4', '.avi', '.ts', '.m2ts'}
        containers = []
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in container_exts:
                tracks = get_audio_tracks(self, f)
                if len(tracks) > 1:
                    containers.append(f)
                elif len(tracks) == 1:
                    self.file_list.insert(tk.END, f)
            elif is_audio_file(self, f):
                self.file_list.insert(tk.END, f)
        # Conteneurs multi-pistes : batch picker si plusieurs, sinon picker simple
        if len(containers) > 1:
            first_tracks = get_audio_tracks(self, containers[0])
            self._show_batch_track_picker(containers, first_tracks)
        elif len(containers) == 1:
            tracks = get_audio_tracks(self, containers[0])
            self._show_track_picker(containers[0], tracks)
    def update_codec_params(self, event=None):
        c=self.codec_var.get(); k=self.codec_reverse_map.get(c,c)
        self.custom_params_entry.delete(0,tk.END)
        br=['32','64','96','128','192','256','320','448','640']
        if k=='libopus': br=['32','64','96','128','192','256']
        elif k=='dts': br=['192','256','384','448','640','768','1536']
        self.bitrate_combo.configure(values=br)
        if self.settings.get('bitrate') in br: self.bitrate_combo.set(self.settings.get('bitrate'))
        else: self.bitrate_combo.set(br[-1])
        sv=['same','2.0','5.1','7.1'] if k in ['aac','ac3','eac3','libopus','dts','libvorbis'] else ['same','2.0']
        self.channels_combo.configure(values=sv)
        if self.surround_mode_var.get() not in sv: self.surround_mode_var.set('same')
        self.sample_rate_combo.configure(values=['8000','11025','16000','22050','32000','44100','48000','96000'])
        self.sample_rate_combo.set(self.settings.get('sample_rate','48000'))
        self.loudnorm_i_combo.configure(values=[str(i) for i in range(-70,1,2)]); self.loudnorm_i_combo.set(self.settings.get('loudnorm_i','-18'))
        self.loudnorm_lra_combo.configure(values=[str(i) for i in range(1,51,2)]); self.loudnorm_lra_combo.set(self.settings.get('loudnorm_lra','11'))
        self.loudnorm_tp_combo.configure(values=[f'{i:.1f}' for i in range(-9,1)]); self.loudnorm_tp_combo.set(self.settings.get('loudnorm_tp','-1.0'))
        ln_ok=k in ['aac','ac3','eac3','libmp3lame','libopus','wmav2','libvorbis']
        st='normal' if self.loudnorm_var.get() and ln_ok else 'disabled'
        self.loudnorm_i_combo.configure(state=st); self.loudnorm_lra_combo.configure(state=st); self.loudnorm_tp_combo.configure(state=st)
        st2='normal' if ln_ok else 'disabled'
        for w in [self.analyze_duration_combo,self.probe_size_combo,self.async_combo,self.min_hard_comp_entry,self.first_pts_entry,self.resampler_combo]:
            if w: w.configure(state=st2)
        self.update_codec_specific_frame(); self.validate_params_realtime()
    def update_codec_specific_frame(self):
        for w in self.codec_specific_frame.winfo_children(): w.destroy()
        c=self.codec_var.get(); k=self.codec_reverse_map.get(c,c); self.codec_params[c]={}
        f=ctk.CTkFrame(self.codec_specific_frame,fg_color="transparent"); has=False
        if k=='aac':
            has=True; f.pack()
            ctk.CTkLabel(f,text=T('lbl_enc_mode')).pack(side="left",padx=5)
            self.codec_params[c]['bitrate_mode']=ctk.StringVar(value='CBR')
            bm=ctk.CTkOptionMenu(f,variable=self.codec_params[c]['bitrate_mode'],values=['CBR','VBR','ABR']); bm.pack(side="left",padx=5)
            ToolTip(bm,"CBR (Constant Bit Rate) : Bitrate fixe. Taille de fichier prévisible.\nVBR (Variable Bit Rate) : Bitrate variable. Meilleur rapport qualité/taille.\nABR (Average Bit Rate) : Compromis entre CBR et VBR.")
            ctk.CTkLabel(f,text=T('lbl_aac_profile')).pack(side="left",padx=5)
            self.codec_params[c]['profile']=ctk.StringVar(value='aac_low')
            pr=ctk.CTkOptionMenu(f,variable=self.codec_params[c]['profile'],values=['aac_low','aac_he','aac_he_v2']); pr.pack(side="left",padx=5)
            ToolTip(pr,"aac_low : Profil standard. Bonne qualité à 128+ kbps.\naac_he : Haute efficacité. Meilleur à bas bitrate (64-96 kbps).\naac_he_v2 : HE v2. Excellent à très bas bitrate (32-64 kbps). Stéréo seulement.")
        elif k=='libmp3lame':
            has=True; f.pack()
            ctk.CTkLabel(f,text=T('lbl_enc_mode')).pack(side="left",padx=5)
            self.codec_params[c]['bitrate_mode']=ctk.StringVar(value='CBR')
            bm=ctk.CTkOptionMenu(f,variable=self.codec_params[c]['bitrate_mode'],values=['CBR','VBR']); bm.pack(side="left",padx=5)
            ToolTip(bm,"CBR : Bitrate fixe. Compatible partout.\nVBR : Bitrate variable. Meilleure qualité à taille équivalente.")
            ctk.CTkLabel(f,text=T('lbl_vbr_quality')).pack(side="left",padx=5)
            self.codec_params[c]['vbr_quality']=ctk.StringVar(value='2')
            vq=ctk.CTkOptionMenu(f,variable=self.codec_params[c]['vbr_quality'],values=[str(i) for i in range(10)]); vq.pack(side="left",padx=5)
            ToolTip(vq,"De 0 (meilleure qualité, ~245 kbps) à 9 (pire qualité, ~65 kbps).\n\n0-2 : Excellente qualité (recommandé)\n3-5 : Bonne qualité\n6-9 : Qualité réduite (fichiers petits)")
        elif k=='libopus':
            has=True; f.pack()
            ctk.CTkLabel(f,text=T('lbl_vbr_mode')).pack(side="left",padx=5)
            self.codec_params[c]['vbr']=ctk.StringVar(value='on')
            vb=ctk.CTkOptionMenu(f,variable=self.codec_params[c]['vbr'],values=['on','off']); vb.pack(side="left",padx=5)
            ToolTip(vb,"on : Bitrate variable (recommandé). Meilleur rapport qualité/taille.\noff : Bitrate constant. Taille plus prévisible mais qualité légèrement moindre.")
        if has: ctk.CTkLabel(self.codec_specific_frame,text=T('codec_opts_title',codec=c),font=("Arial",11,"bold")).pack(side="top",before=f)
        else: ctk.CTkLabel(self.codec_specific_frame,text=T('codec_no_opts'),text_color="gray").pack()
    def update_loudnorm_state(self): self.update_codec_params(); self.toggle_loudness_visibility()
    def toggle_loudness_visibility(self):
        if self.loudnorm_var.get(): self.loudness_params_frame.pack(fill='x',pady=5,after=self.codec_specific_frame)
        else: self.loudness_params_frame.pack_forget()
    def on_close(self):
        try:
            for i in self.root.tk.call('after','info'): self.root.after_cancel(i)
        except: pass
        self.root.quit()
        try: self.root.update_idletasks()
        except: pass
        self.save_settings(); self.root.destroy()
