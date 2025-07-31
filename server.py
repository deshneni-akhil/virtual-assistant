import argparse
import os
import uuid
from typing import Optional, Dict, Any

import uvicorn
from bot import run_bot
from fastapi import FastAPI, WebSocket, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse
from dotenv import load_dotenv, find_dotenv
from azure.communication.callautomation import (
    MediaStreamingOptions,
    AudioFormat,
    MediaStreamingTransportType,
    MediaStreamingContentType,
    MediaStreamingAudioChannelType,
    CallAutomationClient,
    PhoneNumberIdentifier,
)
from urllib.parse import urlencode, urlparse, urlunparse
from azure.eventgrid import EventGridEvent, SystemEventNames
from logging import getLogger
from bot import run_bot
from acshandler.serializers.acs.acs_serializer import ACSFrameSerializer
from cache import get_cache as get_cache_instance

load_dotenv(find_dotenv())

# # printing environment variables for debugging
# for key, value in os.environ.items():
#     print(f"{key}: {value}")

app = FastAPI()
# Set up logging
logger = getLogger("pipecat.acs_chatbot")

# Initialize Azure Communication Services client
acs_client = CallAutomationClient.from_connection_string(
    os.getenv("ACS_CONNECTION_STRING", "")
)
CALLBACK_EVENTS_URI = os.getenv(
    "CALLBACK_EVENTS_URI", "http://localhost:8000/api/callbacks"
)

if "localhost" not in CALLBACK_EVENTS_URI:
    CALLBACK_EVENTS_URI = CALLBACK_EVENTS_URI + "/api/callbacks"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/")
async def start_call():
    print("POST TwiML")
    return HTMLResponse(
        content=open("templates/streams.xml").read(), media_type="application/xml"
    )


# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     start_data = websocket.iter_text()
#     await start_data.__anext__()
#     call_data = json.loads(await start_data.__anext__())
#     print(call_data, flush=True)
#     stream_sid = call_data["start"]["streamSid"]
#     call_sid = call_data["start"]["callSid"]
#     print("WebSocket connection accepted")
#     await run_bot(websocket, stream_sid, call_sid, app.state.testing)


@app.post("/api/incomingCall")
async def incoming_call_handler(request: Request):
    logger.info("incoming event data")
    for event_dict in await request.json():
        event = EventGridEvent.from_dict(event_dict)
        # logger.info("incoming event data --> %s", event.data)
        if (
            event.event_type
            == SystemEventNames.EventGridSubscriptionValidationEventName
        ):
            logger.info("Validating subscription")
            validation_code = event.data["validationCode"]
            validation_response = {"validationResponse": validation_code}
            logger.info(validation_response)
            return JSONResponse(
                content=validation_response, status_code=status.HTTP_200_OK
            )
        elif event.event_type == "Microsoft.Communication.IncomingCall":
            # logger.info("Incoming call event")
            # logger.info(f"Event data: {event.data}")

            # Extracting the caller ID mobile number who is calling
            if event.data["from"]["kind"] == "phoneNumber":
                caller_id = event.data["from"]["phoneNumber"]["value"]
            else:
                caller_id = event.data["from"]["rawId"]

            # Fetching the mobile number from where the call is coming from
            acs_mobile_number = event.data["to"]["phoneNumber"]["value"]

            incoming_call_context = event.data["incomingCallContext"]
            guid = uuid.uuid4()
            # Generated guid to be used as a unique identifier for the call
            logger.info(f"GUID: {guid}")

            query_parameters = urlencode({"callerId": caller_id})
            callback_uri = f"{CALLBACK_EVENTS_URI}/{guid}?{query_parameters}"

            parsed_url = urlparse(CALLBACK_EVENTS_URI)

            # adding caller id to cache
            get_cache_instance().set(
                str(guid),
                {"caller_id": caller_id, "acs_mobile_number": acs_mobile_number},
            )

            # Use the same query parameters for both callback and websocket URLs
            query_parameters = urlencode(
                {"uuid": str(guid), "acsPhoneNumber": acs_mobile_number}
            )

            websocket_url = urlunparse(
                ("wss", parsed_url.netloc, "/ws", None, query_parameters, None)
            )

            logger.info(f"callback url: {callback_uri}")
            logger.info(f"websocket url: {websocket_url}")

            try:
                # Answer the incoming call

                media_streaming_options = MediaStreamingOptions(
                    transport_url=websocket_url,
                    transport_type=MediaStreamingTransportType.WEBSOCKET,
                    content_type=MediaStreamingContentType.AUDIO,
                    audio_channel_type=MediaStreamingAudioChannelType.MIXED,
                    start_media_streaming=True,
                    enable_bidirectional=True,
                    audio_format=AudioFormat.PCM16_K_MONO,
                )

                answer_call_result = acs_client.answer_call(
                    incoming_call_context=incoming_call_context,
                    operation_context="incomingCall",
                    callback_url=callback_uri,
                    media_streaming=media_streaming_options,
                )

            except Exception as e:
                raise e

            logger.info(
                f"Answered call for connection id: {answer_call_result.call_connection_id}"
            )


