"""Tekstowy protokół komend OpenFFBoard (CDC / wirtualny port COM).

Na podstawie źródeł firmware (Firmware/FFBoard/Src/CmdParser.cpp, CommandInterface.cpp):

- komendy: ``cls.inst.cmd?`` (odczyt), ``cls.inst.cmd=val`` (zapis), ``cls.inst.cmd!`` (info),
  rozdzielane ``;`` albo znakiem nowej linii,
- odpowiedzi: ``[cls.inst.cmd?|wartość]`` / ``[cls.inst.cmd=val|OK]`` / ``|ERR]`` / ``|NOT_FOUND]``,
  każda zakończona ``\\n``; odpowiedź wielowierszowa ma wiersze rozdzielone ``\\n`` w środku nawiasu,
- zmiana wartości przez inny interfejs komend (np. HID) przychodzi jako niezamówiona
  odpowiedź ``[cls.inst.cmd?|nowa_wartość]``,
- komenda nieznana firmware'owi nie dostaje żadnej odpowiedzi - trzeba czekać z limitem czasu.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

USB_VID = 0x1209
USB_PID = 0xFFB0
MAX_BATCH_CHARS = 200  # bezpiecznie poniżej bufora parsera w firmware

_REPLY_RE = re.compile(r"\[([^\[\]|]+)\|([^\[\]]*)\]")
_CMD_RE = re.compile(r"^([A-Za-z0-9_]+)\.(\d+)\.([A-Za-z0-9_]+)(\?|=(-?\d+)(?:\?(-?\d+))?|!)?$")


@dataclass(frozen=True)
class Reply:
    command: str   # np. "axis.0.power?" albo "axis.0.power=5000"
    value: str     # np. "5000", "OK", "ERR", "1.17.1", wiele wierszy...

    @property
    def key(self) -> str:
        """Ścieżka bez operatora: "axis.0.power"."""
        return re.split(r"[?=!]", self.command, maxsplit=1)[0]

    @property
    def is_set(self) -> bool:
        return "=" in self.command

    @property
    def ok(self) -> bool:
        return self.value not in ("ERR", "NOT_FOUND", "None")

    def int_value(self) -> int | None:
        """Wartość liczbowa (dla odpowiedzi "val:adr" bierze val)."""
        head = self.value.split(":", 1)[0].strip()
        try:
            return int(head, 0) if head.lower().startswith("0x") else int(head)
        except ValueError:
            return None


def get(key: str) -> str:
    return f"{key}?"


def set_(key: str, value: int) -> str:
    return f"{key}={int(value)}"


def batches(commands: list[str]) -> list[bytes]:
    """Grupuje komendy w paczki "a;b;c\\n" nie dłuższe niż MAX_BATCH_CHARS."""
    out, cur = [], ""
    for cmd in commands:
        if cur and len(cur) + len(cmd) + 1 > MAX_BATCH_CHARS:
            out.append((cur + "\n").encode())
            cur = ""
        cur = f"{cur};{cmd}" if cur else cmd
    if cur:
        out.append((cur + "\n").encode())
    return out


def parse_command(text: str):
    """Rozbiór komendy -> (cls, inst, cmd, typ, wartość). Używane przez symulator."""
    m = _CMD_RE.match(text.strip())
    if not m:
        return None
    cls, inst, cmd, op, val, _adr = m.groups()
    if op is None or op == "?":
        kind = "get"
    elif op == "!":
        kind = "info"
    else:
        kind = "set"
    return cls, int(inst), cmd, kind, (int(val) if val is not None else None)


def parse_lsactive(text: str) -> set[str]:
    """`sys.0.lsactive?` -> {"axis.0", "fx.0", ...}. Wiersze: "Nazwa:cls:inst:clsid:idx"."""
    active = set()
    for line in text.splitlines():
        parts = line.split(":")
        if len(parts) >= 3 and parts[2].strip().isdigit():
            active.add(f"{parts[1].strip()}.{parts[2].strip()}")
    return active


class ReplyParser:
    """Składa odpowiedzi z kawałków danych z portu szeregowego."""

    def __init__(self) -> None:
        self._buf = ""

    def feed(self, data: bytes | str) -> list[Reply]:
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        self._buf += data
        replies, last = [], 0
        for m in _REPLY_RE.finditer(self._buf):
            replies.append(Reply(m.group(1).strip(), m.group(2).strip()))
            last = m.end()
        self._buf = self._buf[last:]
        # śmieci bez otwierającego nawiasu nie zablokują bufora
        start = self._buf.rfind("[")
        self._buf = self._buf[start:] if start >= 0 else ""
        if len(self._buf) > 8192:
            self._buf = ""
        return replies
