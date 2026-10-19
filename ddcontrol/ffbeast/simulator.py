"""Symulator bazy FFBeast udający urządzenie hidapi na poziomie bajtów.

Implementuje ten sam interfejs co `hid.device` (read / write /
get_feature_report / close), więc aplikacja w trybie demo przechodzi przez
dokładnie ten sam kod protokołu co z prawdziwą bazą.
"""
from __future__ import annotations

import math
import random
import time

from . import protocol as p

DEFAULT_EFFECTS = {
    "motionRange": 900,
    "staticDampening": 5,
    "softStopDampening": 50,
    "totalStrength": 60,
    "integratedSpring": 0,
    "softStopRange": 10,
    "softStopStrength": 100,
    "dxConstantDirection": 1,
    "dxSpringStrength": 100,
    "dxConstantStrength": 100,
    "dxPeriodicStrength": 100,
    "dynamicDampening": 10,
}

DEFAULT_HARDWARE = {
    "encoderCpr": 4096,
    "iGain": 100,
    "pGain": 50,
    "forceEnabled": 1,
    "debugTorque": 0,
    "amplifierGain": int(p.AmplifierGain.GAIN_40),
    "calibrationMagnitude": 30,
    "calibrationSpeed": 30,
    "powerLimit": 80,
    "brakingLimit": 60,
    "positionSmoothing": 20,
    "speedBufferSize": 16,
    "encoderDirection": 1,
    "forceDirection": 1,
    "polePairs": 15,
}

FIRMWARE = p.FirmwareVersion(release_type=1, major=25, minor=1, patch=3)


class SimulatedWheelBase:
    """Emulacja firmware: ustawienia w RAM + 'flash', stan wysyłany co ~2 ms."""

    def __init__(self) -> None:
        self.flash_effects = dict(DEFAULT_EFFECTS)
        self.flash_hardware = dict(DEFAULT_HARDWARE)
        self.effects = dict(self.flash_effects)
        self.hardware = dict(self.flash_hardware)
        self.registered = False
        self.closed = False
        self._t0 = time.monotonic()
        self._last_read = 0.0
        self.writes: list[bytes] = []  # historia - przydatna w testach

    # --- interfejs hid.device ---------------------------------------------

    def read(self, max_length: int, timeout_ms: int = 0) -> list[int]:
        self._check_open()
        # prawdziwa baza wysyła raport stanu ciągle - tu ograniczamy do ~500 Hz
        wait = 0.002 - (time.monotonic() - self._last_read)
        if wait > 0:
            time.sleep(min(wait, timeout_ms / 1000 if timeout_ms else wait))
        self._last_read = time.monotonic()
        report = bytes([p.ReportType.GENERIC_INPUT_OUTPUT]) + p.encode_state(self._state())
        return list(report[:max_length])

    def write(self, data) -> int:
        self._check_open()
        data = bytes(data)
        self.writes.append(data)
        if data[0] != p.ReportType.GENERIC_INPUT_OUTPUT:
            raise OSError("nieznany raport")
        kind = data[1]
        if kind == p.ReportData.SETTINGS_FIELD_DATA:
            field, _index, value = p.decode_setting_write(data)
            key = next(s.key for s in p.FIELDS_BY_KEY.values() if s.field == field)
            target = self.effects if key in self.effects else self.hardware
            target[key] = p.clamp_setting(key, value)
        elif kind == p.ReportData.COMMAND_SAVE_SETTINGS:
            self.flash_effects = dict(self.effects)
            self.flash_hardware = dict(self.hardware)
        elif kind == p.ReportData.COMMAND_REBOOT:
            self.effects = dict(self.flash_effects)
            self.hardware = dict(self.flash_hardware)
            self.closed = True  # po restarcie urządzenie znika z USB
        elif kind == p.ReportData.COMMAND_DFU_MODE:
            self.closed = True
        return len(data)

    def get_feature_report(self, report_id: int, max_length: int) -> list[int]:
        self._check_open()
        if report_id == p.ReportType.EFFECT_SETTINGS_FEATURE:
            body = p.encode_effect_settings(self.effects)
        elif report_id == p.ReportType.HARDWARE_SETTINGS_FEATURE:
            body = p.encode_hardware_settings(self.hardware)
        elif report_id == p.ReportType.FIRMWARE_LICENSE_FEATURE:
            body = p.encode_license(p.LicenseInfo(FIRMWARE, (0, 0, 0),
                                                  (0x0042_4545, 0x5446_4644, 0x0000_2026),
                                                  self.registered))
        else:
            body = bytes(p.REPORT_SIZE)
        return list((bytes([report_id]) + body)[:max_length])

    def close(self) -> None:
        self.closed = True

    # --- "fizyka" -----------------------------------------------------------

    def _check_open(self) -> None:
        if self.closed:
            raise OSError("urządzenie odłączone")

    def _state(self) -> p.DeviceState:
        t = time.monotonic() - self._t0
        # kierowca kręci kierownicą: wolna jazda po zakrętach + drobne korekty
        angle = 140 * math.sin(t * 0.45) + 35 * math.sin(t * 1.9) + 6 * math.sin(t * 7.3)
        half_range = self.effects["motionRange"] / 2
        position = max(-1.0, min(1.0, angle / half_range))
        strength = self.effects["totalStrength"] / 100 if self.hardware["forceEnabled"] else 0.0
        spring = 0.25 + self.effects["integratedSpring"] / 200
        road = 0.08 * math.sin(t * 23) + random.uniform(-0.04, 0.04)
        torque = (-position * spring * 2.2 + road) * strength * self.hardware["forceDirection"]
        return p.DeviceState(FIRMWARE, self.registered, position, max(-1.0, min(1.0, torque)))
