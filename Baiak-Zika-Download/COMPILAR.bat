@echo off
echo ========================================
echo    COMPILANDO BAIAK-ZIKA LAUNCHER
echo ========================================
echo.

echo [1/3] Instalando dependencias...
pip install pyinstaller PyQt5 pillow requests

echo.
echo [2/3] Compilando launcher...
pyinstaller --onefile --windowed --name "Baiak-Zika" --icon="icon.ico" --add-data "assets;assets" launcher.py

echo.
echo [3/3] Copiando arquivos...
if not exist "Baiak-Zika-Pronto" mkdir Baiak-Zika-Pronto
copy dist\Baiak-Zika.exe Baiak-Zika-Pronto\
xcopy /E /I assets Baiak-Zika-Pronto\assets
copy icon.ico Baiak-Zika-Pronto\

echo.
echo ========================================
echo    PRONTO! Executavel em:
echo    Baiak-Zika-Pronto\Baiak-Zika.exe
echo ========================================
pause
