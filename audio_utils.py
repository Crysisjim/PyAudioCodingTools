# audio_utils.py - v2.4 (FFT Spectrogram + Refactored + bilingual)
import os, subprocess, json, re, time, shutil, shlex
from strings import T
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from concurrent.futures import ThreadPoolExecutor, as_completed
import customtkinter as ctk

NO_WINDOW = 0x08000000 if os.name == 'nt' else 0

def _safe_queue_put(app, callback):
    """Met un callback dans la queue UI sans bloquer si elle est pleine."""
    try: app.update_queue.put_nowait(callback)
    except: pass  # Queue pleine, on skip cette update UI

# =============================================================================
#  UTILITAIRES PATH
# =============================================================================
def _get_ffprobe(app):
    p = app.ffprobe_path_entry.get()
    return p if os.path.exists(p) else (shutil.which('ffprobe') or 'ffprobe')

def _get_ffmpeg(app):
    p = app.ffmpeg_path_entry.get()
    return p if os.path.exists(p) else (shutil.which('ffmpeg') or 'ffmpeg')

def _default_codecs():
    return ['aac','ac3','alac','flac','libmp3lame','libopus','pcm_s16le','wmav2','eac3','dts','libvorbis']

# =============================================================================
#  FONCTIONS FFPROBE
# =============================================================================
def get_ffmpeg_codecs(app):
    ffmpeg = _get_ffmpeg(app)
    try:
        r = subprocess.run([ffmpeg, "-encoders"], capture_output=True, text=True, encoding='utf-8', creationflags=NO_WINDOW)
        codecs = []
        for line in r.stdout.splitlines():
            if line.strip().startswith('A.....'):
                c = line.split()[1].strip()
                if c and c not in ['anull','copy','none','=','']: codecs.append(c)
        return sorted(set(codecs)) or _default_codecs()
    except Exception as e:
        app.update_queue.put(lambda e=e: app.output_text.insert("end", f"Erreur codecs: {e}\n"))
        return _default_codecs()

def is_audio_file(app, f):
    cmd = [_get_ffprobe(app), "-v","error","-show_streams","-select_streams","a:0","-show_format","-print_format","json", f]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True, creationflags=NO_WINDOW)
        d = json.loads(out)
        return "streams" in d and any(s["codec_type"]=="audio" for s in d["streams"])
    except: return False

def get_input_channels(app, f):
    cmd = [_get_ffprobe(app),"-v","error","-select_streams","a:0","-show_entries","stream=channels","-of","default=noprint_wrappers=1:nokey=1",f]
    try: return int(subprocess.check_output(cmd, creationflags=NO_WINDOW).decode().strip())
    except: return 2

def validate_file_codec(app, f):
    cmd = [_get_ffprobe(app),"-v","error","-show_streams","-select_streams","a:0","-show_format","-print_format","json",f]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True, creationflags=NO_WINDOW)
        d = json.loads(out)
        return bool(d.get("streams")) and d["streams"][0].get("codec_name") is not None
    except: return False

def get_duration(app, f):
    cmd = [_get_ffprobe(app),"-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",f]
    try: return float(subprocess.check_output(cmd, creationflags=NO_WINDOW).decode().strip())
    except Exception as e:
        app.update_queue.put(lambda e=e: app.output_text.insert("end", f"Erreur durée: {e}\n"))
        return None

def get_bitrate(app, f):
    cmd = [_get_ffprobe(app),"-v","error","-show_entries","format=bit_rate","-of","default=noprint_wrappers=1:nokey=1",f]
    try: return f"{int(subprocess.check_output(cmd, creationflags=NO_WINDOW).decode().strip())//1000} kbits/s"
    except: return "N/A"

