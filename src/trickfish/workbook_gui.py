import pathlib
import os
import subprocess
import sys
from importlib.resources import as_file, files
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .workbook import DEFAULT_PROMPT, export_workbook, load_pgn


class WorkbookApp:
    def __init__(self, root):
        self.root = root
        self.book = None
        self.output = None
        root.title("Trickfish PGN Workbook")
        root.geometry("1000x760")
        root.minsize(820, 650)
        frame = ttk.Frame(root, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="PGN Workbook", font=("Segoe UI", 21)).pack(anchor="w")
        ttk.Label(frame, text="Turn your supplied chess lines into student sheets and a separate coach key.").pack(anchor="w", pady=(3, 12))
        opening = ttk.Frame(frame)
        opening.pack(fill="x")
        ttk.Button(opening, text="1. Open PGN", command=self.open).pack(side="left")
        ttk.Button(opening, text="Open example", command=self.open_example).pack(side="left", padx=8)
        self.status = tk.StringVar(value="No PGN loaded. Files remain on this computer.")
        ttk.Label(frame, textvariable=self.status, wraplength=900).pack(anchor="w", pady=8)
        middle = ttk.Frame(frame)
        middle.pack(fill="both", expand=True)
        left = ttk.Frame(middle)
        left.pack(side="left", fill="both", expand=True)
        ttk.Label(left, text="2. Select positions (Ctrl / Shift for multiple)").pack(anchor="w")
        selection = ttk.Frame(left)
        selection.pack(fill="x", pady=5)
        ttk.Button(selection, text="Select all", command=self.select_all).pack(side="left")
        ttk.Button(selection, text="Clear", command=self.clear_selection).pack(side="left", padx=5)
        self.selection_status = tk.StringVar(value="0 selected (maximum 50)")
        ttk.Label(selection, textvariable=self.selection_status).pack(side="left")
        scroll = ttk.Scrollbar(left)
        scroll.pack(side="right", fill="y")
        self.listbox = tk.Listbox(left, selectmode="extended", exportselection=False, yscrollcommand=scroll.set, width=53)
        self.listbox.pack(fill="both", expand=True)
        scroll.configure(command=self.listbox.yview)
        self.listbox.bind("<<ListboxSelect>>", self.preview)
        self.board = tk.Canvas(middle, width=330, height=345, background="white", highlightthickness=0)
        self.board.pack(side="right", padx=(16, 0))
        ttk.Label(frame, text="Workbook title").pack(anchor="w", pady=(12, 0))
        self.title = tk.StringVar(value="Chess workbook")
        ttk.Entry(frame, textvariable=self.title).pack(fill="x")
        ttk.Label(frame, text="Student prompt (comments and source continuations stay in the coach PDF)").pack(anchor="w", pady=(8, 0))
        self.prompt = tk.Text(frame, height=3, wrap="word")
        self.prompt.insert("1.0", DEFAULT_PROMPT)
        self.prompt.pack(fill="x")
        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=12)
        self.export_button = ttk.Button(actions, text="3. Export PDFs", command=self.export, state="disabled")
        self.export_button.pack(side="left")
        self.result_buttons = []
        for label, target in (("Open student PDF", "student.pdf"), ("Open coach PDF", "coach.pdf"), ("Open output folder", None)):
            button = ttk.Button(actions, text=label, command=lambda target=target: self.open_result(target), state="disabled")
            button.pack(side="left", padx=(8, 0))
            self.result_buttons.append(button)
        ttk.Label(frame, text="No engine analysis. Supplied lines are not certified best moves. Coach review is required.", wraplength=900).pack(anchor="w")

    def open(self):
        path = filedialog.askopenfilename(filetypes=[("PGN files", "*.pgn"), ("All files", "*.*")])
        if not path:
            return
        self.load(path)

    def open_example(self):
        with as_file(files("trickfish").joinpath("data/workbook-demo.pgn")) as path:
            self.load(path)

    def load(self, path):
        try:
            book = load_pgn(path)
        except (ValueError, OSError, UnicodeError) as error:
            messagebox.showerror("Cannot open PGN", str(error))
            return
        self.book = book
        self.listbox.delete(0, "end")
        for entry in book.entries:
            self.listbox.insert("end", f"{entry.number}. {entry.label}")
        self.listbox.selection_set(0)
        self.status.set(f"{pathlib.Path(path).name}: {len(book.entries)} positions, including side variations.")
        self.preview()

    def select_all(self):
        if self.book is not None:
            self.listbox.selection_set(0, "end")
            self.preview()

    def clear_selection(self):
        self.listbox.selection_clear(0, "end")
        self.preview()

    def preview(self, event=None):
        import chess

        self.board.delete("all")
        selected = self.listbox.curselection()
        self.selection_status.set(f"{len(selected)} selected (maximum 50)")
        self.export_button.configure(state="normal" if 1 <= len(selected) <= 50 else "disabled")
        if not selected or self.book is None:
            return
        board = chess.Board(self.book.entries[selected[0]].fen)
        for rank in range(8):
            for file in range(8):
                x, y = 22 + file * 36, 15 + (7 - rank) * 36
                color = "#e8edef" if (file + rank) % 2 else "#66828f"
                self.board.create_rectangle(x, y, x + 36, y + 36, fill=color, outline=color)
                piece = board.piece_at(chess.square(file, rank))
                if piece:
                    self.board.create_text(x + 18, y + 18, text=piece.unicode_symbol(), font=("Segoe UI Symbol", 26), fill="#101820")
        for index in range(8):
            self.board.create_text(40 + index * 36, 315, text="abcdefgh"[index])
            self.board.create_text(11, 33 + (7 - index) * 36, text=str(index + 1))

    def export(self):
        selected = self.listbox.curselection()
        if not selected:
            messagebox.showerror("Select positions", "Select at least one position.")
            return
        if len(selected) > 50:
            messagebox.showerror("Too many positions", "Select at most 50 positions per workbook.")
            return
        parent = filedialog.askdirectory(title="Choose parent folder for a NEW workbook folder")
        if not parent:
            return
        from tkinter.simpledialog import askstring

        name = askstring("New folder", "New folder name:", initialvalue="trickfish-workbook", parent=self.root)
        if name is None:
            return
        reserved = {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}
        if (not name.strip() or pathlib.Path(name).name != name or name.endswith((" ", "."))
                or name.split(".")[0].upper() in reserved or any(c in name for c in '/\\:<>"|?*')
                or any(ord(c) < 32 for c in name)):
            messagebox.showerror("Invalid folder", "Use a simple new folder name.")
            return
        try:
            output = export_workbook(self.book, [n + 1 for n in selected], pathlib.Path(parent) / name,
                                     self.title.get(), self.prompt.get("1.0", "end").strip())
        except (ValueError, OSError) as error:
            messagebox.showerror("Export failed", str(error))
            return
        self.status.set(f"Saved: {output}")
        self.output = output
        for button in self.result_buttons:
            button.configure(state="normal")
        messagebox.showinfo("Workbook exported", f"Saved student.pdf, coach.pdf and receipt.json to:\n{output}")

    def open_result(self, name):
        if self.output is None:
            return
        path = self.output / name if name else self.output
        try:
            if not path.exists():
                raise OSError("The exported file or folder was moved or deleted. Export again.")
            if sys.platform == "win32":
                os.startfile(str(path))
            else:
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])
        except OSError as error:
            messagebox.showerror("Cannot open result", str(error))


def main():
    root = tk.Tk()
    WorkbookApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
