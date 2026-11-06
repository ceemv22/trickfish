import pathlib
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .workbook import export_workbook, load_pgn


class WorkbookApp:
    def __init__(self, root):
        self.root = root
        self.book = None
        root.title("Trickfish PGN Workbook")
        root.geometry("1000x760")
        root.minsize(820, 650)
        frame = ttk.Frame(root, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="PGN Workbook", font=("Segoe UI", 21)).pack(anchor="w")
        ttk.Label(frame, text="Turn your supplied chess lines into student sheets and a separate coach key.").pack(anchor="w", pady=(3, 12))
        ttk.Button(frame, text="1. Open PGN", command=self.open).pack(anchor="w")
        self.status = tk.StringVar(value="No PGN loaded. Files remain on this computer.")
        ttk.Label(frame, textvariable=self.status, wraplength=900).pack(anchor="w", pady=8)
        middle = ttk.Frame(frame)
        middle.pack(fill="both", expand=True)
        left = ttk.Frame(middle)
        left.pack(side="left", fill="both", expand=True)
        ttk.Label(left, text="2. Select positions (Ctrl / Shift for multiple)").pack(anchor="w")
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
        self.prompt.insert("1.0", "Choose a move and explain your plan. What reply should you check?")
        self.prompt.pack(fill="x")
        self.export_button = ttk.Button(frame, text="3. Export student PDF + coach PDF", command=self.export, state="disabled")
        self.export_button.pack(anchor="w", pady=12)
        ttk.Label(frame, text="No engine analysis. Supplied lines are not certified best moves. Coach review is required.", wraplength=900).pack(anchor="w")

    def open(self):
        path = filedialog.askopenfilename(filetypes=[("PGN files", "*.pgn"), ("All files", "*.*")])
        if not path:
            return
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
        self.export_button.configure(state="normal")
        self.status.set(f"{pathlib.Path(path).name}: {len(book.entries)} positions, including side variations.")
        self.preview()

    def preview(self, event=None):
        import chess

        self.board.delete("all")
        selected = self.listbox.curselection()
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
        parent = filedialog.askdirectory(title="Choose parent folder for a NEW workbook folder")
        if not parent:
            return
        from tkinter.simpledialog import askstring

        name = askstring("New folder", "New folder name:", initialvalue="trickfish-workbook", parent=self.root)
        if name is None:
            return
        if not name.strip() or pathlib.Path(name).name != name or name in {".", ".."} or any(c in name for c in '/\\:'):
            messagebox.showerror("Invalid folder", "Use a simple new folder name.")
            return
        try:
            output = export_workbook(self.book, [n + 1 for n in selected], pathlib.Path(parent) / name,
                                     self.title.get(), self.prompt.get("1.0", "end").strip())
        except (ValueError, OSError) as error:
            messagebox.showerror("Export failed", str(error))
            return
        self.status.set(f"Saved: {output}")
        messagebox.showinfo("Workbook exported", f"Saved student.pdf, coach.pdf and receipt.json to:\n{output}")


def main():
    root = tk.Tk()
    WorkbookApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
