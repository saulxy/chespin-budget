# Chespin (Wake-Word Screen Activation)

Chespin is an offline, low-resource Python daemon designed for the Raspberry Pi. It runs continuously in the background, listening for the wake word **"CHESPIN"**, and turns on an HDMI-connected display whenever the word is detected.

The screen automatically goes to sleep after a configured timeout period, conserving energy.

---

## Folder Structure

```text
chespin/
├── README.md                  # This file
├── requirements.txt           # Python packages required
├── config.yaml                # Main configuration settings
├── resource/                  # Audio notifications and assets
│   └── wake.wav               # Wake chime audio played on screen turn-on
├── chespin/                   # Core application package
│   ├── __init__.py
│   ├── audio.py               # Sound capture and stream abstraction
│   ├── screen.py              # HDMI hardware interfacing and commands
│   └── detector/              # Audio analysis components
│       ├── __init__.py
│       ├── base.py            # Base detector class
│       └── vosk_detector.py   # Vosk speech recognition backend
└── scripts/                   # User-executable command-line utilities
    ├── wake_screen.py         # The primary background listener script
    ├── on_screen.py           # A script to manually turn on the display
    └── off_screen.py          # A script to manually shut off the display
```

---

## Setup & Installation

### 1. Prerequisites (PortAudio Setup)

This project requires **PortAudio** for audio capture through Python's `sounddevice` library.

#### On Raspberry Pi / Linux:
```bash
sudo apt update
sudo apt install -y libportaudio2 python3-dev
```

#### On macOS:
```bash
brew install portaudio
```

#### On Windows:
`sounddevice` installs pre-built PortAudio binaries automatically when installing via `pip`.

---

### 2. Download the Offline Speech Recognition Model (Vosk) 

Chespin uses **Vosk** for offline keyword spotting. You must download a small English acoustic model:

1. Download the small English model: **[vosk-model-small-en-us-0.15.zip](https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip)** (approx. 40MB). (Note: there are many models in different languages, all should work but this one is the smallest)
2. Create a folder named `models` in the root of this project:
   ```bash
   mkdir models
   ```
3. Extract the downloaded zip file into the `models` directory. The structure should look like:
   ```text
   chespin/
   └── models/
       └── vosk-model-small-en-us-0.15/
           ├── am/
           ├── graph/
           ├── ivector/
           └── ...
   ```

---

### 3. Install Python Dependencies

Run the following command to install the required libraries:
```bash
pip install -r requirements.txt
```

---

## Running Chespin

### Configuration

*   `wake_word_enabled`: Enable or disable wake-word voice listening (default: `true`).
*   `wake_word`: The word to listen for (default: `"chespin"`).
*   `screen_backend`: Set to:
    *   `"auto"`: Automatically detects available tools (GNOME/Mutter, XFCE/xset, `wlr-randr`, `vcgencmd`, fallback to mock).
    *   `"gnome"`: GNOME Mutter DisplayConfig via D-Bus (compatible with **Ubuntu 26.04**, Ubuntu 24.04, Debian GNOME, Fedora).
    *   `"xfce"`: XFCE DPMS / `xset` / screensaver / `xrandr` (compatible with **XFCE**, Xubuntu, Debian XFCE, Raspberry Pi OS XFCE).
    *   `"wlr-randr"`: Wayland wlroots HDMI control (Raspberry Pi OS Bookworm with labwc/wayfire).
    *   `"vcgencmd"`: X11/legacy Raspberry Pi HDMI control.
    *   `"mock"`: Test mode (logs screen state changes to console without actual hardware calls).
*   `screen_on_sound`: WAV sound file played when the screen turns on (default: `"wake.wav"` located in `resource/`). Set to `null` to disable.
*   `screen_timeout_seconds`: Time (in seconds) the screen stays on after wake word detection before automatically turning off. Set to `null` to leave it on permanently until turned off manually.
*   `hourly_routine_enabled`: Automatically power on the screen every hour at the top of the hour (default: `true`).
*   `hourly_routine_duration_seconds`: Duration (in seconds) the screen remains on during each hourly cycle before turning off (default: `600` = 10 minutes).

> [!NOTE]
> At least one activation method (`wake_word_enabled` or `hourly_routine_enabled`) must be set to `true` for `wake_screen.py` to run. If both are disabled, the script will exit with an error.


### Start the Daemon

To start the wake-word listener, run:
```bash
python scripts/wake_screen.py
```
Speak your wake word **"CHESPIN"** (or whatever word is configured). You will see logs in the console confirming that the wake word was recognized and that the screen is being activated.

