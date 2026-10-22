"""Most między logiką (baza, gamepady, profile) a interfejsem QML."""
from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot

from .core import BaseLink, DeviceInfo, FirmwareSpec
from .ffbeast.driver import FFBeastLink
from .gamepads import (AXIS_NAMES, JoystickReader, SimulatedJoysticks, guess_role)
from .openffboard.driver import OpenFFBoardLink
from .storage import Store

UI_RATE_MS = 16          # ~60 Hz odświeżania podglądu
ENUMERATE_EVERY_S = 3.0  # jak często szukać nowych kontrolerów
LEARN_TIMEOUT_S = 8.0
WHEEL_SLOTS = 14         # 12 przycisków na panelu + 2 łopatki
PEDALS = ("throttle", "brake")

LINKS: dict[str, type[BaseLink]] = {"ffbeast": FFBeastLink, "openffboard": OpenFFBoardLink}
SPECS: dict[str, FirmwareSpec] = {k: cls.spec for k, cls in LINKS.items()}

ACTION_TOASTS = {
    "zero": ("Kierownica wycentrowana – obecna pozycja to 0°", "success"),
    "calibrate": ("Kalibracja uruchomiona – nie dotykaj kierownicy", "info"),
    "test": ("Test obrotu uruchomiony – nie dotykaj kierownicy", "info"),
    "reboot": ("Restart bazy…", "info"),
    "dfu": ("Baza przechodzi w tryb DFU – wgraj firmware w STM32CubeProgrammer", "info"),
}