# =============================================================================
#  SPECTROGRAM FFT + Forme d'onde
# =============================================================================
def _extract_audio_samples(app, fp, ds=2):
    ffprobe = _get_ffprobe(app); ffmpeg = _get_ffmpeg(app)
    cmd_p = [ffprobe,"-v","error","-show_streams","-select_streams","a:0","-show_format","-print_format","json",fp]
    out = subprocess.check_output(cmd_p, stderr=subprocess.STDOUT, universal_newlines=True, creationflags=NO_WINDOW)
    d = json.loads(out)
    sr = int(d["streams"][0].get("sample_rate",44100)); ch = int(d["streams"][0].get("channels",1))
    esr = sr // ds
    cmd = [ffmpeg,"-i",fp,"-t","60","-f","s16le","-acodec","pcm_s16le","-ar",str(esr),"-ac",str(min(ch,2)),"pipe:"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=NO_WINDOW)
    raw, err = p.communicate()
    if p.returncode != 0: raise Exception(f"FFmpeg: {err.decode()}")
    s = np.frombuffer(raw, dtype=np.int16)
    if len(s)==0: raise Exception("Pas d'échantillons")
    s = np.where(s==0, np.finfo(float).eps, s)
    return s / np.max(np.abs(s)), esr

def show_audio_spectrum(app, fp, ft):
    try:
        samples, sr = _extract_audio_samples(app, fp, 2)
        bn = os.path.basename(fp)
        def _gui(s=samples, sr=sr, bn=bn, ft=ft):
            try:
                fig, ax = plt.subplots()
                ax.plot(np.linspace(0,len(s)/sr,len(s)), s, color='blue')
                ax.set_title(f"Forme d'onde: {bn} ({ft})"); ax.set_xlabel("Temps (s)"); ax.set_ylabel("Amplitude"); ax.grid(True)
                w = ctk.CTkToplevel(app.root); w.title(f"Spectre: {bn}")
                c = FigureCanvasTkAgg(fig, master=w); c.draw(); c.get_tk_widget().pack(fill='both', expand=True)
            except Exception as e: print(f"Erreur GUI spectre: {e}")
        app.update_queue.put(_gui)
    except Exception as e: print(f"Erreur spectre: {e}")

