import json
import logging
import os
from vosk import Model, KaldiRecognizer
from chespin.detector.base import BaseWakeWordDetector

logger = logging.getLogger(__name__)

class VoskWakeWordDetector(BaseWakeWordDetector):
    """Wake-word detector backend using the offline Vosk speech-to-text engine."""
    
    def __init__(self, wake_word: str, model_path: str):
        super().__init__(wake_word)
        self.model_path = model_path
        
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Vosk model directory not found at '{self.model_path}'. "
                "Please download the small English model and unpack it there. "
                "Refer to README.md for instructions."
            )
            
        logger.info(f"Loading Vosk speech model from '{self.model_path}'...")
        self.model = Model(self.model_path)
        
        # Restricting the vocabulary list speeds up recognition, reduces CPU load,
        # and eliminates most false positives.
        grammar = f'["{self.wake_word}", "[unk]"]'
        self.rec = KaldiRecognizer(self.model, 16000, grammar)
        logger.info(f"Vosk KaldiRecognizer configured with grammar vocabulary: {grammar}")

    def process_audio(self, audio_data: bytes) -> bool:
        """Analyze a PCM buffer to check if the wake word is spoken.
        
        Uses both final and partial transcripts to trigger at sub-second latency.
        """
        if not audio_data:
            return False

        detected = False
        
        # Check if silence/phrase ending was reached
        if self.rec.AcceptWaveform(audio_data):
            result = json.loads(self.rec.Result())
            text = result.get("text", "").strip()
            if self.wake_word in text:
                logger.info(f"Wake word '{self.wake_word}' matched in final result.")
                detected = True
        else:
            # Check partial utterance buffer for fast triggering
            partial_result = json.loads(self.rec.PartialResult())
            partial_text = partial_result.get("partial", "").strip()
            if self.wake_word in partial_text:
                logger.info(f"Wake word '{self.wake_word}' matched in partial result.")
                detected = True

        if detected:
            # Flush the recognizer's internal audio memory so we do not trigger twice
            self.rec.Reset()
            return True

        return False
