import os
import sys
import yaml
import logging

# Add the project root to sys.path so we can import 'chespin' library components
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from chespin.screen import ScreenController

# Initialize Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("on_screen")

import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Turn HDMI Screen ON")
    parser.add_argument(
        "-b", "--backend",
        choices=["auto", "gnome", "xfce", "wlr-randr", "vcgencmd", "mock"],
        default=None,
        help="Screen control backend (auto, gnome, xfce, wlr-randr, vcgencmd, mock)"
    )
    parser.add_argument(
        "-o", "--output",
        dest="output_id",
        default=None,
        help="Display output ID (e.g. HDMI-A-1, primarily used for wlr-randr)"
    )
    parser.add_argument(
        "-s", "--sound",
        dest="sound_file",
        default=None,
        help="Path or filename of sound file to play on wake"
    )
    return parser.parse_args()

def main():
    args = parse_args()
    config_path = os.path.join(project_root, "config.yaml")
    backend = "auto"
    output_id = "HDMI-A-1"
    sound_file = None
    
    # Load configuration if available
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                if config:
                    backend = config.get("screen_backend", "auto")
                    output_id = config.get("display_output_id", "HDMI-A-1")
                    sound_file = config.get("screen_on_sound", config.get("sound_file", None))
        except Exception as e:
            logger.warning(f"Could not read config.yaml ({e}). Proceeding with default values.")

    # Command line arguments override config file values if provided
    if args.backend is not None:
        backend = args.backend
    if args.output_id is not None:
        output_id = args.output_id
    if args.sound_file is not None:
        sound_file = args.sound_file

    logger.info(f"Triggering screen ON command via backend: '{backend}'...")
    try:
        screen_controller = ScreenController(backend=backend, output_id=output_id, sound_file=sound_file)
        if screen_controller.turn_on():
            logger.info("Screen turned ON successfully.")
        else:
            logger.error("Screen controller command reported a failure.")
            sys.exit(1)
    except Exception as e:
        logger.exception(f"An error occurred while attempting to turn the screen ON: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