def show_audio_spectrum_comparison(app, inp, out):
    try:
        ss, srs = _extract_audio_samples(app, inp, 4)
        so, sro = _extract_audio_samples(app, out, 4)
        bn = os.path.basename(inp)
        def _gui(ss=ss, srs=srs, so=so, sro=sro, bn=bn):
            try:
                fig, axs = plt.subplots(2, 2, figsize=(14, 8)); plt.subplots_adjust(hspace=0.4, wspace=0.3)
                axs[0,0].plot(np.linspace(0,len(ss)/srs,len(ss)), ss, color='#2196F3', linewidth=0.5)
                axs[0,0].set_title("Forme d'onde - Source", fontsize=10, fontweight='bold')
                axs[0,0].set_xlabel("Temps (s)"); axs[0,0].set_ylabel("Amplitude"); axs[0,0].set_ylim(-1,1); axs[0,0].grid(True, alpha=0.3)
                axs[0,1].plot(np.linspace(0,len(so)/sro,len(so)), so, color='#4CAF50', linewidth=0.5)
                axs[0,1].set_title("Forme d'onde - Encodé", fontsize=10, fontweight='bold')
                axs[0,1].set_xlabel("Temps (s)"); axs[0,1].set_ylabel("Amplitude"); axs[0,1].set_ylim(-1,1); axs[0,1].grid(True, alpha=0.3)
                mono_s = ss[::2] if len(ss) > srs else ss; mono_o = so[::2] if len(so) > sro else so
                axs[1,0].specgram(mono_s, NFFT=2048, Fs=srs, noverlap=1536, cmap='inferno', vmin=-100, vmax=0, scale='dB')
                axs[1,0].set_title("Spectrogramme FFT - Source", fontsize=10, fontweight='bold')
                axs[1,0].set_xlabel("Temps (s)"); axs[1,0].set_ylabel("Fréquence (Hz)"); axs[1,0].set_ylim(0, srs//2)
                sp = axs[1,1].specgram(mono_o, NFFT=2048, Fs=sro, noverlap=1536, cmap='inferno', vmin=-100, vmax=0, scale='dB')
                axs[1,1].set_title("Spectrogramme FFT - Encodé", fontsize=10, fontweight='bold')
                axs[1,1].set_xlabel("Temps (s)"); axs[1,1].set_ylabel("Fréquence (Hz)"); axs[1,1].set_ylim(0, sro//2)
                fig.colorbar(sp[3], ax=axs[1,:], orientation='horizontal', pad=0.12, aspect=40, shrink=0.8).set_label('Puissance (dB)')
                fig.suptitle(f"Comparaison: {bn}", fontsize=12, fontweight='bold', y=0.98)
                w = ctk.CTkToplevel(app.root); w.title(f"Comparaison: {bn}"); w.geometry("1200x700")
                canvas = FigureCanvasTkAgg(fig, master=w); canvas.draw(); canvas.get_tk_widget().pack(fill='both', expand=True)
                from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
                NavigationToolbar2Tk(canvas, w).pack(side='bottom', fill='x')
            except Exception as e: print(f"Erreur GUI comparaison: {e}")
        app.update_queue.put(_gui)
    except Exception as e: print(f"Erreur comparaison: {e}")

def get_audio_tracks(app, filepath):
    """Récupère toutes les pistes audio d'un fichier (MKV, MP4, etc.).
    Retourne une liste de dicts avec les infos de chaque piste audio."""
    ffprobe = _get_ffprobe(app)
    cmd = [ffprobe, "-v", "error", "-show_streams", "-select_streams", "a",
           "-show_entries", "stream=index,codec_name,channels,channel_layout,bit_rate,sample_rate:stream_tags=language,title",
           "-print_format", "json", filepath]
    try:
        raw = subprocess.check_output(cmd, stderr=subprocess.STDOUT, creationflags=NO_WINDOW)
        d = json.loads(raw.decode('utf-8', errors='replace'))
        tracks = []
        for i, s in enumerate(d.get("streams", [])):
            tags = s.get("tags", {})
            tracks.append({
                'index': i,
                'stream_index': s.get('index', i),
                'codec': s.get('codec_name', '?'),
                'channels': s.get('channels', 0),
                'channel_layout': s.get('channel_layout', ''),
                'sample_rate': s.get('sample_rate', '?'),
                'bitrate': f"{int(s['bit_rate'])//1000}k" if s.get('bit_rate') else 'N/A',
                'language': tags.get('language', '???'),
                'title': tags.get('title', ''),
            })
        return tracks
    except Exception as e:
        print(f"Erreur probe tracks: {e}")
        return []

# =============================================================================
#  CONSTANTES ENCODAGE
# =============================================================================
CODEC_TO_EXT = {'aac':'aac','ac3':'ac3','alac':'m4a','flac':'flac','libmp3lame':'mp3',
                'libopus':'opus','pcm_s16le':'wav','wmav2':'wma','eac3':'eac3','dts':'dts','libvorbis':'ogg'}
SURROUND_CODECS = {'aac','ac3','eac3','libopus','dts','libvorbis'}
LOUDNORM_CODECS = {'aac','ac3','eac3','libmp3lame','libopus','wmav2','libvorbis'}
AC_MAP = {'2.0':'2','5.1':'6','7.1':'8'}
MAX_CHANNELS = {'libmp3lame':2,'wmav2':2,'ac3':6,'eac3':8,'aac':8,'libopus':8,'dts':6,'libvorbis':8,'flac':8,'alac':8,'pcm_s16le':8}

# =============================================================================
#  HELPERS
# =============================================================================
def _update_step(app, inp, bn, step, tbr):
    with app.data_lock:
        app.current_steps[inp] = step
        app.bitrates[inp] = f"Cible: {tbr}, Réel: {app.real_bitrates[inp]}"
    idx = app.file_indices[inp]
    if not app.detailed_output_var.get():
        def _do(idx=idx, bn=bn, s=step):
            app.output_text.delete(f"{idx}.0",f"{idx}.end")
            app.output_text.insert(f"{idx}.0",f"{bn} : Étape - {s}")
        app.update_queue.put(_do)
    else:
        app.update_queue.put(lambda bn=bn, s=step: app.output_text.insert("end",f"[{bn}] : Étape - {s}\n"))

def _build_surround_params(codec, cp):
    if codec not in SURROUND_CODECS and codec != 'libmp3lame': return []
    sm = cp.get('surround_mode', ctk.StringVar(value='same')).get()
    if sm == 'same': return []
    if codec == 'libmp3lame': return ['-ac','2']
    return ['-ac', AC_MAP.get(sm,'6')]

def _validate_channel_config(codec, sm, inch):
    if sm == 'same':
        mx = MAX_CHANNELS.get(codec,8)
        if inch > mx: return False, f"{codec} max {mx} ch, source {inch}."
        return True, ""
    req = int(AC_MAP.get(sm,'6')); mx = MAX_CHANNELS.get(codec,8)
    if req > mx: return False, f"{codec} max {mx} ch, demandé {sm}."
    return True, ""

def _build_common_params(app, codec, cp):
    params = ["-analyzeduration",app.analyze_duration_combo.get(),"-probesize",app.probe_size_combo.get(),
              "-vn","-c:a",codec,"-b:a",f"{app.bitrate_combo.get()}k","-ar",app.sample_rate_combo.get()]
    if codec == 'aac':
        bm = cp.get('bitrate_mode', ctk.StringVar(value='CBR')).get()
        if bm == 'VBR': params.extend(['-vbr','on'])
        elif bm == 'ABR': params.extend(['-abr','1'])
        params.extend(['-profile:a', cp.get('profile', ctk.StringVar(value='aac_low')).get()])
    elif codec == 'libmp3lame':
        bm = cp.get('bitrate_mode', ctk.StringVar(value='CBR')).get()
        if bm == 'VBR': params.extend(['-q:a', cp.get('vbr_quality', ctk.StringVar(value='2')).get()])
    elif codec == 'libopus':
        params.extend(['-vbr', cp.get('vbr', ctk.StringVar(value='on')).get()])
    params.extend(_build_surround_params(codec, cp))
    if codec == 'eac3' and app.dialnorm_var.get(): params.extend(["-dialnorm","-31"])
    if app.copy_metadata_var.get(): params.extend(["-map_metadata","0","-map_chapters","0"])
    cs = app.custom_params_entry.get().strip()
    if cs: params.extend(shlex.split(cs))
    return params

def _read_ffmpeg_output(proc, app, inp, bn, dur, pb, pl, tbr, off=0, rng=50):
    lines = []; batch = []; last_ui = 0
    # Adapter le throttle au nombre de fichiers parallèles
    num_files = max(1, len(app.progress_bars))
    UI_INT = max(0.25, min(1.0, num_files * 0.08))  # 0.25s pour 1-3 fichiers, jusqu'à 1s pour 12+
    while True:
        if app.cancel_processing: proc.terminate(); return lines, True
        line = proc.stderr.readline()
        if not line and proc.poll() is not None: break
        lines.append(line); batch.append(line)
        if len(batch) >= 8 or not line:
            if app.detailed_output_var.get():
                b = ''.join(batch)
                _safe_queue_put(app, lambda b=b, bn=bn: app.output_text.insert("end",f"[{bn}] {b}"))
            batch = []
        sm = re.search(r'speed= *(\d+\.\d+)x', line)
        if sm:
            with app.data_lock: app.speeds[inp] = sm.group(1)+"x"
        tm = re.search(r'time=(\d{2}):(\d{2}):(\d{2})\.\d{2}', line)
        bm = re.search(r'bitrate= *(\d+\.\d+)kbits/s', line)
        if tm and dur:
            h,m,s = map(int, tm.groups()); cur = h*3600+m*60+s
            pct = min(off + (cur/dur)*rng, off+rng)
            with app.data_lock:
                app.progress_values[inp] = pct
                app.real_bitrates[inp] = (bm.group(1)+" kbits/s") if bm else "N/A"
                app.bitrates[inp] = f"Cible: {tbr}, Réel: {app.real_bitrates[inp]}"
            now = time.time()
            if now - last_ui >= UI_INT:
                last_ui = now
                ipct=int(pct); bi=app.bitrates[inp]; si=app.speeds.get(inp,'N/A'); fn=os.path.basename(inp)
                _safe_queue_put(app, lambda p=ipct: pb.set(p/100))
                _safe_queue_put(app, lambda fn=fn,p=ipct,si=si,bi=bi: pl.configure(text=f"{fn} - {p}% - {si} - {bi}"))
                _safe_queue_put(app, lambda: app.update_global_progress(len(app.progress_bars)))
    with app.data_lock: fp = int(app.progress_values.get(inp,0))
    if fp > 0:
        fn=os.path.basename(inp); si=app.speeds.get(inp,'N/A'); bi=app.bitrates.get(inp,'N/A')
        _safe_queue_put(app, lambda f=fp: pb.set(f/100))
        _safe_queue_put(app, lambda fn=fn,f=fp,si=si,bi=bi: pl.configure(text=f"{fn} - {f}% - {si} - {bi}"))
    return lines, False

def _cleanup_temp(app, tw, bn):
    if not os.path.exists(tw): return
    try:
        os.remove(tw)
        app.update_queue.put(lambda tw=tw: app.output_text.insert("end",f"Temp {tw} supprimé.\n","info"))
    except Exception as e:
        app.update_queue.put(lambda tw=tw,e=str(e): app.output_text.insert("end",f"Erreur suppression {tw}: {e}\n","error"))

# =============================================================================
#  PROCESS FILE (FFmpeg uniquement)
# =============================================================================
def process_file(app, input_file, progress_bar, progress_label):
    # Parse track selection: "filepath|track:N" format
    track_index = None
    actual_file = input_file
    track_language = None  # Langue de la piste source
    track_title = None     # Titre de la piste source
    if '|track:' in input_file:
        parts = input_file.rsplit('|track:', 1)
        actual_file = parts[0]
        track_index = int(parts[1])
        # Récupérer les métadonnées de la piste sélectionnée
        try:
            tracks = get_audio_tracks(app, actual_file)
            for t in tracks:
                if t['index'] == track_index:
                    track_language = t.get('language', '')
                    track_title = t.get('title', '')
                    break
        except: pass
    
    basename = os.path.basename(actual_file)
    if track_index is not None:
        basename = f"{os.path.splitext(basename)[0]}_track{track_index}{os.path.splitext(basename)[1]}"
    
    if app.cancel_processing: return input_file, "Annulé.\n", False
    if not validate_file_codec(app, actual_file):
        return input_file, f"Erreur: {actual_file} incompatible.\n", False
    
    ffmpeg = _get_ffmpeg(app); out_dir = app.output_dir_entry.get()
    codec = app.codec_reverse_map.get(app.codec_var.get(), app.codec_var.get())
    ext = CODEC_TO_EXT.get(codec,'wav'); bname = os.path.splitext(os.path.basename(actual_file))[0]
    
    # Formats qui NE supportent PAS les métadonnées de flux (langue, titre)
    # Si l'option MKA est activée, on utilise .mka (Matroska Audio) comme conteneur
    RAW_FORMATS = {'eac3', 'ac3', 'dts', 'wav', 'wma', 'aac'}
    use_mka = (hasattr(app, 'mka_output_var') and app.mka_output_var.get() 
               and track_language and track_language not in ('???', 'und', '') 
               and ext in RAW_FORMATS)
    if use_mka:
        ext = 'mka'  # Matroska Audio — préserve les métadonnées
    
    if track_index is not None:
        # Inclure la langue dans le nom du fichier si disponible
        lang_suffix = f"_{track_language.upper()}" if track_language and track_language not in ('???', 'und', '') else ""
        bname = f"{bname}_track{track_index}{lang_suffix}"
    dest = out_dir or os.path.dirname(actual_file)
    outf = os.path.join(dest, f"{bname}_CONVERTED.{ext}")
    tmpw = os.path.join(dest, f"{bname}_TEMP.wav")
    c = 1
    while os.path.exists(outf): outf = os.path.join(dest, f"{bname}_CONVERTED_{c}.{ext}"); c+=1
    
    tbr = app.bitrate_combo.get()+" kbits/s"
    with app.data_lock: app.target_bitrates[input_file]=tbr; app.real_bitrates[input_file]="N/A"
    _update_step(app, input_file, basename, T('step_prepare'), tbr)
    
    try:
        if not os.path.exists(ffmpeg) and not shutil.which(ffmpeg):
            raise FileNotFoundError(f"ffmpeg introuvable: {ffmpeg}")
        inch = get_input_channels(app, actual_file)
        sv = app.codec_params.get(app.codec_var.get(),{}).get('surround_mode', ctk.StringVar(value='same'))
        sm = sv.get() if hasattr(sv,'get') else sv
        _ok, warn = _validate_channel_config(codec, sm, inch)
        if warn: app.update_queue.put(lambda w=warn, bn=basename: app.output_text.insert("end",f"[{bn}] ⚠ {w}\n","info"))
        
        _update_step(app, input_file, basename, T('step_wav'), tbr)
        cw = [ffmpeg,"-i",actual_file,"-vn"]
        if track_index is not None:
            cw.extend(["-map", f"0:a:{track_index}"])
        cw.extend(["-c:a","pcm_s16le","-y"])
        if app.copy_metadata_var.get(): cw.extend(["-map_metadata","0","-map_chapters","0"])
        cw.append(tmpw)
        
        # Timeout adaptatif : plus le fichier est long/gros, plus on donne de temps.
        # Base de 600s (10 min) + 2x la durée estimée de l'audio pour gérer :
        # - les gros fichiers Blu-ray PCM (24-bit LPCM peut faire 400+ Mo par piste)
        # - le traitement parallèle de plusieurs fichiers qui sature les I/O disque
        # - les disques lents/fragmentés
        try:
            src_dur = get_duration(app, actual_file) or 1500
        except: src_dur = 1500
        wav_timeout = max(600, int(src_dur * 2))
        
        p = subprocess.Popen(cw, stderr=subprocess.PIPE, universal_newlines=True, creationflags=NO_WINDOW)
        try: se = p.communicate(timeout=wav_timeout)[1]
        except subprocess.TimeoutExpired:
            p.kill(); p.communicate()
            raise TimeoutError(f"Timeout WAV après {wav_timeout}s — réduisez le nombre de fichiers parallèles (onglet Options)")
        if p.returncode != 0: raise subprocess.CalledProcessError(p.returncode, cw, stderr=se)
        
        _update_step(app, input_file, basename, T('step_duration'), tbr)
        dur = get_duration(app, tmpw)
        if dur is None: raise ValueError("Durée introuvable")
        app.update_queue.put(lambda: progress_bar.set(0))
        
        cp = app.codec_params.get(app.codec_var.get(),{})
        cparams = _build_common_params(app, codec, cp)
        
        ld = None
        if app.loudnorm_var.get() and codec in LOUDNORM_CODECS:
            _update_step(app, input_file, basename, T('step_loudnorm1'), tbr)
            c1 = [ffmpeg,"-i",tmpw]+cparams+["-filter:a","loudnorm=print_format=json","-f","null","-"]
            p1 = subprocess.Popen(c1, stderr=subprocess.PIPE, universal_newlines=True, creationflags=NO_WINDOW)
            l1, cancelled = _read_ffmpeg_output(p1, app, input_file, basename, dur, progress_bar, progress_label, tbr, 0, 50)
            if cancelled: _cleanup_temp(app, tmpw, basename); return input_file, "Annulé.\n", False
            if p1.returncode != 0: raise subprocess.CalledProcessError(p1.returncode, c1, stderr=''.join(l1))
            if app.detailed_output_var.get():
                cs = ' '.join(c1)
                app.update_queue.put(lambda cs=cs, bn=basename: app.output_text.insert("end",f"[{bn}] Passe 1: {cs}\n"))
            jm = re.search(r'\[Parsed_loudnorm_.*?\]\s*(\{.*?\})\s*(?=\[|$)', ''.join(l1), re.DOTALL)
            if not jm: raise ValueError("JSON loudnorm introuvable dans la sortie FFmpeg")
            ld = json.loads(jm.group(1).strip())
            if app.detailed_output_var.get():
                d2 = dict(ld)
                app.update_queue.put(lambda bn=basename, d=d2: app.output_text.insert("end",
                    f"[{bn}] Loudnorm mesuré: I={d['input_i']}, LRA={d['input_lra']}, TP={d['input_tp']}\n"))
        
        _update_step(app, input_file, basename, T('step_encode'), tbr)
        filt = (f"aresample=async={1 if app.async_combo.get()=='On' else 0}"
                f":min_hard_comp={app.min_hard_comp_entry.get()}"
                f":first_pts={app.first_pts_entry.get()}"
                f":resampler={app.resampler_combo.get()}")
        if app.loudnorm_var.get() and codec in LOUDNORM_CODECS and ld:
            filt = (f"loudnorm=I={app.loudnorm_i_combo.get()}:LRA={app.loudnorm_lra_combo.get()}:"
                    f"TP={app.loudnorm_tp_combo.get()}:measured_I={ld['input_i']}:"
                    f"measured_LRA={ld['input_lra']}:measured_TP={ld['input_tp']}:"
                    f"measured_thresh={ld['input_thresh']},{filt}")
        c2 = [ffmpeg,"-i",tmpw,"-y"]+cparams+["-filter:a",filt]
        # Injecter les métadonnées de langue et titre de la piste source
        if track_language and track_language not in ('???', 'und', ''):
            c2.extend(["-metadata:s:a:0", f"language={track_language}"])
        if track_title:
            c2.extend(["-metadata:s:a:0", f"title={track_title}"])
        c2.append(outf)
        p2 = subprocess.Popen(c2, stderr=subprocess.PIPE, universal_newlines=True, creationflags=NO_WINDOW)
        l2, cancelled = _read_ffmpeg_output(p2, app, input_file, basename, dur, progress_bar, progress_label, tbr, 50, 50)
        if cancelled: _cleanup_temp(app, tmpw, basename); return input_file, "Annulé.\n", False
        if p2.returncode != 0: raise subprocess.CalledProcessError(p2.returncode, c2, stderr=''.join(l2))
        if app.detailed_output_var.get():
            cs = ' '.join(c2)
            app.update_queue.put(lambda cs=cs, bn=basename: app.output_text.insert("end",f"[{bn}] Encodage: {cs}\n"))
        
        with app.data_lock:
            app.real_bitrates[input_file] = get_bitrate(app, outf)
            app.bitrates[input_file] = f"Cible: {tbr}, Réel: {app.real_bitrates[input_file]}"
            app.progress_values[input_file] = 100
        fn=basename; si=app.speeds.get(input_file,'N/A'); bi=app.bitrates[input_file]
        app.update_queue.put(lambda: progress_bar.set(1.0))
        app.update_queue.put(lambda fn=fn,si=si,bi=bi: progress_label.configure(text=f"{fn} - 100% - Vitesse: {si} - {bi}"))
        if app.compare_spectrum_var.get(): app.spectrum_queue.put((input_file, outf))
        _cleanup_temp(app, tmpw, basename)
        return input_file, f"✓ Réussi: {outf}\n", True
    except Exception as e:
        msg = f"✗ Erreur {input_file}: {e}\n"
        app.update_queue.put(lambda m=msg: app.output_text.insert("end", m, "error"))
        _cleanup_temp(app, tmpw, basename)
        return input_file, msg, False
