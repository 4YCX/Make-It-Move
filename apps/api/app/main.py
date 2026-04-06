from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import Body, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .game import decide_winner
from .rooms import Room, broadcast_json, create_room, get_room, run_room_loop
from .schemas import CreateMatchRequest, CreateMatchResponse, PlayerActionMessage


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Agent Arena API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "name": "Agent Arena API",
        "status": "ok",
        "message": "Backend is running. Open http://localhost:3000 for the game UI.",
        "health": "/health",
        "createMatch": "/matches",
        "websocket": "/ws/matches/{matchId}",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/matches", response_model=CreateMatchResponse)
async def create_match(payload: CreateMatchRequest = Body(default_factory=CreateMatchRequest)):
    match_id = uuid.uuid4().hex[:8]
    create_room(match_id, payload.settings.model_dump())
    return CreateMatchResponse(matchId=match_id)


async def finish_room(room: Room) -> None:
    winner = decide_winner(room.state)
    await broadcast_json(room, {"type": "MATCH_RESULT", "payload": {"winner": winner}})


@app.websocket("/ws/matches/{match_id}")
async def match_ws(websocket: WebSocket, match_id: str):
    room = get_room(match_id)
    if room is None:
        await websocket.accept()
        await websocket.send_json({"type": "ERROR", "payload": {"message": "Match not found"}})
        await websocket.close()
        return

    await websocket.accept()
    room.connections.add(websocket)
    await websocket.send_json({"type": "MATCH_STATE", "payload": room.state})

    if room.loop_task is None and not room.finished:
        import asyncio

        room.loop_task = asyncio.create_task(run_room_loop(room, finish_room))

    try:
        while True:
            raw = await websocket.receive_json()
            try:
                message = PlayerActionMessage.model_validate(raw)
            except Exception:
                await websocket.send_json({"type": "ERROR", "payload": {"message": "Invalid message"}})
                continue
            room.last_action = message.payload.action
    except WebSocketDisconnect:
        room.connections.discard(websocket)
    except Exception:
        room.connections.discard(websocket)
        try:
            await websocket.send_json({"type": "ERROR", "payload": {"message": "Match connection interrupted"}})
        except Exception:
            pass
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
