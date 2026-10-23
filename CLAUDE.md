# DD Control (wheel-control)

Aplikacja konfiguracyjna kierownicy DIY Direct Drive. Python 3.11+, PySide6/QML. Kontekst całego
projektu: `../CLAUDE.md`. Firmware bazy: `../OpenFFBoard-XDrive`.

## Komendy

```bash
python run.py                 # aplikacja (sprzęt)
python run.py --demo          # symulacja całego sprzętu
python -m pytest -q           # testy (muszą przechodzić przed commitem)
build.bat                     # testy + PyInstaller -> dist\DDControl\DDControl.exe
```

Zrzuty wszystkich stron bez okna (sprawdzanie QML):

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_FONTDIR=C:/Windows/Fonts python -m ddcontrol.main --demo --screenshots <katalog>
```

## Architektura

- `ddcontrol/core.py` – opis ustawień niezależny od firmware: `Field` (kind slider/stepper/toggle/choice/
  readonly, `scale`, `decimals`, `options`, `live`), `Section`, `Action` (`requires`, `ends_session`,
  potwierdzenie), `FirmwareSpec`, `BaseLink` – wątek połączenia (zmiany suwaków są scalane, potem resync).
- `ddcontrol/openffboard/` – OpenFFBoard przez USB CDC (`1209:FFB0`), protokół tekstowy
  `cls.inst.cmd?` / `=val` / `!`, odpowiedzi `[cmd|val]`. `driver.py`: `SECTIONS`, `ACTIONS`,
  `OPENFFBOARD_DEFAULTS`, profile, auto-wybór sterownika XDrive (`axis.0.drvtype=13`), konsola.
  `simulator.py` – symulowana płytka do testów i trybu demo (każde nowe pole dodaj też tutaj).
- `ddcontrol/ffbeast/` – FFBeast przez HID (`1115:22999`, raporty 0x21/0x22/0x25, 0xA3).
- `ddcontrol/backend.py` – most Python ↔ QML (właściwości, zdarzenia, profile, konsola, banery).
- `ddcontrol/qml/` – UI generowane ze schematu (`SchemaCards`, `SettingField`, `SettingSlider`);
  `Theme.qml` – kolory, ikony, `formatField`.
- `ddcontrol/gamepads.py` – pedały i kierownica przez WinMM; `storage.py` – profile i ustawienia.
- `WheelGraphic.qml` – rzut kierownicy z modelu STL: `tools/render_wheel.py <base.stl>` generuje
  `assets/wheel_front.png` (karbon, uchwyty, śruby, moduł diod; okna przezroczyste; łopatki wystają po bokach,
  pod obrazem) i wypisuje środki otworów przycisków i diod (wklejone w `slotPositions`/`ledPositions`).
  Sloty: lewa kolumna od góry, prawa od góry, łopatki L/P; etykieta = numer przycisku kontrolera
  (`wheelButtonMap`). Numeracja w kształcie U była próbowana i cofnięta na życzenie użytkownika.
  Diody: zasilanie, Bluetooth (mruga = szuka), ładowanie (kontroler nie wysyła stanu).

## Zasady

- Każde pole `xdrive.*` musi istnieć w `MotorXDrive::registerCommands` – pilnuje tego test
  `test_app_fields_match_firmware_commands`; `test_defaults_match_firmware_source` porównuje
  `OPENFFBOARD_DEFAULTS` z `EffectsCalculator.h` / `Axis.h`. Oba wymagają repo firmware obok.
- Nowe pole = wpis w `SECTIONS` + wartość w `simulator.DEFAULTS` (test sprawdza, że handshake czyta wszystkie).
- Napisy w UI po polsku, w opisie pola podaj komendę firmware w nawiasie, np. `(axis.esgain)`.
- Firmware nie odpowiada na nieznane komendy – brak odpowiedzi = pole ukryte / klasa nieaktywna.
