"""OpenFFBoard: opis ustawień dla interfejsu + połączenie przez wirtualny port COM.

Komendy klas `sys`, `axis`, `fx` pochodzą z oficjalnego OpenFFBoard (v1.17). Klasa `xdrive`
to sterownik MotorXDrive z naszej specyfikacji - firmware musi zarejestrować dokładnie te
nazwy komend (patrz README, "Kontrakt komend xdrive"). Jeśli klasy nie ma w `sys.lsactive`,
jej pola i akcje są ukrywane.
"""
from __future__ import annotations

import logging
import time

from ..core import Action, BaseLink, DeviceInfo, Event, Field, FirmwareSpec, LiveState, Section
from . import protocol as p
from .simulator import SimulatedOpenFFBoard

log = logging.getLogger(__name__)

try:
    import serial
    from serial.tools import list_ports
except ImportError:  # pragma: no cover - zostaje tylko symulacja
    serial = None
    list_ports = None

POLL_INTERVAL = 0.015
LIVE_INTERVAL = 1.0  # odczyty diagnostyczne (napięcie, stan sterownika)
QUERY_TIMEOUT = 0.6
POWER_MAX = 0x7FFF
G = 100 / 255  # gain 0..255 pokazywany jako %


def _gain(key: str, label: str, description: str = "") -> Field:
    return Field(key, label, 0, 255, scale=G, description=description)


