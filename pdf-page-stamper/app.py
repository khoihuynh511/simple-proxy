"""PDF Page Stamper - Giao dien keo-tha de danh so trang hang loat cho file PDF.

Cach dung:
    python app.py

Xem README.md de biet cach dong goi thanh file .exe chay tren Windows.
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _HAS_DND = True
except ImportError:
    _HAS_DND = False

from fonts import FONT_NAMES
from stamper import POSITIONS, get_page_count, stamp_pdf

FONT_SIZES = [8, 10, 12, 14]
DEFAULT_POSITION = "Header - Phai"
DEFAULT_FONT = "Arial"
DEFAULT_SIZE = 10
DEFAULT_MARGIN_X_MM = 15
DEFAULT_MARGIN_Y_MM = 10


class FileEntry:
    def __init__(self, path):
        self.path = path
        self.file_name = os.path.basename(path)
        try:
            self.page_count = get_page_count(path)
            self.error = None
        except Exception as exc:  # noqa: BLE001 - hien loi ro rang cho nguoi dung
            self.page_count = 0
            self.error = str(exc)
        self.customer_name = os.path.splitext(self.file_name)[0]


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Page Stamper - Danh so trang hang loat")
        self.root.geometry("820x560")

        self.files = {}  # tree item id -> FileEntry
        self.output_dir = tk.StringVar(value="")

        self._build_widgets()

    # ---------- UI construction ----------

    def _build_widgets(self):
        drop_frame = tk.LabelFrame(self.root, text="1. Keo file/folder PDF vao day (hoac bam nut Them file)")
        drop_frame.pack(fill="x", padx=10, pady=(10, 5))

        self.drop_label = tk.Label(
            drop_frame,
            text="Keo-tha file PDF hoac folder chua file PDF vao day",
            height=3, relief="ridge", bg="#f5f5f5",
        )
        self.drop_label.pack(fill="x", padx=8, pady=8)

        if _HAS_DND:
            self.drop_label.drop_target_register(DND_FILES)
            self.drop_label.dnd_bind("<<Drop>>", self._on_drop)
        else:
            self.drop_label.config(
                text="(Thu vien keo-tha chua duoc cai. Dung nut 'Them file' ben duoi de chon file.)"
            )

        btn_row = tk.Frame(drop_frame)
        btn_row.pack(fill="x", padx=8, pady=(0, 8))
        tk.Button(btn_row, text="Them file PDF...", command=self._browse_files).pack(side="left")
        tk.Button(btn_row, text="Xoa muc da chon", command=self._remove_selected).pack(side="left", padx=6)
        tk.Button(btn_row, text="Xoa tat ca", command=self._clear_all).pack(side="left")

        list_frame = tk.LabelFrame(self.root, text="2. Danh sach file (bam doi 2 lan vao 'Ten khach' de sua)")
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("file_name", "page_count", "customer_name")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        self.tree.heading("file_name", text="Ten file")
        self.tree.heading("page_count", text="So trang")
        self.tree.heading("customer_name", text="Ten khach")
        self.tree.column("file_name", width=350)
        self.tree.column("page_count", width=90, anchor="center")
        self.tree.column("customer_name", width=260)
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree.bind("<Double-1>", self._on_tree_double_click)

        opts_frame = tk.LabelFrame(self.root, text="3. Tuy chon dong dau")
        opts_frame.pack(fill="x", padx=10, pady=5)

        row1 = tk.Frame(opts_frame)
        row1.pack(fill="x", padx=8, pady=4)

        tk.Label(row1, text="Vi tri:").pack(side="left")
        self.position_var = tk.StringVar(value=DEFAULT_POSITION)
        ttk.Combobox(row1, textvariable=self.position_var, values=POSITIONS,
                     state="readonly", width=16).pack(side="left", padx=(4, 16))

        tk.Label(row1, text="Font:").pack(side="left")
        self.font_var = tk.StringVar(value=DEFAULT_FONT)
        ttk.Combobox(row1, textvariable=self.font_var, values=FONT_NAMES,
                     state="readonly", width=16).pack(side="left", padx=(4, 16))

        tk.Label(row1, text="Co chu:").pack(side="left")
        self.size_var = tk.StringVar(value=str(DEFAULT_SIZE))
        ttk.Combobox(row1, textvariable=self.size_var,
                     values=[str(s) for s in FONT_SIZES],
                     state="readonly", width=6).pack(side="left", padx=(4, 16))

        row2 = tk.Frame(opts_frame)
        row2.pack(fill="x", padx=8, pady=(0, 8))

        tk.Label(row2, text="Le ngang (mm, dung khi chon Trai/Phai):").pack(side="left")
        self.margin_x_var = tk.StringVar(value=str(DEFAULT_MARGIN_X_MM))
        tk.Entry(row2, textvariable=self.margin_x_var, width=6).pack(side="left", padx=(4, 16))

        tk.Label(row2, text="Le doc (mm, cach mep tren/duoi):").pack(side="left")
        self.margin_y_var = tk.StringVar(value=str(DEFAULT_MARGIN_Y_MM))
        tk.Entry(row2, textvariable=self.margin_y_var, width=6).pack(side="left", padx=(4, 16))

        out_frame = tk.LabelFrame(self.root, text="4. Thu muc luu ket qua")
        out_frame.pack(fill="x", padx=10, pady=5)
        row3 = tk.Frame(out_frame)
        row3.pack(fill="x", padx=8, pady=8)
        tk.Entry(row3, textvariable=self.output_dir).pack(side="left", fill="x", expand=True)
        tk.Button(row3, text="Chon thu muc...", command=self._browse_output_dir).pack(side="left", padx=(6, 0))

        action_frame = tk.Frame(self.root)
        action_frame.pack(fill="x", padx=10, pady=(5, 10))
        self.process_btn = tk.Button(
            action_frame, text="Xu ly", bg="#2e7d32", fg="white",
            font=("Segoe UI", 11, "bold"), command=self._on_process_clicked,
        )
        self.process_btn.pack(side="left")

        self.status_var = tk.StringVar(value="San sang.")
        tk.Label(action_frame, textvariable=self.status_var, anchor="w").pack(
            side="left", padx=12, fill="x", expand=True
        )

    # ---------- File list handling ----------

    def _add_paths(self, paths):
        pdf_paths = []
        for p in paths:
            p = p.strip("{}")  # tkinterdnd2 boc duong dan co khoang trang trong {}
            if os.path.isdir(p):
                for name in sorted(os.listdir(p)):
                    if name.lower().endswith(".pdf"):
                        pdf_paths.append(os.path.join(p, name))
            elif p.lower().endswith(".pdf"):
                pdf_paths.append(p)

        added, skipped_dupe = 0, 0
        existing_paths = {e.path for e in self.files.values()}
        for path in pdf_paths:
            if path in existing_paths:
                skipped_dupe += 1
                continue
            entry = FileEntry(path)
            item_id = self.tree.insert(
                "", "end",
                values=(entry.file_name,
                        entry.page_count if not entry.error else f"Loi: {entry.error}",
                        entry.customer_name),
            )
            self.files[item_id] = entry
            existing_paths.add(path)
            added += 1

        msg = f"Da them {added} file."
        if skipped_dupe:
            msg += f" ({skipped_dupe} file trung, bo qua)"
        self.status_var.set(msg)

    def _on_drop(self, event):
        paths = self.root.tk.splitlist(event.data)
        self._add_paths(paths)

    def _browse_files(self):
        paths = filedialog.askopenfilenames(
            title="Chon file PDF", filetypes=[("PDF files", "*.pdf")]
        )
        if paths:
            self._add_paths(paths)

    def _browse_output_dir(self):
        d = filedialog.askdirectory(title="Chon thu muc luu ket qua")
        if d:
            self.output_dir.set(d)

    def _remove_selected(self):
        for item_id in self.tree.selection():
            self.tree.delete(item_id)
            self.files.pop(item_id, None)

    def _clear_all(self):
        self.tree.delete(*self.tree.get_children())
        self.files.clear()

    def _on_tree_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item_id or column != "#3":  # chi cho sua cot "Ten khach"
            return

        x, y, width, height = self.tree.bbox(item_id, column)
        entry = self.files[item_id]

        edit_var = tk.StringVar(value=entry.customer_name)
        editor = tk.Entry(self.tree, textvariable=edit_var)
        editor.place(x=x, y=y, width=width, height=height)
        editor.focus_set()

        def commit(_event=None):
            entry.customer_name = edit_var.get().strip() or entry.customer_name
            self.tree.set(item_id, "customer_name", entry.customer_name)
            editor.destroy()

        editor.bind("<Return>", commit)
        editor.bind("<FocusOut>", commit)

    # ---------- Processing ----------

    @staticmethod
    def _unique_output_name(file_name, used_names):
        """Tranh de 2 file trung ten (VD tu 2 folder khac nhau) ghi de len nhau."""
        if file_name not in used_names:
            return file_name
        base, ext = os.path.splitext(file_name)
        counter = 2
        while f"{base} ({counter}){ext}" in used_names:
            counter += 1
        return f"{base} ({counter}){ext}"

    def _validate_inputs(self):
        if not self.files:
            messagebox.showwarning("Thieu file", "Chua co file PDF nao trong danh sach.")
            return None

        out_dir = self.output_dir.get().strip()
        if not out_dir:
            first_entry = next(iter(self.files.values()))
            out_dir = os.path.join(os.path.dirname(first_entry.path), "Da_danh_so")
            self.output_dir.set(out_dir)

        try:
            font_size = float(self.size_var.get())
            margin_x = float(self.margin_x_var.get())
            margin_y = float(self.margin_y_var.get())
        except ValueError:
            messagebox.showerror("Sai du lieu", "Co chu / le ngang / le doc phai la so.")
            return None

        return {
            "output_dir": out_dir,
            "position": self.position_var.get(),
            "font_name": self.font_var.get(),
            "font_size": font_size,
            "margin_x_mm": margin_x,
            "margin_y_mm": margin_y,
        }

    def _on_process_clicked(self):
        settings = self._validate_inputs()
        if settings is None:
            return

        self.process_btn.config(state="disabled")
        self.status_var.set("Dang xu ly...")
        thread = threading.Thread(target=self._process_all, args=(settings,), daemon=True)
        thread.start()

    def _process_all(self, settings):
        entries = list(self.files.values())
        ok_count, fail_messages = 0, []
        used_output_names = set()

        for idx, entry in enumerate(entries, start=1):
            self.root.after(0, self.status_var.set,
                             f"Dang xu ly {idx}/{len(entries)}: {entry.file_name}")
            if entry.error:
                fail_messages.append(f"{entry.file_name}: {entry.error}")
                continue
            try:
                out_name = self._unique_output_name(entry.file_name, used_output_names)
                used_output_names.add(out_name)
                out_path = os.path.join(settings["output_dir"], out_name)
                stamp_pdf(
                    input_path=entry.path,
                    output_path=out_path,
                    customer_name=entry.customer_name,
                    position=settings["position"],
                    font_name=settings["font_name"],
                    font_size=settings["font_size"],
                    margin_x_mm=settings["margin_x_mm"],
                    margin_y_mm=settings["margin_y_mm"],
                )
                ok_count += 1
            except Exception as exc:  # noqa: BLE001 - hien loi ro rang cho nguoi dung
                fail_messages.append(f"{entry.file_name}: {exc}")

        def finish():
            self.process_btn.config(state="normal")
            summary = f"Xong: {ok_count}/{len(entries)} file thanh cong."
            self.status_var.set(summary)
            if fail_messages:
                messagebox.showwarning(
                    "Hoan tat (co loi)",
                    summary + "\n\nCac file loi:\n" + "\n".join(fail_messages),
                )
            else:
                messagebox.showinfo(
                    "Hoan tat", summary + f"\nKet qua luu tai:\n{settings['output_dir']}"
                )

        self.root.after(0, finish)


def main():
    root = TkinterDnD.Tk() if _HAS_DND else tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
