import struct
import time

import pytest

from ddcontrol.ffbeast import protocol as p
from ddcontrol.ffbeast.driver import SPEC, FFBeastLink
from ddcontrol.ffbeast.simulator import DEFAULT_EFFECTS, DEFAULT_HARDWARE, SimulatedWheelBase
from ddcontrol.storage import Store


def test_struct_layouts_match_documentation():
    # EffectSettingsTypeDef: MotionRange(u16) na początku, DynamicDampening(u16) na końcu
    body = p.encode_effect_settings(DEFAULT_EFFECTS)
    assert len(body) == 64
    assert struct.unpack_from("<H", body, 0)[0] == DEFAULT_EFFECTS["motionRange"]
    assert body[6] == DEFAULT_EFFECTS["totalStrength"]
    assert struct.unpack_from("<b", body, 10)[0] == DEFAULT_EFFECTS["dxConstantDirection"]
    assert struct.unpack_from("<H", body, 14)[0] == DEFAULT_EFFECTS["dynamicDampening"]

    # HardwareSettingsTypeDef: EncoderCPR(u16), IntegralGain(u16), ProportionalGain(u8)...
    body = p.encode_hardware_settings(DEFAULT_HARDWARE)
    assert len(body) == 64
    assert struct.unpack_from("<HHB", body, 0) == (4096, 100, 50)
    assert body[16] == DEFAULT_HARDWARE["polePairs"]


def test_parse_roundtrip_with_report_id():
    report = bytes([p.ReportType.EFFECT_SETTINGS_FEATURE]) + p.encode_effect_settings(DEFAULT_EFFECTS)
    assert p.parse_effect_settings(report) == DEFAULT_EFFECTS
    report = bytes([p.ReportType.HARDWARE_SETTINGS_FEATURE]) + p.encode_hardware_settings(DEFAULT_HARDWARE)
    assert p.parse_hardware_settings(report) == DEFAULT_HARDWARE


def test_state_report():
    state = p.DeviceState(p.FirmwareVersion(1, 25, 1, 3), True, -0.25, 0.5)
    parsed = p.parse_state(p.encode_state(state))
    assert parsed.position == pytest.approx(-0.25)
    assert parsed.torque == pytest.approx(0.5)
    assert parsed.registered and str(parsed.firmware) == "25.1.3"


def test_setting_report_layout():
    report = p.build_setting("motionRange", 1080)
    assert len(report) == 65
    # ReportId, ReportData, FieldId, Index, uint16 LE
    assert report[:6] == bytes([0xA3, 0x14, 5, 0]) + struct.pack("<H", 1080)
    assert not any(report[6:])

    report = p.build_setting("forceDirection", -1)
    assert report[2] == p.SettingsField.FORCE_DIRECTION and report[4] == 0xFF


def test_clamping():
    assert p.clamp_setting("totalStrength", 150) == 100
    assert p.clamp_setting("totalStrength", -5) == 0
    assert p.clamp_setting("encoderDirection", 0) == 1
    assert p.clamp_setting("encoderDirection", -3) == -1


def test_commands():
    assert p.build_command(p.ReportData.COMMAND_SAVE_SETTINGS)[:2] == bytes([0xA3, 0x02])
    with pytest.raises(ValueError):
        p.build_command(p.ReportData.OVERRIDE_DATA)


def test_direct_control():
    report = p.build_direct_control(spring=0.5, constant=-2.0, force_drop=30)
    assert struct.unpack_from("<hhhB", report, 2) == (5000, -10000, 0, 30)


def _wait(cond, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.01)
    return False


def test_link_end_to_end_with_simulator():
    sim = SimulatedWheelBase()
    link = FFBeastLink(device_factory=lambda: sim)
    link.start()
    try:
        assert _wait(lambda: link.connected and link.latest_state is not None)
        events = []
        assert _wait(lambda: (events.append(link.events.get_nowait()) if not link.events.empty() else None)
                     or any(e.kind == "settings" for e in events))
        settings = next(e.data for e in events if e.kind == "settings")
        assert settings["motionRange"] == 900 and settings["polePairs"] == 15

        # szybka seria zmian (suwak) -> do bazy dociera ostatnia wartość
        for v in range(10, 80, 5):
            link.set_setting("totalStrength", v)
        link.set_setting("motionRange", 1080)
        assert _wait(lambda: sim.effects["totalStrength"] == 75 and sim.effects["motionRange"] == 1080)
        assert sim.flash_effects["motionRange"] == 900

        link.run_action("save")
        assert _wait(lambda: sim.flash_effects["motionRange"] == 1080)
    finally:
        link.stop()


def test_spec_matches_protocol():
    # każde pole protokołu ma opis w interfejsie, a profile obejmują tylko efekty
    assert set(SPEC.fields()) == set(p.FIELDS_BY_KEY)
    assert set(SPEC.profile_keys) == {f.key for f in p.EFFECT_FIELDS}
    for prof in SPEC.builtin_profiles.values():
        assert set(prof["settings"]) == set(SPEC.profile_keys)


def test_profiles_store(tmp_path):
    store = Store(tmp_path)
    assert {p_["name"] for p_ in store.profiles(SPEC)} >= set(SPEC.builtin_profiles)
    store.save_profile(SPEC, "Mój", {**DEFAULT_EFFECTS, "totalStrength": 300, "polePairs": 7})
    mine = store.profile(SPEC, "Mój")
    assert mine["settings"]["totalStrength"] == 100  # przycięte do zakresu
    assert "polePairs" not in mine["settings"]       # profile nie ruszają sprzętu
    with pytest.raises(ValueError):
        store.save_profile(SPEC, "iRacing", DEFAULT_EFFECTS)

    out = tmp_path / "x.json"
    store.export_profile(SPEC, "Mój", out)
    assert store.import_profile(SPEC, out) == "Mój (import)"
    assert Store(tmp_path).profile(SPEC, "Mój (import)") is not None


def test_legacy_profiles_are_ffbeast(tmp_path):
    # profiles.json sprzed obsługi OpenFFBoard: klucz = sama nazwa, bez pola firmware
    import json
    (tmp_path / "profiles.json").write_text(json.dumps(
        {"Stary": {"game": "X", "settings": {"totalStrength": 50}}}), encoding="utf-8")
    store = Store(tmp_path)
    assert store.profile(SPEC, "Stary")["settings"] == {"totalStrength": 50}
