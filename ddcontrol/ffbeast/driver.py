"""FFBeast: opis ustawień dla interfejsu + połączenie USB HID."""
from __future__ import annotations

import logging

from ..core import Action, BaseLink, DeviceInfo, Field, FirmwareSpec, LiveState, Section
from . import protocol as p
from .simulator import SimulatedWheelBase

log = logging.getLogger(__name__)

try:
    import hid  # pakiet "hidapi"
except ImportError:  # pragma: no cover - zostaje tylko symulacja
    hid = None


def _f(key: str, label: str, **kw) -> Field:
    spec = p.FIELDS_BY_KEY[key]
    if spec.fmt == "b" and spec.minimum == -1:
        kw.setdefault("signed_direction", True)
    return Field(key, label, spec.minimum, spec.maximum, **kw)


DIRECTION = (("Normalny", 1), ("Odwrócony", -1))
CLIP_LEVEL = 0.99  # moment >= 99% maksimum = clipping

SECTIONS = (
    Section("ffb", "Ogólne", "Najważniejsze parametry", "ffb", (
        _f("motionRange", "Kąt obrotu", unit="°", step=10, slider_min=180, slider_max=2520,
           presets=(360, 540, 720, 900, 1080, 1440),
           description="Pełny kąt obrotu od blokady do blokady. Gry ustawiające kąt same "
                       "(iRacing, ACC, AC) najlepiej działają z 900–1080°."),
        _f("totalStrength", "Siła całkowita",
           description="Globalny mnożnik wszystkich efektów. Zaczynaj od niskich wartości – silnik "
                       "z hoverboardu potrafi oddać ok. 15 Nm."),
    )),
    Section("ffb", "Efekty z gry", "Siły wysyłane przez symulator (DirectInput)", "wheel", (
        _f("dxConstantStrength", "Siła stała",
           description="Główny kanał FFB – siły na kołach, przyczepność, podsterowność."),
        _f("dxPeriodicStrength", "Efekty okresowe",
           description="Wibracje: tarki, nierówności nawierzchni, praca silnika."),
        _f("dxSpringStrength", "Sprężyna",
           description="Sprężyna centrująca wysyłana przez grę (np. w menu albo starszych tytułach)."),
        _f("dxConstantDirection", "Kierunek sił z gry", kind="choice", options=DIRECTION,
           description="Odwróć, jeśli w grze kierownica „ucieka” w zakręt zamiast stawiać opór."),
    )),
    Section("ffb", "Efekty bazy", "Generowane przez sterownik, niezależnie od gry", "base", (
        _f("integratedSpring", "Sprężyna centrująca",
           description="Stała siła wracająca do środka. Przydatna w grach bez FFB; w symulatorach zwykle 0%."),
        _f("staticDampening", "Tłumienie statyczne",
           description="Stały opór obrotu – dodaje „ciężaru” i wycisza drobne oscylacje."),
        _f("dynamicDampening", "Tłumienie dynamiczne",
           description="Opór rosnący z prędkością obrotu – stabilizuje kierownicę przy szybkich kontrach."),
    )),
    Section("ffb", "Wirtualna blokada", "Soft stop na końcu zakresu obrotu", "warning", (
        _f("softStopStrength", "Siła blokady",
           description="Jak mocno baza zatrzymuje kierownicę po przekroczeniu kąta obrotu."),
        _f("softStopRange", "Zakres narastania", unit="°", slider_max=90,
           description="Kąt (ponad zakres obrotu), na którym siła blokady rośnie do maksimum."),
        _f("softStopDampening", "Tłumienie blokady",
           description="Zapobiega odbijaniu się kierownicy od blokady."),
    )),
    Section("base", "Zasilanie", "Moc silnika i ochrona zasilacza", "power", (
        _f("forceEnabled", "Siły włączone", kind="toggle",
           description="Wyłączenie odcina moment silnika – kierownica obraca się swobodnie."),
        _f("powerLimit", "Limit mocy",
           description="Maksymalny moment jako % możliwości sterownika. Przy pierwszych testach trzymaj nisko."),
        _f("brakingLimit", "Limit hamowania",
           description="Ogranicza energię oddawaną przez silnik przy hamowaniu – chroni zasilacz przed przepięciem."),
    )),
    Section("base", "Silnik i enkoder", "Silnik BLDC z hoverboardu + MT6701", "base", (
        _f("polePairs", "Pary biegunów", kind="stepper",
           description="Silnik z hoverboardu ma zwykle 15 par (30 magnesów)."),
        _f("encoderCpr", "CPR enkodera", kind="stepper", step=64,
           description="Impulsy na obrót. MT6701 w trybie ABZ 1024 PPR × 4 = 4096."),
        _f("encoderDirection", "Kierunek enkodera", kind="choice", options=DIRECTION),
        _f("forceDirection", "Kierunek siły", kind="choice", options=DIRECTION),
        _f("amplifierGain", "Wzmocnienie pomiaru prądu", kind="choice",
           options=(("80 V/V", 0), ("40 V/V", 1), ("20 V/V", 2), ("10 V/V", 3)),
           description="Wzmocnienie wzmacniaczy prądu w sterowniku (DRV8301). Wyższe = lepsza "
                       "rozdzielczość, mniejszy zakres prądu."),
    )),
    Section("base", "Regulator", "Pętla prądu i filtracja pozycji", "tune", (
        _f("pGain", "Wzmocnienie P", kind="stepper"),
        _f("iGain", "Wzmocnienie I", kind="stepper", step=10),
        _f("positionSmoothing", "Wygładzanie pozycji",
           description="Filtr odczytu enkodera. Więcej = gładziej, ale z większym opóźnieniem."),
        _f("speedBufferSize", "Bufor prędkości", kind="stepper",
           description="Liczba próbek do wyliczania prędkości (wpływa na tłumienie dynamiczne)."),
    )),
    Section("base", "Kalibracja", "Ustawianie kąta elektrycznego przy starcie", "diag", (
        _f("calibrationMagnitude", "Siła kalibracji",
           description="Moment używany przy wyszukiwaniu położenia wirnika."),
        _f("calibrationSpeed", "Prędkość kalibracji"),
        _f("debugTorque", "Tryb debugowania momentu", kind="toggle",
           description="Diagnostyka sterownika – na co dzień wyłączony."),
    )),
)

