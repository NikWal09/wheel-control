"""Wspólna warstwa dla obsługiwanych firmware'ów bazy (FFBeast, OpenFFBoard).

Każdy firmware dostarcza:
- `FirmwareSpec` - jakie ma ustawienia (pola pogrupowane w sekcje), akcje i presety profili;
  z tego opisu interfejs QML sam buduje strony "Force Feedback" i "Baza i silnik",
- klasę połączenia dziedziczącą po `BaseLink` - wątek, który rozmawia z urządzeniem.

Wątek jest jedynym właścicielem połączenia: odczytuje stan, wysyła zakolejkowane zmiany
ustawień (scalane - przy przeciąganiu suwaka leci tylko ostatnia wartość) i akcje. GUI
czyta `latest_state` i zdarzenia z `events` w swoim timerze, więc tu nie ma Qt.
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

RECONNECT_INTERVAL = 1.0
RESYNC_DELAY = 0.4  # po serii zapisów odczytaj ustawienia, by zobaczyć co przyjęła baza


# --- opis ustawień ----------------------------------------------------------------

@dataclass(frozen=True)
class Field:
    key: str
    label: str
    minimum: int
    maximum: int
    kind: str = "slider"         # slider | stepper | toggle | choice
    unit: str = "%"
    description: str = ""
    step: int = 1
    scale: float = 1.0           # wartość wyświetlana = surowa * scale
    slider_min: int | None = None
    slider_max: int | None = None
    presets: tuple[int, ...] = ()
    options: tuple[tuple[str, int], ...] = ()   # dla kind == "choice"
    signed_direction: bool = False              # wartość tylko -1 albo +1
    live: bool = False                          # odczyt odświeżany cyklicznie (np. napięcie)

    def clamp(self, value) -> int:
        value = int(round(float(value)))
        if self.signed_direction:
            return -1 if value < 0 else 1
        return max(self.minimum, min(self.maximum, value))

    def display(self, value) -> str:
        if value is None:
            return "–"
        if self.options:
            return next((lbl for lbl, v in self.options if v == value), str(value))
        if self.kind == "toggle":
            return "Wł." if value else "Wył."
        shown = round(value * self.scale)
        return f"{shown}{self.unit}" if self.unit in ("%", "°") else f"{shown} {self.unit}".strip()

    def to_qml(self) -> dict:
        return {
            "key": self.key, "label": self.label, "kind": self.kind, "unit": self.unit,
            "description": self.description, "min": self.minimum, "max": self.maximum,
            "step": self.step, "scale": self.scale,
            "sliderMin": self.minimum if self.slider_min is None else self.slider_min,
            "sliderMax": self.maximum if self.slider_max is None else self.slider_max,
            "presets": list(self.presets),
            "options": [{"label": lbl, "value": v} for lbl, v in self.options],
        }


@dataclass(frozen=True)
class Section:
    page: str          # "ffb" | "base"
    title: str
    subtitle: str
    icon: str          # nazwa ikony z Theme.icons
    fields: tuple[Field, ...]

    def to_qml(self) -> dict:
        return {"page": self.page, "title": self.title, "subtitle": self.subtitle,
                "icon": self.icon, "fields": [f.to_qml() for f in self.fields]}


@dataclass(frozen=True)
class Action:
    id: str
    label: str
    icon: str
    variant: str = "secondary"   # primary | secondary | danger
    confirm_title: str = ""
    confirm_text: str = ""
    confirm_label: str = ""
    ends_session: bool = False   # urządzenie znika z USB (restart, DFU)
    requires: str = ""           # akcja dostępna tylko, gdy urządzenie ma tę klasę/funkcję

    def to_qml(self) -> dict:
        return {"id": self.id, "label": self.label, "icon": self.icon, "variant": self.variant,
                "confirmTitle": self.confirm_title, "confirmText": self.confirm_text,
                "confirmLabel": self.confirm_label, "danger": self.variant == "danger"}


@dataclass(frozen=True)
class FirmwareSpec:
    id: str
    name: str
    controller: str
    sections: tuple[Section, ...]
    actions: tuple[Action, ...]
    profile_keys: tuple[str, ...]
    strength_key: str
    range_key: str
    builtin_profiles: dict[str, dict]

    def fields(self) -> dict[str, Field]:
        return {f.key: f for s in self.sections for f in s.fields}

    def action(self, action_id: str) -> Action | None:
        return next((a for a in self.actions if a.id == action_id), None)


# --- stan i informacje z urządzenia ------------------------------------------------------

@dataclass
class LiveState:
    position: float  # -1..+1 względem połowy zakresu obrotu
    torque: float    # -1..+1 względem maksymalnego momentu


@dataclass
class DeviceInfo:
    firmware_id: str
    simulated: bool
    product: str = ""
    version: str = ""
    details: list[tuple[str, str]] = field(default_factory=list)  # wiersze "Urządzenie"
    capabilities: set[str] = field(default_factory=set)            # np. {"xdrive.0"}


@dataclass
class Event:
    kind: str  # connected | disconnected | settings | saved | action | error
    data: Any = None


# --- wątek połączenia ---------------------------------------------------------------

@dataclass
class _Shared:
    lock: threading.Lock = field(default_factory=threading.Lock)
    pending: dict[str, int] = field(default_factory=dict)
    actions: list[str] = field(default_factory=list)
    reload: bool = False


class BaseLink:
    """Szkielet wątku połączenia. Podklasy implementują metody `_open` ... `_run_action`."""

    spec: FirmwareSpec

    def __init__(self, simulate: bool = False) -> None:
        self.simulate = simulate
        self._shared = _Shared()
        self.events: "queue.Queue[Event]" = queue.Queue()
        self.latest_state: LiveState | None = None
        self.connected = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._fields = self.spec.fields()

    # --- API dla GUI (wątek główny) ----------------------------------------------

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name=f"{self.spec.id}-link", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def set_setting(self, key: str, value) -> None:
        with self._shared.lock:
            self._shared.pending[key] = self._fields[key].clamp(value)

    def run_action(self, action_id: str) -> None:
        with self._shared.lock:
            self._shared.actions.append(action_id)

    def request_reload(self) -> None:
        with self._shared.lock:
            self._shared.reload = True

    # --- do zaimplementowania ----------------------------------------------------------

    def _open(self) -> Any | None:
        """Otwiera urządzenie albo zwraca None, jeśli go nie ma."""
        raise NotImplementedError

    def _handshake(self, dev) -> tuple[DeviceInfo, dict[str, int]]:
        raise NotImplementedError

    def _read_settings(self, dev) -> dict[str, int]:
        raise NotImplementedError

    def _poll(self, dev) -> LiveState | None:
        """Czeka maks. ~20 ms na nowy stan. Może też wrzucać zdarzenia (np. zmiany z innego programu)."""
        raise NotImplementedError

    def _write_settings(self, dev, values: dict[str, int]) -> None:
        raise NotImplementedError

    def _do_action(self, dev, action_id: str) -> None:
        raise NotImplementedError

    def _close(self, dev) -> None:
        try:
            dev.close()
        except Exception:  # noqa: BLE001 - zamykamy co się da
            pass

    # --- pętla wątku ---------------------------------------------------------------

    def _run(self) -> None:
        last_error = ""
        while not self._stop.is_set():
            dev = None
            try:
                dev = self._open()
            except OSError as exc:
                # np. port COM zajęty przez OpenFFBoard Configurator - zgłoś raz, nie co sekundę
                if str(exc) != last_error:
                    last_error = str(exc)
                    log.warning("%s: nie udało się otworzyć urządzenia: %s", self.spec.name, exc)
                    self.events.put(Event("error", f"Nie udało się otworzyć bazy ({self.spec.name}): "
                                                   f"{exc}. Czy inny program nie używa portu?"))
            if dev is not None:
                last_error = ""
            if dev is None:
                self._stop.wait(RECONNECT_INTERVAL)
                continue
            try:
                self._session(dev)
            except OSError as exc:
                log.info("%s: rozłączono: %s", self.spec.name, exc)
            finally:
                self._close(dev)
                if self.connected:
                    self.connected = False
                    self.latest_state = None
                    self.events.put(Event("disconnected"))
            self._stop.wait(RECONNECT_INTERVAL)

    def _session(self, dev) -> None:
        with self._shared.lock:  # stare zmiany z poprzedniej sesji nie mają sensu
            self._shared.pending.clear()
            self._shared.actions.clear()
        info, settings = self._handshake(dev)
        self.connected = True
        self.events.put(Event("connected", info))
        self.events.put(Event("settings", settings))

        resync_at = 0.0
        while not self._stop.is_set():
            state = self._poll(dev)
            if state is not None:
                self.latest_state = state

            with self._shared.lock:
                pending, self._shared.pending = self._shared.pending, {}
                actions, self._shared.actions = self._shared.actions, []
                reload, self._shared.reload = self._shared.reload, False

            if pending:
                self._write_settings(dev, pending)
                resync_at = time.monotonic() + RESYNC_DELAY

            for action_id in actions:
                self._do_action(dev, action_id)
                action = self.spec.action(action_id)
                if action_id == "save":
                    self.events.put(Event("saved"))
                elif action is not None and action.ends_session:
                    return
                else:
                    self.events.put(Event("action", action_id))

            if reload or (resync_at and time.monotonic() >= resync_at):
                resync_at = 0.0
                self.events.put(Event("settings", self._read_settings(dev)))
