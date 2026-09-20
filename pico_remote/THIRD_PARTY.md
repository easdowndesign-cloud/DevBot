# Bundled third-party files

The Core Electronics PiicoDev MicroPython drivers and font below were retrieved
from their public `main` branches on 2026-09-06. Their upstream `LICENSE.md`
files are preserved in `vendor_licenses/`; the code portion is MIT-licensed.

| Local file | Upstream source | SHA-256 |
|---|---|---|
| `PiicoDev_Unified.py` | https://github.com/CoreElectronics/CE-PiicoDev-Unified | `1507C2126B0FCB1B140674CD9A5281A82BB5D19E1DBCCC3FD5114DD7EE53AFE8` |
| `PiicoDev_Transceiver.py` | https://github.com/CoreElectronics/CE-PiicoDev-Transceiver-MicroPython-Module | `C39663DB547AB50BA26357CC44A520527550AEAB11CFDCEBAB35A36E9F246750` |
| `PiicoDev_SSD1306.py` | https://github.com/CoreElectronics/CE-PiicoDev-SSD1306-MicroPython-Module | `FA8A4D1C4B1D958AE5B7A98D90E4615FFB1A5F5FBCE8FF5CE1B7B2CC6C3B403F` |
| `font-pet-me-128.dat` | https://github.com/CoreElectronics/CE-PiicoDev-SSD1306-MicroPython-Module | `B0DB3489E4E877A8B901BA857C373F9F3DAE73C71A9E2829F4D3696BC3586A34` |

Because the recorded upstream locations are moving branches, update these
files deliberately: download all three together, re-run the desktop tests and
hardware smoke tests, update the checksums/date here, and retain the licence
files. Do not allow Thonny or an automated package action to replace just one
driver silently.
