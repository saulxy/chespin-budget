from abc import ABC, abstractmethod

class BaseWakeWordDetector(ABC):
    """Abstract base class for all wake-word detectors."""
    
    def __init__(self, wake_word: str):
        self.wake_word = wake_word.strip().lower()

    @abstractmethod
    def process_audio(self, audio_data: bytes) -> bool:
        """Processes a block of raw 16-bit mono 16kHz PCM audio.
        
        Args:
            audio_data (bytes): Raw PCM audio buffer.
            
        Returns:
            bool: True if the wake word was detected in this block, False otherwise.
        """
        pass
