from importlib.resources import as_file, files
import json
import pathlib
import sys

from .workbook import export_workbook, load_pgn


def run(output):
    from .workbook_gui import WorkbookApp
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    try:
        app = WorkbookApp(root)
        app.open_example()
        root.update_idletasks()
        if app.book is None or len(app.book.entries) != 9:
            raise ValueError("Bundled example did not load")
        app.clear_selection()
        app.listbox.selection_set(0)
        app.listbox.selection_set(2)
        app.preview()
        if app.listbox.curselection() != (0, 2):
            raise ValueError("Position selection failed")
    finally:
        root.destroy()
    with as_file(files("trickfish").joinpath("data/workbook-demo.pgn")) as path:
        book = load_pgn(path)
    target = export_workbook(book, [1, 3], output, "Packaged workbook smoke")
    for name in ("student.pdf", "coach.pdf"):
        if not (target / name).read_bytes().startswith(b"%PDF-"):
            raise ValueError("Missing packaged PDF output")
    (target / "smoke.json").write_text(json.dumps({"frozen": bool(getattr(sys, "frozen", False)),
        "example_positions": len(book.entries), "selected_positions": [1, 3],
        "tk_widgets": "constructed", "export": "completed",
        "scope": "startup/resources/selection/PDF export; not visual or clean-machine certification"}, indent=2), encoding="utf-8")
    return pathlib.Path(target)