@app.post("/api/callbacks/{contextId}")
async def handle_callback_with_context(contextId: str, request: Request):
    async def handle_call_connected(event_data: Dict[str, Any]):
        call_connection_id = event_data["callConnectionId"]
        call_connection_properties = acs_client.get_call_connection(
            call_connection_id
        ).get_call_properties()
        media_streaming_subscription = (
            call_connection_properties.media_streaming_subscription
        )
        # adding call connection id and corelation to cache
        get_cache_instance().set(
            contextId,
            {
                "callConnectionId": call_connection_id,
                "correlationId": event_data["correlationId"],
            },
        )
        logger.info(f"MediaStreamingSubscription:--> {media_streaming_subscription}")
        logger.info(
            f"Received CallConnected event for connection id: {call_connection_id}"
        )
        logger.info(f"CORRELATION ID:--> { event_data['correlationId'] }")
        logger.info(f"CALL CONNECTION ID:--> {event_data['callConnectionId']}")

    async def handle_media_streaming_started(event_data: Dict[str, Any]):
        logger.info(
            f"Media streaming content type:--> {event_data['mediaStreamingUpdate']['contentType']}"
        )
        logger.info(
            f"Media streaming status:--> {event_data['mediaStreamingUpdate']['mediaStreamingStatus']}"
        )
        logger.info(
            f"Media streaming status details:--> {event_data['mediaStreamingUpdate']['mediaStreamingStatusDetails']}"
        )

    async def handle_media_streaming_stopped(event_data: Dict[str, Any]):
        logger.info(
            f"Media streaming content type:--> {event_data['mediaStreamingUpdate']['contentType']}"
        )
        logger.info(
            f"Media streaming status:--> {event_data['mediaStreamingUpdate']['mediaStreamingStatus']}"
        )
        logger.info(
            f"Media streaming status details:--> {event_data['mediaStreamingUpdate']['mediaStreamingStatusDetails']}"
        )

    async def handle_media_streaming_failed(event_data: Dict[str, Any]):
        logger.info(
            f"Code:->{event_data['resultInformation']['code']}, Subcode:-> {event_data['resultInformation']['subCode']}"
        )
        logger.info(f"Message:->{event_data['resultInformation']['message']}")

    async def handle_terminate_call(event_data: Dict[str, Any]):
        call_connection_id = event_data["callConnectionId"]
        try:
            # stop media streaming
            acs_client.get_call_connection(call_connection_id).hang_up(
                is_for_everyone=True
            )
            logger.info(f"Terminated call for connection id: {call_connection_id}")
        except Exception as e:
            logger.error(f"Error stopping media streaming: {e}")
        finally:
            # evict the record from cache
            get_cache_instance().delete(contextId)

    async def handle_transfer_call_to_agent(event_data: Dict[str, Any]):
        call_connection_id = event_data["callConnectionId"]
        try:
            logger.info(
                f"Transfer call to agent event received for connection id: {call_connection_id}"
            )
            # Handle transfer call to agent event
            agent_phone_number = event_data["agentPhoneNumber"]
            acs_phone_number = event_data["acsPhoneNumber"]
            transfer_destination = PhoneNumberIdentifier(agent_phone_number)
            transferee = PhoneNumberIdentifier(acs_phone_number)
            # waiting for 5 seconds before transferring the call
            # This is to ensure that the media streaming is done before transferring the call
            # time.sleep(5)
            # Transfer the call to the agent
            result = acs_client.get_call_connection(
                call_connection_id
            ).transfer_call_to_participant(
                target_participant=transfer_destination,
                source_caller_id_number=transferee,
                operation_context="TransferCallToAgent",
                operation_callback_url=CALLBACK_EVENTS_URI + f"/{contextId}",
            )

            logger.info(
                f"Transfer call to agent initiated for connection id: {call_connection_id}"
            )
        except Exception as e:
            logger.error(f"Error transferring call to agent: {e}")

    event_handlers = {
        "Microsoft.Communication.CallConnected": handle_call_connected,
        "Microsoft.Communication.MediaStreamingStarted": handle_media_streaming_started,
        "Microsoft.Communication.MediaStreamingStopped": handle_media_streaming_stopped,
        "Microsoft.Communication.MediaStreamingFailed": handle_media_streaming_failed,
        "Microsoft.Communication.TerminateCall": handle_terminate_call,
        "Microsoft.Communication.TransferCallToAgent": handle_transfer_call_to_agent,
    }

    for event in await request.json():
        event_data = event["data"]
        call_connection_id = event_data["callConnectionId"]
        event_type = event["type"]

        logger.info(
            f"Received Event:-> {event_type}, Correlation Id:-> {event_data['correlationId']}, CallConnectionId:-> {call_connection_id}"
        )

        handler = event_handlers.get(event_type)
        # setting contextId to event data
        event_data["contextId"] = contextId

        if handler:
            await handler(event_data)
        else:
            logger.info(
                f"Unhandled event type: {event_type}, CallConnectionId: {call_connection_id}"
            )


@app.websocket("/ws")
async def acs_ws(websocket: WebSocket):
    # Accept the connection
    await websocket.accept()
    query_params = dict(websocket.query_params)
    uuid = query_params.get("uuid", "")
    acs_phone_number = query_params.get("acsPhoneNumber", "")
    print(
        f"WebSocket connection accepted with UUID: {uuid} and ACS Phone Number: {acs_phone_number} and query params: {query_params} with websocket: {websocket}"
    )
    # Run your bot pipeline
    await run_bot(
        websocket_client=websocket, stream_sid=uuid, call_sid=acs_phone_number
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipecat ACS Chatbot Server")
    parser.add_argument(
        "-t",
        "--test",
        action="store_true",
        default=False,
        help="set the server in testing mode",
    )
    args, _ = parser.parse_known_args()

    app.state.testing = args.test

    uvicorn.run("server:app", host="0.0.0.0", port=8765, reload=True)