SECTIONS = (
    Section("ffb", "Ogólne", "Najważniejsze parametry", "ffb", (
        Field("axis.0.degrees", "Kąt obrotu", 1, 0x7FFF, unit="°", step=10, slider_min=180,
              slider_max=2520, presets=(360, 540, 720, 900, 1080, 1440),
              description="Pełny kąt obrotu od blokady do blokady (axis.degrees)."),
        Field("axis.0.power", "Moc", 0, POWER_MAX, scale=100 / POWER_MAX, step=50,
              description="Maksymalny moment silnika – 100% to pełna skala sterownika (axis.power). "
                          "Zaczynaj od niskich wartości."),
        _gain("axis.0.fxratio", "Udział efektów z gry",
              "Część mocy dostępna dla efektów z gry; reszta zostaje jako zapas dla blokady "
              "(axis.fxratio, domyślnie 80%)."),
    )),
    Section("ffb", "Efekty z gry", "Wzmocnienie efektów warunkowych wysyłanych przez grę", "wheel", (
        _gain("fx.0.spring", "Sprężyna", "Efekt sprężyny z gry (fx.spring)."),
        _gain("fx.0.damper", "Tłumienie", "Efekt tłumienia z gry (fx.damper)."),
        _gain("fx.0.friction", "Tarcie", "Efekt tarcia z gry (fx.friction)."),
        _gain("fx.0.inertia", "Bezwładność", "Efekt bezwładności z gry (fx.inertia)."),
    )),
    Section("ffb", "Efekty bazy", "Generowane przez sterownik, niezależnie od gry", "base", (
        _gain("axis.0.idlespring", "Sprężyna bezczynności",
              "Centruje kierownicę, gdy żadna gra nie wysyła FFB (axis.idlespring)."),
        _gain("axis.0.axisdamper", "Tłumienie osi",
              "Stały opór zależny od prędkości – wycisza oscylacje (axis.axisdamper)."),
        _gain("axis.0.axisfriction", "Tarcie osi", "Stałe tarcie osi (axis.axisfriction)."),
        _gain("axis.0.axisinertia", "Bezwładność osi", "Symulowana masa kierownicy (axis.axisinertia)."),
    )),
    Section("ffb", "Blokada i krzywa", "Koniec zakresu i charakterystyka siły", "warning", (
        _gain("axis.0.esgain", "Sztywność blokady",
              "Jak mocno baza zatrzymuje kierownicę na końcu zakresu (axis.esgain)."),
        Field("axis.0.expo", "Krzywa wykładnicza", -127, 127, unit="", kind="slider",
              description="Korekcja charakterystyki siły: 0 = liniowo, dodatnie = łagodniej przy "
                          "małych siłach (axis.expo)."),
    )),
    Section("base", "Oś", "Kierunek i ograniczenia ruchu", "power", (
        Field("axis.0.invert", "Odwróć oś", 0, 1, kind="toggle",
              description="Odwraca kierunek osi i sił (axis.invert)."),
        Field("axis.0.maxspeed", "Limit prędkości", 0, 65535, unit="°/s", step=50, slider_max=3000,
              description="Ogranicza prędkość obrotu kierownicy bez trzymania. 0 = bez limitu (axis.maxspeed)."),
        Field("axis.0.maxtorquerate", "Limit narastania momentu", 0, 65535, kind="stepper", unit="",
              step=10, description="Maksymalna zmiana momentu w zliczeniach/ms. 0 = bez limitu "
                                   "(axis.maxtorquerate)."),
        Field("axis.0.cpr", "CPR enkodera (odczyt)", 0, 1 << 30, kind="readonly", unit="",
              description="Rozdzielczość zgłaszana przez enkoder – MT6701 ABZ: 4096 (axis.cpr)."),
    )),
    Section("base", "Silnik XDrive", "Sterownik FOC MotorXDrive (DRV8301 + MT6701)", "base", (
        Field("xdrive.0.ilimit", "Limit prądu", 500, 30000, unit="mA", step=250, slider_max=20000,
              description="Maksymalny prąd fazowy = maksymalny moment (xdrive.ilimit). Przy pierwszych "
                          "testach 3000–5000 mA."),
        Field("xdrive.0.vlimit", "Limit napięcia", 500, 24000, unit="mV", step=100, slider_max=12000,
              description="Maksymalne napięcie na fazach (xdrive.vlimit)."),
        Field("xdrive.0.mode", "Tryb sterowania", 0, 1, kind="choice",
              options=(("Prądowy (FOC)", 1), ("Napięciowy", 0)),
              description="Prądowy to normalna praca. Napięciowy tylko do diagnostyki – "
                          "kierownica stawia opór przy szybkim obrocie (xdrive.mode)."),
        Field("xdrive.0.poles", "Pary biegunów", 1, 64, kind="stepper",
              description="Silnik z hoverboardu ma zwykle 15 par. Zmiana unieważnia kalibrację (xdrive.poles)."),
        Field("xdrive.0.cpr", "CPR enkodera", 64, 65535, kind="stepper", step=64,
              description="MT6701 w trybie ABZ: 1024 PPR × 4 = 4096. Zmiana unieważnia kalibrację (xdrive.cpr)."),
        Field("xdrive.0.bw", "Pasmo regulatora prądu", 100, 5000, kind="stepper", step=100, unit="rad/s",
              description="Szybkość pętli prądowej. Domyślnie 1000 (xdrive.bw)."),
        Field("xdrive.0.index", "Środek z indeksu Z", 0, 1, kind="toggle",
              description="Po włączeniu baza odtwarza zapisany środek, gdy kierownica minie impuls Z "
                          "enkodera (xdrive.index)."),
        Field("xdrive.0.sensorDirection", "Kierunek enkodera", -1, 1, kind="choice",
              options=(("Normalny", 1), ("Odwrócony", -1)), signed_direction=True,
              description="Ustawiany przez kalibrację; ręcznie zmieniaj tylko, jeśli wiesz po co."),
        Field("xdrive.0.invert", "Odwróć kierunek", 0, 1, kind="toggle",
              description="Odwraca moment i pozycję razem (xdrive.invert)."),
    )),
    Section("base", "Diagnostyka XDrive", "Odczyty odświeżane co sekundę", "diag", (
        Field("xdrive.0.state", "Stan sterownika", 0, 7, kind="readonly", unit="",
              options=(("Start", 0), ("Pomiar offsetów", 1), ("Bezczynny", 2), ("Wyrównanie", 3),
                       ("Kalibracja", 4), ("Praca", 5), ("Test", 6), ("Błąd", 7)), live=True),
        Field("xdrive.0.errors", "Błędy (bity)", 0, 1 << 30, kind="readonly", unit="", live=True,
              description="0 = brak. 1 DRV8301, 2 SPI, 4 offset ADC, 8 nadnapięcie, 16 podnapięcie, "
                          "32 hamowanie za długo, 64 brak prądu przy kalibracji, 128 bieguny/CPR, "
                          "256 rezystancja, 512 brak kalibracji, 1024 nadprąd, 2048 test przerwany."),
        Field("xdrive.0.vbus", "Napięcie zasilania", 0, 1 << 20, kind="readonly", unit="V", scale=0.001,
              live=True),
        Field("xdrive.0.brake", "Rezystor hamujący", 0, 100, kind="readonly", live=True),
        Field("xdrive.0.res", "Rezystancja fazy", 0, 65535, kind="readonly", unit="mΩ", scale=0.1),
        Field("xdrive.0.ind", "Indukcyjność fazy", 0, 65535, kind="readonly", unit="µH"),
        Field("xdrive.0.calratio", "Kontrola biegunów/CPR", 0, 5000, kind="readonly", unit="‰",
              description="Ruch enkodera przy kalibracji względem oczekiwanego, 1000 = idealnie (950–1050 OK)."),
        Field("xdrive.0.indexfound", "Indeks Z wykryty", 0, 1, kind="readonly", unit="",
              options=(("Nie", 0), ("Tak", 1)), live=True),
        Field("xdrive.0.offset", "Offset elektryczny", -(1 << 30), 1 << 30, kind="readonly", unit=""),
    )),
)

