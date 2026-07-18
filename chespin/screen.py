import subprocess
import shutil
import logging

logger = logging.getLogger(__name__)

class ScreenController:
    """Controls HDMI screen power on Raspberry Pi using various command line interfaces."""
    
    def __init__(self, backend="auto", output_id="HDMI-A-1"):
        self.output_id = output_id
        self.backend = self._resolve_backend(backend)
        self.is_screen_on = True  # Initial assumption
        logger.info(f"ScreenController initialized. Using '{self.backend}' backend.")

    def _resolve_backend(self, backend):
        """Determine which backend to use depending on system tools available."""
        if backend != "auto":
            return backend

        # Auto-detect tools on the system PATH
        if shutil.which("wlr-randr") is not None:
            return "wlr-randr"
        elif shutil.which("vcgencmd") is not None:
            return "vcgencmd"
        else:
            logger.warning("Neither 'wlr-randr' nor 'vcgencmd' was found in PATH. Falling back to 'mock' mode.")
            return "mock"

    def turn_on(self):
        """Power ON the screen."""
        logger.info("Command: Turn Screen ON")
        success = False
        
        if self.backend == "wlr-randr":
            success = self._run_command(["wlr-randr", "--output", self.output_id, "--on"])
        elif self.backend == "vcgencmd":
            success = self._run_command(["vcgencmd", "display_power", "1"])
        elif self.backend == "mock":
            logger.info("[MOCK] Screen power set to: ON")
            success = True
            
        if success:
            self.is_screen_on = True
        return success

    def turn_off(self):
        """Power OFF the screen."""
        logger.info("Command: Turn Screen OFF")
        success = False
        
        if self.backend == "wlr-randr":
            success = self._run_command(["wlr-randr", "--output", self.output_id, "--off"])
        elif self.backend == "vcgencmd":
            success = self._run_command(["vcgencmd", "display_power", "0"])
        elif self.backend == "mock":
            logger.info("[MOCK] Screen power set to: OFF")
            success = True

        if success:
            self.is_screen_on = False
        return success

    def _run_command(self, cmd):
        """Execute a subprocess command and handle logging/exceptions."""
        try:
            logger.debug(f"Executing system command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            if result.stdout:
                logger.info(f"Command output: {result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed (code {e.returncode}): {e.stderr.strip()}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error running command '{cmd[0]}': {e}")
            return False

if __name__ == "__main__":
    # Test execution
    logging.basicConfig(level=logging.INFO)
    controller = ScreenController()
    print(f"Detected backend: {controller.backend}")
    controller.turn_on()
    controller.turn_off()
