import os
import glob
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
            # 1. Try with configured output_id + --preferred (fixes 'failed to apply configuration')
            success = self._run_command(["wlr-randr", "--output", self.output_id, "--on", "--preferred"])
            
            # 2. Try plain --on if --preferred fails
            if not success:
                logger.warning(f"wlr-randr --on --preferred failed for '{self.output_id}'. Retrying plain --on...")
                success = self._run_command(["wlr-randr", "--output", self.output_id, "--on"])
            
            # 3. If configured output failed, search for available wlr-randr outputs and try them
            if not success:
                detected_outputs = self._get_wlr_outputs()
                for out_id in detected_outputs:
                    if out_id != self.output_id:
                        logger.info(f"Retrying wlr-randr on detected output '{out_id}'...")
                        success = self._run_command(["wlr-randr", "--output", out_id, "--on", "--preferred"])
                        if success:
                            self.output_id = out_id
                            break
            
            # 4. Fallback to vcgencmd if available
            if not success and shutil.which("vcgencmd"):
                logger.warning("wlr-randr commands failed. Attempting fallback via vcgencmd...")
                success = self._run_command(["vcgencmd", "display_power", "1"])
                
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
            
            # If configured output_id failed, try detected outputs
            if not success:
                detected_outputs = self._get_wlr_outputs()
                for out_id in detected_outputs:
                    if out_id != self.output_id:
                        logger.info(f"Retrying wlr-randr off on detected output '{out_id}'...")
                        success = self._run_command(["wlr-randr", "--output", out_id, "--off"])
                        if success:
                            self.output_id = out_id
                            break
                            
            if not success and shutil.which("vcgencmd"):
                logger.warning("wlr-randr --off failed. Attempting fallback via vcgencmd...")
                success = self._run_command(["vcgencmd", "display_power", "0"])
                
        elif self.backend == "vcgencmd":
            success = self._run_command(["vcgencmd", "display_power", "0"])
        elif self.backend == "mock":
            logger.info("[MOCK] Screen power set to: OFF")
            success = True

        if success:
            self.is_screen_on = False
        return success

    def _get_env(self):
        """Prepare environment variables needed for Wayland/wlr-randr."""
        env = os.environ.copy()

        # Check if XDG_RUNTIME_DIR is already set and valid
        xdg_dir = env.get("XDG_RUNTIME_DIR")
        if not xdg_dir or not os.path.isdir(xdg_dir):
            candidates = []
            if hasattr(os, "getuid"):
                candidates.append(f"/run/user/{os.getuid()}")
            candidates.extend(["/run/user/1000", "/run/user/1001"])
            try:
                candidates.extend(glob.glob("/run/user/*"))
            except Exception:
                pass

            resolved_dir = None
            detected_socket = None

            # First pass: search for an existing directory containing a wayland-* socket
            for c in candidates:
                if os.path.isdir(c):
                    try:
                        sockets = glob.glob(os.path.join(c, "wayland-*"))
                        if sockets:
                            resolved_dir = c
                            detected_socket = os.path.basename(sockets[0])
                            break
                    except Exception:
                        pass

            # Second pass: if no socket found yet, pick the first valid candidate directory
            if not resolved_dir:
                for c in candidates:
                    if os.path.isdir(c):
                        resolved_dir = c
                        break

            if resolved_dir:
                env["XDG_RUNTIME_DIR"] = resolved_dir
                logger.debug(f"Auto-configured XDG_RUNTIME_DIR={resolved_dir}")
                if detected_socket and "WAYLAND_DISPLAY" not in env:
                    env["WAYLAND_DISPLAY"] = detected_socket
                    logger.debug(f"Auto-configured WAYLAND_DISPLAY={detected_socket}")

        # Ensure WAYLAND_DISPLAY has a default fallback if missing
        if "WAYLAND_DISPLAY" not in env:
            env["WAYLAND_DISPLAY"] = "wayland-0"

        return env

    def _get_wlr_outputs(self):
        """Query wlr-randr for available output display names."""
        try:
            res = subprocess.run(["wlr-randr"], env=self._get_env(), capture_output=True, text=True)
            outputs = []
            for line in res.stdout.splitlines():
                if line and not line.startswith(" ") and not line.startswith("\t"):
                    parts = line.split()
                    if parts:
                        outputs.append(parts[0])
            return outputs
        except Exception:
            return []

    def _run_command(self, cmd):
        """Execute a subprocess command and handle logging/exceptions."""
        try:
            logger.debug(f"Executing system command: {' '.join(cmd)}")
            result = subprocess.run(cmd, env=self._get_env(), capture_output=True, text=True, check=True)
            if result.stdout:
                logger.info(f"Command output: {result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.strip() if e.stderr else str(e)
            logger.error(f"Command failed (code {e.returncode}): {err_msg}")
            if "XDG_RUNTIME_DIR" in err_msg or "wayland" in err_msg.lower():
                logger.warning(
                    "Hint: Wayland environment variables (XDG_RUNTIME_DIR or WAYLAND_DISPLAY) may be missing or inaccessible. "
                    "If running under systemd, add 'Environment=XDG_RUNTIME_DIR=/run/user/1000' and "
                    "'Environment=WAYLAND_DISPLAY=wayland-0' to your service unit file."
                )
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