ACTIONS = (
    # bez potwierdzenia: nic się nie rusza, a przycisk ma być pod ręką na pulpicie
    Action("zero", "Wycentruj", "center"),
    Action("calibrate", "Kalibracja silnika", "diag", requires="xdrive.0",
           confirm_title="Uruchomić kalibrację?",
           confirm_text="Silnik ustawi wirnik i sprawdzi kierunek enkodera (xdrive.cal). "
                        "Kierownica się poruszy – puść ją i odsuń ręce.",
           confirm_label="Kalibruj"),
    Action("test", "Test obrotu", "sync", requires="xdrive.0",
           confirm_title="Uruchomić test obrotu?",
           confirm_text="Kierownica wykona +360° w prawo, 720° w lewo i wróci do zera (xdrive.test). "
                        "Puść kierownicę i upewnij się, że nic nie blokuje obrotu.",
           confirm_label="Start testu"),
    Action("reboot", "Restart", "power", ends_session=True,
           confirm_title="Zrestartować płytkę?",
           confirm_text="Niezapisane zmiany zostaną utracone (sys.reboot).",
           confirm_label="Restartuj"),
    Action("dfu", "Tryb DFU", "import", variant="danger", ends_session=True,
           confirm_title="Przejść w tryb DFU?",
           confirm_text="Płytka uruchomi bootloader STM32 (sys.dfu). Wgraj plik .hex / .bin w "
                        "STM32CubeProgrammer (połączenie USB). Po wgraniu zrestartuj płytkę.",
           confirm_label="Przejdź w DFU"),
)

_ACTION_COMMANDS = {
    "save": "sys.0.save",
    "reboot": "sys.0.reboot",
    "dfu": "sys.0.dfu",
    "zero": "axis.0.zeroenc",
    "calibrate": "xdrive.0.cal",
    "test": "xdrive.0.test",
}

PROFILE_KEYS = ("axis.0.degrees", "axis.0.fxratio", "fx.0.spring", "fx.0.damper", "fx.0.friction",
                "fx.0.inertia", "axis.0.idlespring", "axis.0.axisdamper", "axis.0.axisfriction",
                "axis.0.axisinertia", "axis.0.esgain")


def _profile(degrees, fxratio, spring, damper, friction, inertia, idle, a_damper, a_friction,
             a_inertia, esgain) -> dict[str, int]:
    return dict(zip(PROFILE_KEYS, (degrees, fxratio, spring, damper, friction, inertia, idle,
                                   a_damper, a_friction, a_inertia, esgain)))