ACTIONS = (
    Action("reboot", "Restart", "power", ends_session=True,
           confirm_title="Zrestartować bazę?",
           confirm_text="Niezapisane zmiany zostaną utracone. Po restarcie baza przeprowadzi "
                        "kalibrację – nie trzymaj kierownicy.",
           confirm_label="Restartuj"),
    Action("dfu", "Tryb DFU", "import", variant="danger", ends_session=True,
           confirm_title="Przejść w tryb DFU?",
           confirm_text="Baza zniknie jako kierownica i będzie czekać na nowy firmware "
                        "(STM32CubeProgrammer). Aby wrócić, odłącz i podłącz zasilanie.",
           confirm_label="Przejdź w DFU"),
)


def _profile(motion_range, total, spring, static_d, dynamic_d, dx_spring, dx_const, dx_periodic,
             soft_strength=100, soft_range=10, soft_damping=50, direction=1) -> dict[str, int]:
    return {
        "motionRange": motion_range, "totalStrength": total, "integratedSpring": spring,
        "staticDampening": static_d, "dynamicDampening": dynamic_d,
        "dxSpringStrength": dx_spring, "dxConstantStrength": dx_const,
        "dxPeriodicStrength": dx_periodic, "softStopStrength": soft_strength,
        "softStopRange": soft_range, "softStopDampening": soft_damping,
        "dxConstantDirection": direction,
    }


# Punkty startowe - do dostrojenia pod konkretną bazę i preferencje.
BUILTIN_PROFILES = {
    "Domyślny": {"game": "Uniwersalny", "settings": _profile(900, 60, 0, 5, 10, 100, 100, 100)},
    "iRacing": {"game": "iRacing", "settings": _profile(900, 70, 0, 0, 5, 0, 100, 40)},
    "Assetto Corsa Competizione": {"game": "ACC", "settings": _profile(900, 65, 0, 5, 10, 60, 100, 50)},
    "Assetto Corsa": {"game": "Assetto Corsa", "settings": _profile(900, 75, 0, 5, 5, 50, 100, 60)},
    "F1 25": {"game": "F1", "settings": _profile(360, 60, 0, 0, 10, 100, 100, 70)},
    "Drift": {"game": "AC / Drift", "settings": _profile(1080, 70, 0, 0, 0, 30, 100, 30)},
    "Euro Truck Simulator 2": {"game": "ETS2 / ATS", "settings": _profile(1440, 40, 20, 10, 15, 80, 90, 40)},
}

