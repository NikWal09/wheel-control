# DD Control

Aplikacja konfiguracyjna do zestawu **DIY Direct Drive** (baza na MKS XDrive Mini + firmware FFBeast,
kierownica BLE i pedały na ESP32-S3). Zastępuje FFBeast Setup App własnym interfejsem w stylu
aplikacji Fanatec: podgląd na żywo, strojenie Force Feedback, ustawienia silnika i profile pod gry.

Projekt: [sim-racing-setup-DIY](https://github.com/Camildo7/sim-racing-setup-DIY) – Politechnika Poznańska.

![Pulpit](docs/pulpit.png)

## Funkcje

| Strona | Co robi |
| --- | --- |
| **Pulpit** | Kierownica obracająca się na żywo, kąt, moment (pasek + wykres), pedały, przyciski, szybki tuning |
| **Force Feedback** | Kąt obrotu, siła całkowita, efekty z gry (constant / periodic / spring), efekty bazy (sprężyna, tłumienia), wirtualna blokada |
| **Baza i silnik** | Włączanie sił, limit mocy i hamowania, pary biegunów, CPR enkodera, kierunki, wzmocnienia P/I, kalibracja, zapis / restart / DFU |
| **Pedały** | Podgląd gazu i hamulca, wybór osi, odwracanie, automatyczne wykrywanie osi („wciśnij pedał”) |
| **Kierownica** | Grafika kierownicy z 12 przyciskami + 2 łopatkami, test przycisków, przypisywanie przez kliknięcie |
| **Profile** | Wbudowane presety (iRacing, ACC, AC, F1, Drift, ETS2) i własne profile, porównanie z bieżącymi ustawieniami, eksport / import |
| **Ustawienia** | Tryb demo (symulacja całego sprzętu), kolor akcentu |

Zmiany ustawień trafiają do bazy natychmiast (do RAM). **Zapisz w bazie** utrwala je w pamięci flash,
**Cofnij** wczytuje z powrotem to, co jest w bazie.

## Uruchomienie

```bash
python -m pip install -r requirements.txt
python run.py            # normalnie - łączy się z bazą przez USB
python run.py --demo     # bez sprzętu: symulowana baza, pedały i kierownica
```

Gotowy plik `.exe` (folder `dist\DDControl`):

```bash
build.bat
```

Testy: `python -m pytest`

## Jak to działa

```
ddcontrol/
├─ ffbeast/
│  ├─ protocol.py    struktury i raporty HID FFBeast (pakowanie / rozpakowanie bajtów)
│  ├─ device.py      wątek połączenia: odczyt stanu, scalanie zapisów, komendy, auto-reconnect
│  └─ simulator.py   wirtualna baza udająca hid.device na poziomie bajtów
├─ gamepads.py       pedały i kierownica przez WinMM (joyGetPosEx) + symulacja
├─ storage.py        konfiguracja i profile w %APPDATA%\DDControl
├─ backend.py        QObject wystawiający dane i akcje do QML
├─ main.py           start aplikacji
└─ qml/              interfejs (Qt Quick, styl Basic z własnym motywem)
```

**Baza (FFBeast).** Komunikacja przez interfejs vendor HID (VID 1115, PID 22999, interfejs 0) zgodnie z
[dokumentacją FFBeast](https://ffbeast.github.io/docs/en/wheel_programming.html):

- stan (pozycja, moment, wersja firmware) – raport wejściowy wysyłany ciągle przez bazę,
- ustawienia – feature reporty `0x22` (efekty) i `0x21` (sprzęt), 64 bajty, spakowane little-endian,
- zmiana ustawienia – raport `0xA3` z typem `0x14`, ID pola, indeksem i wartością,
- komendy – raport `0xA3` z typem `0x01` restart / `0x02` zapis do flash / `0x03` DFU.

Wątek połączenia jest jedynym właścicielem uchwytu HID. Przy przeciąganiu suwaka do bazy leci tylko
ostatnia wartość, a ~0,4 s po serii zmian aplikacja odczytuje ustawienia z powrotem, żeby pokazać to,
co baza faktycznie przyjęła.

**Pedały i kierownica** to zwykłe kontrolery gier Windows, więc aplikacja tylko je podgląda. Kalibracja
i martwe strefy zostają w firmware ESP32. Urządzenia są rozpoznawane po domyślnych VID bibliotek
(`0x303A` USB HID ESP32, `0xE502` ESP32-BLE-Gamepad) albo wybierane ręcznie.

**Symulator** implementuje ten sam interfejs co `hid.device`, więc tryb demo i testy przechodzą przez
dokładnie ten sam kod protokołu co prawdziwa baza.

## Do sprawdzenia na prawdziwym sprzęcie

Protokół jest zaimplementowany według dokumentacji, ale nie był jeszcze testowany z fizyczną bazą:

- **Report ID raportu stanu** – dokumentacja nie podaje go wprost; aplikacja bierze 64 bajty po pierwszym
  bajcie niezależnie od ID. Jeśli kąt na pulpicie skacze bez sensu, uruchom `python run.py -v` i sprawdź log.
- **Zakresy pól** – np. maksymalny kąt obrotu przyjmowany przez firmware (suwak pozwala 180–2520°;
  wartość odczytana z bazy po zmianie pokaże, czy coś zostało przycięte).
- **Mapowanie osi pedałów i numeracja przycisków kierownicy** – użyj „Wykryj oś” i przypisywania
  przycisków na stronach Pedały / Kierownica.
- **Presety profili** to punkty startowe, nie wartości zmierzone na tej bazie.

Pierwsze testy rób z niskim *Limitem mocy* i rękami z dala od kierownicy.

![Force Feedback](docs/force-feedback.png)
![Kierownica](docs/kierownica.png)