### Turn Screen On / Off Manually

Both scripts support command-line arguments (run with `-h` or `--help` to view options):

*   **Turn on the screen:**
    ```bash
    # Uses backend configured in config.yaml (or auto-detected)
    python scripts/on_screen.py

    # Explicitly specify backend (e.g. GNOME or XFCE)
    python scripts/on_screen.py --backend xfce
    python scripts/on_screen.py --backend gnome

    # Optional: customize sound or output
    python scripts/on_screen.py --backend xfce --sound wake.wav
    ```

*   **Turn off the screen:**
    ```bash
    # Uses backend configured in config.yaml (or auto-detected)
    python scripts/off_screen.py

    # Explicitly specify backend
    python scripts/off_screen.py --backend xfce
    python scripts/off_screen.py --backend gnome
    ```

---

## Deploying as a Background Systemd Service

Depending on your operating system and desktop environment, choose the deployment method below:

### Option A: Systemd User Service (Recommended for Desktop Sessions)

Running as a **user service** is recommended because it runs inside your user session, natively inheriting access to your desktop session, D-Bus session bus, and microphone devices without requiring `sudo`.

1. Create a user systemd service directory and file:
   ```bash
   mkdir -p ~/.config/systemd/user
   nano ~/.config/systemd/user/chespin.service
   ```

2. **For GNOME (Ubuntu 24.04 / 26.04 / Wayland):**
   ```ini
   [Unit]
   Description=Chespin Wake Word Screen Activation Daemon
   After=graphical-session.target sound.target
   PartOf=graphical-session.target

   [Service]
   Type=simple
   WorkingDirectory=%h/chespin
   ExecStart=%h/chespin/.venv/bin/python scripts/wake_screen.py
   Restart=always
   RestartSec=5
   Environment=PYTHONUNBUFFERED=1

   [Install]
   WantedBy=graphical-session.target
   ```

3. **For XFCE (Xubuntu / Debian XFCE / X11):**
   > [!NOTE]
   > XFCE sessions run under X11 and may not trigger systemd's `graphical-session.target`. Therefore, `WantedBy=default.target` and `Environment=DISPLAY=:0` should be used:

   ```ini
   [Unit]
   Description=Chespin Wake Word Screen Activation Daemon
   After=sound.target

   [Service]
   Type=simple
   WorkingDirectory=%h/chespin
   ExecStart=%h/chespin/.venv/bin/python scripts/wake_screen.py
   Restart=always
   RestartSec=5
   Environment=PYTHONUNBUFFERED=1
   Environment=DISPLAY=:0

   [Install]
   WantedBy=default.target
   ```
   *(Note: Chespin's internal engine will also automatically fallback to `DISPLAY=:0` and locate `~/.Xauthority` if they are omitted from the service file).*

4. Enable and start the user service (no `sudo` required):
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable chespin.service
   systemctl --user start chespin.service
   ```

5. View service logs:
   ```bash
   journalctl --user -u chespin.service -f
   ```

6. *(Optional)* To allow the user service to start on boot even before you log into the desktop seat:
   ```bash
   loginctl enable-linger $USER
   ```

---

### Option B: System-Wide Service (For Raspberry Pi OS / Kiosk / Root)

For dedicated appliances, kiosks, or headless setups running under `/etc/systemd/system/`:

1. Create a service file:
   ```bash
   sudo nano /etc/systemd/system/chespin.service
   ```
2. Paste the following configuration (replace `pi` with your actual username, and adjust paths as needed):
   ```ini
   [Unit]
   Description=Chespin Wake Word Screen Activation Daemon
   After=network.target sound.target

   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/chespin
   ExecStart=/home/pi/chespin/.venv/bin/python scripts/wake_screen.py
   Restart=always
   RestartSec=5
   Environment=PYTHONUNBUFFERED=1

   # Required for Wayland / wlr-randr and GNOME D-Bus display control:
   # Replace 1000 with your user's UID (check using: id -u $USER)
   Environment=XDG_RUNTIME_DIR=/run/user/1000
   Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
   Environment=WAYLAND_DISPLAY=wayland-0

   # Required for XFCE / X11 display control:
   Environment=DISPLAY=:0
   Environment=XAUTHORITY=/home/pi/.Xauthority

   [Install]
   WantedBy=multi-user.target
   ```
3. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable chespin.service
   sudo systemctl start chespin.service
   ```
4. View service logs:
   ```bash
   sudo journalctl -u chespin.service -f
   ```
