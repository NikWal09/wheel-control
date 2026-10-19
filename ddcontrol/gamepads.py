"""Odczyt pedałów i przycisków kierownicy (zwykłe gamepady HID).

Pedały (ESP32-S3, USB HID) i kierownica (ESP32-S3, BLE gamepad) są widoczne
w Windows jako standardowe kontrolery gier, więc czytamy je przez WinMM
(joyGetPosEx) - bez dodatkowych zależności. Kalibracja siedzi w firmware
ESP32, tu tylko je podglądamy.
"""
from __future__ import annotations

import ctypes
import math
import sys
import time
from ctypes import wintypes
from dataclasses import dataclass, field

MAX_AXES = 6
AXIS_NAMES = ("X", "Y", "Z", "R", "U", "V")

# Domyślne VID z bibliotek użytych w firmware ESP32 - pozwalają zgadnąć rolę.
ESPRESSIF_USB_VID = 0x303A      # USBHIDGamepad na ESP32-S3 (pedały)
BLE_GAMEPAD_VID = 0xE502        # biblioteka ESP32-BLE-Gamepad (kierownica)
FFBEAST_VID = 1115


@dataclass
class JoystickInfo:
    id: int
    name: str
    vid: int
    pid: int
    num_axes: int
    num_buttons: int

    @property
    def key(self) -> str:
        """Stały identyfikator do zapisania w konfiguracji (id WinMM potrafi się zmienić)."""
        return f"{self.vid:04X}:{self.pid:04X}"

    def to_qml(self) -> dict:
        return {"id": self.id, "key": self.key, "name": self.name, "vid": self.vid,
                "pid": self.pid, "axes": self.num_axes, "buttons": self.num_buttons}


@dataclass
class JoystickSample:
    axes: list[float] = field(default_factory=lambda: [0.0] * MAX_AXES)  # 0..1
    buttons: int = 0  # maska bitowa, bit 0 = przycisk 1


class _JOYINFOEX(ctypes.Structure):
    _fields_ = [(n, wintypes.DWORD) for n in (
        "dwSize", "dwFlags", "dwXpos", "dwYpos", "dwZpos", "dwRpos", "dwUpos", "dwVpos",
        "dwButtons", "dwButtonNumber", "dwPOV", "dwReserved1", "dwReserved2")]


class _JOYCAPSW(ctypes.Structure):
    _fields_ = [
        ("wMid", wintypes.WORD), ("wPid", wintypes.WORD), ("szPname", wintypes.WCHAR * 32),
        ("wXmin", wintypes.UINT), ("wXmax", wintypes.UINT), ("wYmin", wintypes.UINT),
        ("wYmax", wintypes.UINT), ("wZmin", wintypes.UINT), ("wZmax", wintypes.UINT),
        ("wNumButtons", wintypes.UINT), ("wPeriodMin", wintypes.UINT),
        ("wPeriodMax", wintypes.UINT), ("wRmin", wintypes.UINT), ("wRmax", wintypes.UINT),
        ("wUmin", wintypes.UINT), ("wUmax", wintypes.UINT), ("wVmin", wintypes.UINT),
        ("wVmax", wintypes.UINT), ("wCaps", wintypes.UINT), ("wMaxAxes", wintypes.UINT),
        ("wNumAxes", wintypes.UINT), ("wMaxButtons", wintypes.UINT),
        ("szRegKey", wintypes.WCHAR * 32), ("szOEMVxD", wintypes.WCHAR * 260)]


JOY_RETURNALL = 0xFF
JOYERR_NOERROR = 0


def _oem_name(vid: int, pid: int) -> str | None:
    """Nazwa urządzenia z rejestru (ta sama, którą pokazuje joy.cpl)."""
    try:
        import winreg
        key = (r"System\CurrentControlSet\Control\MediaProperties\PrivateProperties"
               rf"\Joystick\OEM\VID_{vid:04X}&PID_{pid:04X}")
        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(root, key) as k:
                    return winreg.QueryValueEx(k, "OEMName")[0]
            except OSError:
                continue
    except ImportError:
        pass
    return None


