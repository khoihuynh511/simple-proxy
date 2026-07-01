@echo off
REM Dong goi PDF Page Stamper thanh 1 file .exe duy nhat.
REM Chay file nay bang cach double-click, sau khi da cai Python va requirements.
REM Xem README.md de biet chi tiet.

python -m pip install --upgrade pyinstaller
python -m PyInstaller --onefile --windowed --name "PDF-Danh-So" --collect-all tkinterdnd2 app.py

echo.
echo Xong! File .exe nam trong thu muc dist\PDF-Danh-So.exe
pause
