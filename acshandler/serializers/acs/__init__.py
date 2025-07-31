# Azure Communication Services (ACS) serializer for Pipecat
import dataclasses

@dataclasses.dataclass
class ACSFrameSerializerParams:
    """Parameters for ACS frame serializer."""
    audio_format: str = "PCM"  # PCM is used by ACS
    sample_rate: int = 16000   # 16kHz as default
    bits_per_sample: int = 16  # 16-bit PCM
    channels: int = 1          # Mono audio
    frame_size: int = 320      # Default frame size (20ms @ 16kHz)