# Punkty startowe (wartości surowe 0-255 jak w firmware) - do dostrojenia na bazie.
BUILTIN_PROFILES = {
    "Domyślny": {"game": "Uniwersalny", "settings": _profile(900, 204, 64, 64, 254, 127, 127, 30, 0, 0, 127)},
    "iRacing": {"game": "iRacing", "settings": _profile(900, 230, 0, 40, 100, 60, 60, 20, 0, 0, 160)},
    "Assetto Corsa Competizione": {"game": "ACC", "settings": _profile(900, 210, 64, 64, 120, 80, 60, 30, 0, 0, 160)},
    "Assetto Corsa": {"game": "Assetto Corsa", "settings": _profile(900, 220, 64, 64, 150, 100, 60, 25, 0, 0, 160)},
    "F1 25": {"game": "F1", "settings": _profile(360, 200, 128, 80, 100, 80, 60, 30, 0, 0, 200)},
    "Drift": {"game": "AC / Drift", "settings": _profile(1080, 220, 30, 20, 60, 40, 40, 10, 0, 0, 140)},
    "Euro Truck Simulator 2": {"game": "ETS2 / ATS", "settings": _profile(1440, 160, 128, 100, 160, 120, 100, 40, 20, 0, 120)},
}

SPEC = FirmwareSpec(
    id="openffboard",
    name="OpenFFBoard",
    controller="MKS XDrive Mini + firmware OpenFFBoard (MotorXDrive)",
    sections=SECTIONS,
    actions=ACTIONS,
    profile_keys=PROFILE_KEYS,
    strength_key="axis.0.power",
    range_key="axis.0.degrees",
    builtin_profiles=BUILTIN_PROFILES,
)

_MAIN_CLASSES = {0: "Basic (failsafe)", 1: "FFB Wheel (1 oś)", 2: "FFB Joystick (2 osie)",
                 3: "HID Gamepad (ext FFB)"}


def find_port() -> str | None:
    if list_ports is None:
        return None
    for port in list_ports.comports():
        if port.vid == p.USB_VID and port.pid == p.USB_PID:
            return port.device
    return None


