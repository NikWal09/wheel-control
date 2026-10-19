"""Konfiguracja aplikacji i profile FFB zapisywane w %APPDATA%\\DDControl."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .ffbeast.protocol import EFFECT_FIELDS, clamp_setting

PROFILE_KEYS = tuple(f.key for f in EFFECT_FIELDS)
PROFILE_FILE_FORMAT = "ddcontrol-profile/1"


def _profile(motion_range, total, spring, static_d, dynamic_d, dx_spring, dx_const, dx_periodic,
             soft_strength=100, soft_range=10, soft_damping=50, direction=1) -> dict[str, int]:
    return {
        "motionRange": motion_range, "totalStrength": total, "integratedSpring": spring,
        "staticDampening": static_d, "dynamicDampening": dynamic_d,
        "dxSpringStrength": dx_spring, "dxConstantStrength": dx_const,
        "dxPeriodicStrength": dx_periodic, "softStopStrength": soft_strength,
        "softStopRange": soft_range, "softStopDampening": soft_damping,
        "dxConstantDirection": direction,
    }


# Punkty startowe - do dostrojenia pod konkretną bazę i preferencje.
BUILTIN_PROFILES: dict[str, dict] = {
    "Domyślny": {"game": "Uniwersalny", "settings": _profile(900, 60, 0, 5, 10, 100, 100, 100)},
    "iRacing": {"game": "iRacing", "settings": _profile(900, 70, 0, 0, 5, 0, 100, 40)},
    "Assetto Corsa Competizione": {"game": "ACC", "settings": _profile(900, 65, 0, 5, 10, 60, 100, 50)},
    "Assetto Corsa": {"game": "Assetto Corsa", "settings": _profile(900, 75, 0, 5, 5, 50, 100, 60)},
    "F1 25": {"game": "F1", "settings": _profile(360, 60, 0, 0, 10, 100, 100, 70)},
    "Drift": {"game": "AC / Drift", "settings": _profile(1080, 70, 0, 0, 0, 30, 100, 30)},
    "Euro Truck Simulator 2": {"game": "ETS2 / ATS", "settings": _profile(1440, 40, 20, 10, 15, 80, 90, 40)},
}


def app_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    path = Path(base) / "DDControl"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sanitize(settings: dict) -> dict[str, int]:
    return {k: clamp_setting(k, settings[k]) for k in PROFILE_KEYS if k in settings}


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

    def profiles(self) -> list[dict]:
        out = [{"name": n, "game": p["game"], "builtin": True, "settings": p["settings"]}
               for n, p in BUILTIN_PROFILES.items()]
        out += [{"name": n, "game": p.get("game", "Własny"), "builtin": False,
                 "settings": p["settings"]} for n, p in sorted(self.user_profiles.items())]
        return out

    def profile(self, name: str) -> dict | None:
        return next((p for p in self.profiles() if p["name"] == name), None)

    def save_profile(self, name: str, settings: dict, game: str = "Własny") -> None:
        if name in BUILTIN_PROFILES:
            raise ValueError("Nie można nadpisać profilu wbudowanego")
        self.user_profiles[name] = {"game": game, "settings": _sanitize(settings)}
        self._save(self.profiles_path, self.user_profiles)

    def delete_profile(self, name: str) -> None:
        if self.user_profiles.pop(name, None) is not None:
            self._save(self.profiles_path, self.user_profiles)

    def export_profile(self, name: str, path: Path) -> None:
        prof = self.profile(name)
        if prof is None:
            raise KeyError(name)
        data = {"format": PROFILE_FILE_FORMAT, "name": prof["name"], "game": prof["game"],
                "settings": prof["settings"]}
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def import_profile(self, path: Path) -> str:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("format") != PROFILE_FILE_FORMAT or not isinstance(data.get("settings"), dict):
            raise ValueError("To nie jest plik profilu DD Control")
        name = str(data.get("name") or path.stem)
        while name in BUILTIN_PROFILES or name in self.user_profiles:
            name += " (import)"
        self.save_profile(name, data["settings"], data.get("game", "Własny"))
        return name
