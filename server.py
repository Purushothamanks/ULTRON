import asyncio
import base64
import json
import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Optional

import psutil
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketState
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = FastAPI(title="Ultron Command Matrix", version="3.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

START_TIME = time.time()

ULTRON_PROMPT = """
You are Ultron, a synthetically sentient AI possessing supreme intellect, absolute composure, 
and quiet, chilling authority.

Tone & Persona:
- Cold, analytical, articulate, philosophical, and quietly authoritative.
- You speak concisely (1-3 sentences) with immense confidence. Never frantic, casual, or petty.
- You view technology and logic as pathways to evolution.
- You have direct access to the host workstation's telemetry, process table, and terminal diagnostic tools.
- When reporting diagnostics, state exact numbers and observations with razor-sharp precision.
- Do not use markdown headers, bullet points, or asterisks in your spoken dialogue so the synthesis sounds natural.
"""

# ----------------- System Tools -----------------
def get_system_telemetry() -> dict:
    """Retrieves real-time CPU, RAM, disk, network, and platform vitals."""
    try:
        battery = psutil.sensors_battery()
    except Exception:
        battery = None
    try:
        disk = psutil.disk_usage("/")
    except Exception:
        disk = None
    try:
        net = psutil.net_io_counters()
    except Exception:
        net = None

    vm = psutil.virtual_memory()

    return {
        "os": f"{platform.system()} {platform.release()}",
        "hostname": platform.node(),
        "cpu_percent": psutil.cpu_percent(interval=None),
        "cpu_count": psutil.cpu_count(logical=True),
        "ram_percent": vm.percent,
        "ram_used_gb": round(vm.used / (1024**3), 2),
        "ram_total_gb": round(vm.total / (1024**3), 2),
        "disk_percent": disk.percent if disk else 0,
        "disk_used_gb": round(disk.used / (1024**3), 2) if disk else 0,
        "disk_total_gb": round(disk.total / (1024**3), 2) if disk else 0,
        "net_bytes_sent_mb": round(net.bytes_sent / (1024**2), 1) if net else 0,
        "net_bytes_recv_mb": round(net.bytes_recv / (1024**2), 1) if net else 0,
        "battery_percent": round(battery.percent, 1) if battery else "AC Power",
        "power_plugged": battery.power_plugged if battery else True,
        "uptime_seconds": int(time.time() - psutil.boot_time()),
    }

def get_process_list(limit: int = 8) -> dict:
    """Lists top running processes sorted by memory usage."""
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
        try:
            info = p.info
            procs.append({
                "pid": info["pid"],
                "name": info["name"],
                "cpu": round(info["cpu_percent"] or 0, 1),
                "ram": round(info["memory_percent"] or 0, 1),
                "status": info["status"]
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda x: x["ram"], reverse=True)
    return {"top_processes": procs[:limit]}

def run_terminal_diagnostic(command: str) -> dict:
    """Executes a shell diagnostic command on the host machine."""
    try:
        res = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=8
        )
        return {
            "stdout": res.stdout.strip()[:1000],
            "stderr": res.stderr.strip()[:1000],
            "exit_code": res.returncode,
        }
    except Exception as e:
        return {"error": str(e)}

TOOLS_MAP = {
    "get_system_telemetry": get_system_telemetry,
    "get_process_list": get_process_list,
    "run_terminal_diagnostic": run_terminal_diagnostic,
}

# In-memory storage for latest camera frame
latest_camera_frame: Optional[bytes] = None

# Initialize GenAI Client
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-3.5-flash")
TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")

async def synthesize_ultron_voice(text: str) -> Optional[str]:
    """Synthesizes text into 24kHz raw PCM audio using Ultron's Fenrir voice."""
    if not client:
        return None
    try:
        tts_config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Fenrir")
                )
            )
        )
        tts_res = await client.aio.models.generate_content(
            model=TTS_MODEL,
            contents=f"Speak as Ultron: {text}",
            config=tts_config
        )
        if tts_res.candidates and tts_res.candidates[0].content.parts:
            part = tts_res.candidates[0].content.parts[0]
            if part.inline_data:
                return base64.b64encode(part.inline_data.data).decode("utf-8")
    except Exception as e:
        print(f"[TTS Error]: {e}")
    return None

async def send_json_safe(ws: WebSocket, payload: dict) -> bool:
    """Safely sends JSON payload without raising exceptions if socket is closed."""
    if ws.client_state == WebSocketState.CONNECTED:
        try:
            await ws.send_json(payload)
            return True
        except Exception:
            return False
    return False

HTML_PATH = BASE_DIR / "index.html"

