import os
import json
import logging
from datetime import datetime, time

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

logger = logging.getLogger(__name__)

class NoDisturbManager:
    """Manages No Disturb (quiet hours) schedule and manual overrides."""

    def __init__(self, config_path=None, state_file=None):
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.config_path = config_path or os.path.join(self.project_root, "config.yaml")
        self.state_file = state_file or os.path.join(self.project_root, ".no_disturb_state.json")
        self._config_cache = None
        self._config_mtime = 0

    def _load_config(self):
        """Load configuration from config.yaml, reloading if modified."""
        if not os.path.isfile(self.config_path) or not HAS_YAML:
            return self._config_cache or {}

        try:
            mtime = os.path.getmtime(self.config_path)
            if self._config_cache is None or mtime != self._config_mtime:
                with open(self.config_path, "r") as f:
                    self._config_cache = yaml.safe_load(f) or {}
                self._config_mtime = mtime
        except Exception as e:
            logger.warning(f"Error loading {self.config_path}: {e}")
            if self._config_cache is None:
                self._config_cache = {}

        return self._config_cache

    def _parse_time_str(self, time_str, default_time):
        """Parse HH:MM string into datetime.time object."""
        if not time_str or not isinstance(time_str, str):
            return default_time
        try:
            parts = time_str.strip().split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            return time(hour=hour, minute=minute)
        except Exception as e:
            logger.warning(f"Invalid time format '{time_str}', using default: {e}")
            return default_time

    def is_schedule_active(self, now=None):
        """Check whether the current time falls inside the configured No Disturb schedule."""
        config = self._load_config()
        enabled = config.get("no_disturb_enabled", False)
        if not enabled:
            return False

        start_str = config.get("no_disturb_start", "22:00")
        end_str = config.get("no_disturb_end", "07:00")

        start_t = self._parse_time_str(start_str, time(22, 0))
        end_t = self._parse_time_str(end_str, time(7, 0))

        if start_t == end_t:
            return False

        current_dt = now or datetime.now()
        curr_t = current_dt.time()

        if start_t < end_t:
            # Same day window (e.g. 13:00 to 15:00)
            return start_t <= curr_t < end_t
        else:
            # Overnight window spanning midnight (e.g. 22:00 to 07:00)
            return curr_t >= start_t or curr_t < end_t

    def get_manual_mode(self):
        """Read manual override status from state file. Returns True, False, or None."""
        if not os.path.isfile(self.state_file):
            return None

        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
            return data.get("manual_override")
        except Exception as e:
            logger.warning(f"Error reading state file {self.state_file}: {e}")
            return None

    def set_manual_mode(self, enabled: bool):
        """Set manual override (True for ON, False for OFF)."""
        data = {
            "manual_override": bool(enabled),
            "last_updated": datetime.now().isoformat(),
            "status": "ON" if enabled else "OFF"
        }
        try:
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"No Disturb manual state set to: {data['status']}")
            return True
        except Exception as e:
            logger.error(f"Failed to write state file {self.state_file}: {e}")
            return False

    def clear_manual_mode(self):
        """Clear manual override and return to schedule."""
        if os.path.isfile(self.state_file):
            try:
                os.remove(self.state_file)
                logger.info("Cleared No Disturb manual state override.")
                return True
            except Exception as e:
                logger.error(f"Failed to remove state file {self.state_file}: {e}")
                return False
        return True

    def get_status(self, now=None):
        """Get tuple of (is_active: bool, reason: str)."""
        manual = self.get_manual_mode()
        sched_active = self.is_schedule_active(now=now)

        if manual is True:
            return True, "Manual Override (ON)"

        if manual is False:
            # If the user ran OFF, but the schedule has passed, auto-clear the override
            # so future scheduled quiet hours can take effect automatically
            if not sched_active:
                self.clear_manual_mode()
                return False, "Inactive"
            return False, "Manual Override (OFF)"

        # No manual override: follow schedule
        if sched_active:
            config = self._load_config()
            start_str = config.get("no_disturb_start", "22:00")
            end_str = config.get("no_disturb_end", "07:00")
            return True, f"Schedule Active ({start_str} - {end_str})"

        return False, "Inactive"

    def is_active(self, now=None) -> bool:
        """Convenience method returning boolean indicating if No Disturb is active."""
        active, _ = self.get_status(now=now)
        return active
