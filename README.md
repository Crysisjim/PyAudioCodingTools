# PyAudioCodingTools v2.4

<div align="center">

**Interface graphique batch pour l'encodage audio via FFmpeg**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6?logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Release](https://img.shields.io/github/v/release/Crysisjim/PyAudioCodingTools?color=orange)
![FFmpeg](https://img.shields.io/badge/FFmpeg-Required-red?logo=ffmpeg&logoColor=white)

</div>

---

## Présentation

PyAudioCodingTools est une interface graphique Windows pour encoder des fichiers audio en batch via FFmpeg.  
Conçu pour les passionnés de home-cinéma, les créateurs de contenu et les archivistes audio qui veulent contrôler précisément leurs encodages sans taper des commandes FFmpeg à la main.

**Version portable disponible** — téléchargez le ZIP, extrayez, lancez l'exe. Aucune installation Python requise.  
⚠️ **FFmpeg est requis séparément** — l'application inclut un installateur intégré (WinGet / téléchargement direct).

---

## Fonctionnalités

### Encodage batch multi-codec
- **11 codecs supportés** : AAC, MP3 (libmp3lame), Opus, FLAC, ALAC, Vorbis, PCM 16-bit, WMA v2, Dolby Digital (AC3), Dolby Digital Plus (E-AC3), DTS
- Traitement **parallèle** configurable (jusqu'à 32 workers)
- File d'attente avec reprise après interruption/crash
- Paramètres avancés : durée d'analyse, taille de sonde, resampler (soxr/swr)

### Normalisation Loudness EBU R128
- Traitement en **2 passes** pour une précision maximale
- Paramètres configurables : Integrated (-70 à 0 LUFS), LRA, True Peak
- Compatible avec AAC, AC3, E-AC3, MP3, Opus, WMA, Vorbis

### Sélection de pistes MKV / MP4
- Détecte automatiquement **toutes les pistes audio** d'un conteneur
- Sélecteur unitaire (un fichier) et **batch** (plusieurs épisodes en une fois)
- Auto-sélection par **langue préférée** (FR, EN, JP, etc.)
- Sortie MKA avec **préservation des tags langue/titre** pour MKVMerge

### Analyse spectrale
- Comparaison **waveform + Spectrogramme FFT** source vs encodé
- Rendu matplotlib avec barre de navigation intégrée

### Mise à jour FFmpeg intégrée
- Installation via **WinGet** (Release Full ou Essentials)
- Téléchargement direct **Git Master Full** depuis gyan.dev
- Création automatique des symlinks WinGet + mise à jour du PATH utilisateur

### Interface
- **Drag & drop** de fichiers et dossiers
- **11 thèmes** de couleurs + mode clair/sombre
- **Préréglages one-click** : Série 5.1, Podcast, Musique HQ, Web léger, FLAC
- Préréglages **personnels** illimités
- Progression dans la **barre des tâches Windows** (ITaskbarList3)
- **Notifications Windows Toast** en fin de batch
- Crash log détaillé (`pyaudiocodingtools_crash.log`)

---

## Installation (version portable)

1. Téléchargez **`PyAudioCodingTools_v2.4_Portable.zip`** depuis [Releases](https://github.com/Crysisjim/PyAudioCodingTools/releases)
2. Extrayez dans n'importe quel dossier
3. Lancez `PyAudioCodingTools_v2.4.exe`
4. À la première utilisation, cliquez **Options → Mise à jour FFmpeg** pour installer FFmpeg

> Les fichiers de configuration (`pyaudiocodingtools_settings.json`, `pyaudiocodingtools_presets.json`) sont créés automatiquement à côté de l'exe.

---

## Installation (depuis les sources)

```bash
git clone https://github.com/Crysisjim/PyAudioCodingTools.git
cd PyAudioCodingTools
pip install -r requirements.txt
python main.py
```

**Dépendances** : `customtkinter`, `tkinterdnd2`, `pygame-ce`, `Pillow`, `numpy`, `matplotlib`, `requests`, `win11toast`

---

## FFmpeg

FFmpeg n'est **pas inclus** dans l'exe pour des raisons de taille et de licence.

| Méthode | Commande |
|---------|----------|
| WinGet (recommandé) | `winget install Gyan.FFmpeg` |
| Via l'app | Onglet Options → bouton **Mise à jour FFmpeg** |
| Manuel | [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) |

---

## Codecs — référence rapide

| Codec | Format | Surround | Loudnorm |
|-------|--------|----------|----------|
| AAC | `.aac` / `.m4a` | ✅ 7.1 | ✅ |
| Dolby Digital Plus | `.eac3` / `.mka` | ✅ 7.1 | ✅ |
| Dolby Digital | `.ac3` / `.mka` | ✅ 5.1 | ✅ |
| DTS | `.dts` / `.mka` | ✅ 5.1 | ❌ |
| MP3 | `.mp3` | ❌ stéréo | ✅ |
| Opus | `.opus` | ✅ 7.1 | ✅ |
| FLAC | `.flac` | ✅ 8ch | ❌ |
| ALAC | `.m4a` | ✅ 8ch | ❌ |
| Vorbis | `.ogg` | ✅ 8ch | ✅ |
| WMA v2 | `.wma` | ❌ stéréo | ✅ |
| PCM 16-bit | `.wav` | ✅ 8ch | ❌ |

---

## Compilation (rebuild l'exe)

```bat
build.bat
```

Le script installe les dépendances, nettoie les anciens builds, et produit `dist\PyAudioCodingTools_v2.4.exe` via PyInstaller.

> **PyInstaller** est requis uniquement pour la compilation : `pip install pyinstaller`

---

## Crédits

- **Développé par** Crysisjim
- Code & Architecture initiale : Grok 4 (xAI) — 20%
- Optimisation & Finitions : Gemini 2.5 Pro (Google) — 20%
- Refactoring, corrections & features v2.1–2.4 : Claude Opus / Sonnet (Anthropic) — 20%
- Direction, tests & intégration : Crysisjim — 40%

**Bibliothèques** : Python · CustomTkinter · FFmpeg · Pygame · Matplotlib · NumPy · Pillow · tkinterdnd2

---

## Changelog

### v2.4
- Préréglages intégrés one-click (Série, Podcast, Musique, Web, FLAC)
- Auto-sélection de la piste préférée (FR/EN/JP/…) dans les sélecteurs
- Bouton "Ouvrir le dossier de sortie"
- Timeout WAV adaptatif (gros fichiers PCM Blu-ray)
- Reprise après crash avec relance auto de l'encodage
- Crash log détaillé

### v2.3
- Sélection de pistes MKV/MP4 unitaire et batch
- Sortie MKA avec préservation des tags langue/titre
- Mise à jour FFmpeg intégrée (WinGet + Git Master Full)
- Création automatique des symlinks WinGet

### v2.2
- Spectrogramme FFT (comparaison source/encodé)
- Normalisation Loudnorm EBU R128 en 2 passes
- Traitement parallèle configurable
- Notifications Windows Toast

---

## Licence

MIT — voir [LICENSE](LICENSE)