SPEC = FirmwareSpec(
    id="ffbeast",
    name="FFBeast",
    controller="MKS XDrive Mini + firmware FFBeast",
    sections=SECTIONS,
    actions=ACTIONS,
    profile_keys=tuple(f.key for f in p.EFFECT_FIELDS),
    strength_key="totalStrength",
    range_key="motionRange",
    builtin_profiles=BUILTIN_PROFILES,
)

_COMMANDS = {
    "save": p.ReportData.COMMAND_SAVE_SETTINGS,
    "reboot": p.ReportData.COMMAND_REBOOT,
    "dfu": p.ReportData.COMMAND_DFU_MODE,
}


def find_vendor_interface() -> bytes | None:
    """Ścieżka do interfejsu vendor (0) bazy albo None."""
    if hid is None:
        return None
    for dev in hid.enumerate(p.USB_VID, p.WHEEL_PID_FS):
        if dev.get("interface_number") == p.INTERFACE_VENDOR:
            return dev["path"]
    return None


class FFBeastLink(BaseLink):
    spec = SPEC

    def __init__(self, simulate: bool = False, device_factory=None) -> None:
        super().__init__(simulate)
        self._device_factory = device_factory
        self._sim: SimulatedWheelBase | None = None
        self._seen_ids: set[int] = set()
        self._product = ""

    def _open(self):
        if self._device_factory:
            self._product = "Fake"
            return self._device_factory()
        if self.simulate:
            if self._sim is None:
                self._sim = SimulatedWheelBase()
            self._sim.closed = False
            self._product = "Symulator FFBeast"
            return self._sim
        path = find_vendor_interface()
        if path is None:
            return None
        dev = hid.device()
        dev.open_path(path)
        try:
            self._product = dev.get_product_string() or "FFBeast Wheel"
        except OSError:
            self._product = "FFBeast Wheel"
        return dev

    def _read_settings(self, dev) -> dict[str, int]:
        size = p.REPORT_SIZE + 1
        effects = p.parse_effect_settings(
            bytes(dev.get_feature_report(p.ReportType.EFFECT_SETTINGS_FEATURE, size)))
        hardware = p.parse_hardware_settings(
            bytes(dev.get_feature_report(p.ReportType.HARDWARE_SETTINGS_FEATURE, size)))
        return {**effects, **hardware}

    def _handshake(self, dev):
        settings = self._read_settings(dev)
        lic = p.parse_license(bytes(dev.get_feature_report(
            p.ReportType.FIRMWARE_LICENSE_FEATURE, p.REPORT_SIZE + 1)))
        self._seen_ids.clear()
        simulated = self.simulate or self._device_factory is not None
        info = DeviceInfo(
            firmware_id=SPEC.id, simulated=simulated, product=self._product,
            version=str(lic.firmware),
            details=[
                ("Urządzenie", self._product),
                ("Firmware", f"FFBeast {lic.firmware}"),
                ("Licencja", "Premium" if lic.registered else "Light"),
                ("Połączenie", "Symulacja" if simulated else "USB HID"),
                ("ID urządzenia", "-".join(f"{x:08X}" for x in lic.device_id)),
            ])
        return info, settings

    def _poll(self, dev) -> LiveState | None:
        data = dev.read(p.REPORT_SIZE + 1, 20)
        if not data:
            return None
        if data[0] not in self._seen_ids:
            self._seen_ids.add(data[0])
            log.debug("Raport wejściowy ID 0x%02X, %d B: %s", data[0], len(data),
                      bytes(data[:16]).hex(" "))
        if len(data) < 10:
            return None
        body = bytes(data[1:]) if len(data) > p.REPORT_SIZE else bytes(data)
        state = p.parse_state(body)
        return LiveState(state.position, state.torque, abs(state.torque) >= CLIP_LEVEL)

    def _write_settings(self, dev, values: dict[str, int]) -> None:
        for key, value in values.items():
            dev.write(p.build_setting(key, value))

    def _do_action(self, dev, action_id: str) -> None:
        dev.write(p.build_command(_COMMANDS[action_id]))