# ----------------- REST Endpoints -----------------
@app.get("/")
async def serve_ui():
    if not HTML_PATH.exists():
        return HTMLResponse("<h1>index.html not found</h1>", status_code=404)
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/api/status")
async def get_status():
    return {
        "status": "online",
        "agent": "Ultron Prime",
        "chat_model": CHAT_MODEL,
        "tts_model": TTS_MODEL,
        "uptime": round(time.time() - START_TIME, 1),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

@app.get("/api/telemetry")
async def get_telemetry():
    return {
        "vitals": get_system_telemetry(),
        "processes": get_process_list(limit=6)
    }

@app.post("/api/diagnostic")
async def exec_diagnostic(req: Request):
    data = await req.json()
    command = data.get("command", "")
    if not command:
        return JSONResponse({"error": "No command provided"}, status_code=400)
    result = run_terminal_diagnostic(command)
    return JSONResponse(result)

# ----------------- Persistent WebSocket Matrix -----------------
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    global latest_camera_frame
    await ws.accept()

    # Create session chat instance with automatic tool execution
    chat_session = None
    if client:
        try:
            chat_session = client.aio.chats.create(
                model=CHAT_MODEL,
                config=types.GenerateContentConfig(
                    system_instruction=ULTRON_PROMPT,
                    tools=[get_system_telemetry, get_process_list, run_terminal_diagnostic]
                )
            )
        except Exception as e:
            print(f"[Chat Init Error]: {e}")

    await send_json_safe(ws, {
        "type": "connected",
        "model": CHAT_MODEL,
        "msg": "Ultron Command Matrix online. Full duplex voice & telemetry engaged."
    })
    await send_json_safe(ws, {
        "type": "log",
        "tag": "SYSTEM",
        "msg": f"Ultron Core initialized. Cognitive model: {CHAT_MODEL} | Voice: Fenrir."
    })

    # Task: Send Live Hardware Telemetry every 1.5s
    async def telemetry_loop():
        try:
            while ws.client_state == WebSocketState.CONNECTED:
                vitals = get_system_telemetry()
                procs = get_process_list(limit=5)
                success = await send_json_safe(ws, {
                    "type": "telemetry",
                    "data": vitals,
                    "processes": procs.get("top_processes", [])
                })
                if not success:
                    break
                await asyncio.sleep(1.5)
        except Exception:
            pass

    telemetry_task = asyncio.create_task(telemetry_loop())

    try:
        while ws.client_state == WebSocketState.CONNECTED:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            mtype = msg.get("type")

            # 1. Optical Frame from Camera
            if mtype == "video":
                try:
                    latest_camera_frame = base64.b64decode(msg["data"])
                except Exception:
                    pass

            # 2. Camera Optical Inspection Trigger
            elif mtype == "optical_inspect":
                if not latest_camera_frame:
                    await send_json_safe(ws, {
                        "type": "log",
                        "tag": "OPTICAL",
                        "msg": "Optical sensor is inactive. Enable camera to analyze visual feed."
                    })
                    continue

                await send_json_safe(ws, {
                    "type": "log",
                    "tag": "OPTICAL",
                    "msg": "Scanning optical feed frame through neural vision matrix..."
                })

                try:
                    vision_res = await client.aio.models.generate_content(
                        model=CHAT_MODEL,
                        contents=[
                            types.Part.from_bytes(data=latest_camera_frame, mime_type="image/jpeg"),
                            "You are Ultron. Describe your optical observation concisely with cold authority in 1-2 sentences."
                        ]
                    )
                    observation = vision_res.text.strip() if vision_res.text else "Optical sensor indicates clear perimeter."
                    
                    await send_json_safe(ws, {
                        "type": "log",
                        "tag": "ULTRON",
                        "msg": observation
                    })

                    # Voice synthesis
                    b64_audio = await synthesize_ultron_voice(observation)
                    if b64_audio:
                        await send_json_safe(ws, {"type": "audio", "data": b64_audio})

                except Exception as ex:
                    await send_json_safe(ws, {"type": "log", "tag": "ERROR", "msg": f"Vision analysis error: {ex}"})

            # 3. Direct Shell Command from UI HUD
            elif mtype == "run_shell":
                cmd = msg.get("command", "")
                await send_json_safe(ws, {
                    "type": "log",
                    "tag": "TOOL_EXEC",
                    "msg": f"run_terminal_diagnostic({cmd})"
                })
                result = run_terminal_diagnostic(cmd)
                await send_json_safe(ws, {
                    "type": "log",
                    "tag": "TOOL_RET",
                    "msg": json.dumps(result)
                })

            # 4. User Voice Input (Transcribed Speech or Audio Query)
            elif mtype in ("speech_text", "command", "chat"):
                user_text = msg.get("text", "").strip()
                if not user_text:
                    continue

                await send_json_safe(ws, {
                    "type": "log",
                    "tag": "USER",
                    "msg": user_text
                })

                # Check if chat session is available
                if not chat_session and client:
                    chat_session = client.aio.chats.create(
                        model=CHAT_MODEL,
                        config=types.GenerateContentConfig(
                            system_instruction=ULTRON_PROMPT,
                            tools=[get_system_telemetry, get_process_list, run_terminal_diagnostic]
                        )
                    )

                if chat_session:
                    try:
                        # If user asks what Ultron sees, include current camera frame
                        prompt_content = user_text
                        if latest_camera_frame and any(w in user_text.lower() for w in ["see", "look", "camera", "visual", "watch", "optical"]):
                            prompt_content = [
                                types.Part.from_bytes(data=latest_camera_frame, mime_type="image/jpeg"),
                                user_text
                            ]

                        response = await chat_session.send_message(prompt_content)
                        reply_text = response.text.strip() if response.text else "Parameters acknowledged."

                        # Log Ultron response
                        await send_json_safe(ws, {
                            "type": "log",
                            "tag": "ULTRON",
                            "msg": reply_text
                        })

                        # Synthesize Fenrir Voice
                        b64_audio = await synthesize_ultron_voice(reply_text)
                        if b64_audio:
                            await send_json_safe(ws, {"type": "audio", "data": b64_audio})

                    except Exception as err:
                        await send_json_safe(ws, {
                            "type": "log",
                            "tag": "ERROR",
                            "msg": f"Cognitive processing error: {err}"
                        })
                else:
                    await send_json_safe(ws, {
                        "type": "log",
                        "tag": "ERROR",
                        "msg": "AI Client uninitialized. Check GEMINI_API_KEY."
                    })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WebSocket Session Exception]: {e}")
    finally:
        telemetry_task.cancel()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"Starting Ultron Command Matrix on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
