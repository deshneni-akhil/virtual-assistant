from pipecat.services.elevenlabs.tts import ElevenLabsTTSService

class TTSService:
    def __init__(self, api_key: str, voice_id: str, sample_rate: int):
        self.tts = ElevenLabsTTSService(
            api_key=api_key,
            voice_id=voice_id,
            sample_rate=sample_rate,
            params=ElevenLabsTTSService.InputParams(
                auto_mode=True,
                use_speaker_boost=True
            ),
        )

    def get_tts(self):
        return self.tts
