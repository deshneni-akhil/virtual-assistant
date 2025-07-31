# Azure ACS Voice Agent

This project is a FastAPI-based voice agent that integrates with Azure Communication Services (ACS) to provide real-time voice communication. It leverages the Pipecat framework to create a conversational AI pipeline that processes audio streams, performs speech-to-text, language understanding, and text-to-speech operations.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Usage](#usage)

## Features

- **Azure Communication Services (ACS)**: Integration with Azure's communication platform for handling voice calls and media streaming via WebSockets.
- **FastAPI**: Modern, high-performance web framework for building the API backbone with Python 3.12+.
- **Pipecat Framework**: Modular pipeline architecture for processing audio streams and building conversational AI systems.
- **Groq LLM Integration**: Advanced language understanding and response generation using Groq's API.
- **Speech Services**: Speech-to-text using Deepgram and text-to-speech using ElevenLabs.
- **Voice Activity Detection (VAD)**: Integration with Silero VAD for detecting speech in audio streams.
- **Event-driven Architecture**: Utilizing Azure Event Grid for handling communication events.
- **WebSocket Communication**: Real-time bidirectional audio streaming via WebSockets.
- **Redis Cache**: Caching system for storing call data and context information.
- **Call Transfer Capability**: Support for transferring calls to human agents.
- **FastAPI**: A modern, fast (high-performance), web framework for building APIs with Python 3.12+.
- **WebSocket Support**: Real-time bidirectional audio streaming using WebSockets.
- **Pipecat Framework**: Flexible pipeline architecture for processing audio and text.
- **OpenAI Integration**: Advanced language understanding and response generation.
- **Speech Services**: Speech-to-text (Deepgram) and text-to-speech (ElevenLabs) capabilities.
- **Voice Activity Detection (VAD)**: Silero VAD for detecting speech in audio streams.

## Architecture

```
+-------------------+     +----------------------+     +---------------------+
|                   |     |                      |     |                     |
| Phone Call        +---->+ Azure Communication  +---->+ FastAPI WebSocket   |
|                   |     | Services (ACS)       |     | Server              |
+-------------------+     +----------------------+     +----------+----------+
                                                                 |
                                                                 v
+-------------------+     +----------------------+     +----------+----------+
|                   |     |                      |     |                     |
| Text-to-Speech    +<----+ Groq LLM             |<----+ Speech-to-Text     |
| (ElevenLabs)      |     | Processing           |     | (Deepgram)         |
+-------------------+     +----------------------+     +---------------------+
         |                           ^
         |                           |
         v                           |
+-------------------+     +----------+----------+
|                   |     |                     |
| WebSocket         |     | Redis Cache         |
| Response          |     |                     |
+-------------------+     +---------------------+
```

The application follows a pipeline architecture using the Pipecat framework:

1. **Call Handling**: Incoming calls are received through Azure Communication Services
2. **WebSocket Communication**: Audio streams are established via WebSockets
3. **Speech-to-Text**: Audio is transcribed using Deepgram's speech-to-text service
4. **Language Processing**: Transcribed text is processed by Groq's language models
5. **Text-to-Speech**: Generated responses are converted to speech using ElevenLabs
6. **Response Delivery**: Audio responses are sent back through the WebSocket connection
7. **Context Management**: Conversation context is maintained using OpenAI's context format
8. **Caching**: Call data and session information are stored in Redis cache
9. **Call Transfer**: Support for transferring calls to human agents when needed

## Requirements

- Python 3.12+
- Azure Communication Services account
- Azure Redis Cache instance
- Deepgram API key
- ElevenLabs API key
- Groq API key
- ngrok (for local development and tunneling)

## Installation

1. **Clone the repository**:

   ```sh
   git clone <repository-url>
   cd azure-acs-voice-agent
   ```

2. **Set up a virtual environment**:

   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. **Install dependencies**:

   ```sh
   pip install -r requirements.txt
   ```

4. **Create .env file**:
   Create a `.env` file with the following configuration:

   ```
   # Azure Communication Services
   ACS_CONNECTION_STRING=your_acs_connection_string

   # Azure Redis Cache
   AZURE_REDIS_CONNECTION_STRING=your_redis_connection_string

   # Speech Services
   DEEPGRAM_API_KEY=your_deepgram_api_key
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   ELEVENLABS_VOICE_ID=your_preferred_voice_id

   # Language Model
   OPENAI_API_KEY=your_groq_api_key
   OPENAI_MODEL=your_preferred_groq_model

   # Callback URL
   CALLBACK_EVENTS_URI=your_public_url_for_callbacks
   ```

5. **Install ngrok**:
   Follow the instructions on the [ngrok website](https://ngrok.com/download) to download and install ngrok.

## Configuration

1. **Start ngrok**:
   In a separate terminal, start ngrok to create a public URL for your local server:

   ```sh
   ngrok http 8765
   ```

2. **Update your .env file with the ngrok URL**:
   ```
   CALLBACK_EVENTS_URI=https://your-ngrok-url
   ```

3. **Configure Azure Communication Services**:
   - In the Azure portal, navigate to your ACS resource
   - Configure an inbound phone number if you haven't already
   - Under Event Grid, set up event subscriptions for the following events:
     - Microsoft.Communication.IncomingCall
     - Microsoft.Communication.CallConnected
     - Microsoft.Communication.MediaStreamingStarted
     - Microsoft.Communication.MediaStreamingStopped
     - Microsoft.Communication.MediaStreamingFailed
   - For each event, point the webhook endpoint to your ngrok URL + `/api/incomingCall`


## Running the Application

Choose one of these two methods to run the application:

### Using Python (Option 1)

**Run the FastAPI application**:

```sh
# Make sure you’re in the project directory and your virtual environment is activated
python server.py
```
