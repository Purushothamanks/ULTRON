# Ultron // Synthetic Command Matrix

A real-time, fullstack, multimodal synthetic command console inspired by Ultron. Powered by a FastAPI resilient WebSocket backend and an interactive single-file web console featuring 24kHz native voice synthesis, live camera computer vision, local system telemetry tools, and a dynamic 3D cursor-tracking avatar.

---

## Architecture Overview

```
                      +---------------------------------------+
                      |       Ultron Command Console UI       |
                      |   (Single-file HTML/CSS/Web Audio)    |
                      +---------------------------------------+
                                          |
                      Full-Duplex Persistent WebSocket (/ws)
                                          |
                                          v
                      +---------------------------------------+
                      |         FastAPI WebSocket Core        |
                      +---------------------------------------+
                        |                 |                 |
                        v                 v                 v
            +--------------------+ +-------------+ +--------------------+
            | Gemini 3.5 Flash   | | Fenrir TTS  | | Local Host Tools   |
            | Reasoning & Vision | | 24kHz PCM   | | Telemetry & Shell  |
            +--------------------+ +-------------+ +--------------------+
```

- **Frontend**: Zero-dependency standalone HTML/CSS console with JetBrains Mono & Inter typography, zinc monochrome design, audio-reactive equalizers, and collapsible HUD log drawer.
- **Ultron Metallic Avatar**: Sized to fill the stage viewport with continuous 3D cursor-tracking parallax (`perspective(1200px)`), multi-harmonic idle floating, and acoustic resonance scaling during speech (clean metallic finish with zero artificial red lights).
- **Voice Duplex Pipeline**: Real-time microphone listening with Web Speech API and native Web Audio API equalizer coupled to 24kHz PCM playback synthesizing Ultron's authoritative **Fenrir** voice.
- **Optical Sensor Matrix**: Real-time webcam streaming at 1 FPS with on-demand vision analysis (*"What do you see?"* or direct `[Inspect]` trigger).
- **System Telemetry & Diagnostics**: Real-time CPU load, memory usage, disk utilization, and top processes ticker streamed every 1.5 seconds, with autonomous tool execution for terminal diagnostics.

---

## Quickstart

### 1. Prerequisites
- Python 3.10+
- A Google Gemini API key from [Google AI Studio](https://aistudio.google.com/)

### 2. Installation
Clone the repository and install required dependencies:

```bash
git clone https://github.com/Purushothamanks/ultron-command-matrix.git
cd ultron-command-matrix
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file from the provided `.env.example`:

```bash
cp .env.example .env
```

Open `.env` and configure your API key:
```env
GEMINI_API_KEY="your_api_key_here"
GEMINI_CHAT_MODEL="gemini-3.5-flash"
GEMINI_TTS_MODEL="gemini-2.5-flash-preview-tts"
HOST="0.0.0.0"
PORT=8000
```

### 4. Running the Server
Launch the console with:

```bash
python server.py
# or using the helper script
chmod +x run.sh && ./run.sh
```

Open your browser at **`http://localhost:8000`** (or `http://127.0.0.1:8000`).

---

## Features

- **Engage Voice**: Tap the voice presence equalizer or top header button to activate full-duplex speech.
- **Optical Camera**: Enable the optical sensor to feed video frames into Ultron's visual perception matrix.
- **Interactive Command & Diagnostic Input**: Type queries or diagnostic instructions into the bottom HUD dock bar and press **Transmit** or **Shell**.
- **Collapsible Logs HUD**: Expand logs to inspect filtered execution streams (`ALL`, `DIALOGUE`, `TOOLS`).
- **Resilient Fallback**: Hardware telemetry automatically falls back to REST polling if WebSocket resets, ensuring telemetry never freezes.

---

## License
MIT License. Created by K S Purushothaman.
