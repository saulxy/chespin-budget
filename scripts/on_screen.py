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

def main():
    config_path = os.path.join(project_root, "config.yaml")
    backend = "auto"
    output_id = "HDMI-A-1"
    
    # Load configuration if available
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                if config:
                    backend = config.get("screen_backend", "auto")
                    output_id = config.get("display_output_id", "HDMI-A-1")
        except Exception as e:
            logger.warning(f"Could not read config.yaml ({e}). Proceeding with default values.")

    logger.info(f"Triggering screen ON command via backend: '{backend}'...")
    try:
        screen_controller = ScreenController(backend=backend, output_id=output_id)
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
