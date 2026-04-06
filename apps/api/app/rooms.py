from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Dict, Optional, Set
from fastapi import WebSocket

from .game import create_match_state, step_state, TICK_RATE_MS


@dataclass
class Room:
    match_id: str
    state: Dict
    connections: Set[WebSocket] = field(default_factory=set)
    last_action: str = "idle"
    loop_task: Optional[asyncio.Task] = None
    finished: bool = False


rooms: Dict[str, Room] = {}


def create_room(match_id: str, settings: Dict | None = None) -> Room:
    room = Room(match_id=match_id, state=create_match_state(settings))
    rooms[match_id] = room
    return room


def get_room(match_id: str) -> Optional[Room]:
    return rooms.get(match_id)


async def broadcast_json(room: Room, payload: Dict) -> None:
    stale_connections: list[WebSocket] = []
    for connection in list(room.connections):
        try:
            await connection.send_json(payload)
        except Exception:
            stale_connections.append(connection)
    for connection in stale_connections:
        room.connections.discard(connection)


async def run_room_loop(room: Room, on_finish) -> None:
    try:
        while not room.finished:
            await asyncio.sleep(TICK_RATE_MS / 1000)
            room.state = step_state(room.state, room.last_action)
            await broadcast_json(room, {"type": "MATCH_STATE", "payload": room.state})
            room.last_action = "idle"
            if room.state["status"] == "finished":
                room.finished = True
                await on_finish(room)
                break
    finally:
        room.loop_task = None
