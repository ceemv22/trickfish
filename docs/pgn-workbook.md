# PGN Workbook

Local Python prototype for turning supplied PGN lines into a student worksheet and a separate coach key. It does not use the C++ engine, Stockfish, Maia, cloud services or an account. No playing-strength or commercial-value claim is established.

## Windows setup

Use Python 3.11 or newer with Tkinter (the standard python.org Windows installer includes it):

```powershell
cd C:\Users\vibor\trickfish
python -m venv .venv-workbook
.\.venv-workbook\Scripts\python.exe -m pip install -e ".[workbook]"
.\.venv-workbook\Scripts\python.exe -m trickfish.workbook_gui
```

In the GUI:

1. Click **Open example** for the bundled example, or **Open PGN** for your own UTF-8 PGN. The example is included in installed Python packages; no repository checkout is needed to find it.
2. Select one or more position rows using Ctrl or Shift, or use **Select all** and **Clear**. The selection counter shows how many pages will be exported; export is disabled for zero or more than 50 positions. The preview displays the first selected position, with White at the bottom.
3. Set a title and a common open-ended question. Do not put an answer into the title or question: both are printed in the student PDF.
4. Export, choose the parent directory and enter a new folder name. Existing output folders are never overwritten.
5. Use **Open student PDF**, **Open coach PDF**, or **Open output folder** after export. Files open with the operating system's associated application. If an output was moved or deleted, the app reports that it must be exported again. Keep the coach file separate when sharing with students. `receipt.json` records the exact source-byte SHA-256, selected FENs and output hashes.

The preview is a position selector, not a chess-playing interface. There is no installer, payment integration or public storefront in this version. The optional dependency installation requires internet; normal importing and exporting run locally.

## CLI

```powershell
python -m trickfish.workbook examples/workbook-demo.pgn
python -m trickfish.workbook examples/workbook-demo.pgn --positions 1,3 --output my-new-workbook --title "Italian Game"
```

Without `--positions`, the command lists position numbers. Export creates one page per selected position in each PDF. The student PDF contains a board, side to move, common question and writing space. It omits PGN comments and continuations. The coach PDF includes the comment attached to the selected node and up to eight plies from that node's supplied first continuation. Side variations appear as separately selectable positions, not as all possible answers on a single page. Comments at future nodes are not combined into the selected node's comment.

## Input and limits

Multi-game PGN, SetUp/FEN roots, comments and side variations are supported through python-chess. Parser-reported errors, illegal variations and invalid starting boards are rejected. This is not byte-for-byte strict PGN syntax certification: python-chess accepts some nonstandard formatting. Result tags do not certify played outcomes. Position replay does not certify historical reachability or adjudication from missing pre-root history.

Limits: 5 MB input, 2000 imported positions, 50 selected positions, title 120 characters, question 600 characters and comment 4000 characters, subject to actual page space. Oversized text fails rather than silently clipping. Long comments must be shortened in the source. Generation occurs in a temporary sibling directory; layout errors do not publish a partial output package. A process crash may leave an intermediate `.workbook-*` directory.

PDF chess glyphs use an installed Segoe UI Symbol on Windows or DejaVu Sans on Linux. Apple Symbols is an unverified macOS fallback. The text font is ReportLab's bundled Vera. Windows PDF export has been exercised; the original workbook's Linux tests passed at b90e267, and macOS has not been tested. A local real-Tk integration smoke exercised example loading, selection, actual PDF generation, result-opening dispatch and preservation of the loaded document after a failed import. File dialogs and external application launch were mocked in that smoke. GUI appearance and interactive dialog behavior have not been visually certified through the desktop automation surface.

## Answer policy

A supplied PGN continuation is author material, not a proven best move. Positions without a continuation are marked explicitly. The tool does not generate tactical solutions, diagnose a student or infer a stable weakness. A coach must review the selected question, comments and continuations before use. Legal-move validation is not pedagogical validation.

## Distribution boundary

This repository still has no selected license. No project license is selected by this feature. The optional `chess` dependency has its own GPL license; inspect its installed distribution notice before planning a distributed commercial build. The prototype does not bundle external engines. Packaging, dependency-license compliance, supported-platform checks and paid-product validation remain separate unfinished release work. This source implementation is not a ready-to-sell installer.

## Validation

Install `pypdf` in the workbook environment to run PDF regression tests:

```powershell
python -m pip install pypdf
python -m unittest discover -s tests -p test_workbook.py -v
```

Tests check branch and black-to-move positions, illegal tails, invalid roots, promotion/en-passant, hidden answer text, receipt hashes, overwrite refusal and failed-layout cleanup. The Python workflow installs workbook dependencies and runs these tests separately. Existing reference-engine tests can run without the optional dependencies.
