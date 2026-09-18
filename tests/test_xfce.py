import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chespin.screen import ScreenController

def test_xfce_init():
    ctrl = ScreenController(backend="xfce")
    assert ctrl.backend == "xfce"
    print("test_xfce_init: OK")

def test_xfce_auto_detect():
    # 1. Test XDG_CURRENT_DESKTOP = XFCE
    with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "XFCE", "DESKTOP_SESSION": ""}):
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: "/usr/bin/" + cmd if cmd in ["xset", "xfce4-session"] else None
            ctrl = ScreenController(backend="auto")
            assert ctrl.backend == "xfce", f"Expected xfce but got {ctrl.backend}"

    # 2. Test DESKTOP_SESSION = xubuntu
    with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "X-XFCE", "DESKTOP_SESSION": "xubuntu"}):
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: "/usr/bin/" + cmd if cmd in ["xset", "xfce4-session"] else None
            ctrl = ScreenController(backend="auto")
            assert ctrl.backend == "xfce", f"Expected xfce on xubuntu but got {ctrl.backend}"

    # 3. Test that xubuntu is not detected as GNOME
    with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "X-XFCE", "DESKTOP_SESSION": "xubuntu"}):
        ctrl = ScreenController(backend="auto")
        assert ctrl.backend != "gnome", "XFCE/Xubuntu was mistakenly detected as GNOME"

    print("test_xfce_auto_detect: OK")

def test_xfce_turn_on_and_off_xset():
    ctrl = ScreenController(backend="xfce")
    executed_commands = []

    def mock_run(cmd, *args, **kwargs):
        executed_commands.append(cmd)
        result = MagicMock()
        result.stdout = ""
        result.returncode = 0
        return result

    with patch("shutil.which") as mock_which:
        mock_which.side_effect = lambda cmd: "/usr/bin/" + cmd if cmd == "xset" else None
        with patch("subprocess.run", side_effect=mock_run):
            # Turn ON
            assert ctrl.turn_on() is True
            assert ctrl.is_screen_on is True
            # Turn OFF
            assert ctrl.turn_off() is True
            assert ctrl.is_screen_on is False

    on_cmds = [cmd for cmd in executed_commands if "on" in cmd]
    off_cmds = [cmd for cmd in executed_commands if "off" in cmd]
    assert len(on_cmds) > 0, f"No turn-on command executed: {executed_commands}"
    assert len(off_cmds) > 0, f"No turn-off command executed: {executed_commands}"
    assert ["xset", "dpms", "force", "on"] in executed_commands
    assert ["xset", "dpms", "force", "off"] in executed_commands
    print("test_xfce_turn_on_and_off_xset: OK")

def test_xfce_screensaver_fallback():
    ctrl = ScreenController(backend="xfce")
    executed_commands = []

    def mock_run(cmd, *args, **kwargs):
        executed_commands.append(cmd)
        result = MagicMock()
        result.stdout = ""
        result.returncode = 0
        return result

    with patch("shutil.which") as mock_which:
        mock_which.side_effect = lambda cmd: "/usr/bin/" + cmd if cmd == "xfce4-screensaver-command" else None
        with patch("subprocess.run", side_effect=mock_run):
            assert ctrl.turn_on() is True
            assert ctrl.turn_off() is True

    assert ["xfce4-screensaver-command", "--deactivate"] in executed_commands
    assert ["xfce4-screensaver-command", "--activate"] in executed_commands
    print("test_xfce_screensaver_fallback: OK")

def test_xfce_xrandr_fallback():
    ctrl = ScreenController(backend="xfce", output_id="HDMI-1")
    executed_commands = []

    def mock_run(cmd, *args, **kwargs):
        executed_commands.append(cmd)
        result = MagicMock()
        result.stdout = ""
        result.returncode = 0
        return result

    with patch("shutil.which") as mock_which:
        mock_which.side_effect = lambda cmd: "/usr/bin/" + cmd if cmd == "xrandr" else None
        with patch("subprocess.run", side_effect=mock_run):
            assert ctrl.turn_on() is True
            assert ctrl.turn_off() is True

    assert ["xrandr", "--output", "HDMI-1", "--auto"] in executed_commands
    assert ["xrandr", "--output", "HDMI-1", "--off"] in executed_commands
    print("test_xfce_xrandr_fallback: OK")

def test_xfce_environment_display():
    ctrl = ScreenController(backend="xfce")
    with patch.dict(os.environ, {}, clear=True):
        env = ctrl._get_env()
        assert "DISPLAY" in env
        assert env["DISPLAY"] == ":0"
    print("test_xfce_environment_display: OK")

if __name__ == "__main__":
    test_xfce_init()
    test_xfce_auto_detect()
    test_xfce_turn_on_and_off_xset()
    test_xfce_screensaver_fallback()
    test_xfce_xrandr_fallback()
    test_xfce_environment_display()
    print("All XFCE tests passed!")
