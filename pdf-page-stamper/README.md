# PDF Page Stamper - Dong dau so trang hang loat

Cong cu keo-tha nhieu file PDF vao 1 cua so, tu dong dong dau
`Ten khach | Ten file | Trang X/Y` len tung trang cua tung file, xuat ra
file PDF moi (giu nguyen file goc). In xong chi can nhin so `Trang X/Y`
la biet ngay file nao het bao nhieu trang, staple dung bo cho khach.

## Buoc 1: Cai Python (chi lam 1 lan duy nhat)

1. Vao https://www.python.org/downloads/ , tai ban Python moi nhat cho Windows.
2. Chay file cai dat vua tai. **Quan trong:** o man hinh dau tien, tick chon
   o **"Add python.exe to PATH"** truoc khi bam Install.
3. Cai xong, mo Command Prompt (go `cmd` vao Start Menu), go lenh:

   ```
   python --version
   ```

   Neu hien ra so phien ban (VD `Python 3.12.x`) la cai thanh cong.

## Buoc 2: Cai thu vien can thiet

1. Tai/copy nguyen thu muc `pdf-page-stamper` nay ve may Windows.
2. Mo Command Prompt, di chuyen vao thu muc do, vi du:

   ```
   cd C:\Users\ban\Downloads\pdf-page-stamper
   ```

3. Cai cac thu vien can thiet:

   ```
   pip install -r requirements.txt
   ```

## Buoc 3: Chay thu (chua can dong goi .exe)

```
python app.py
```

Neu cua so app hien ra, keo vai file PDF vao thu de kiem tra truoc khi dong
goi thanh .exe.

## Buoc 4: Dong goi thanh file .exe (double-click la chay)

Cach don gian nhat: double-click file `build_exe.bat` trong thu muc nay.
No se tu dong cai PyInstaller va tao file exe.

Hoac tu go lenh:

```
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name "PDF-Danh-So" --collect-all tkinterdnd2 app.py
```

Sau khi chay xong, file exe nam tai:

```
dist\PDF-Danh-So.exe
```

Ve sau, chi can double-click file `PDF-Danh-So.exe` nay de mo app, khong
can mo Command Prompt hay dung Python nua. Anh co the copy file exe nay ra
Desktop hoac bat cu dau tien loi cho anh.

## Cach su dung app

1. Mo app (`python app.py` hoac double-click file .exe).
2. Keo-tha nhieu file PDF (hoac ca 1 folder chua PDF) vao khung phia tren,
   hoac bam "Them file PDF..." de chon thu cong.
3. App tu doc so trang tung file va tu dien "Ten khach" = ten file. Bam
   dup 2 lan vao o "Ten khach" de sua neu can.
4. Chon Vi tri (Header/Footer x Trai/Giua/Phai), Font, Co chu. Co the
   chinh them Le ngang / Le doc (mm) neu vi tri mac dinh chua vua y.
5. Chon thu muc luu ket qua (mac dinh la folder `Da_danh_so` ngay canh
   file dau tien).
6. Bam **Xu ly**. Xong se co thong bao va danh sach file loi (neu co).
7. Mo cac file PDF trong thu muc ket qua de in nhu binh thuong. File goc
   khong bi thay doi gi ca.

## Ghi chu ve font tieng Viet

App chi dung font co san tren Windows (Arial, Times New Roman, Tahoma,
Calibri) de dam bao dau tieng Viet hien thi dung. Neu bao loi "Khong tim
thay file font", nghia la may khong cai font do - chon font khac trong
danh sach.

## Cau truc thu muc

- `app.py` - giao dien nguoi dung (keo-tha, danh sach file, nut Xu ly).
- `stamper.py` - logic dong dau so trang len PDF (doc lap voi giao dien).
- `fonts.py` - tra cuu duong dan file font tren Windows.
- `requirements.txt` - danh sach thu vien can cai.
- `build_exe.bat` - script dong goi thanh file .exe.
