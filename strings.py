# strings.py - Bilingual FR/EN translation system for PyAudioCodingTools

_LANG = 'fr'

def set_lang(lang: str):
    global _LANG
    _LANG = lang if lang in ('fr', 'en') else 'fr'

def get_lang() -> str:
    return _LANG

def T(key: str, **kwargs) -> str:
    """Return translated string. Falls back to FR then to key itself."""
    s = _STRINGS.get(_LANG, _STRINGS['fr']).get(key)
    if s is None:
        s = _STRINGS['fr'].get(key, key)
    if kwargs:
        return s.format(**kwargs)
    return s

_STRINGS = {
    'fr': {
        # === WINDOW ===
        'window_title':         "PyAudioCodingTools v{version} - Batch GUI pour encodage audio",
        'window_title_pct':     "[{pct}%] PyAudioCodingTools v{version}",
        'window_title_done':    "PyAudioCodingTools v{version} — ✓ Terminé",

        # === TABS ===
        'tab_input':    'Input',
        'tab_output':   'Output',
        'tab_params':   "Paramètres d'encodage",
        'tab_presets':  'Préréglages',
        'tab_options':  'Options',
        'tab_about':    'À propos',

        # === INPUT TAB ===
        'btn_add_files':        "Ajouter des fichiers 📄",
        'btn_add_folder':       "Ajouter un dossier 📁",
        'btn_remove_sel':       "Retirer la sélection 🗑️",
        'btn_clear_all':        "Tout vider ❌",
        'btn_move_up':          "Monter ↑",
        'btn_move_down':        "Descendre ↓",
        'btn_open_output':      "📂 Dossier sortie",

        # === OUTPUT TAB ===
        'chk_detailed':         "Informations détaillées",
        'btn_save_log':         "Sauvegarder le log 💾",
        'btn_clear_log':        "Effacer log et tâches 🧹",
        'tasks_label':          "Liste des tâches en cours",

        # === ENCODING PARAMS TAB ===
        'lbl_codec':            "Codec Audio :",
        'lbl_bitrate':          "Bitrate (kbps) :",
        'lbl_samplerate':       "Fréquence (Hz) :",
        'lbl_channels':         "Canaux :",
        'valid_ok':             "✓ Configuration valide — Prêt à encoder",
        'chk_copy_meta':        "Copier les métadonnées",
        'chk_loudnorm':         "Normalisation Loudnorm (EBU R128)",
        'chk_dialnorm':         "Dialnorm (-31 dB)",
        'chk_spectrum':         "Comparaison de spectre audio",
        'chk_mka':              "Sortie MKA (conteneur)",
        'loudnorm_title':       "Paramètres de normalisation Loudness (EBU R128)",
        'lbl_target_i':         "Cible I (LUFS) :",
        'lbl_lra':              "LRA :",
        'lbl_truepeak':         "True Peak (dB) :",
        'adv_title':            "Paramètres avancés FFmpeg",
        'lbl_analyze_dur':      "Durée d'analyse :",
        'lbl_probe_size':       "Taille de sonde :",
        'lbl_async':            "Synchronisation audio :",
        'lbl_resampler':        "Resampler :",
        'lbl_min_comp':         "Compensation synchro :",
        'lbl_first_pts':        "Premier PTS :",
        'lbl_custom_params':    "Arguments personnalisés FFmpeg :",
        'custom_params_ph':     "ex: -af bass=g=5  |  -ac 2  |  -map 0:a:1",
        'codec_opts_title':     "Options spécifiques {codec}",
        'codec_no_opts':        "Aucune option spécifique pour ce codec",
        'lbl_enc_mode':         "Mode d'encodage :",
        'lbl_aac_profile':      "Profil AAC :",
        'lbl_vbr_quality':      "Qualité VBR :",
        'lbl_vbr_mode':         "Mode VBR :",

        # === PRESETS TAB ===
        'presets_builtin_title':"⚡ Préréglages intégrés (one-click)",
        'presets_custom_title': "💾 Préréglages personnels",
        'lbl_preset_name':      "Nom du préréglage :",
        'btn_preset_save':      "Sauvegarder 💾",
        'btn_preset_load':      "Charger 📂",
        'btn_preset_delete':    "Supprimer 🗑️",

        # === OPTIONS TAB ===
        'lbl_ffmpeg_path':      "Chemin vers FFmpeg :",
        'lbl_ffprobe_path':     "Chemin vers FFprobe :",
        'lbl_output_dir':       "Dossier de sortie :",
        'lbl_cpu_cores':        "Cœurs CPU :",
        'chk_parallel':         "Traitement parallèle",
        'lbl_accent_color':     "Couleur d'accentuation :",
        'chk_light_mode':       "Mode clair",
        'chk_sounds':           "Sons",
        'lbl_volume':           "Volume :",
        'btn_test_sound':       "🔊 Test",
        'chk_toast':            "Notifications Windows (Toast)",
        'lbl_language':         "Langue / Language :",
        'lang_restart_msg':     "La langue changera au prochain démarrage.\nThe language will change on next launch.",

        # === BOTTOM BAR ===
        'status_waiting':       "En attente...",
        'btn_start':            "Lancer l'encodage 🚀",
        'btn_pause':            "Pause ⏸️",
        'btn_resume':           "Reprendre ▶️",
        'btn_stop':             "Arrêter tout 🛑",

        # === PROGRESS / STATUS ===
        'step_prepare':         "Préparation",
        'step_wav':             "Conversion en WAV",
        'step_duration':        "Récupération de la durée",
        'step_loudnorm1':       "Analyse Loudnorm (passe 1/2)",
        'step_encode':          "Encodage final (passe 2/2)",
        'step_cancelled':       "Annulé.",
        'progress_txt':         "{done}/{total} ({pct}%) — Vitesse moy: {avg:.1f}x — Écoulé: {elapsed}   |   Restant estimé: {rem}",
        'progress_final':       "{done}/{total} (100%) — {status} — Temps total: {elapsed}",
        'status_ok':            "✓ Terminé",
        'status_partial':       "⚠ {ok}/{total} réussis",
        'cancel_msg':           "⛔ Annulation en cours...\n",

        # === MESSAGES / DIALOGS ===
        'err_empty_list':       "La liste de fichiers est vide !\nAjoutez des fichiers dans l'onglet Input avant de lancer.",
        'err_no_audio':         "Aucun fichier audio trouvé dans :\n{path}",
        'err_config_title':     "Erreur de configuration",
        'err_cpu_range':        "Le nombre de cœurs CPU doit être entre 1 et 32.",
        'err_ffmpeg_missing':   "FFmpeg introuvable ! Vérifiez le chemin dans l'onglet Options.",
        'err_ffprobe_missing':  "FFprobe introuvable ! Vérifiez le chemin dans l'onglet Options.",
        'warn_attention':       "Attention",
        'warn_empty_files':     "La liste de fichiers est vide !",
        'warn_preset_name':     "Veuillez entrer un nom de préréglage.",
        'warn_preset_invalid':  "Sélectionnez un préréglage valide dans la liste.",
        'info_preset_saved':    "Préréglage '{name}' sauvegardé !",
        'info_preset_loaded':   "Préréglage '{name}' chargé !",
        'info_preset_deleted':  "Préréglage supprimé !",
        'success_title':        "Succès",
        'log_saved':            "Log sauvegardé dans :\n{path}",
        'save_log_title':       "Enregistrer le log sous...",
        'no_output_folder':     "Aucun dossier de sortie défini et aucun fichier dans la liste.\n\nConfigurez le dossier de sortie dans l'onglet Options,\nou ajoutez des fichiers à traiter.",
        'no_output_title':      "Aucun dossier à ouvrir",
        'folder_not_found':     "Dossier introuvable :\n{path}",
        'folder_open_err':      "Impossible d'ouvrir le dossier :\n{err}",
        'warn_folder':          "Attention",

        # === SUMMARY WINDOW ===
        'summary_title':        "Résumé de l'encodage",
        'summary_encoding_title': "Résumé de l'encodage",
        'summary_success':      "Fichiers réussis : {n}",
        'summary_errors':       "Fichiers en erreur : {n}",
        'summary_time':         "Temps total : {t}",
        'btn_open_folder':      "📂 Ouvrir le dossier de sortie",
        'btn_show_errors':      "Voir les détails des erreurs",
        'btn_close':            "Fermer",
        'err_details_title':    "Détails des erreurs",

        # === TRACK PICKER ===
        'track_picker_title':   "Pistes audio — {filename}",
        'track_picker_info':    "Le fichier contient {n} piste(s) audio.\nCochez celles que vous souhaitez encoder :",
        'track_picker_note':    "Chaque piste cochée sera extraite puis encodée individuellement.",
        'track_lang_label':     "🌐 Langue préférée (pré-cochée automatiquement) :",
        'btn_check_all':        "Tout cocher",
        'btn_uncheck_all':      "Tout décocher",
        'btn_add_tracks':       "Ajouter les pistes cochées ✓",
        'btn_cancel':           "Annuler",
        'batch_picker_title':   "Sélection de pistes — {n} fichiers",
        'batch_picker_info':    "Vous avez sélectionné {n} fichiers conteneurs.\nVoici les pistes audio du premier fichier ({first}).\n\nLa même sélection sera appliquée à TOUS les fichiers :",
        'batch_picker_files':   "Fichiers concernés :",
        'batch_picker_warn':    "⚠ Si un fichier n'a pas la piste demandée, il sera ignoré pour cette piste.",
        'btn_apply_batch':      "Appliquer à {n} fichiers ✓",
        'no_audio_in_file':     "Aucune piste audio dans :\n{filename}",
        'tracks_added':         "{count} piste(s) ajoutée(s) à la file d'attente\npour {n} fichier(s).",
        'tracks_added_title':   "Pistes ajoutées",

        # === TOAST ===
        'toast_done_ok':        "Les {n} fichiers ont été encodés avec succès !",
        'toast_done_err':       "{ok}/{total} fichiers réussis, {err} en erreur",
        'toast_done_title_ok':  "Encodage terminé ✓",
        'toast_done_title_err': "Encodage terminé",

        # === VALIDATION WARNINGS ===
        'val_opus_max':         "Opus : le bitrate maximum recommandé est 256 kbps",
        'val_ac3_max':          "Dolby Digital (AC3) : le bitrate maximum est 640 kbps",
        'val_br_max':           "{codec} : le bitrate maximum recommandé est 320 kbps",
        'val_ch_max':           "{codec} ne supporte que {max} canaux maximum (vous demandez {req})",
        'val_loudnorm_incompat':"La normalisation Loudnorm n'est pas compatible avec {codec}",
        'val_dialnorm_only':    "Dialnorm est uniquement utilisé avec Dolby Digital Plus (E-AC3)",

        # === CRASH RECOVERY ===
        'recovery_title':       "Reprise après interruption",
        'recovery_msg':         "Un batch interrompu a été détecté !\n\n"
                                "• {remaining} fichier(s) restant(s) sur {total}\n"
                                "• {done} déjà terminé(s), {failed} en erreur\n"
                                "• Interrompu il y a environ {age} minute(s)\n",
        'recovery_missing':     "• ⚠ {n} fichier(s) introuvable(s) (ignorés)\n",
        'recovery_choice':      "\nOui = Reprendre automatiquement l'encodage\n"
                                "Non = Abandonner et supprimer la sauvegarde\n"
                                "Annuler = Ne rien faire (on redemandera au prochain lancement)",

        # === PRESET APPLIED ===
        'preset_applied_title': "Préréglage appliqué",
        'preset_applied_msg':   "✓ {name} appliqué.\n\nCodec : {codec}\nBitrate : {bitrate} kbps\nCanaux : {channels}\nLoudnorm : {loudnorm}\nDialnorm : {dialnorm}",

        # === FFMPEG UPDATE ===
        'ffmpeg_update_title':  "Installation / Mise à jour FFmpeg",
        'btn_ffmpeg_full':      "📦 Release Full (WinGet)",
        'btn_ffmpeg_ess':       "📦 Essentials (WinGet)",
        'btn_ffmpeg_git':       "🔧 Git Master Full",
        'ffmpeg_test_title':    "Test FFmpeg / FFprobe",
        'btn_ffmpeg_update':    "📥 Mise à jour",
        'btn_ffmpeg_gitbtn':    "🔧 Git Master",
        'btn_gyandev':          "🌐 gyan.dev",
        'ffmpeg_outdated':      "\n\n⚠ Une mise à jour est disponible !",
    },

    'en': {
        # === WINDOW ===
        'window_title':         "PyAudioCodingTools v{version} - Batch GUI for Audio Encoding",
        'window_title_pct':     "[{pct}%] PyAudioCodingTools v{version}",
        'window_title_done':    "PyAudioCodingTools v{version} — ✓ Done",

        # === TABS ===
        'tab_input':    'Input',
        'tab_output':   'Output',
        'tab_params':   'Encoding Settings',
        'tab_presets':  'Presets',
        'tab_options':  'Options',
        'tab_about':    'About',

        # === INPUT TAB ===
        'btn_add_files':        "Add Files 📄",
        'btn_add_folder':       "Add Folder 📁",
        'btn_remove_sel':       "Remove Selected 🗑️",
        'btn_clear_all':        "Clear All ❌",
        'btn_move_up':          "Move Up ↑",
        'btn_move_down':        "Move Down ↓",
        'btn_open_output':      "📂 Output Folder",

        # === OUTPUT TAB ===
        'chk_detailed':         "Detailed Output",
        'btn_save_log':         "Save Log 💾",
        'btn_clear_log':        "Clear Log & Tasks 🧹",
        'tasks_label':          "Active Tasks",

        # === ENCODING PARAMS TAB ===
        'lbl_codec':            "Audio Codec:",
        'lbl_bitrate':          "Bitrate (kbps):",
        'lbl_samplerate':       "Sample Rate (Hz):",
        'lbl_channels':         "Channels:",
        'valid_ok':             "✓ Valid configuration — Ready to encode",
        'chk_copy_meta':        "Copy Metadata",
        'chk_loudnorm':         "Loudness Normalization (EBU R128)",
        'chk_dialnorm':         "Dialnorm (-31 dB)",
        'chk_spectrum':         "Audio Spectrum Comparison",
        'chk_mka':              "MKA Output (container)",
        'loudnorm_title':       "EBU R128 Loudness Normalization Settings",
        'lbl_target_i':         "Target I (LUFS):",
        'lbl_lra':              "LRA:",
        'lbl_truepeak':         "True Peak (dB):",
        'adv_title':            "Advanced FFmpeg Parameters",
        'lbl_analyze_dur':      "Analyze Duration:",
        'lbl_probe_size':       "Probe Size:",
        'lbl_async':            "Audio Sync:",
        'lbl_resampler':        "Resampler:",
        'lbl_min_comp':         "Min Hard Comp:",
        'lbl_first_pts':        "First PTS:",
        'lbl_custom_params':    "Custom FFmpeg Arguments:",
        'custom_params_ph':     "e.g.: -af bass=g=5  |  -ac 2  |  -map 0:a:1",
        'codec_opts_title':     "{codec} specific options",
        'codec_no_opts':        "No specific options for this codec",
        'lbl_enc_mode':         "Encoding Mode:",
        'lbl_aac_profile':      "AAC Profile:",
        'lbl_vbr_quality':      "VBR Quality:",
        'lbl_vbr_mode':         "VBR Mode:",

        # === PRESETS TAB ===
        'presets_builtin_title':"⚡ Built-in Presets (one-click)",
        'presets_custom_title': "💾 Custom Presets",
        'lbl_preset_name':      "Preset name:",
        'btn_preset_save':      "Save 💾",
        'btn_preset_load':      "Load 📂",
        'btn_preset_delete':    "Delete 🗑️",

        # === OPTIONS TAB ===
        'lbl_ffmpeg_path':      "FFmpeg Path:",
        'lbl_ffprobe_path':     "FFprobe Path:",
        'lbl_output_dir':       "Output Folder:",
        'lbl_cpu_cores':        "CPU Cores:",
        'chk_parallel':         "Parallel Processing",
        'lbl_accent_color':     "Accent Color:",
        'chk_light_mode':       "Light Mode",
        'chk_sounds':           "Sounds",
        'lbl_volume':           "Volume:",
        'btn_test_sound':       "🔊 Test",
        'chk_toast':            "Windows Toast Notifications",
        'lbl_language':         "Language / Langue:",
        'lang_restart_msg':     "The language will change on next launch.\nLa langue changera au prochain démarrage.",

        # === BOTTOM BAR ===
        'status_waiting':       "Waiting...",
        'btn_start':            "Start Encoding 🚀",
        'btn_pause':            "Pause ⏸️",
        'btn_resume':           "Resume ▶️",
        'btn_stop':             "Stop All 🛑",

        # === PROGRESS / STATUS ===
        'step_prepare':         "Preparing",
        'step_wav':             "Converting to WAV",
        'step_duration':        "Getting duration",
        'step_loudnorm1':       "Loudnorm analysis (pass 1/2)",
        'step_encode':          "Final encoding (pass 2/2)",
        'step_cancelled':       "Cancelled.",
        'progress_txt':         "{done}/{total} ({pct}%) — Avg speed: {avg:.1f}x — Elapsed: {elapsed}   |   ETA: {rem}",
        'progress_final':       "{done}/{total} (100%) — {status} — Total time: {elapsed}",
        'status_ok':            "✓ Done",
        'status_partial':       "⚠ {ok}/{total} succeeded",
        'cancel_msg':           "⛔ Cancelling...\n",

        # === MESSAGES / DIALOGS ===
        'err_empty_list':       "File list is empty!\nAdd files in the Input tab before starting.",
        'err_no_audio':         "No audio files found in:\n{path}",
        'err_config_title':     "Configuration Error",
        'err_cpu_range':        "CPU cores must be between 1 and 32.",
        'err_ffmpeg_missing':   "FFmpeg not found! Check the path in the Options tab.",
        'err_ffprobe_missing':  "FFprobe not found! Check the path in the Options tab.",
        'warn_attention':       "Warning",
        'warn_empty_files':     "File list is empty!",
        'warn_preset_name':     "Please enter a preset name.",
        'warn_preset_invalid':  "Select a valid preset from the list.",
        'info_preset_saved':    "Preset '{name}' saved!",
        'info_preset_loaded':   "Preset '{name}' loaded!",
        'info_preset_deleted':  "Preset deleted!",
        'success_title':        "Success",
        'log_saved':            "Log saved to:\n{path}",
        'save_log_title':       "Save Log As...",
        'no_output_folder':     "No output folder set and no files in list.\n\nSet the output folder in the Options tab,\nor add files to process.",
        'no_output_title':      "No Folder to Open",
        'folder_not_found':     "Folder not found:\n{path}",
        'folder_open_err':      "Cannot open folder:\n{err}",
        'warn_folder':          "Warning",

        # === SUMMARY WINDOW ===
        'summary_title':        "Encoding Summary",
        'summary_encoding_title': "Encoding Summary",
        'summary_success':      "Files succeeded: {n}",
        'summary_errors':       "Files with errors: {n}",
        'summary_time':         "Total time: {t}",
        'btn_open_folder':      "📂 Open Output Folder",
        'btn_show_errors':      "View Error Details",
        'btn_close':            "Close",
        'err_details_title':    "Error Details",

        # === TRACK PICKER ===
        'track_picker_title':   "Audio Tracks — {filename}",
        'track_picker_info':    "This file contains {n} audio track(s).\nCheck the ones you want to encode:",
        'track_picker_note':    "Each checked track will be extracted and encoded separately.",
        'track_lang_label':     "🌐 Preferred language (auto-checked):",
        'btn_check_all':        "Check All",
        'btn_uncheck_all':      "Uncheck All",
        'btn_add_tracks':       "Add Checked Tracks ✓",
        'btn_cancel':           "Cancel",
        'batch_picker_title':   "Track Selection — {n} Files",
        'batch_picker_info':    "You selected {n} container files.\nShowing audio tracks from the first file ({first}).\n\nThe same selection will apply to ALL files:",
        'batch_picker_files':   "Affected files:",
        'batch_picker_warn':    "⚠ If a file doesn't have the requested track, it will be skipped for that track.",
        'btn_apply_batch':      "Apply to {n} Files ✓",
        'no_audio_in_file':     "No audio tracks in:\n{filename}",
        'tracks_added':         "{count} track(s) added to queue\nfor {n} file(s).",
        'tracks_added_title':   "Tracks Added",

        # === TOAST ===
        'toast_done_ok':        "All {n} files encoded successfully!",
        'toast_done_err':       "{ok}/{total} files succeeded, {err} failed",
        'toast_done_title_ok':  "Encoding complete ✓",
        'toast_done_title_err': "Encoding complete",

        # === VALIDATION WARNINGS ===
        'val_opus_max':         "Opus: maximum recommended bitrate is 256 kbps",
        'val_ac3_max':          "Dolby Digital (AC3): maximum bitrate is 640 kbps",
        'val_br_max':           "{codec}: maximum recommended bitrate is 320 kbps",
        'val_ch_max':           "{codec} supports {max} channels max (you requested {req})",
        'val_loudnorm_incompat':"Loudness normalization is not compatible with {codec}",
        'val_dialnorm_only':    "Dialnorm is only used with Dolby Digital Plus (E-AC3)",

        # === CRASH RECOVERY ===
        'recovery_title':       "Resume After Interruption",
        'recovery_msg':         "An interrupted batch was detected!\n\n"
                                "• {remaining} file(s) remaining out of {total}\n"
                                "• {done} already done, {failed} failed\n"
                                "• Interrupted about {age} minute(s) ago\n",
        'recovery_missing':     "• ⚠ {n} file(s) not found (will be skipped)\n",
        'recovery_choice':      "\nYes = Resume encoding automatically\n"
                                "No = Discard and delete the saved state\n"
                                "Cancel = Do nothing (will ask again on next launch)",

        # === PRESET APPLIED ===
        'preset_applied_title': "Preset Applied",
        'preset_applied_msg':   "✓ {name} applied.\n\nCodec: {codec}\nBitrate: {bitrate} kbps\nChannels: {channels}\nLoudnorm: {loudnorm}\nDialnorm: {dialnorm}",

        # === FFMPEG UPDATE ===
        'ffmpeg_update_title':  "Install / Update FFmpeg",
        'btn_ffmpeg_full':      "📦 Full Release (WinGet)",
        'btn_ffmpeg_ess':       "📦 Essentials (WinGet)",
        'btn_ffmpeg_git':       "🔧 Git Master Full",
        'ffmpeg_test_title':    "Test FFmpeg / FFprobe",
        'btn_ffmpeg_update':    "📥 Update",
        'btn_ffmpeg_gitbtn':    "🔧 Git Master",
        'btn_gyandev':          "🌐 gyan.dev",
        'ffmpeg_outdated':      "\n\n⚠ An update is available!",
    }
}
