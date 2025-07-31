from pipecat.services.deepgram.stt import DeepgramSTTService

class STTService:
    def __init__(self, api_key: str):
        self.stt = DeepgramSTTService(
            api_key=api_key,
            audio_passthrough=True
        )

    def get_stt(self):
        return self.stt
