import datetime
import io
import os
import sys
import wave

import aiofiles
from dotenv import load_dotenv
from fastapi import WebSocket
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from acshandler.serializers.acs.acs_serializer import ACSFrameSerializer

from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

from services.tts_service import TTSService
from services.llm_service import LLMService
from services.stt_service import STTService
from services.context_service import OpenAILLMContextService

load_dotenv(override=True)

logger.add(sys.stderr, level="DEBUG")

logger.info("Starting Pipecat bot...")


async def save_audio(
    server_name: str, audio: bytes, sample_rate: int, num_channels: int
):
    if len(audio) > 0:
        filename = f"{server_name}_recording_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        with io.BytesIO() as buffer:
            with wave.open(buffer, "wb") as wf:
                wf.setsampwidth(2)
                wf.setnchannels(num_channels)
                wf.setframerate(sample_rate)
                wf.writeframes(audio)
            async with aiofiles.open(filename, "wb") as file:
                await file.write(buffer.getvalue())
        logger.info(f"Merged audio saved to {filename}")
    else:
        logger.info("No audio data to save")


async def run_bot(websocket_client: WebSocket, stream_sid: str, call_sid: str):
    # Initialize the appropriate serializer based on the use_acs flag
    serializer = ACSFrameSerializer(connection_id=call_sid, sample_rate=16000)

    # Configure transport parameters based on the serializer type
    transport_params = FastAPIWebsocketParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        add_wav_header=False,
        vad_analyzer=SileroVADAnalyzer(),
        serializer=serializer,
    )

    transport = FastAPIWebsocketTransport(
        websocket=websocket_client,
        params=transport_params,
    )

    # Use the new STTService class
    stt_service = STTService(api_key=os.getenv("DEEPGRAM_API_KEY", ""))
    stt = stt_service.get_stt()

    # Use the new TTSService class
    tts_service = TTSService(
        api_key=os.getenv("ELEVENLABS_API_KEY", ""),
        voice_id=os.getenv("ELEVENLABS_VOICE_ID", ""),
        sample_rate=16000,
    )
    tts = tts_service.get_tts()

    # Use the new LLMService class
    llm_service = LLMService(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
    )
    llm = llm_service.get_llm()
    llm_service.register_functions_from_tools()

    context_service = OpenAILLMContextService().get_OpenAILLMcontext()

    context_aggregator = llm.create_context_aggregator(context=context_service)

    # NOTE: Watch out! This will save all the conversation in memory. You can
    # pass `buffer_size` to get periodic callbacks.
    audiobuffer = AudioBufferProcessor(user_continuous_stream=True)

    pipeline = Pipeline(
        [
            transport.input(),  # Websocket input from client
            stt,  # Speech-To-Text
            context_aggregator.user(),  # User responses
            llm,  # LLM
            tts,  # Text-To-Speech
            transport.output(),  # Websocket output to client
            context_aggregator.assistant(),
        ]
    )

    # Configure pipeline based on serializer type
    audio_sample_rate = serializer.sample_rate

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=audio_sample_rate,
            audio_out_sample_rate=audio_sample_rate,
            allow_interruptions=True,
            enable_metrics=True,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        # Start recording.
        await audiobuffer.start_recording()
        # Kick off the conversation.
        system_message = OpenAILLMContextService()
        system_message.updateContext("Please introduce yourself")
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        await task.cancel()

    @audiobuffer.event_handler("on_audio_data")
    async def on_audio_data(buffer, audio, sample_rate, num_channels):
        server_name = f"server_unknown"
        if websocket_client.client:
            server_name = f"server_{websocket_client.client.port}"
        await save_audio(server_name, audio, sample_rate, num_channels)

    # We use `handle_sigint=False` because `uvicorn` is controlling keyboard
    # interruptions. We use `force_gc=True` to force garbage collection after
    # the runner finishes running a task which could be useful for long running
    # applications with multiple clients connecting.
    runner = PipelineRunner(handle_sigint=False, force_gc=True)

    await runner.run(task)
