import os
import sys
import time
from datetime import datetime, timedelta
import yaml
import logging
import signal

# Add the project root folder to sys.path so we can import the 'chespin' module structure
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from chespin.audio import AudioStreamer
from chespin.screen import ScreenController
from chespin.detector.vosk_detector import VoskWakeWordDetector

# Initialize Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("chespin_daemon")

# Flag to manage main execution loop
running = True

def handle_shutdown(sig, frame):
    """Gracefully handles termination signals."""
    global running
    logger.info("Termination signal received. Shutting down daemon...")
    running = False

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

def get_next_hourly_trigger(now=None):
    """Computes the timestamp for the top of the next hour."""
    if now is None:
        now = datetime.now()
    return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

def main():
    logger.info("Starting Chespin Wake-Word screen activation daemon...")
    
    # 1. Load configuration
    config_path = os.path.join(project_root, "config.yaml")
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found at: {config_path}")
        sys.exit(1)
        
    with open(config_path, "r") as f:
        try:
            config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error parsing config.yaml: {e}")
            sys.exit(1)
            
    wake_word_enabled = config.get("wake_word_enabled", True)
    wake_word = config.get("wake_word", "chespin")
    if wake_word and isinstance(wake_word, str):
        wake_word = wake_word.strip().lower()
    else:
        wake_word = "chespin"
    model_path = config.get("vosk_model_path", "models/vosk-model-small-en-us-0.15")
    device_index = config.get("audio_device_index", None)
    backend = config.get("screen_backend", "auto")
    output_id = config.get("display_output_id", "HDMI-A-1")
    timeout = config.get("screen_timeout_seconds", 60)
    sound_file = config.get("screen_on_sound", config.get("sound_file", "wake.wav"))
    hourly_enabled = config.get("hourly_routine_enabled", True)
    hourly_duration = config.get("hourly_routine_duration_seconds", 600)
    
    # Validate that at least one activation method is enabled
    if not wake_word_enabled and not hourly_enabled:
        logger.error(
            "Configuration error: Both wake word listening (wake_word_enabled) and "
            "hourly routine (hourly_routine_enabled) are disabled. "
            "At least one must be enabled to run the daemon."
        )
        sys.exit(1)
        
    # 2. Check for speech model existence if wake word is enabled
    if wake_word_enabled:
        # Resolve relative model path to absolute project root path
        if not os.path.isabs(model_path):
            model_path = os.path.join(project_root, model_path)
            
        if not os.path.exists(model_path):
            logger.error("=" * 70)
            logger.error(f"CRITICAL ERROR: Vosk speech model not found at '{model_path}'")
            logger.error("Please download the small English model and extract it to that location.")
            logger.error("Download URL: https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
            logger.error("Refer to the README.md file in the project folder for instructions.")
            logger.error("=" * 70)
            sys.exit(1)

    # 3. Instantiate modules
    detector = None
    streamer = None
    try:
        screen_controller = ScreenController(backend=backend, output_id=output_id, sound_file=sound_file)
        if wake_word_enabled:
            detector = VoskWakeWordDetector(wake_word=wake_word, model_path=model_path)
            streamer = AudioStreamer(device_index=device_index)
    except Exception as e:
        logger.exception(f"Failed to initialize core components: {e}")
        sys.exit(1)

    # Turn the screen off initially on start, waiting for the wake word or scheduled routine
    logger.info("Initializing screen state (turning OFF)...")
    screen_controller.turn_off()
    screen_is_on = False
    screen_on_until = 0.0

    # Hourly routine setup
    next_hourly_trigger = get_next_hourly_trigger() if hourly_enabled else None
    if hourly_enabled:
        logger.info(
            f"Hourly routine enabled: Next screen activation at {next_hourly_trigger.strftime('%Y-%m-%d %H:%M:%S')} "
            f"for {hourly_duration}s."
        )
    else:
        logger.info("Hourly routine is disabled by configuration.")

    # Start audio stream if wake word is enabled
    if wake_word_enabled and streamer:
        try:
            streamer.start()
        except Exception as e:
            logger.error("Fatal: Unable to start audio recording stream.")
            sys.exit(1)
        logger.info(f"Chespin is running. Listening for the wake-word '{wake_word.upper()}'...")
    else:
        logger.info("Wake-word listening is disabled by configuration.")
    
    while running:
        if wake_word_enabled and streamer:
            # Retrieve audio chunks. Timeout prevents the loop from blocking and locking shutdown signals
            chunk = streamer.get_chunk(timeout=0.1)
            
            if chunk:
                try:
                    if detector.process_audio(chunk):
                        logger.info(f"Wake-word '{wake_word.upper()}' detected!")
                        screen_controller.turn_on()
                        screen_is_on = True
                        
                        if timeout:
                            screen_on_until = max(screen_on_until, time.time() + timeout)
                            logger.info(f"Screen will remain active for {timeout} seconds.")
                        else:
                            screen_on_until = float('inf')
                            logger.info("Screen timeout is disabled. Screen will remain on indefinitely.")
                except Exception as e:
                    logger.error(f"Error processing audio data chunk: {e}")
        else:
            time.sleep(0.5)

        # Check hourly routine trigger
        if hourly_enabled and datetime.now() >= next_hourly_trigger:
            logger.info(
                f"Hourly routine triggered ({datetime.now().strftime('%H:%M:%S')}). "
                f"Turning screen ON for {hourly_duration} seconds..."
            )
            screen_controller.turn_on()
            screen_is_on = True
            screen_on_until = max(screen_on_until, time.time() + hourly_duration)
            next_hourly_trigger = get_next_hourly_trigger()
            logger.info(f"Next hourly activation scheduled for {next_hourly_trigger.strftime('%Y-%m-%d %H:%M:%S')}.")

        # Handle screen timeout check
        if screen_is_on and screen_on_until > 0 and time.time() > screen_on_until:
            logger.info("Screen active timeout reached. Powering screen off...")
            screen_controller.turn_off()
            screen_is_on = False
            screen_on_until = 0.0
            
    # Clean cleanup on exit
    if streamer:
        streamer.stop()
    logger.info("Chespin daemon stopped.")

if __name__ == "__main__":
    main()
