"""Protokół komunikacji z bazą FFBeast (interfejs vendor HID).

Na podstawie oficjalnej dokumentacji:
https://ffbeast.github.io/docs/en/wheel_programming.html

Wszystkie struktury są spakowane (little-endian, bez wyrównania) i mają
dokładnie 64 bajty - inaczej Windows odrzuca raport.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum

USB_VID = 1115
WHEEL_PID_FS = 22999
INTERFACE_VENDOR = 0
INTERFACE_JOYSTICK = 1

REPORT_SIZE = 64  # bez bajtu Report ID


class ReportType(IntEnum):
    JOYSTICK_INPUT = 0x01
    HARDWARE_SETTINGS_FEATURE = 0x21
    EFFECT_SETTINGS_FEATURE = 0x22
    FIRMWARE_LICENSE_FEATURE = 0x25
    GPIO_SETTINGS_FEATURE = 0xA1
    ADC_SETTINGS_FEATURE = 0xA2
    GENERIC_INPUT_OUTPUT = 0xA3


class ReportData(IntEnum):
    COMMAND_REBOOT = 0x01
    COMMAND_SAVE_SETTINGS = 0x02
    COMMAND_DFU_MODE = 0x03
    OVERRIDE_DATA = 0x10
    FIRMWARE_ACTIVATION_DATA = 0x13
    SETTINGS_FIELD_DATA = 0x14


class SettingsField(IntEnum):
    DIRECT_X_CONSTANT_DIRECTION = 0
    DIRECT_X_SPRING_STRENGTH = 1
    DIRECT_X_CONSTANT_STRENGTH = 2
    DIRECT_X_PERIODIC_STRENGTH = 3
    TOTAL_EFFECT_STRENGTH = 4
    MOTION_RANGE = 5
    SOFT_STOP_STRENGTH = 6
    SOFT_STOP_RANGE = 7
    STATIC_DAMPENING_STRENGTH = 8
    SOFT_STOP_DAMPENING_STRENGTH = 9
    DYNAMIC_DAMPENING_STRENGTH = 10
    FORCE_ENABLED = 11
    DEBUG_TORQUE = 12
    AMPLIFIER_GAIN = 13
    CALIBRATION_MAGNITUDE = 15
    CALIBRATION_SPEED = 16
    POWER_LIMIT = 17
    BRAKING_LIMIT = 18
    POSITION_SMOOTHING = 19
    SPEED_BUFFER_SIZE = 20
    ENCODER_DIRECTION = 21
    FORCE_DIRECTION = 22
    POLE_PAIRS = 23
    ENCODER_CPR = 24
    P_GAIN = 25
    I_GAIN = 26
    RESET_CENTER_ON_Z0 = 41
    INTEGRATED_SPRING_STRENGTH = 43


class AmplifierGain(IntEnum):
    GAIN_80 = 0
    GAIN_40 = 1
    GAIN_20 = 2
    GAIN_10 = 3


@dataclass(frozen=True)
class FieldSpec:
    """Opis jednego ustawienia: gdzie leży w strukturze i jak je zapisać."""
    key: str             # nazwa używana w aplikacji / profilach
    field: SettingsField
    fmt: str             # format struct dla wartości (B, b, H, h)
    minimum: int
    maximum: int


# Kolejność pól = kolejność w EffectSettingsTypeDef.
EFFECT_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec("motionRange", SettingsField.MOTION_RANGE, "H", 90, 3600),
    FieldSpec("staticDampening", SettingsField.STATIC_DAMPENING_STRENGTH, "H", 0, 100),
    FieldSpec("softStopDampening", SettingsField.SOFT_STOP_DAMPENING_STRENGTH, "H", 0, 100),
    FieldSpec("totalStrength", SettingsField.TOTAL_EFFECT_STRENGTH, "B", 0, 100),
    FieldSpec("integratedSpring", SettingsField.INTEGRATED_SPRING_STRENGTH, "B", 0, 100),
    FieldSpec("softStopRange", SettingsField.SOFT_STOP_RANGE, "B", 0, 180),
    FieldSpec("softStopStrength", SettingsField.SOFT_STOP_STRENGTH, "B", 0, 100),
    FieldSpec("dxConstantDirection", SettingsField.DIRECT_X_CONSTANT_DIRECTION, "b", -1, 1),
    FieldSpec("dxSpringStrength", SettingsField.DIRECT_X_SPRING_STRENGTH, "B", 0, 100),
    FieldSpec("dxConstantStrength", SettingsField.DIRECT_X_CONSTANT_STRENGTH, "B", 0, 100),
    FieldSpec("dxPeriodicStrength", SettingsField.DIRECT_X_PERIODIC_STRENGTH, "B", 0, 100),
    FieldSpec("dynamicDampening", SettingsField.DYNAMIC_DAMPENING_STRENGTH, "H", 0, 100),
)

# Kolejność pól = kolejność w HardwareSettingsTypeDef.
HARDWARE_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec("encoderCpr", SettingsField.ENCODER_CPR, "H", 1, 65535),
    FieldSpec("iGain", SettingsField.I_GAIN, "H", 0, 65535),
    FieldSpec("pGain", SettingsField.P_GAIN, "B", 0, 255),
    FieldSpec("forceEnabled", SettingsField.FORCE_ENABLED, "B", 0, 1),
    FieldSpec("debugTorque", SettingsField.DEBUG_TORQUE, "B", 0, 1),
    FieldSpec("amplifierGain", SettingsField.AMPLIFIER_GAIN, "B", 0, 3),
    FieldSpec("calibrationMagnitude", SettingsField.CALIBRATION_MAGNITUDE, "B", 0, 100),
    FieldSpec("calibrationSpeed", SettingsField.CALIBRATION_SPEED, "B", 0, 100),
    FieldSpec("powerLimit", SettingsField.POWER_LIMIT, "B", 0, 100),
    FieldSpec("brakingLimit", SettingsField.BRAKING_LIMIT, "B", 0, 100),
    FieldSpec("positionSmoothing", SettingsField.POSITION_SMOOTHING, "B", 0, 100),
    FieldSpec("speedBufferSize", SettingsField.SPEED_BUFFER_SIZE, "B", 1, 255),
    FieldSpec("encoderDirection", SettingsField.ENCODER_DIRECTION, "b", -1, 1),
    FieldSpec("forceDirection", SettingsField.FORCE_DIRECTION, "b", -1, 1),
    FieldSpec("polePairs", SettingsField.POLE_PAIRS, "B", 1, 255),
)

FIELDS_BY_KEY: dict[str, FieldSpec] = {f.key: f for f in EFFECT_FIELDS + HARDWARE_FIELDS}

_EFFECT_STRUCT = struct.Struct("<" + "".join(f.fmt for f in EFFECT_FIELDS))
_HARDWARE_STRUCT = struct.Struct("<" + "".join(f.fmt for f in HARDWARE_FIELDS))
# FirmwareVersion(4B) + IsRegistered + Position + Torque
_STATE_STRUCT = struct.Struct("<4BBhh")
# FirmwareVersion(4B) + SerialKey[3] + DeviceId[3] + IsRegistered
_LICENSE_STRUCT = struct.Struct("<4B3I3IB")
_DIRECT_CONTROL_STRUCT = struct.Struct("<hhhB")

assert _EFFECT_STRUCT.size == 16 and _HARDWARE_STRUCT.size == 17


@dataclass
class FirmwareVersion:
    release_type: int = 0
    major: int = 0
    minor: int = 0
    patch: int = 0

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass
class DeviceState:
    firmware: FirmwareVersion
    registered: bool
    position: float  # -1..+1 (pełny zakres MotionRange)
    torque: float    # -1..+1


@dataclass
class LicenseInfo:
    firmware: FirmwareVersion
    serial_key: tuple[int, int, int]
    device_id: tuple[int, int, int]
    registered: bool


def _pad(payload: bytes, size: int = REPORT_SIZE) -> bytes:
    if len(payload) > size:
        raise ValueError(f"payload {len(payload)}B > {size}B")
    return payload + bytes(size - len(payload))


def _strip_report_id(data: bytes, report_id: int) -> bytes:
    """hidapi zwraca raporty z Report ID na początku - odcinamy go."""
    data = bytes(data)
    if len(data) == REPORT_SIZE + 1 and data[0] == report_id:
        return data[1:]
    return data


# --- dekodowanie -----------------------------------------------------------

def parse_effect_settings(data: bytes) -> dict[str, int]:
    body = _strip_report_id(data, ReportType.EFFECT_SETTINGS_FEATURE)
    values = _EFFECT_STRUCT.unpack_from(body)
    return {f.key: v for f, v in zip(EFFECT_FIELDS, values)}


def parse_hardware_settings(data: bytes) -> dict[str, int]:
    body = _strip_report_id(data, ReportType.HARDWARE_SETTINGS_FEATURE)
    values = _HARDWARE_STRUCT.unpack_from(body)
    return {f.key: v for f, v in zip(HARDWARE_FIELDS, values)}


def parse_state(data: bytes) -> DeviceState:
    body = _strip_report_id(data, ReportType.GENERIC_INPUT_OUTPUT)
    rt, ma, mi, pa, reg, pos, tq = _STATE_STRUCT.unpack_from(body)
    return DeviceState(FirmwareVersion(rt, ma, mi, pa), bool(reg), pos / 10000.0, tq / 10000.0)


def parse_license(data: bytes) -> LicenseInfo:
    body = _strip_report_id(data, ReportType.FIRMWARE_LICENSE_FEATURE)
    v = _LICENSE_STRUCT.unpack_from(body)
    return LicenseInfo(FirmwareVersion(*v[0:4]), tuple(v[4:7]), tuple(v[7:10]), bool(v[10]))


# --- kodowanie (raporty wysyłane hid_write: 1B Report ID + 64B) -------------

def _generic(data_type: ReportData, buffer: bytes = b"") -> bytes:
    return bytes([ReportType.GENERIC_INPUT_OUTPUT]) + _pad(bytes([data_type]) + buffer)


def build_command(command: ReportData) -> bytes:
    if command not in (ReportData.COMMAND_REBOOT, ReportData.COMMAND_SAVE_SETTINGS,
                       ReportData.COMMAND_DFU_MODE):
        raise ValueError(f"{command!r} nie jest komendą")
    return _generic(command)


def build_setting(key: str, value: int, index: int = 0) -> bytes:
    """Raport zmieniający jedno ustawienie (FieldDataTypeDef)."""
    spec = FIELDS_BY_KEY[key]
    value = clamp_setting(key, value)
    payload = bytes([spec.field, index]) + struct.pack("<" + spec.fmt, value)
    return _generic(ReportData.SETTINGS_FIELD_DATA, payload)


def build_direct_control(spring: float = 0.0, constant: float = 0.0,
                         periodic: float = 0.0, force_drop: int = 0) -> bytes:
    def n(x: float) -> int:
        return max(-10000, min(10000, round(x * 10000)))
    payload = _DIRECT_CONTROL_STRUCT.pack(n(spring), n(constant), n(periodic),
                                          max(0, min(100, int(force_drop))))
    return _generic(ReportData.OVERRIDE_DATA, payload)


def clamp_setting(key: str, value) -> int:
    spec = FIELDS_BY_KEY[key]
    value = int(round(float(value)))
    if spec.fmt == "b" and spec.minimum == -1 and spec.maximum == 1:
        return -1 if value < 0 else 1  # kierunek: tylko -1 albo +1
    return max(spec.minimum, min(spec.maximum, value))


def encode_effect_settings(values: dict[str, int]) -> bytes:
    """Odwrotność parse_effect_settings (używane przez symulator i testy)."""
    return _pad(_EFFECT_STRUCT.pack(*(values[f.key] for f in EFFECT_FIELDS)))


def encode_hardware_settings(values: dict[str, int]) -> bytes:
    return _pad(_HARDWARE_STRUCT.pack(*(values[f.key] for f in HARDWARE_FIELDS)))


def encode_state(state: DeviceState) -> bytes:
    fw = state.firmware
    return _pad(_STATE_STRUCT.pack(fw.release_type, fw.major, fw.minor, fw.patch,
                                   int(state.registered),
                                   max(-10000, min(10000, round(state.position * 10000))),
                                   max(-10000, min(10000, round(state.torque * 10000)))))


def encode_license(info: LicenseInfo) -> bytes:
    fw = info.firmware
    return _pad(_LICENSE_STRUCT.pack(fw.release_type, fw.major, fw.minor, fw.patch,
                                     *info.serial_key, *info.device_id, int(info.registered)))


def decode_setting_write(report: bytes) -> tuple[SettingsField, int, int]:
    """Rozkodowuje raport z build_setting -> (pole, index, wartość)."""
    if report[0] != ReportType.GENERIC_INPUT_OUTPUT or report[1] != ReportData.SETTINGS_FIELD_DATA:
        raise ValueError("to nie jest raport ustawienia")
    field = SettingsField(report[2])
    index = report[3]
    spec = next(s for s in FIELDS_BY_KEY.values() if s.field == field)
    (value,) = struct.unpack_from("<" + spec.fmt, report, 4)
    return field, index, value