class Backend(QObject):
    baseChanged = Signal()
    specChanged = Signal()
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

    def __init__(self, store: Store | None = None, simulate: bool | None = None,
                 links: list[BaseLink] | None = None) -> None:
        super().__init__()
        self._store = store or Store()
        self._simulation = bool(self._store.get("simulation", False) if simulate is None else simulate)

        self._links: list[BaseLink] = links if links is not None else self._make_links()
        self._active: BaseLink | None = None
        self._info: DeviceInfo | None = None
        self._settings: dict[str, int] = {}
        self._dirty = False
        self._position = 0.0
        self._torque = 0.0
        self._peak_torque = 0.0
        self._started = False

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

    def _make_links(self) -> list[BaseLink]:
        if self._simulation:
            return [LINKS[self.demoFirmware](simulate=True)]
        # bez symulacji szukamy obu firmware'ów naraz - aktywny jest ten, który odpowie
        return [cls() for cls in LINKS.values()]

    def start(self) -> None:
        self._started = True
        for link in self._links:
            link.start()
        self._enumerate_joysticks()
        self._timer.start()

    @Slot()
    def shutdown(self) -> None:
        self._timer.stop()
        for link in self._links:
            link.stop()

    def _restart_links(self) -> None:
        for link in self._links:
            link.stop()
        if self._active is not None:
            self._on_disconnected(silent=True)
        self._links = self._make_links()
        if self._started:
            for link in self._links:
                link.start()
        self.specChanged.emit()
        self.profilesChanged.emit()
        self.profileStatusChanged.emit()

    def _tick(self) -> None:
        self._drain_events()
        state = self._active.latest_state if self._active else None
        if state is not None:
            self._position, self._torque = state.position, state.torque
            self._peak_torque = max(abs(self._torque), self._peak_torque * 0.995)
            self.stateChanged.emit()
        if time.monotonic() - self._last_enum > ENUMERATE_EVERY_S:
            self._enumerate_joysticks()
        self._poll_inputs()

    def _drain_events(self) -> None:
        for link in self._links:
            while not link.events.empty():
                ev = link.events.get_nowait()
                if ev.kind == "connected":
                    if self._active is None:
                        self._on_connected(link, ev.data)
                    continue
                if link is not self._active:
                    continue  # np. druga baza podłączona naraz - ignorujemy
                self._handle_event(ev)

    def _on_connected(self, link: BaseLink, info: DeviceInfo) -> None:
        firmware_changed = self.firmwareId != link.spec.id
        self._active, self._info = link, info
        self._store.set("lastFirmware", link.spec.id)
        self._dirty = False
        self.dirtyChanged.emit()
        if firmware_changed:
            self.specChanged.emit()
            self.profilesChanged.emit()
        self.baseChanged.emit()
        self.toast.emit(f"Połączono z bazą {link.spec.name}" + (" (symulacja)" if info.simulated else ""),
                        "success")

    def _on_disconnected(self, silent: bool = False) -> None:
        self._active, self._info = None, None
        self._settings = {}
        self._position = self._torque = 0.0
        self.baseChanged.emit()
        self.settingsChanged.emit()
        self.stateChanged.emit()
        if not silent:
            self.toast.emit("Baza odłączona", "info")

    def _handle_event(self, ev) -> None:
        if ev.kind == "disconnected":
            self._on_disconnected()
        elif ev.kind == "settings":
            self._settings = dict(ev.data)
            self.settingsChanged.emit()
            self.profileStatusChanged.emit()
        elif ev.kind == "saved":
            self._dirty = False
            self.dirtyChanged.emit()
            self.toast.emit("Ustawienia zapisane w pamięci bazy", "success")
        elif ev.kind == "action":
            message, kind = ACTION_TOASTS.get(ev.data, ("Wykonano", "success"))
            self.toast.emit(message, kind)
        elif ev.kind == "error":
            self.toast.emit(str(ev.data), "error")
        elif ev.kind == "info":
            self.toast.emit(str(ev.data), "success")

    # --- firmware i opis ustawień ---------------------------------------------------

    @property
    def spec(self) -> FirmwareSpec:
        if self._active is not None:
            return self._active.spec
        if self._simulation:
            return SPECS[self.demoFirmware]
        return SPECS.get(self._store.get("lastFirmware") or "", SPECS["ffbeast"])

    @Property(str, notify=specChanged)
    def firmwareId(self) -> str:
        return self.spec.id

    @Property(str, notify=specChanged)
    def firmwareName(self) -> str:
        return self.spec.name

    @Property(str, notify=specChanged)
    def controllerName(self) -> str:
        return self.spec.controller

    @Property("QVariantList", notify=specChanged)
    def schema(self) -> list:
        return [s.to_qml() for s in self.spec.sections]

    @Property("QVariantMap", notify=specChanged)
    def fieldMap(self) -> dict:
        return {k: f.to_qml() for k, f in self.spec.fields().items()}

    @Property("QVariantMap", notify=specChanged)
    def strengthField(self) -> dict:
        return self.spec.fields()[self.spec.strength_key].to_qml()

    @Property("QVariantMap", notify=specChanged)
    def rangeField(self) -> dict:
        return self.spec.fields()[self.spec.range_key].to_qml()

    @Property(str, notify=specChanged)
    def demoFirmware(self) -> str:
        fw = self._store.get("demoFirmware")
        return fw if fw in LINKS else "ffbeast"

    @Slot(str)
    def setDemoFirmware(self, firmware_id: str) -> None:
        if firmware_id not in LINKS or firmware_id == self.demoFirmware:
            return
        self._store.set("demoFirmware", firmware_id)
        if self._simulation:
            self._restart_links()
        else:
            self.specChanged.emit()

    # --- baza: status ----------------------------------------------------------

    @Property(bool, notify=baseChanged)
    def baseConnected(self) -> bool:
        return self._info is not None

    @Property(bool, notify=baseChanged)
    def baseSimulated(self) -> bool:
        return bool(self._info and self._info.simulated)

    @Property(str, notify=baseChanged)
    def baseName(self) -> str:
        return self._info.product if self._info else ""

    @Property(str, notify=baseChanged)
    def firmware(self) -> str:
        return self._info.version if self._info else ""

    @Property("QVariantList", notify=baseChanged)
    def deviceDetails(self) -> list:
        if not self._info:
            return [{"k": "Status", "v": "Niepodłączona"}]
        return [{"k": k, "v": v} for k, v in self._info.details]

    @Property("QVariantList", notify=baseChanged)
    def actions(self) -> list:
        caps = self._info.capabilities if self._info else set()
        return [a.to_qml() for a in self.spec.actions
                if not a.requires or not self._info or a.requires in caps]

    @Property(bool, notify=baseChanged)
    def simulation(self) -> bool:
        return self._simulation

    @Slot(bool)
    def setSimulation(self, enabled: bool) -> None:
        if enabled == self._simulation:
            return
        self._simulation = enabled
        self._store.set("simulation", enabled)
        self._restart_links()
        self._enumerate_joysticks()
        self.baseChanged.emit()

    # --- baza: stan na żywo --------------------------------------------------

    @Property(float, notify=stateChanged)
    def position(self) -> float:
        return self._position

    @Property(int, notify=settingsChanged)
    def motionRange(self) -> int:
        return self._settings.get(self.spec.range_key, 0)

    @Property(float, notify=stateChanged)
    def angle(self) -> float:
        return self._position * (self._settings.get(self.spec.range_key) or 900) / 2

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

    @Property(bool, notify=dirtyChanged)
    def dirty(self) -> bool:
        return self._dirty

    @Slot(str, float)
    def setSetting(self, key: str, value: float) -> None:
        field = self.spec.fields().get(key)
        if field is None or field.kind == "readonly" or self._active is None:
            return
        value = field.clamp(value)
        if self._settings.get(key) == value:
            return
        self._settings[key] = value
        self._active.set_setting(key, value)
        self.settingsChanged.emit()
        self.profileStatusChanged.emit()
        if not self._dirty:
            self._dirty = True
            self.dirtyChanged.emit()

    @Slot()
    def saveToBase(self) -> None:
        if self._active:
            self._active.run_action("save")

    @Slot()
    def reloadSettings(self) -> None:
        if self._active:
            self._active.request_reload()
        self._dirty = False
        self.dirtyChanged.emit()

    @Property(bool, notify=specChanged)
    def canCenter(self) -> bool:
        """Czy firmware pozwala ustawić środek z aplikacji (FFBeast nie ma takiej komendy)."""
        return self.spec.action("zero") is not None

    @Slot()
    def centerWheel(self) -> None:
        self.runAction("zero")

    @Slot(str)
    def runAction(self, action_id: str) -> None:
        if self._active is None or self.spec.action(action_id) is None:
            return
        self._active.run_action(action_id)
        if self.spec.action(action_id).ends_session:
            message, kind = ACTION_TOASTS.get(action_id, ("Wykonano", "info"))
            self.toast.emit(message, kind)

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

    # --- profile (zawsze dla aktywnego firmware'u) ------------------------------------

    def _active_profile_key(self) -> str:
        return f"activeProfile/{self.spec.id}"

    @Property("QVariantList", notify=profilesChanged)
    def profiles(self) -> list:
        return self._store.profiles(self.spec)

    @Property(str, notify=profileStatusChanged)
    def activeProfile(self) -> str:
        return self._store.get(self._active_profile_key()) or ""

    @Property(bool, notify=profileStatusChanged)
    def profileModified(self) -> bool:
        prof = self._store.profile(self.spec, self.activeProfile)
        if not prof or not self._settings:
            return False
        return any(k in self._settings and self._settings[k] != v for k, v in prof["settings"].items())

    @Property("QVariantList", notify=specChanged)
    def profileKeys(self) -> list:
        return list(self.spec.profile_keys)

    @Slot(str)
    def applyProfile(self, name: str) -> None:
        prof = self._store.profile(self.spec, name)
        if prof is None:
            return
        if not self.baseConnected:
            self.toast.emit("Podłącz bazę, aby zastosować profil", "error")
            return
        for key, value in prof["settings"].items():
            self.setSetting(key, value)
        self._store.set(self._active_profile_key(), name)
        self.profileStatusChanged.emit()
        self.toast.emit(f"Zastosowano profil „{name}”", "success")

    @Slot(str, str)
    def saveProfile(self, name: str, game: str) -> None:
        name = name.strip()
        if not name or not self._settings:
            return
        try:
            self._store.save_profile(self.spec, name,
                                     {k: self._settings[k] for k in self.spec.profile_keys
                                      if k in self._settings},
                                     game.strip() or "Własny")
        except ValueError as exc:
            self.toast.emit(str(exc), "error")
            return
        self._store.set(self._active_profile_key(), name)
        self.profilesChanged.emit()
        self.profileStatusChanged.emit()
        self.toast.emit(f"Zapisano profil „{name}”", "success")

    @Slot(str)
    def deleteProfile(self, name: str) -> None:
        self._store.delete_profile(self.spec, name)
        if self.activeProfile == name:
            self._store.set(self._active_profile_key(), None)
        self.profilesChanged.emit()
        self.profileStatusChanged.emit()
        self.toast.emit(f"Usunięto profil „{name}”", "info")

    @Slot(str, QUrl)
    def exportProfile(self, name: str, url: QUrl) -> None:
        try:
            self._store.export_profile(self.spec, name, Path(url.toLocalFile()))
            self.toast.emit("Wyeksportowano profil", "success")
        except (OSError, KeyError) as exc:
            self.toast.emit(f"Eksport nieudany: {exc}", "error")

    @Slot(QUrl)
    def importProfile(self, url: QUrl) -> None:
        try:
            name = self._store.import_profile(self.spec, Path(url.toLocalFile()))
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
