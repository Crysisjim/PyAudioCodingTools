<div align="center">

# 🎛️ PyAudioCodingTools v2.4

**Batch audio encoding GUI — FFmpeg frontend**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6?logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e)](LICENSE)
[![Release](https://img.shields.io/github/v/release/Crysisjim/PyAudioCodingTools?color=f97316&label=Latest)](https://github.com/Crysisjim/PyAudioCodingTools/releases/latest)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-Required-ef4444?logo=ffmpeg&logoColor=white)](https://www.gyan.dev/ffmpeg/builds/)

🇬🇧 [English](#english) · 🇫🇷 [Français](#français)

</div>

---

<a name="english"></a>
## 🇬🇧 English

### What is it?

PyAudioCodingTools is a Windows GUI for batch audio encoding via FFmpeg. No command line needed — configure everything visually, drop your files, and let it encode.

**Portable version available** — download the ZIP, extract, run the exe. No Python required.

> ⚠️ **FFmpeg is required separately** — the app includes a built-in installer (WinGet / direct download from gyan.dev).

### ✨ Features

| Category | Features |
|----------|---------|
| 🎵 **Codecs** | AAC · MP3 · Opus · FLAC · ALAC · Vorbis · PCM 16-bit · WMA · Dolby Digital · Dolby Digital Plus · DTS |
| 📊 **Loudness** | EBU R128 normalization (2-pass) — configurable I/LRA/TP targets |
| 🎬 **MKV/MP4** | Multi-track selection (single file or batch) · MKA output with language/title tags |
| 📈 **Spectral** | Waveform + FFT spectrogram comparison (source vs encoded) |
| ⚡ **Presets** | 6 built-in one-click presets + unlimited custom presets |
| 🔄 **Processing** | Parallel processing (up to 32 workers) · Crash recovery with auto-resume |
| 🖥️ **UI** | Drag & drop · 11 color themes · Dark/Light mode · **FR/EN language toggle** |
| 🔔 **Notifications** | Windows taskbar progress · Windows Toast notifications |
| 🔧 **FFmpeg** | Built-in installer (WinGet / Git Master Full) · Auto symlink + PATH setup |

### ⬇️ Download & Install (Portable)

1. Download **[PyAudioCodingTools_v2.4_Portable.zip](https://github.com/Crysisjim/PyAudioCodingTools/releases/latest)** from Releases
2. Extract to any folder
3. Run `PyAudioCodingTools_v2.4.exe`
4. On first launch: **Options → Update FFmpeg** to install FFmpeg

### 🏗️ Run from Source

```bash
git clone https://github.com/Crysisjim/PyAudioCodingTools.git
cd PyAudioCodingTools
pip install -r requirements.txt
python main.py
```

### 🔧 Build the exe

```bat
pip install pyinstaller
build.bat
```

### 📦 FFmpeg

| Method | Command |
|--------|---------|
| Via the app (recommended) | Options → **Update FFmpeg** → Release Full |
| WinGet | `winget install Gyan.FFmpeg` |
| Manual | [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) |

---

<a name="français"></a>
## 🇫🇷 Français

### C'est quoi ?

PyAudioCodingTools est une interface graphique Windows pour l'encodage audio en batch via FFmpeg. Pas de ligne de commande — configurez tout visuellement, glissez vos fichiers, et lancez l'encodage.

**Version portable disponible** — téléchargez le ZIP, extrayez, lancez l'exe. Aucune installation Python requise.

> ⚠️ **FFmpeg est requis séparément** — l'application inclut un installateur intégré (WinGet / téléchargement direct depuis gyan.dev).

### ✨ Fonctionnalités

| Catégorie | Fonctionnalités |
|-----------|----------------|
| 🎵 **Codecs** | AAC · MP3 · Opus · FLAC · ALAC · Vorbis · PCM 16-bit · WMA · Dolby Digital · Dolby Digital Plus · DTS |
| 📊 **Loudness** | Normalisation EBU R128 en 2 passes — cibles I/LRA/TP configurables |
| 🎬 **MKV/MP4** | Sélection de pistes (unitaire ou batch) · Sortie MKA avec tags langue/titre |
| 📈 **Spectral** | Comparaison waveform + Spectrogramme FFT (source vs encodé) |
| ⚡ **Préréglages** | 6 préréglages intégrés one-click + préréglages personnels illimités |
| 🔄 **Traitement** | Traitement parallèle (jusqu'à 32 workers) · Reprise après crash |
| 🖥️ **Interface** | Drag & drop · 11 thèmes · Mode clair/sombre · **Bascule FR/EN** |
| 🔔 **Notifications** | Progression barre des tâches · Notifications Toast Windows |
| 🔧 **FFmpeg** | Installateur intégré (WinGet / Git Master Full) · Symlinks + PATH auto |

### ⬇️ Téléchargement & Installation (Portable)

1. Téléchargez **[PyAudioCodingTools_v2.4_Portable.zip](https://github.com/Crysisjim/PyAudioCodingTools/releases/latest)** depuis Releases
2. Extrayez dans n'importe quel dossier
3. Lancez `PyAudioCodingTools_v2.4.exe`
4. Au premier lancement : **Options → Mise à jour FFmpeg** pour installer FFmpeg

### 🏗️ Lancer depuis les sources

```bash
git clone https://github.com/Crysisjim/PyAudioCodingTools.git
cd PyAudioCodingTools
pip install -r requirements.txt
python main.py
```

### 🔧 Compiler l'exe

```bat
pip install pyinstaller
build.bat
```

### 📦 FFmpeg

| Méthode | Commande |
|---------|----------|
| Via l'app (recommandé) | Options → **Mise à jour FFmpeg** → Release Full |
| WinGet | `winget install Gyan.FFmpeg` |
| Manuel | [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) |

### 📋 Tableau des codecs

| Codec | Extension | Surround | Loudnorm | Bitrate typique |
|-------|-----------|----------|----------|-----------------|
| **AAC** | `.aac` | ✅ 7.1 | ✅ | 96–320 kbps |
| **Dolby Digital Plus** | `.eac3` / `.mka` | ✅ 7.1 | ✅ | 128–640+ kbps |
| **Dolby Digital** | `.ac3` / `.mka` | ✅ 5.1 | ✅ | 192–640 kbps |
| **DTS** | `.dts` / `.mka` | ✅ 5.1 | ❌ | 192–1536 kbps |
| **MP3** | `.mp3` | ❌ stéréo | ✅ | 64–320 kbps |
| **Opus** | `.opus` | ✅ 7.1 | ✅ | 32–256 kbps |
| **FLAC** | `.flac` | ✅ 8ch | ❌ | Sans perte |
| **PCM 16-bit** | `.wav` | ✅ 8ch | ❌ | Non compressé |

---

## 📖 Wiki

Documentation complète : **[github.com/Crysisjim/PyAudioCodingTools/wiki](https://github.com/Crysisjim/PyAudioCodingTools/wiki)**

- [Installation](../../wiki/Installation)
- [FFmpeg](../../wiki/FFmpeg)
- [Codecs](../../wiki/Codecs)
- [EBU R128 Loudness](../../wiki/Loudnorm-EBU-R128)
- [MKV/MP4 Track Selection](../../wiki/Pistes-MKV-MP4)
- [Presets](../../wiki/Presets)
- [Troubleshooting](../../wiki/Troubleshooting)

---

## 📝 Changelog

### v2.4
- ⚡ Built-in one-click presets (Series, Podcast, Music HQ, Web, FLAC)
- 🌐 **FR/EN language toggle** (Options tab, takes effect on restart)
- ⭐ Auto-selection of preferred language track in MKV pickers
- 📂 "Open Output Folder" button
- ⏱️ Adaptive WAV timeout (large Blu-ray PCM files)
- 🔄 Crash recovery with auto-resume on next launch
- 📋 Detailed crash log with system info
- 🐛 Fixed: custom FFmpeg args with quoted paths (shlex.split)
- 🐛 Fixed: duplicate WinGet symlink call removed

### v2.3
- MKV/MP4 track selection (single + batch)
- MKA output with language/title tag preservation
- Built-in FFmpeg installer (WinGet + Git Master Full)
- WinGet symlinks auto-creation

### v2.2
- FFT spectrogram comparison
- EBU R128 loudness normalization (2-pass)
- Configurable parallel processing
- Windows Toast notifications

---

## 🙏 Credits

**Developed by** [Crysisjim](https://github.com/Crysisjim)

| Contributor | Role | Share |
|-------------|------|-------|
| Grok 4 (xAI) | Initial code & architecture | 20% |
| Gemini 2.5 Pro (Google) | Optimization & polish | 20% |
| Claude Sonnet/Opus (Anthropic) | Refactoring, fixes, features v2.1–2.4 | 20% |
| Crysisjim | Direction, testing & integration | 40% |

**Libraries:** Python · CustomTkinter · FFmpeg · Pygame · Matplotlib · NumPy · Pillow · tkinterdnd2

---

<div align="center">

**MIT License** · [Crysisjim](https://github.com/Crysisjim) · 2026

</div>
