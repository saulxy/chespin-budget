import queue
import logging
import sounddevice as sd

logger = logging.getLogger(__name__)

class AudioStreamer:
    """Wrapper to capture microphone audio using sounddevice and pipe it safely into queues."""
    def __init__(self, sample_rate=16000, device_index=None, block_size=4000):
        self.sample_rate = sample_rate
        self.device_index = device_index
        self.block_size = block_size
        self.queue = queue.Queue()
        self.stream = None

    def _audio_callback(self, indata, frames, time, status):
        """Callback function for the sounddevice raw input stream."""
        if status:
            logger.warning(f"Audio stream status: {status}")
        self.queue.put(bytes(indata))

    def start(self):
        """Start capturing audio from the input device."""
        if self.stream is not None:
            return
        
        logger.info(f"Initializing audio capture (Samplerate: {self.sample_rate}Hz, Device: {self.device_index or 'Default'})...")
        try:
            self.stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                device=self.device_index,
                dtype='int16',
                channels=1,
                callback=self._audio_callback
            )
            self.stream.start()
            logger.info("Audio stream started successfully.")
        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}")
            logger.error("Please verify that your microphone is plugged in, and verify available devices using audio.py's list_devices().")
            raise

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
