import os
import sys
import yaml
import logging

# Add the project root to sys.path so we can import 'chespin' library components
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from chespin.screen import ScreenController
from chespin.no_disturb import NoDisturbManager

# Initialize Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("no_disturb")

def print_usage():
    """Print command-line usage information."""
    print(
        "Usage: python scripts/no_disturb.py [ON | OFF | STATUS]\n\n"
        "Parameters:\n"
        "  ON     - Activate No Disturb mode (powers off display, disables wake screen and audio)\n"
        "  OFF    - Deactivate No Disturb mode (resumes configured wake screen and audio routines)\n"
        "  STATUS - View the current No Disturb state and schedule status\n"
    )

def main():
    if len(sys.argv) < 2 or sys.argv[1].lower() in ["-h", "--help"]:
        print_usage()
        sys.exit(1)

    action = sys.argv[1].strip().upper()
    if action not in ["ON", "OFF", "STATUS"]:
        logger.error(f"Invalid parameter '{sys.argv[1]}'. Parameter must be 'ON', 'OFF', or 'STATUS'.")
        print_usage()
        sys.exit(1)

    manager = NoDisturbManager()

    if action == "STATUS":
        active, reason = manager.get_status()
        state_label = "ACTIVE (Quiet Mode)" if active else "INACTIVE (Normal Mode)"
        print("=" * 50)
        print(f" Chespin No Disturb Status: {state_label}")
        print(f" Details: {reason}")
        print("=" * 50)
        return

    # Load backend and output_id from config for screen control
    config_path = os.path.join(project_root, "config.yaml")
    backend = "auto"
    output_id = "HDMI-A-1"
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f) or {}
                backend = config.get("screen_backend", "auto")
                output_id = config.get("display_output_id", "HDMI-A-1")
        except Exception as e:
            logger.warning(f"Could not read config.yaml ({e}). Proceeding with default display values.")

    if action == "ON":
        logger.info("Enabling No Disturb mode...")
        success = manager.set_manual_mode(True)
        if not success:
            logger.error("Failed to persist No Disturb mode state.")
            sys.exit(1)

        # Power off screen immediately to ensure quiet state
        try:
            screen_controller = ScreenController(backend=backend, output_id=output_id)
            screen_controller.turn_off()
        except Exception as e:
            logger.warning(f"Could not power off screen during No Disturb activation: {e}")

        logger.info("No Disturb mode is now ON. Screen turned OFF. Wake screen and audio are disabled.")

    elif action == "OFF":
        logger.info("Disabling No Disturb mode...")
        success = manager.set_manual_mode(False)
        if not success:
            logger.error("Failed to persist No Disturb mode state.")
            sys.exit(1)

        logger.info("No Disturb mode is now OFF. Configured wake-up screen and audio functionality resumed.")

if __name__ == "__main__":
    main()
