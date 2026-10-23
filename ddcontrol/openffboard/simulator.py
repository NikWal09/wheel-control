"""Symulator OpenFFBoard na MKS XDrive Mini udający port szeregowy (interfejs pyserial).

Odpowiada tekstowo dokładnie w formacie firmware, więc tryb demo i testy przechodzą przez
ten sam parser co z prawdziwą płytką. Komendy, których "firmware" nie zna, zostają bez
odpowiedzi - tak jak w oryginale.
"""
from __future__ import annotations

import math
import random
import threading
import time

from . import protocol as p

SW_VERSION = "1.17.1"
HW_TYPE = "MKS XDrive Mini (F405)"

DEFAULTS = {
    "axis.0.power": 12000,
    "axis.0.degrees": 900,
    "axis.0.esgain": 127,
    "axis.0.invert": 0,
    "axis.0.idlespring": 127,
    "axis.0.axisdamper": 30,
    "axis.0.axisfriction": 0,
    "axis.0.axisinertia": 0,
    "axis.0.maxspeed": 0,
    "axis.0.maxtorquerate": 0,
    "axis.0.fxratio": 204,
    "axis.0.expo": 0,
    "axis.0.cpr": 4096,
    "fx.0.spring": 64,
    "fx.0.damper": 64,
    "fx.0.friction": 254,
    "fx.0.inertia": 127,
    "fx.0.filterProfile_id": 0,
    "fx.0.damper_f": 30,
    "fx.0.damper_q": 40,
    "fx.0.friction_f": 50,
    "fx.0.friction_q": 20,
    "fx.0.inertia_f": 15,
    "fx.0.inertia_q": 20,
    "fx.0.frictionPctSpeedToRampup": 25,
    "fx.0.filterCfFreq": 500,
    "fx.0.filterCfQ": 70,
    "axis.0.filterProfile_id": 1,
    "xdrive.0.poles": 15,
    "xdrive.0.vlimit": 12000,
    "xdrive.0.sensorDirection": 1,
    "xdrive.0.invert": 0,
    "xdrive.0.offset": 1837,
    "xdrive.0.ilimit": 10000,
    "xdrive.0.mode": 1,
    "xdrive.0.cpr": 4096,
    "xdrive.0.bw": 1000,
    "xdrive.0.index": 1,
    "xdrive.0.state": 5,
    "xdrive.0.errors": 0,
    "xdrive.0.vbus": 19500,
    "xdrive.0.brake": 0,
    "xdrive.0.iq": 0,
    "xdrive.0.fwrev": 2026102302,
    "xdrive.0.vsupply": 19500,
    "xdrive.0.res": 2000,
    "xdrive.0.ind": 400,
    "xdrive.0.calratio": 1003,
    "xdrive.0.indexfound": 1,
}
XDRIVE_DRVTYPE = 13  # MotorDriver::all_drivers w firmware
READ_ONLY = {"axis.0.cpr", "xdrive.0.offset", "xdrive.0.iq", "xdrive.0.fwrev", "xdrive.0.vsupply", "xdrive.0.state", "xdrive.0.vbus", "xdrive.0.brake",
             "xdrive.0.res", "xdrive.0.ind", "xdrive.0.calratio", "xdrive.0.indexfound"}


