import time

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QCoreApplication, QUrl  # noqa: E402

from ddcontrol.backend import Backend  # noqa: E402
from ddcontrol.ffbeast.driver import BUILTIN_PROFILES  # noqa: E402
from ddcontrol.storage import Store  # noqa: E402


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
    sim = backend._active._sim
    backend.setSetting("totalStrength", 42)
    assert backend.dirty
    assert spin(app, lambda: sim.effects["totalStrength"] == 42)
    assert sim.flash_effects["totalStrength"] != 42
    backend.saveToBase()
    assert spin(app, lambda: not backend.dirty)
    assert sim.flash_effects["totalStrength"] == 42


def test_out_of_range_value_is_clamped(app, backend):
    sim = backend._active._sim
    backend.setSetting("powerLimit", 500)
    assert spin(app, lambda: sim.hardware["powerLimit"] == 100)


def test_apply_and_save_profile(app, backend):
    sim = backend._active._sim
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
    sim = backend._active._sim
    backend.setSetting("motionRange", 540)
    assert spin(app, lambda: sim.effects["motionRange"] == 540)
    backend.runAction("reboot")  # niezapisane -> po restarcie wraca wartość z flash
    assert spin(app, lambda: not backend.baseConnected)
    assert spin(app, lambda: backend.baseConnected and backend.settings.get("motionRange") == 900)


def test_pedal_learning(app, backend):
    backend.learnPedal("brake")
    # symulator naciska pedały cyklicznie - prędzej czy później któraś oś ruszy
    assert spin(app, lambda: backend.learning == "", timeout=9)


@pytest.fixture
def offb_backend(app, tmp_path):
    store = Store(tmp_path)
    store.set("demoFirmware", "openffboard")
    b = Backend(store, simulate=True)
    b.start()
    assert spin(app, lambda: b.baseConnected and b.settings)
    yield b
    b.shutdown()


def test_openffboard_demo_uses_its_own_schema_and_profiles(app, offb_backend):
    b = offb_backend
    assert b.firmwareId == "openffboard" and b.firmware == "1.17.1"
    keys = {f["key"] for s in b.schema for f in s["fields"]}
    assert "axis.0.power" in keys and "totalStrength" not in keys
    assert b.strengthField["key"] == "axis.0.power" and b.motionRange == 900
    assert {a["id"] for a in b.actions} >= {"calibrate", "test", "zero", "dfu"}

    sim = b._active._sim
    b.applyProfile("F1 25")
    assert spin(app, lambda: sim.values["axis.0.degrees"] == 360)
    assert b.activeProfile == "F1 25"
    b.runAction("calibrate")
    assert spin(app, lambda: "xdrive.0.cal?" in sim.received)


def test_switching_demo_firmware_restarts_link(app, backend):
    assert backend.firmwareId == "ffbeast"
    backend.setDemoFirmware("openffboard")
    assert spin(app, lambda: backend.baseConnected and backend.firmwareId == "openffboard")
    assert "axis.0.degrees" in backend.settings


def test_center_wheel(app, offb_backend):
    assert offb_backend.canCenter
    sim = offb_backend._active._sim
    offb_backend.centerWheel()
    assert spin(app, lambda: "axis.0.zeroenc?" in sim.received)


def test_ffbeast_has_no_center_command(app, backend):
    assert backend.firmwareId == "ffbeast" and not backend.canCenter


def test_calibration_banner_flag(app, offb_backend):
    sim = offb_backend._active._sim
    assert not offb_backend.needsCalibration and not offb_backend.needsXdrive
    sim.values["xdrive.0.errors"] = 512  # firmware: brak kalibracji
    assert spin(app, lambda: offb_backend.needsCalibration, timeout=3)
    offb_backend.sendConsole("xdrive.0.errors?")
    assert spin(app, lambda: any("512" in line for line in offb_backend.consoleLog), timeout=3)
