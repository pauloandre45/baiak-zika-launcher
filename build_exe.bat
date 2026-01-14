@echo off
echo ========================================
echo   Compilando Baiak-Zika Launcher
echo ========================================
echo.

REM Instala dependencias
pip install -r requirements.txt

REM Compila para .exe
pyinstaller --onefile --windowed --name "Baiak-Zika" --icon=icon.ico launcher.py

echo.
echo ========================================
echo   Compilacao concluida!
echo   O arquivo .exe esta em: dist\Baiak-Zika.exe
echo ========================================
pause
