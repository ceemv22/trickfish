# Start with PGN Workbook

This guide describes the Windows preview. It is an unpublished customer-document draft until attached to an actual release.

## First export

1. Extract the complete ZIP to a writable folder. Keep `TrickfishWorkbook.exe` and `_internal` together.
2. Double-click `TrickfishWorkbook.exe`. No separate Python installation is needed. If Windows blocks startup, report the exact message instead of disabling protections.
3. Click **Open example** for an immediate trial, or **Open PGN** to choose a UTF-8 `.pgn` file you are entitled to use.
4. Click a position row. Use Ctrl/Shift for multiple positions, or **Select all** / **Clear**. The counter must show 1 to 50 selected positions.
5. Set the workbook title and question. Keep answers out of both fields: they are printed on student pages.
6. Click **Export PDFs**, choose a parent directory and enter a new folder name. Existing folders are not overwritten.
7. Click **Open student PDF** or **Open coach PDF**. You need a normal PDF reader or browser associated with PDF files.

Each selected position produces one page per PDF. The student file contains a board, question and writing space. The coach file contains the selected node's comment and up to eight plies of its supplied first continuation. Review that source material before teaching with it. A supplied move is not a certified best answer.

## What stays private

Normal import/export runs on your computer without a file-upload service or user account. If you later send a bug report, only share material you intend to disclose. Prefer a small anonymized PGN reproducer rather than private student names, a complete repertoire or copyrighted teaching material.

## Common problems

| Problem | What to do |
| --- | --- |
| Export button disabled | Select between 1 and 50 positions. |
| Existing output folder | Choose a new folder name. The app does not overwrite your earlier workbook. |
| Illegal/malformed PGN or invalid FEN | Check the indicated game in the PGN source. Legal replay validation does not silently repair a bad line. |
| Import shows unexpected branches | Side variations are selectable separately. Use the labels and board preview to choose the intended position. |
| Comment does not fit | Shorten the comment at the selected node and import again. Long text fails rather than being silently clipped. |
| Wrong continuation in coach PDF | The first supplied continuation is used. Edit the PGN main/side-line ordering if you intended a different answer. |
| No continuation supplied | That node has no recorded next move. This is not proof that the position is a solved puzzle. |
| Last output no longer opens | The files were moved/deleted or the operating system has no associated PDF reader. Locate them manually or export into a new folder. |

## Terms and source

Workbook is GPL-3.0-or-later software, without warranty as set out in the license. The matching source and build instructions are in `SOURCE-CODE.zip`. Dependency notices and the exact scope are included in the application folder. Paying for a prepared download does not remove your GPL rights to modify and redistribute. This is a document-formatting tool, not coaching, engine analysis or player profiling.
