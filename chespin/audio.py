import queue
import logging
import sounddevice as sd
import numpy as np

try:
    from scipy import signal
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

logger = logging.getLogger(__name__)

class AudioStreamer:
    """Wrapper to capture microphone audio at native hardware rate (48kHz) and downsample to 16kHz for Vosk."""
    def __init__(self, sample_rate=16000, input_sample_rate=48000, device_index=None, block_size=12000):
        self.sample_rate = sample_rate
        self.input_sample_rate = input_sample_rate
        self.device_index = 2
        self.block_size = block_size
        self.queue = queue.Queue()
        self.stream = None

    def _audio_callback(self, indata, frames, time, status):
        """Callback function for the sounddevice raw input stream."""
        if status:
            logger.warning(f"Audio stream status: {status}")
        
        audio_np = np.frombuffer(indata, dtype=np.int16)
        
        if self.input_sample_rate != self.sample_rate:
            step = self.input_sample_rate // self.sample_rate
            if HAS_SCIPY:
                try:
                    audio_np = signal.decimate(audio_np, step).astype(np.int16)
                except Exception:
                    audio_np = audio_np[::step]
            else:
                audio_np = audio_np[::step]

        self.queue.put(audio_np.tobytes())

    def start(self):
        """Start capturing audio from the input device."""
        if self.stream is not None:
            return

        ratio = max(1, self.input_sample_rate // self.sample_rate)
        stream_block_size = self.block_size * ratio

        logger.info(
            f"Initializing audio capture (Input: {self.input_sample_rate}Hz -> Output: {self.sample_rate}Hz, "
            f"Device: {self.device_index or 'Default'})..."
        )
        try:
            self.stream = sd.RawInputStream(
                samplerate=self.input_sample_rate,
                blocksize=stream_block_size,
                device=self.device_index,
                dtype='int16',
                channels=1,
                callback=self._audio_callback
            )
            self.stream.start()
            logger.info("Audio stream started successfully.")
        except Exception as exc:
            logger.error(f"Failed to start audio stream: {exc}")
            raise exc

    def stop(self):
        """Stop capturing audio and release resources."""
        if self.stream is not None:
            logger.info("Stopping audio stream...")
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                logger.warning(f"Error during audio stream closure: {e}")
            self.stream = None
            logger.info("Audio stream stopped.")

    def get_chunk(self, timeout=None):
        """Get the next raw audio block from the queue."""
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def clear(self):
        """Flush any pending audio blocks in the queue."""
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break

    @staticmethod
    def list_devices():
        """Query and return details of all audio hardware devices."""
        try:
            return str(sd.query_devices())
        except Exception as e:
            return f"Error listing audio devices: {e}"

if __name__ == "__main__":
    # If run directly, list the audio devices to assist users in troubleshooting
    logging.basicConfig(level=logging.INFO)
    print("--- Available Audio Devices ---")
    print(AudioStreamer.list_devices())

