# Workbook license scope

Effective 2026-11-08, the copyright holder licenses the following original Trickfish Workbook files under the GNU General Public License, version 3 or, at your option, any later version (SPDX: GPL-3.0-or-later):

- `src/trickfish/workbook.py`
- `src/trickfish/workbook_gui.py`
- `src/trickfish/workbook_smoke.py`
- `src/trickfish/data/workbook-demo.pgn`
- `packaging/workbook_package_init.py`
- `packaging/workbook_entry.py`
- `packaging/build_workbook.py`
- `packaging/requirements-workbook-build.txt`
- `packaging/WINDOWS-READ-ME.txt`
- `packaging/SOURCE-READ-ME.txt`
- `tests/test_workbook.py`
- `examples/workbook-demo.pgn`
- `examples/workbook-edge-cases.pgn`
- `docs/pgn-workbook.md`
- `docs/workbook-preview.md`
- `docs/workbook-preview/student.pdf`
- `docs/workbook-preview/coach.pdf`
- `docs/workbook-preview/student.png`
- `docs/workbook-preview/coach.png`
- `.github/workflows/workbook-windows.yml`
- this scope notice

Copyright (C) 2026 Vibor Sumić.

These files are free software: you can redistribute them and/or modify them under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

These files are distributed in the hope that they will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See `LICENSE-WORKBOOK.txt` for the full terms.

This grant does not license the entire repository. In particular, it does not grant a license for the C++ engine, the Python reference engine, practical-selection modules, the existing `src/trickfish/__init__.py`, logo, or other files not listed above. The Windows Workbook build stages only the three Workbook modules, packaged example and an isolated package initializer. It audits the frozen module list to reject other `trickfish.*` modules.

Dependencies retain their own copyright and license notices. The unmodified `chess` library is GPL-3.0-or-later; other bundled dependencies and runtime components retain their respective terms. Source distribution includes the matching chess source archive and the listed application/build sources. Third-party licenses are not replaced by this notice.

Charging for copies is permitted under the GPL, and recipients retain the rights granted by that license. There is no license-key or redistribution restriction in this grant. No public release, sale, trademark permission for third parties, warranty or product endorsement is implied by preparing a build. The existing Trickfish logo is not included in the standalone Workbook package.
