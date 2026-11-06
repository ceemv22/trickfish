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

When a selected position has no legal moves, the unchanged default question asks the student to assess legal moves and check status instead of asking for a move. A custom question is preserved as supplied; the author must ensure it fits every selected position.

## Distribution boundary

This repository still has no selected license. No project license is selected by this feature. The optional `chess` dependency has its own GPL license; inspect its installed distribution notice before planning a distributed commercial build. The prototype does not bundle external engines. An internal Windows folder/ZIP build is available as described below. Dependency-license compliance, supported-platform checks and paid-product validation remain separate unfinished release work. This is not a ready-to-sell installer.

## Internal Windows package

Build on Windows x64 with standard Python 3.12:

```powershell
python -m pip install -r packaging/requirements-workbook-build.txt
python packaging/build_workbook.py --output dist/workbook-windows
```

The output directory must not already exist. Build dependencies are installed into the interpreter used for the command. A dedicated virtual environment is recommended. PyInstaller's onedir/windowed mode creates `app/TrickfishWorkbook/TrickfishWorkbook.exe` and its `_internal` directory. Preserve both. The ZIP contains the complete application folder; extract it before double-clicking the executable. Users do not need a separate Python installation. This claim describes the bundle format, not a completed clean-machine certification.

The build runs the resulting executable with `--smoke-test` from outside the repository. It constructs Tk widgets, loads the packaged example, selects positions and generates student/coach PDFs, then requires a `frozen: true` receipt. Build output includes exact dependency versions, file hashes, ZIP SHA-256, smoke evidence and collected Python/Tk/dependency notices. The GUI remains unverified visually; this automated check does not click native dialogs or certify a clean Windows machine.

The **Workbook Windows Package** workflow builds the same internal ZIP on `windows-latest`, preserves its evidence as an Actions artifact and does not create a public release. Its first result must be checked after pushing the new workflow. The package is unsigned; do not disable operating-system protections if startup is blocked. Report the message instead.

See [PyInstaller's usage](https://pyinstaller.org/en/stable/usage.html) for the folder-bundle model. PyInstaller's own [license exception](https://www.pyinstaller.org/en/stable/license.html) does not remove the separate obligations of bundled dependencies or choose a license for this repository. Notice collection is preparation, not a declaration that all distribution obligations have been satisfied.

## Validation

Install `pypdf` in the workbook environment to run PDF regression tests:

```powershell
python -m pip install pypdf
python -m unittest discover -s tests -p test_workbook.py -v
```

Tests check branch and black-to-move positions, illegal tails, invalid roots, promotion/en-passant, hidden answer text, receipt hashes, overwrite refusal and failed-layout cleanup. The Python workflow installs workbook dependencies and runs these tests separately. Existing reference-engine tests can run without the optional dependencies.

`examples/workbook-edge-cases.pgn` is an authored synthetic import fixture, not customer material or a recommended repertoire. It contains four games/24 positions, nested alternatives, Croatian comments, black-to-move and terminal roots, en passant, promotions and opposite castling. Export a six-page sample with:

```powershell
python -m trickfish.workbook examples/workbook-edge-cases.pgn --positions 1,14,16,20,21,24 --output edge-case-workbook
```

A local follow-up imported this fixture plus ten existing project review PGNs: 129 games/analysis lines and 1732 positions. Each node's available first continuation up to eight plies was replayed with the independent Trickfish reference move generator; board states matched after legal en-passant FEN normalization. This checks the exercised corpus, not arbitrary external PGN files. Student/coach text separation, Croatian text extraction and the six-page PDF layouts were checked. The new terminal-question behavior has regression checks for checkmate, stalemate and preservation of custom questions. An already downloaded executable must be rebuilt to include that change.
