"""Połączenie z bazą FFBeast w osobnym wątku.

Wątek jest jedynym właścicielem uchwytu HID: czyta raporty stanu, wysyła
zakolejkowane zmiany ustawień (scalane - przy przeciąganiu suwaka leci tylko
ostatnia wartość) i komendy. GUI odczytuje `latest_state` i zdarzenia z
`events` w swoim timerze, więc nie ma tu żadnego Qt.
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from . import protocol as p
from .simulator import SimulatedWheelBase

log = logging.getLogger(__name__)

try:
    import hid  # pakiet "hidapi"
except ImportError:  # pragma: no cover - aplikacja działa wtedy tylko w symulacji
    hid = None

RECONNECT_INTERVAL = 1.0
RESYNC_DELAY = 0.4  # po serii zapisów odczytaj ustawienia, by zobaczyć co przyjęła baza


@dataclass
class Event:
    kind: str  # connected | disconnected | settings | license | error | saved
    data: Any = None


@dataclass
class BaseInfo:
    simulated: bool
    path: str = ""
    product: str = ""


def find_vendor_interface() -> bytes | None:
    """Ścieżka do interfejsu vendor (0) bazy albo None."""
    if hid is None:
        return None
    for dev in hid.enumerate(p.USB_VID, p.WHEEL_PID_FS):
        if dev.get("interface_number") == p.INTERFACE_VENDOR:
            return dev["path"]
    return None


@dataclass
class _Shared:
    lock: threading.Lock = field(default_factory=threading.Lock)
    pending: dict[str, int] = field(default_factory=dict)
    commands: list[p.ReportData] = field(default_factory=list)
    reload: bool = False


class WheelBaseLink:
    def __init__(self, simulate: bool = False,
                 device_factory: Callable[[], Any] | None = None) -> None:
        self._simulate = simulate
        self._device_factory = device_factory
        self._sim: SimulatedWheelBase | None = None
        self._shared = _Shared()
        self.events: "queue.Queue[Event]" = queue.Queue()
        self.latest_state: p.DeviceState | None = None
        self.connected = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # --- API dla GUI (wątek główny) ------------------------------------------

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="ffbeast-link", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def set_simulation(self, enabled: bool) -> None:
        """Przełączenie trybu - wątek sam się rozłączy i podłączy od nowa."""
        self._simulate = enabled
        self._force_reconnect = True

    def set_setting(self, key: str, value: int) -> None:
        with self._shared.lock:
            self._shared.pending[key] = p.clamp_setting(key, value)

    def send_command(self, command: p.ReportData) -> None:
        with self._shared.lock:
            self._shared.commands.append(command)

    def request_reload(self) -> None:
        with self._shared.lock:
            self._shared.reload = True

    # --- wątek ---------------------------------------------------------------

    _force_reconnect = False

    def _open(self):
        if self._device_factory:
            return self._device_factory(), BaseInfo(simulated=True, product="Fake")
        if self._simulate:
            if self._sim is None:
                self._sim = SimulatedWheelBase()
            self._sim.closed = False
            return self._sim, BaseInfo(simulated=True, product="Symulator FFBeast")
        path = find_vendor_interface()
        if path is None:
            return None, None
        dev = hid.device()
        dev.open_path(path)
        product = ""
        try:
            product = dev.get_product_string() or ""
        except OSError:
            pass
        return dev, BaseInfo(simulated=False, path=path.decode(errors="replace"), product=product)

    def _run(self) -> None:
        while not self._stop.is_set():
            dev = None
            try:
                dev, info = self._open()
            except OSError as exc:
                log.warning("Nie udało się otworzyć bazy: %s", exc)
                self.events.put(Event("error", f"Nie udało się otworzyć bazy: {exc}"))
            if dev is None:
                self._stop.wait(RECONNECT_INTERVAL)
                continue
            self._force_reconnect = False
            try:
                self._session(dev, info)
            except OSError as exc:
                log.info("Baza rozłączona: %s", exc)
            finally:
                try:
                    dev.close()
                except Exception:  # noqa: BLE001 - zamykamy co się da
                    pass
                if self.connected:
                    self.connected = False
                    self.latest_state = None
                    self.events.put(Event("disconnected"))
            self._stop.wait(RECONNECT_INTERVAL)

    def _read_all_settings(self, dev) -> dict[str, int]:
        size = p.REPORT_SIZE + 1
        effects = p.parse_effect_settings(
            bytes(dev.get_feature_report(p.ReportType.EFFECT_SETTINGS_FEATURE, size)))
        hardware = p.parse_hardware_settings(
            bytes(dev.get_feature_report(p.ReportType.HARDWARE_SETTINGS_FEATURE, size)))
        return {**effects, **hardware}

    def _session(self, dev, info: BaseInfo) -> None:
        with self._shared.lock:  # stare zmiany z poprzedniej sesji nie mają sensu
            self._shared.pending.clear()
            self._shared.commands.clear()
        settings = self._read_all_settings(dev)
        lic = p.parse_license(bytes(dev.get_feature_report(
            p.ReportType.FIRMWARE_LICENSE_FEATURE, p.REPORT_SIZE + 1)))
        self.connected = True
        self.events.put(Event("connected", info))
        self.events.put(Event("license", lic))
        self.events.put(Event("settings", settings))

        resync_at = 0.0
        seen_ids: set[int] = set()
        while not self._stop.is_set() and not self._force_reconnect:
            data = dev.read(p.REPORT_SIZE + 1, 20)
            if data and data[0] not in seen_ids:
                seen_ids.add(data[0])
                log.debug("Raport wejściowy ID 0x%02X, %d B: %s", data[0], len(data),
                          bytes(data[:16]).hex(" "))
            if data and len(data) >= 10:
                body = bytes(data[1:]) if len(data) > p.REPORT_SIZE else bytes(data)
                self.latest_state = p.parse_state(body)

            with self._shared.lock:
                pending, self._shared.pending = self._shared.pending, {}
                commands, self._shared.commands = self._shared.commands, []
                reload, self._shared.reload = self._shared.reload, False

            for key, value in pending.items():
                dev.write(p.build_setting(key, value))
            if pending:
                resync_at = time.monotonic() + RESYNC_DELAY

            for cmd in commands:
                dev.write(p.build_command(cmd))
                if cmd == p.ReportData.COMMAND_SAVE_SETTINGS:
                    self.events.put(Event("saved"))
                else:  # restart / DFU - urządzenie zaraz zniknie z USB
                    return

            if reload or (resync_at and time.monotonic() >= resync_at):
                resync_at = 0.0
                self.events.put(Event("settings", self._read_all_settings(dev)))
