"""Most między logiką (baza FFBeast, gamepady, profile) a interfejsem QML."""
from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot

from .ffbeast import protocol as p
from .ffbeast.device import WheelBaseLink
from .gamepads import (AXIS_NAMES, JoystickReader, SimulatedJoysticks, guess_role)
from .storage import PROFILE_KEYS, Store

UI_RATE_MS = 16          # ~60 Hz odświeżania podglądu
ENUMERATE_EVERY_S = 3.0  # jak często szukać nowych kontrolerów
LEARN_TIMEOUT_S = 8.0
WHEEL_SLOTS = 14         # 12 przycisków na panelu + 2 łopatki
PEDALS = ("throttle", "brake")


class Backend(QObject):
    baseChanged = Signal()
    stateChanged = Signal()
    settingsChanged = Signal()
    dirtyChanged = Signal()
    devicesChanged = Signal()
    inputsChanged = Signal()
    mappingChanged = Signal()
    learningChanged = Signal()
    profilesChanged = Signal()
    profileStatusChanged = Signal()  # aktywny profil / czy zmodyfikowany
    appearanceChanged = Signal()
    toast = Signal(str, str, arguments=["message", "kind"])  # kind: info|success|error

    def __init__(self, store: Store | None = None, simulate: bool | None = None) -> None:
        super().__init__()
        self._store = store or Store()
        self._simulation = bool(self._store.get("simulation", False) if simulate is None else simulate)

        self._link = WheelBaseLink(simulate=self._simulation)
        self._base_info = None
        self._license: p.LicenseInfo | None = None
        self._settings: dict[str, int] = {}
        self._dirty = False
        self._position = 0.0
        self._torque = 0.0
        self._peak_torque = 0.0

        self._real_joys = JoystickReader()
        self._sim_joys = SimulatedJoysticks()
        self._joysticks = []
        self._last_enum = 0.0
        self._pedal_raw = [0.0] * len(AXIS_NAMES)
        self._buttons = 0
        self._pedals_ok = False
        self._wheel_ok = False

        self._learning = ""
        self._learn_started = 0.0
        self._learn_baseline: list[float] | int | None = None

        self._timer = QTimer(self)
        self._timer.setInterval(UI_RATE_MS)
        self._timer.timeout.connect(self._tick)

    # --- cykl życia -------------------------------------------------------------

    def start(self) -> None:
        self._link.start()
        self._enumerate_joysticks()
        self._timer.start()

    @Slot()
    def shutdown(self) -> None:
        self._timer.stop()
        self._link.stop()

    def _tick(self) -> None:
        self._drain_events()
        state = self._link.latest_state
        if state is not None:
            self._position, self._torque = state.position, state.torque
            self._peak_torque = max(abs(self._torque), self._peak_torque * 0.995)
            self.stateChanged.emit()
        if time.monotonic() - self._last_enum > ENUMERATE_EVERY_S:
            self._enumerate_joysticks()
        self._poll_inputs()

    def _drain_events(self) -> None:
        while not self._link.events.empty():
            ev = self._link.events.get_nowait()
            if ev.kind == "connected":
                self._base_info = ev.data
                self._dirty = False
                self.dirtyChanged.emit()
                self.baseChanged.emit()
                self.toast.emit("Połączono z bazą" + (" (symulacja)" if ev.data.simulated else ""),
                                "success")
            elif ev.kind == "disconnected":
                self._base_info = None
                self._license = None
                self._position = self._torque = 0.0
                self.baseChanged.emit()
                self.stateChanged.emit()
                self.toast.emit("Baza odłączona", "info")
            elif ev.kind == "license":
                self._license = ev.data
                self.baseChanged.emit()
            elif ev.kind == "settings":
                self._settings = dict(ev.data)
                self.settingsChanged.emit()
                self.profileStatusChanged.emit()
            elif ev.kind == "saved":
                self._dirty = False
                self.dirtyChanged.emit()
                self.toast.emit("Ustawienia zapisane w pamięci bazy", "success")
            elif ev.kind == "error":
                self.toast.emit(str(ev.data), "error")

    # --- baza: status ----------------------------------------------------------

    @Property(bool, notify=baseChanged)
    def baseConnected(self) -> bool:
        return self._base_info is not None

    @Property(bool, notify=baseChanged)
    def baseSimulated(self) -> bool:
        return bool(self._base_info and self._base_info.simulated)

    @Property(str, notify=baseChanged)
    def baseName(self) -> str:
        if not self._base_info:
            return ""
        return self._base_info.product or "FFBeast Wheel"

    @Property(str, notify=baseChanged)
    def firmware(self) -> str:
        return str(self._license.firmware) if self._license else ""

    @Property(bool, notify=baseChanged)
    def licensed(self) -> bool:
        return bool(self._license and self._license.registered)

    @Property(str, notify=baseChanged)
    def deviceId(self) -> str:
        if not self._license:
            return ""
        return "-".join(f"{x:08X}" for x in self._license.device_id)

    @Property(bool, notify=baseChanged)
    def simulation(self) -> bool:
        return self._simulation

    @Slot(bool)
    def setSimulation(self, enabled: bool) -> None:
        if enabled == self._simulation:
            return
        self._simulation = enabled
        self._store.set("simulation", enabled)
        self._link.set_simulation(enabled)
        self._enumerate_joysticks()
        self.baseChanged.emit()

    # --- baza: stan na żywo --------------------------------------------------

    @Property(float, notify=stateChanged)
    def position(self) -> float:
        return self._position

    @Property(float, notify=stateChanged)
    def angle(self) -> float:
        return self._position * self._settings.get("motionRange", 900) / 2

    @Property(float, notify=stateChanged)
    def torque(self) -> float:
        return self._torque

    @Property(float, notify=stateChanged)
    def peakTorque(self) -> float:
        return self._peak_torque

    # --- baza: ustawienia -----------------------------------------------------

    @Property("QVariantMap", notify=settingsChanged)
    def settings(self) -> dict:
        return self._settings

    @Property("QVariantMap", constant=True)
    def limits(self) -> dict:
        return {k: {"min": s.minimum, "max": s.maximum} for k, s in p.FIELDS_BY_KEY.items()}

    @Property(bool, notify=dirtyChanged)
    def dirty(self) -> bool:
        return self._dirty

    @Slot(str, float)
    def setSetting(self, key: str, value: float) -> None:
        if key not in p.FIELDS_BY_KEY or not self.baseConnected:
            return
        value = p.clamp_setting(key, value)
        if self._settings.get(key) == value:
            return
        self._settings[key] = value
        self._link.set_setting(key, value)
        self.settingsChanged.emit()
        self.profileStatusChanged.emit()
        if not self._dirty:
            self._dirty = True
            self.dirtyChanged.emit()

    @Slot()
    def saveToBase(self) -> None:
        self._link.send_command(p.ReportData.COMMAND_SAVE_SETTINGS)

    @Slot()
    def reloadSettings(self) -> None:
        self._link.request_reload()
        self._dirty = False
        self.dirtyChanged.emit()

    @Slot()
    def rebootBase(self) -> None:
        self._link.send_command(p.ReportData.COMMAND_REBOOT)
        self.toast.emit("Restart bazy…", "info")

    @Slot()
    def enterDfu(self) -> None:
        self._link.send_command(p.ReportData.COMMAND_DFU_MODE)
        self.toast.emit("Baza przechodzi w tryb DFU (aktualizacja firmware)", "info")

    # --- pedały i kierownica -------------------------------------------------

    def _reader(self):
        return self._sim_joys if self._simulation else self._real_joys

    def _enumerate_joysticks(self) -> None:
        self._last_enum = time.monotonic()
        joys = self._reader().enumerate()
        if [j.to_qml() for j in joys] != [j.to_qml() for j in self._joysticks]:
            self._joysticks = joys
            self.devicesChanged.emit()

    def _resolve(self, role: str):
        key = self._store.get(f"{role}Device")
        for j in self._joysticks:
            if j.key == key:
                return j
        if key:  # wybrane urządzenie jest odłączone
            return None
        return next((j for j in self._joysticks if guess_role(j) == role), None)

    @Property("QVariantList", notify=devicesChanged)
    def joysticks(self) -> list:
        return [j.to_qml() for j in self._joysticks]

    @Property(str, notify=devicesChanged)
    def pedalsDevice(self) -> str:
        j = self._resolve("pedals")
        return j.key if j else (self._store.get("pedalsDevice") or "")

    @Property(str, notify=devicesChanged)
    def wheelDevice(self) -> str:
        j = self._resolve("wheel")
        return j.key if j else (self._store.get("wheelDevice") or "")

    @Property(str, notify=devicesChanged)
    def pedalsName(self) -> str:
        j = self._resolve("pedals")
        return j.name if j else ""

    @Property(str, notify=devicesChanged)
    def wheelName(self) -> str:
        j = self._resolve("wheel")
        return j.name if j else ""

    @Slot(str, str)
    def assignDevice(self, role: str, key: str) -> None:
        self._store.set(f"{role}Device", key or None)
        self.devicesChanged.emit()

    @Property(bool, notify=inputsChanged)
    def pedalsConnected(self) -> bool:
        return self._pedals_ok

    @Property(bool, notify=inputsChanged)
    def wheelConnected(self) -> bool:
        return self._wheel_ok

    @Property("QVariantList", notify=inputsChanged)
    def pedalRaw(self) -> list:
        return list(self._pedal_raw)

    @Property(float, notify=inputsChanged)
    def throttle(self) -> float:
        return self._pedal_value("throttle")

    @Property(float, notify=inputsChanged)
    def brake(self) -> float:
        return self._pedal_value("brake")

    @Property(int, notify=inputsChanged)
    def buttons(self) -> int:
        return self._buttons

    @Property(int, notify=devicesChanged)
    def wheelButtonCount(self) -> int:
        j = self._resolve("wheel")
        return j.num_buttons if j else WHEEL_SLOTS

    def _pedal_cfg(self, pedal: str) -> dict:
        default = {"axis": PEDALS.index(pedal), "invert": False}
        return {**default, **self._store.get("pedalMap", {}).get(pedal, {})}

    def _pedal_value(self, pedal: str) -> float:
        cfg = self._pedal_cfg(pedal)
        v = self._pedal_raw[cfg["axis"]] if 0 <= cfg["axis"] < len(self._pedal_raw) else 0.0
        return 1.0 - v if cfg["invert"] else v

    @Property("QVariantMap", notify=mappingChanged)
    def pedalMap(self) -> dict:
        return {pd: self._pedal_cfg(pd) for pd in PEDALS}

    @Property("QVariantList", constant=True)
    def axisNames(self) -> list:
        return list(AXIS_NAMES)

    @Slot(str, int, bool)
    def setPedalMapping(self, pedal: str, axis: int, invert: bool) -> None:
        m = dict(self._store.get("pedalMap", {}))
        m[pedal] = {"axis": int(axis), "invert": bool(invert)}
        self._store.set("pedalMap", m)
        self.mappingChanged.emit()

    @Property("QVariantList", notify=mappingChanged)
    def wheelButtonMap(self) -> list:
        saved = self._store.get("wheelButtonMap") or []
        return [saved[i] if i < len(saved) else i for i in range(WHEEL_SLOTS)]

    @Slot()
    def resetWheelButtonMap(self) -> None:
        self._store.set("wheelButtonMap", None)
        self.mappingChanged.emit()

    def _poll_inputs(self) -> None:
        reader = self._reader()
        pedals, wheel = self._resolve("pedals"), self._resolve("wheel")
        ps = reader.read(pedals.id) if pedals else None
        ws = reader.read(wheel.id) if wheel else None
        self._pedals_ok, self._wheel_ok = ps is not None, ws is not None
        self._pedal_raw = ps.axes if ps else [0.0] * len(AXIS_NAMES)
        self._buttons = ws.buttons if ws else 0
        self._update_learning()
        self.inputsChanged.emit()

    # --- uczenie: "naciśnij pedał / przycisk" ------------------------------------

    @Property(str, notify=learningChanged)
    def learning(self) -> str:
        return self._learning

    @Slot(str)
    def learnPedal(self, pedal: str) -> None:
        self._start_learning(f"pedal:{pedal}", list(self._pedal_raw))

    @Slot(int)
    def learnWheelButton(self, slot: int) -> None:
        self._start_learning(f"button:{slot}", self._buttons)

    @Slot()
    def cancelLearning(self) -> None:
        self._learning = ""
        self.learningChanged.emit()

    def _start_learning(self, what: str, baseline) -> None:
        self._learning, self._learn_baseline = what, baseline
        self._learn_started = time.monotonic()
        self.learningChanged.emit()

    def _update_learning(self) -> None:
        if not self._learning:
            return
        kind, target = self._learning.split(":")
        if kind == "pedal":
            deltas = [now - base for now, base in zip(self._pedal_raw, self._learn_baseline)]
            axis = max(range(len(deltas)), key=lambda i: abs(deltas[i]))
            if abs(deltas[axis]) > 0.35:
                self.setPedalMapping(target, axis, deltas[axis] < 0)
                self.toast.emit(f"Przypisano oś {AXIS_NAMES[axis]}" +
                                (" (odwrócona)" if deltas[axis] < 0 else ""), "success")
                self.cancelLearning()
                return
        else:
            new = self._buttons & ~self._learn_baseline
            self._learn_baseline &= self._buttons  # puszczone przyciski też mogą zostać wybrane
            if new:
                button = (new & -new).bit_length() - 1
                mapping = self.wheelButtonMap
                mapping[int(target)] = button
                self._store.set("wheelButtonMap", mapping)
                self.mappingChanged.emit()
                self.toast.emit(f"Przypisano przycisk {button + 1}", "success")
                self.cancelLearning()
                return
        if time.monotonic() - self._learn_started > LEARN_TIMEOUT_S:
            self.toast.emit("Nie wykryto ruchu - spróbuj ponownie", "error")
            self.cancelLearning()

    # --- profile -------------------------------------------------------------

    @Property("QVariantList", notify=profilesChanged)
    def profiles(self) -> list:
        return self._store.profiles()

    @Property(str, notify=profileStatusChanged)
    def activeProfile(self) -> str:
        return self._store.get("activeProfile") or ""

    @Property(bool, notify=profileStatusChanged)
    def profileModified(self) -> bool:
        prof = self._store.profile(self.activeProfile)
        if not prof or not self._settings:
            return False
        return any(self._settings.get(k) != v for k, v in prof["settings"].items())

    @Property("QVariantList", constant=True)
    def profileKeys(self) -> list:
        return list(PROFILE_KEYS)

    @Slot(str)
    def applyProfile(self, name: str) -> None:
        prof = self._store.profile(name)
        if prof is None:
            return
        if not self.baseConnected:
            self.toast.emit("Podłącz bazę, aby zastosować profil", "error")
            return
        for key, value in prof["settings"].items():
            self.setSetting(key, value)
        self._store.set("activeProfile", name)
        self.profileStatusChanged.emit()
        self.toast.emit(f"Zastosowano profil „{name}”", "success")

    @Slot(str, str)
    def saveProfile(self, name: str, game: str) -> None:
        name = name.strip()
        if not name or not self._settings:
            return
        try:
            self._store.save_profile(name, {k: self._settings[k] for k in PROFILE_KEYS},
                                     game.strip() or "Własny")
        except ValueError as exc:
            self.toast.emit(str(exc), "error")
            return
        self._store.set("activeProfile", name)
        self.profilesChanged.emit()
        self.profileStatusChanged.emit()
        self.toast.emit(f"Zapisano profil „{name}”", "success")

    @Slot(str)
    def deleteProfile(self, name: str) -> None:
        self._store.delete_profile(name)
        if self.activeProfile == name:
            self._store.set("activeProfile", None)
        self.profilesChanged.emit()
        self.profileStatusChanged.emit()
        self.toast.emit(f"Usunięto profil „{name}”", "info")

    @Slot(str, QUrl)
    def exportProfile(self, name: str, url: QUrl) -> None:
        try:
            self._store.export_profile(name, Path(url.toLocalFile()))
            self.toast.emit("Wyeksportowano profil", "success")
        except (OSError, KeyError) as exc:
            self.toast.emit(f"Eksport nieudany: {exc}", "error")

    @Slot(QUrl)
    def importProfile(self, url: QUrl) -> None:
        try:
            name = self._store.import_profile(Path(url.toLocalFile()))
        except (OSError, ValueError) as exc:
            self.toast.emit(f"Import nieudany: {exc}", "error")
            return
        self.profilesChanged.emit()
        self.toast.emit(f"Zaimportowano profil „{name}”", "success")

    # --- wygląd ----------------------------------------------------------------

    @Property(str, notify=appearanceChanged)
    def accent(self) -> str:
        return self._store.get("accent") or "#FF4D2E"

    @Slot(str)
    def setAccent(self, color: str) -> None:
        self._store.set("accent", color)
        self.appearanceChanged.emit()