class OpenFFBoardLink(BaseLink):
    spec = SPEC

    def __init__(self, simulate: bool = False, port_factory=None) -> None:
        super().__init__(simulate)
        self._port_factory = port_factory
        self._sim: SimulatedOpenFFBoard | None = None
        self._parser = p.ReplyParser()
        self._settings: dict[str, int] = {}
        self._power = 1
        self._pos: int | None = None
        self._torque: int | None = None
        self._last_poll = 0.0
        self._last_live = 0.0
        self._live_keys = [k for k, f in self._fields.items() if f.live]
        self._port_name = ""

    # --- wejście/wyjście ----------------------------------------------------------------

    def _open(self):
        self._parser = p.ReplyParser()
        if self._port_factory:
            self._port_name = "SIM"
            return self._port_factory()
        if self.simulate:
            if self._sim is None:
                self._sim = SimulatedOpenFFBoard()
            self._sim.closed = False
            self._port_name = "symulacja"
            return self._sim
        port = find_port()
        if port is None:
            return None
        self._port_name = port
        return serial.Serial(port, 115200, timeout=0, write_timeout=0.5)

    def _send(self, dev, commands: list[str]) -> None:
        for chunk in p.batches(commands):
            dev.write(chunk)

    def _pump(self, dev, timeout: float, until=None) -> None:
        """Czyta odpowiedzi przez maks. `timeout` s (krócej, gdy `until()` zwróci True)."""
        end = time.monotonic() + timeout
        while True:
            waiting = dev.in_waiting
            if waiting:
                for reply in self._parser.feed(dev.read(waiting)):
                    self._handle(reply)
            if until is not None and until():
                return
            if time.monotonic() >= end:
                return
            if not waiting:
                time.sleep(0.001)

    def _query(self, dev, keys: list[str], timeout: float = QUERY_TIMEOUT) -> dict[str, str]:
        """Odczyt wielu wartości naraz; brak odpowiedzi = firmware nie zna komendy."""
        answers: dict[str, str] = {}
        self._awaiting = (set(keys), answers)
        try:
            self._send(dev, [p.get(k) for k in keys])
            self._pump(dev, timeout, until=lambda: len(answers) == len(keys))
        finally:
            self._awaiting = None
        return answers

    _awaiting: tuple[set[str], dict[str, str]] | None = None

    def _handle(self, reply: p.Reply) -> None:
        key = reply.key
        if reply.is_set:
            if not reply.ok:
                self.events.put(Event("error", f"Płytka odrzuciła {reply.command}"))
            return
        if self._awaiting and key in self._awaiting[0]:
            self._awaiting[1][key] = reply.value
        if key == "axis.0.curpos":
            self._pos = reply.int_value()
        elif key == "axis.0.curtorque":
            self._torque = reply.int_value()
        elif key in self._fields and not self._awaiting:
            # niezamówiona odpowiedź: firmware rozgłasza zmianę zrobioną innym interfejsem (np. HID)
            value = reply.int_value()
            if value is not None and self._settings.get(key) != value:
                self._settings[key] = value
                self.events.put(Event("settings", dict(self._settings)))
        if key == "axis.0.power":
            self._power = max(1, reply.int_value() or 1)

    # --- BaseLink ---------------------------------------------------------------------

    def _handshake(self, dev):
        if hasattr(dev, "reset_input_buffer"):
            dev.reset_input_buffer()
        sysinfo = self._query(dev, ["sys.0.swver", "sys.0.hwtype", "sys.0.main", "sys.0.lsactive"], 1.5)
        if "sys.0.swver" not in sysinfo:
            raise OSError(f"{self._port_name}: brak odpowiedzi OpenFFBoard")
        active = p.parse_lsactive(sysinfo.get("sys.0.lsactive", ""))
        settings = self._read_settings(dev)
        main = p.Reply("", sysinfo.get("sys.0.main", "")).int_value()
        simulated = self.simulate or self._port_factory is not None
        info = DeviceInfo(
            firmware_id=SPEC.id, simulated=simulated, product=sysinfo.get("sys.0.hwtype", "OpenFFBoard"),
            version=sysinfo["sys.0.swver"],
            capabilities=active,
            details=[
                ("Płytka", sysinfo.get("sys.0.hwtype", "–")),
                ("Firmware", f"OpenFFBoard {sysinfo['sys.0.swver']}"),
                ("Tryb (main)", _MAIN_CLASSES.get(main, str(main))),
                ("Sterownik silnika", "MotorXDrive" if "xdrive.0" in active else "brak klasy xdrive"),
                ("Połączenie", "Symulacja" if simulated else f"USB CDC ({self._port_name})"),
            ])
        return info, settings

    def _read_settings(self, dev) -> dict[str, int]:
        answers = self._query(dev, list(self._fields))
        settings = {}
        for key, raw in answers.items():
            value = p.Reply(key + "?", raw).int_value()
            if value is not None:
                settings[key] = value
        self._settings = settings
        self._power = max(1, settings.get("axis.0.power", 1))
        return dict(settings)

    def _poll(self, dev) -> LiveState | None:
        now = time.monotonic()
        if now - self._last_live >= LIVE_INTERVAL:
            self._last_live = now
            live = [k for k in self._live_keys if k in self._settings]
            if live:  # odpowiedzi trafią do _handle jako zmiany ustawień
                self._send(dev, [p.get(k) for k in live])
        if now - self._last_poll >= POLL_INTERVAL:
            self._last_poll = now
            self._pos = self._torque = None
            self._send(dev, ["axis.0.curpos?", "axis.0.curtorque?"])
        self._pump(dev, 0.02, until=lambda: self._pos is not None and self._torque is not None)
        if self._pos is None:
            return None
        torque = (self._torque or 0) / self._power
        return LiveState(self._pos / 0x7FFF, max(-1.0, min(1.0, torque)))

    def _write_settings(self, dev, values: dict[str, int]) -> None:
        self._send(dev, [p.set_(k, v) for k, v in values.items()])
        self._settings.update(values)
        if "axis.0.power" in values:
            self._power = max(1, values["axis.0.power"])

    def _do_action(self, dev, action_id: str) -> None:
        cmd = _ACTION_COMMANDS[action_id]
        self._send(dev, [p.get(cmd)])
        if action_id == "save":  # zapis do flash chwilę trwa - poczekaj na potwierdzenie
            done = {}
            self._awaiting = ({cmd}, done)
            try:
                self._pump(dev, 1.5, until=lambda: cmd in done)
            finally:
                self._awaiting = None