class SimulatedOpenFFBoard:
    def __init__(self, with_xdrive: bool = True, drvtype: int = XDRIVE_DRVTYPE) -> None:
        self.with_xdrive = with_xdrive
        self.values = {k: v for k, v in DEFAULTS.items() if with_xdrive or not k.startswith("xdrive")}
        self.values["axis.0.drvtype"] = drvtype
        self.flash = dict(self.values)
        self.closed = False
        self.received: list[str] = []      # historia komend - przydatna w testach
        self._out = bytearray()
        self._lock = threading.Lock()
        self._t0 = time.monotonic()
        self._motion: tuple[str, float] | None = None  # ("cal" | "test", start)

    # --- interfejs pyserial ----------------------------------------------------------

    @property
    def in_waiting(self) -> int:
        self._check_open()
        return len(self._out)

    def read(self, size: int = 1) -> bytes:
        self._check_open()
        with self._lock:
            chunk, self._out = bytes(self._out[:size]), self._out[size:]
        return chunk

    def write(self, data: bytes) -> int:
        self._check_open()
        text = data.decode()
        for raw in text.replace("\n", ";").replace("\r", ";").split(";"):
            if raw.strip():
                self.received.append(raw.strip())
                self._handle(raw.strip())
        return len(data)

    def reset_input_buffer(self) -> None:
        with self._lock:
            self._out.clear()

    def close(self) -> None:
        self.closed = True

    @property
    def xdrive_active(self) -> bool:
        return self.with_xdrive and self.values.get("axis.0.drvtype") == XDRIVE_DRVTYPE

    # --- firmware --------------------------------------------------------------------

    def _check_open(self) -> None:
        if self.closed:
            raise OSError("port zamknięty")

    def _reply(self, text: str) -> None:
        with self._lock:
            self._out += text.encode()

    def _handle(self, raw: str) -> None:
        parsed = p.parse_command(raw)
        if parsed is None:
            return
        cls, inst, cmd, kind, val = parsed
        key = f"{cls}.{inst}.{cmd}"
        echo = f"{key}?" if kind == "get" else f"{key}={val}" if kind == "set" else f"{key}!"
        if cls == "xdrive" and not self.xdrive_active:
            return  # klasa sterownika nie istnieje, gdy wybrany jest inny driver

        if kind == "info" and key == "axis.0.drvtype":
            # format ClassChooser::replyAvailableClasses: "id:creatable:nazwa"
            classes = ["0:1:None"] + (["13:1:MKS XDrive (FOC)"] if self.with_xdrive else [])
            self._reply(f"[{echo}|" + "\n".join(classes) + "]\n")
            return
        if kind == "get" and key in self.values:
            self._reply(f"[{echo}|{self.values[key]}]\n")
        elif kind == "set" and key in self.values:
            if key in READ_ONLY:
                self._reply(f"[{echo}|ERR]\n")
            else:
                self.values[key] = self._clip(key, val)
                self._reply(f"[{echo}|OK]\n")
        elif key in ("axis.0.curpos", "axis.0.curtorque"):
            pos, torque = self._physics()
            self._reply(f"[{echo}|{pos if cmd == 'curpos' else torque}]\n")
        elif cls == "sys":
            self._system(cmd, echo)
        elif key in ("xdrive.0.cal", "xdrive.0.test"):
            self._motion = (cmd, time.monotonic())
            self._reply(f"[{echo}|OK]\n")
        elif key == "axis.0.zeroenc":
            self._t0 = time.monotonic()
            self._reply(f"[{echo}|OK]\n")
        # wszystko inne: brak odpowiedzi (jak dla nieznanej komendy w firmware)

    def _system(self, cmd: str, echo: str) -> None:
        if cmd == "swver":
            self._reply(f"[{echo}|{SW_VERSION}]\n")
        elif cmd == "hwtype":
            self._reply(f"[{echo}|{HW_TYPE}]\n")
        elif cmd == "main":
            self._reply(f"[{echo}|1]\n")
        elif cmd == "lsactive":
            lines = ["System:sys:0:0:0", "FFB Wheel (1 Axis):main:0:1:0", "Axis:axis:0:2561:0",
                     "Effects:fx:0:2562:0", "Effects manager:fxm:0:2563:0"]
            if self.xdrive_active:
                lines.append("MKS XDrive FOC:xdrive:0:2401:0")
            self._reply(f"[{echo}|" + "\n".join(lines) + "]\n")
        elif cmd == "save":
            self.flash = dict(self.values)
            self._reply(f"[{echo}|OK]\n")
        elif cmd in ("reboot", "dfu"):
            if cmd == "reboot":
                self.values = dict(self.flash)
            self.closed = True  # port znika z systemu

    @staticmethod
    def _clip(key: str, val: int) -> int:
        if key in ("axis.0.power",):
            return max(0, min(0x7FFF, val))
        if key == "axis.0.degrees":
            return (val & 0x7FFF) or 900
        if key in ("xdrive.0.sensorDirection",):
            return -1 if val < 0 else 1
        if key in ("axis.0.invert", "xdrive.0.invert"):
            return 1 if val >= 1 else 0
        if key.startswith("fx.") or key in ("axis.0.esgain", "axis.0.idlespring", "axis.0.axisdamper",
                                            "axis.0.axisfriction", "axis.0.axisinertia", "axis.0.fxratio"):
            return max(0, min(255, val))
        return val

    def _physics(self) -> tuple[int, int]:
        now = time.monotonic()
        t = now - self._t0
        angle = 140 * math.sin(t * 0.45) + 35 * math.sin(t * 1.9) + 6 * math.sin(t * 7.3)
        if self._motion:
            kind, start = self._motion
            dt = now - start
            if kind == "test" and dt < 6:
                # +360° -> -360° (czyli 720° w lewo) -> 0°, jak xdrive.test w specyfikacji
                angle = 360 * math.sin(dt / 6 * 2 * math.pi) if dt < 6 else 0
            elif kind == "cal" and dt < 2.5:
                angle = 8 * math.sin(dt * 9)
            else:
                self._motion = None
        degrees = self.values["axis.0.degrees"]
        pos = round(max(-1.0, min(1.0, angle / (degrees / 2))) * 0x7FFF)
        power = self.values["axis.0.power"]
        road = 0.08 * math.sin(t * 23) + random.uniform(-0.04, 0.04)
        spring = 0.25 + self.values["axis.0.idlespring"] / 1000
        torque = (-pos / 0x7FFF * spring * 2.2 + road) * power * self.values["axis.0.fxratio"] / 255
        return pos, round(max(-power, min(power, torque)))
