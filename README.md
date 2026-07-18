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

Open `config.yaml` to adjust the settings:
*   `wake_word`: The word to listen for (default: `"chespin"`).
*   `screen_backend`: Set to `"auto"` (detects Raspberry Pi system settings automatically), `"wlr-randr"` (Wayland), `"vcgencmd"` (X11/legacy), or `"mock"` (print to console only, useful for testing on Windows/non-Pi).
*   `screen_timeout_seconds`: Time (in seconds) the screen stays on before automatically turning off. Set to `null` to leave it on permanently until turned off manually.

### Start the Daemon

To start the wake-word listener, run:
```bash
python scripts/wake_screen.py
```
Speak your wake word **"CHESPIN"** (or whatever word is configured). You will see logs in the console confirming that the wake word was recognized and that the screen is being activated.

### Turn Screen Off Manually

To manually turn off the HDMI port, execute:
```bash
python scripts/off_screen.py
```

---

## Deploying as a Background Systemd Service (Raspberry Pi)

To keep Chespin running continuously in the background, you can set it up as a systemd service.

1. Create a service file:
   ```bash
   sudo nano /etc/systemd/system/chespin.service
   ```
2. Paste the following configuration (replace `/home/pi/chespin` and `/usr/bin/python3` with your actual project directory and Python executable paths):
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