def _hid_product_name(vid: int, pid: int) -> str | None:
    try:
        import hid
        for dev in hid.enumerate(vid, pid):
            if dev.get("product_string"):
                return dev["product_string"]
    except Exception:  # noqa: BLE001 - nazwa to tylko kosmetyka
        pass
    return None


class JoystickReader:
    """Lista kontrolerów + odczyt wybranych. Na innych systemach niż Windows pusta."""

    def __init__(self) -> None:
        self._winmm = ctypes.WinDLL("winmm") if sys.platform == "win32" else None
        self._caps: dict[int, _JOYCAPSW] = {}
        self._names: dict[tuple[int, int], str] = {}

    def enumerate(self) -> list[JoystickInfo]:
        if not self._winmm:
            return []
        result = []
        self._caps.clear()
        info = _JOYINFOEX(dwSize=ctypes.sizeof(_JOYINFOEX), dwFlags=JOY_RETURNALL)
        for jid in range(min(self._winmm.joyGetNumDevs(), 16)):
            if self._winmm.joyGetPosEx(jid, ctypes.byref(info)) != JOYERR_NOERROR:
                continue
            caps = _JOYCAPSW()
            if self._winmm.joyGetDevCapsW(jid, ctypes.byref(caps), ctypes.sizeof(caps)) != 0:
                continue
            self._caps[jid] = caps
            ident = (caps.wMid, caps.wPid)
            if ident not in self._names:
                self._names[ident] = (_oem_name(*ident) or _hid_product_name(*ident)
                                      or caps.szPname or f"Kontroler {jid + 1}")
            result.append(JoystickInfo(jid, self._names[ident], caps.wMid, caps.wPid,
                                       caps.wNumAxes, caps.wNumButtons))
        return result

    def read(self, jid: int) -> JoystickSample | None:
        caps = self._caps.get(jid)
        if not self._winmm or caps is None:
            return None
        info = _JOYINFOEX(dwSize=ctypes.sizeof(_JOYINFOEX), dwFlags=JOY_RETURNALL)
        if self._winmm.joyGetPosEx(jid, ctypes.byref(info)) != JOYERR_NOERROR:
            return None
        raw = (info.dwXpos, info.dwYpos, info.dwZpos, info.dwRpos, info.dwUpos, info.dwVpos)
        ranges = ((caps.wXmin, caps.wXmax), (caps.wYmin, caps.wYmax), (caps.wZmin, caps.wZmax),
                  (caps.wRmin, caps.wRmax), (caps.wUmin, caps.wUmax), (caps.wVmin, caps.wVmax))
        axes = [(v - lo) / (hi - lo) if hi > lo else 0.0 for v, (lo, hi) in zip(raw, ranges)]
        return JoystickSample(axes, info.dwButtons)


class SimulatedJoysticks:
    """Udawane pedały i kierownica do trybu demo."""

    PEDALS = JoystickInfo(100, "Pedały DIY (symulacja)", ESPRESSIF_USB_VID, 0x1001, 3, 0)
    WHEEL = JoystickInfo(101, "Kierownica BLE (symulacja)", BLE_GAMEPAD_VID, 0xBBAB, 0, 14)

    def __init__(self) -> None:
        self._t0 = time.monotonic()

    def enumerate(self) -> list[JoystickInfo]:
        return [self.PEDALS, self.WHEEL]

    def read(self, jid: int) -> JoystickSample | None:
        t = time.monotonic() - self._t0
        if jid == self.PEDALS.id:
            throttle = max(0.0, math.sin(t * 0.9)) ** 0.7
            brake = max(0.0, -math.sin(t * 0.9 - 0.3)) ** 1.5
            clutch = max(0.0, math.sin(t * 0.3 + 2)) ** 4
            return JoystickSample([throttle, brake, clutch, 0, 0, 0], 0)
        if jid == self.WHEEL.id:
            step = int(t * 2.5)
            mask = 1 << (step % 14) if step % 3 else 0
            return JoystickSample([0.0] * MAX_AXES, mask)
        return None


def guess_role(info: JoystickInfo) -> str | None:
    if info.vid == ESPRESSIF_USB_VID:
        return "pedals"
    if info.vid == BLE_GAMEPAD_VID:
        return "wheel"
    return None
