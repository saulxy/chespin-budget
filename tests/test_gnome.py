import os
import sys
import shutil
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chespin.screen import ScreenController

def test_gnome_init():
    ctrl = ScreenController(backend="gnome")
    assert ctrl.backend == "gnome"
    print("test_gnome_init: OK")

def test_gnome_auto_detect():
    with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "ubuntu:GNOME"}):
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: "/usr/bin/" + cmd if cmd == "busctl" else None
            ctrl = ScreenController(backend="auto")
            assert ctrl.backend == "gnome"
            print("test_gnome_auto_detect: OK")

def test_gnome_turn_on_and_off():
    ctrl = ScreenController(backend="gnome")
    executed_commands = []

    def mock_run(cmd, *args, **kwargs):
        executed_commands.append(cmd)
        result = MagicMock()
        result.stdout = ""
        result.returncode = 0
        return result

    with patch("shutil.which") as mock_which:
        mock_which.side_effect = lambda cmd: "/usr/bin/" + cmd if cmd in ["busctl", "gdbus"] else None
        with patch("subprocess.run", side_effect=mock_run):
            # Turn ON
            assert ctrl.turn_on() is True
            assert ctrl.is_screen_on is True
            # Turn OFF
            assert ctrl.turn_off() is True
            assert ctrl.is_screen_on is False

    # Check commands executed
    on_cmds = [cmd for cmd in executed_commands if "0" in cmd]
    off_cmds = [cmd for cmd in executed_commands if "1" in cmd or "3" in cmd]
    assert len(on_cmds) > 0, "No turn-on command executed"
    assert len(off_cmds) > 0, "No turn-off command executed"
    print("test_gnome_turn_on_and_off: OK")

if __name__ == "__main__":
    test_gnome_init()
    test_gnome_auto_detect()
    test_gnome_turn_on_and_off()
    print("All tests passed!")
