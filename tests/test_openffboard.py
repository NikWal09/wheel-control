import time

import pytest

from ddcontrol.openffboard import protocol as p
from ddcontrol.openffboard.driver import SPEC, OpenFFBoardLink
from ddcontrol.openffboard.simulator import SimulatedOpenFFBoard


def test_reply_parser_handles_split_and_multiline_replies():
    parser = p.ReplyParser()
    assert parser.feed(b"[axis.0.power?|50") == []
    replies = parser.feed(b"00]\n[axis.0.degrees=900|OK]\n[sys.0.lsactive?|Axis:axis:0:2561:0\nFX:fx:0:2562:0]\n")
    assert [(r.key, r.value) for r in replies[:2]] == [("axis.0.power", "5000"), ("axis.0.degrees", "OK")]
    assert replies[0].int_value() == 5000 and not replies[0].is_set
    assert replies[1].is_set and replies[1].ok
    assert p.parse_lsactive(replies[2].value) == {"axis.0", "fx.0"}


def test_reply_values():
    assert p.Reply("axis.0.power=1|ERR", "ERR").ok is False
    assert p.Reply("sys.0.hwtype?", "MKS:3").int_value() is None
    assert p.Reply("sys.0.devid?", "1043:4096").int_value() == 1043
    assert p.Reply("x.0.y?", "x1F").int_value() is None


def test_command_batches_respect_length_limit():
    cmds = [f"axis.0.power={i}" for i in range(40)]
    chunks = p.batches(cmds)
    assert all(len(c) <= p.MAX_BATCH_CHARS + 1 and c.endswith(b"\n") for c in chunks)
    assert b";".join(c.strip() for c in chunks).decode().split(";") == cmds


def test_parse_command_matches_firmware_syntax():
    assert p.parse_command("axis.0.power?") == ("axis", 0, "power", "get", None)
    assert p.parse_command("axis.0.power=-12") == ("axis", 0, "power", "set", -12)
    assert p.parse_command("fx.0.spring!") == ("fx", 0, "spring", "info", None)
    assert p.parse_command("garbage") is None


def test_profiles_use_known_fields():
    fields = SPEC.fields()
    for prof in SPEC.builtin_profiles.values():
        assert set(prof["settings"]) == set(SPEC.profile_keys)
        for key, value in prof["settings"].items():
            assert fields[key].clamp(value) == value


def _wait(cond, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.01)
    return False


def _events(link):
    out = []
    while not link.events.empty():
        out.append(link.events.get_nowait())
    return out


def _reopening(sim):
    """Fabryka portu: po restarcie płytka znów pojawia się w systemie."""
    def factory():
        sim.closed = False
        return sim
    return factory


@pytest.fixture
def sim_link():
    sim = SimulatedOpenFFBoard()
    link = OpenFFBoardLink(port_factory=_reopening(sim))
    link.start()
    assert _wait(lambda: link.connected and link.latest_state is not None)
    yield sim, link
    link.stop()


def test_handshake_reads_identity_and_settings(sim_link):
    sim, link = sim_link
    events = _events(link)
    info = next(e.data for e in events if e.kind == "connected")
    settings = next(e.data for e in events if e.kind == "settings")
    assert info.version == "1.17.1" and "xdrive.0" in info.capabilities
    assert settings["axis.0.degrees"] == 900 and settings["xdrive.0.poles"] == 15
    assert set(settings) == set(SPEC.fields())


def test_settings_are_coalesced_and_saved(sim_link):
    sim, link = sim_link
    for v in range(10, 200, 10):
        link.set_setting("fx.0.spring", v)
    link.set_setting("axis.0.degrees", 1080)
    assert _wait(lambda: sim.values["fx.0.spring"] == 190 and sim.values["axis.0.degrees"] == 1080)
    sent = [c for c in sim.received if c.startswith("fx.0.spring=")]
    assert len(sent) < 19  # nie każda pozycja suwaka leci do płytki
    assert sim.flash["axis.0.degrees"] == 900
    link.run_action("save")
    assert _wait(lambda: sim.flash["axis.0.degrees"] == 1080)


def test_live_state_is_normalized(sim_link):
    sim, link = sim_link
    assert _wait(lambda: link.latest_state and abs(link.latest_state.position) > 0.01)
    state = link.latest_state
    assert -1 <= state.position <= 1 and -1 <= state.torque <= 1


def test_actions_send_expected_commands(sim_link):
    sim, link = sim_link
    for action in ("zero", "calibrate", "test"):
        link.run_action(action)
    assert _wait(lambda: {"axis.0.zeroenc?", "xdrive.0.cal?", "xdrive.0.test?"} <= set(sim.received))


def test_external_change_is_picked_up(sim_link):
    """Zmiana zrobiona innym interfejsem (np. HID) przychodzi jako niezamówiona odpowiedź."""
    sim, link = sim_link
    _events(link)
    sim._reply("[axis.0.esgain?|200]\n")
    assert _wait(lambda: any(e.kind == "settings" and e.data.get("axis.0.esgain") == 200
                             for e in _events(link)))


def test_firmware_without_xdrive_class():
    sim = SimulatedOpenFFBoard(with_xdrive=False)
    link = OpenFFBoardLink(port_factory=lambda: sim)
    link.start()
    try:
        assert _wait(lambda: link.connected)
        events = _events(link)
        info = next(e.data for e in events if e.kind == "connected")
        settings = next(e.data for e in events if e.kind == "settings")
        assert "xdrive.0" not in info.capabilities
        assert not any(k.startswith("xdrive.") for k in settings)  # brak odpowiedzi = brak pola
        assert "axis.0.power" in settings
    finally:
        link.stop()


def test_reboot_restores_flash_and_reconnects(sim_link):
    sim, link = sim_link
    link.set_setting("axis.0.power", 3000)
    assert _wait(lambda: sim.values["axis.0.power"] == 3000)
    link.run_action("reboot")
    assert _wait(lambda: not link.connected)
    assert _wait(lambda: link.connected, timeout=4)
    assert sim.values["axis.0.power"] == 12000
