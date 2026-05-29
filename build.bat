@echo off
chcp 65001 >nul
echo ========================================================
echo      PyAudioCodingTools v2.4 - Build Script
echo ========================================================
echo.

:: 1. Installation des dependances
echo [1/4] Installation des librairies requises...
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet
echo      OK
echo.

:: 2. Nettoyage des anciens builds
echo [2/4] Nettoyage des anciens builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo      OK
echo.

:: 3. Compilation
echo [3/4] Compilation en cours...
echo      (Cela peut prendre 2-5 minutes)
echo.

python -m PyInstaller --noconsole --onefile ^
 --name "PyAudioCodingTools_v2.4" ^
 --icon "Assets/vivi.ico" ^
 --add-data "Assets;Assets" ^
 --collect-all "tkinterdnd2" ^
 --hidden-import "PIL._tkinter_finder" ^
 --hidden-import "matplotlib" ^
 --hidden-import "matplotlib.pyplot" ^
 --hidden-import "matplotlib.backends.backend_tkagg" ^
 --hidden-import "numpy" ^
 --hidden-import "pygame" ^
 --hidden-import "requests" ^
 --hidden-import "win11toast" ^
 --hidden-import "customtkinter" ^
 --hidden-import "multiprocessing" ^
 --hidden-import "concurrent.futures" ^
 main.py

echo.
if exist "dist\PyAudioCodingTools_v2.4.exe" (
    echo [4/4] Copie des fichiers supplementaires...
    
    :: Taille du fichier
    for %%A in ("dist\PyAudioCodingTools_v2.4.exe") do set SIZE=%%~zA
    set /a SIZE_MB=%SIZE% / 1048576
    
    echo.
    echo ========================================================
    echo      BUILD REUSSI !
    echo ========================================================
    echo.
    echo      Executable : dist\PyAudioCodingTools_v2.4.exe
    echo      Taille     : ~%SIZE_MB% Mo
    echo.
    echo      Pour lancer : double-cliquez sur l'exe dans dist\
    echo      FFmpeg n'est PAS inclus dans l'exe, il doit etre
    echo      installe separement (via le bouton Mise a jour).
    echo ========================================================
) else (
    echo.
    echo ========================================================
    echo      ERREUR DE BUILD !
    echo ========================================================
    echo      Verifiez les erreurs ci-dessus.
    echo      Causes frequentes :
    echo        - Module manquant (pip install ...)
    echo        - Antivirus qui bloque PyInstaller
    echo        - Python 32-bit au lieu de 64-bit
    echo ========================================================
)
echo.
pause
