"""Konfiguracja aplikacji i profile FFB zapisywane w %APPDATA%\\DDControl.

Profil należy do konkretnego firmware'u (FFBeast i OpenFFBoard mają inne parametry),
więc lista profili zawsze dotyczy aktywnego firmware'u.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .core import FirmwareSpec

PROFILE_FILE_FORMAT = "ddcontrol-profile/2"
_LEGACY_FORMAT = "ddcontrol-profile/1"  # sprzed obsługi OpenFFBoard - zawsze FFBeast


def app_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    path = Path(base) / "DDControl"
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize(spec: FirmwareSpec, settings: dict) -> dict[str, int]:
    fields = spec.fields()
    return {k: fields[k].clamp(settings[k]) for k in spec.profile_keys if k in settings}


class Store:
    def __init__(self, directory: Path | None = None) -> None:
        self.dir = directory or app_dir()
        self.config_path = self.dir / "config.json"
        self.profiles_path = self.dir / "profiles.json"
        self.config: dict = self._load(self.config_path, {})
        self.user_profiles: dict[str, dict] = self._load(self.profiles_path, {})

    @staticmethod
    def _load(path: Path, default):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return default

    @staticmethod
    def _save(path: Path, data) -> None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)

    # --- konfiguracja ----------------------------------------------------------

    def get(self, key: str, default=None):
        return self.config.get(key, default)

    def set(self, key: str, value) -> None:
        self.config[key] = value
        self._save(self.config_path, self.config)

    # --- profile -------------------------------------------------------------
    # Klucz w profiles.json: "<firmware>/<nazwa>"; stare wpisy bez prefiksu = FFBeast.

    @staticmethod
    def _split(stored_key: str, entry: dict) -> tuple[str, str]:
        firmware = entry.get("firmware", "ffbeast")
        prefix = firmware + "/"
        name = stored_key[len(prefix):] if stored_key.startswith(prefix) else stored_key
        return firmware, name

    def _user(self, spec: FirmwareSpec) -> dict[str, dict]:
        out = {}
        for stored_key, entry in self.user_profiles.items():
            firmware, name = self._split(stored_key, entry)
            if firmware == spec.id:
                out[name] = entry
        return out

    def profiles(self, spec: FirmwareSpec) -> list[dict]:
        out = [{"name": n, "game": p["game"], "builtin": True, "settings": p["settings"]}
               for n, p in spec.builtin_profiles.items()]
        out += [{"name": n, "game": p.get("game", "Własny"), "builtin": False,
                 "settings": p["settings"]} for n, p in sorted(self._user(spec).items())]
        return out

    def profile(self, spec: FirmwareSpec, name: str) -> dict | None:
        return next((p for p in self.profiles(spec) if p["name"] == name), None)

    def save_profile(self, spec: FirmwareSpec, name: str, settings: dict, game: str = "Własny") -> None:
        if name in spec.builtin_profiles:
            raise ValueError("Nie można nadpisać profilu wbudowanego")
        self._remove(spec, name)
        self.user_profiles[f"{spec.id}/{name}"] = {
            "firmware": spec.id, "game": game, "settings": sanitize(spec, settings)}
        self._save(self.profiles_path, self.user_profiles)

    def _remove(self, spec: FirmwareSpec, name: str) -> bool:
        for stored_key, entry in list(self.user_profiles.items()):
            if self._split(stored_key, entry) == (spec.id, name):
                del self.user_profiles[stored_key]
                return True
        return False

    def delete_profile(self, spec: FirmwareSpec, name: str) -> None:
        if self._remove(spec, name):
            self._save(self.profiles_path, self.user_profiles)

    def export_profile(self, spec: FirmwareSpec, name: str, path: Path) -> None:
        prof = self.profile(spec, name)
        if prof is None:
            raise KeyError(name)
        data = {"format": PROFILE_FILE_FORMAT, "firmware": spec.id, "name": prof["name"],
                "game": prof["game"], "settings": prof["settings"]}
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def import_profile(self, spec: FirmwareSpec, path: Path) -> str:
        data = json.loads(path.read_text(encoding="utf-8"))
        fmt = data.get("format")
        if fmt not in (PROFILE_FILE_FORMAT, _LEGACY_FORMAT) or not isinstance(data.get("settings"), dict):
            raise ValueError("To nie jest plik profilu DD Control")
        firmware = data.get("firmware", "ffbeast")
        if firmware != spec.id:
            raise ValueError(f"Profil jest dla firmware'u {firmware}, a aktywny jest {spec.name}")
        name = str(data.get("name") or path.stem)
        existing = {p["name"] for p in self.profiles(spec)}
        while name in existing:
            name += " (import)"
        self.save_profile(spec, name, data["settings"], data.get("game", "Własny"))
        return name
