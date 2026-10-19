import time

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QCoreApplication, QUrl  # noqa: E402

from ddcontrol.backend import Backend  # noqa: E402
from ddcontrol.storage import BUILTIN_PROFILES, Store  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QCoreApplication.instance() or QCoreApplication([])


def spin(app, cond, timeout=4.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        app.processEvents()
        if cond():
            return True
        time.sleep(0.005)
    return False


@pytest.fixture
def backend(app, tmp_path):
    b = Backend(Store(tmp_path), simulate=True)
    b.start()
    assert spin(app, lambda: b.baseConnected and b.settings)
    yield b
    b.shutdown()


def test_connects_to_simulator_and_streams_state(app, backend):
    assert backend.baseSimulated and backend.firmware == "25.1.3"
    assert spin(app, lambda: abs(backend.angle) > 1.0)
    assert spin(app, lambda: backend.pedalsConnected and backend.wheelConnected)


def test_setting_change_reaches_base_and_save_persists(app, backend):
    sim = backend._link._sim
    backend.setSetting("totalStrength", 42)
    assert backend.dirty
    assert spin(app, lambda: sim.effects["totalStrength"] == 42)
    assert sim.flash_effects["totalStrength"] != 42
    backend.saveToBase()
    assert spin(app, lambda: not backend.dirty)
    assert sim.flash_effects["totalStrength"] == 42


def test_out_of_range_value_is_clamped(app, backend):
    sim = backend._link._sim
    backend.setSetting("powerLimit", 500)
    assert spin(app, lambda: sim.hardware["powerLimit"] == 100)


def test_apply_and_save_profile(app, backend):
    sim = backend._link._sim
    backend.applyProfile("F1 25")
    expected = BUILTIN_PROFILES["F1 25"]["settings"]
    assert spin(app, lambda: all(sim.effects[k] == v for k, v in expected.items()))
    assert backend.activeProfile == "F1 25" and not backend.profileModified

    backend.setSetting("totalStrength", 33)
    assert backend.profileModified
    backend.saveProfile("Moje F1", "F1")
    assert backend.activeProfile == "Moje F1" and not backend.profileModified
    assert any(p["name"] == "Moje F1" for p in backend.profiles)


def test_export_import_profile(app, backend, tmp_path):
    out = tmp_path / "f1.json"
    backend.exportProfile("F1 25", QUrl.fromLocalFile(str(out)))
    assert out.exists()
    backend.importProfile(QUrl.fromLocalFile(str(out)))
    assert any(p["name"] == "F1 25 (import)" for p in backend.profiles)


def test_reboot_reconnects_with_flash_settings(app, backend):
    sim = backend._link._sim
    backend.setSetting("motionRange", 540)
    assert spin(app, lambda: sim.effects["motionRange"] == 540)
    backend.rebootBase()  # niezapisane -> po restarcie wraca wartość z flash
    assert spin(app, lambda: not backend.baseConnected)
    assert spin(app, lambda: backend.baseConnected and backend.settings.get("motionRange") == 900)


def test_pedal_learning(app, backend):
    backend.learnPedal("brake")
    # symulator naciska pedały cyklicznie - prędzej czy później któraś oś ruszy
    assert spin(app, lambda: backend.learning == "", timeout=9)
