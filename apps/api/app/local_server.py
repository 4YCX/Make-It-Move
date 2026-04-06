from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field
from typing import Dict
from urllib.parse import urlparse

from .game import create_match_state, decide_winner, normalize_settings, step_state, TICK_RATE_MS


WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def json_bytes(payload: Dict) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


@dataclass(eq=False)
class SocketConnection:
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    closed: bool = False

    async def send_json(self, payload: Dict) -> None:
        if self.closed:
            return
        await send_ws_frame(self.writer, json_bytes(payload))

    async def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        try:
            await send_close_frame(self.writer)
        except Exception:
            pass
        self.writer.close()
        try:
            await self.writer.wait_closed()
        except Exception:
            pass


@dataclass
class Room:
    match_id: str
    state: Dict
    connections: set[SocketConnection] = field(default_factory=set)
    last_action: str = "idle"
    loop_task: asyncio.Task | None = None
    finished: bool = False


rooms: Dict[str, Room] = {}


def cors_headers() -> Dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }


def create_room(match_id: str, settings: Dict | None = None) -> Room:
    room = Room(match_id=match_id, state=create_match_state(settings))
    rooms[match_id] = room
    return room


def get_room(match_id: str) -> Room | None:
    return rooms.get(match_id)


async def broadcast_json(room: Room, payload: Dict) -> None:
    stale: list[SocketConnection] = []
    for connection in list(room.connections):
        try:
            await connection.send_json(payload)
        except Exception:
            stale.append(connection)
    for connection in stale:
        room.connections.discard(connection)
        await connection.close()


async def finish_room(room: Room) -> None:
    winner = decide_winner(room.state)
    await broadcast_json(room, {"type": "MATCH_RESULT", "payload": {"winner": winner}})


async def run_room_loop(room: Room) -> None:
    try:
        while not room.finished:
            await asyncio.sleep(TICK_RATE_MS / 1000)
            room.state = step_state(room.state, room.last_action)
            await broadcast_json(room, {"type": "MATCH_STATE", "payload": room.state})
            room.last_action = "idle"
            if room.state["status"] == "finished":
                room.finished = True
                await finish_room(room)
                break
    finally:
        room.loop_task = None


async def send_http_response(
    writer: asyncio.StreamWriter,
    status: str,
    body: bytes = b"",
    *,
    content_type: str = "application/json",
    connection: str = "close",
    extra_headers: Dict[str, str] | None = None,
) -> None:
    headers = {
        "Content-Length": str(len(body)),
        "Content-Type": content_type,
        "Connection": connection,
        **cors_headers(),
    }
    if extra_headers:
        headers.update(extra_headers)
    response = [f"HTTP/1.1 {status}\r\n"]
    for key, value in headers.items():
        response.append(f"{key}: {value}\r\n")
    response.append("\r\n")
    writer.write("".join(response).encode("utf-8") + body)
    await writer.drain()


async def read_http_request(reader: asyncio.StreamReader) -> tuple[str, str, Dict[str, str], bytes]:
    request_line = await reader.readline()
    if not request_line:
        raise ConnectionError("empty request")
    try:
        method, path, _version = request_line.decode("utf-8").strip().split(" ")
    except ValueError as exc:
        raise ConnectionError("invalid request line") from exc

    headers: Dict[str, str] = {}
    while True:
        line = await reader.readline()
        if not line or line == b"\r\n":
            break
        name, value = line.decode("utf-8").split(":", 1)
        headers[name.strip().lower()] = value.strip()

    content_length = int(headers.get("content-length", "0") or "0")
    body = await reader.readexactly(content_length) if content_length else b""
    return method, path, headers, body


def websocket_accept_value(key: str) -> str:
    digest = hashlib.sha1((key + WS_MAGIC).encode("utf-8")).digest()
    return base64.b64encode(digest).decode("utf-8")


async def send_ws_frame(writer: asyncio.StreamWriter, payload: bytes, opcode: int = 0x1) -> None:
    frame = bytearray()
    frame.append(0x80 | opcode)
    length = len(payload)
    if length < 126:
        frame.append(length)
    elif length < 65536:
        frame.append(126)
        frame.extend(length.to_bytes(2, "big"))
    else:
        frame.append(127)
        frame.extend(length.to_bytes(8, "big"))
    frame.extend(payload)
    writer.write(frame)
    await writer.drain()


async def send_close_frame(writer: asyncio.StreamWriter) -> None:
    await send_ws_frame(writer, b"", opcode=0x8)


async def read_ws_frame(reader: asyncio.StreamReader) -> tuple[int, bytes]:
    first = await reader.readexactly(2)
    opcode = first[0] & 0x0F
    masked = bool(first[1] & 0x80)
    length = first[1] & 0x7F
    if length == 126:
        length = int.from_bytes(await reader.readexactly(2), "big")
    elif length == 127:
        length = int.from_bytes(await reader.readexactly(8), "big")

    mask = await reader.readexactly(4) if masked else b""
    payload = await reader.readexactly(length) if length else b""
    if masked:
        payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    return opcode, payload


async def handle_match_ws(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    path: str,
    headers: Dict[str, str],
) -> None:
    match_id = path.rsplit("/", 1)[-1]
    room = get_room(match_id)
    key = headers.get("sec-websocket-key")
    if key is None:
        await send_http_response(writer, "400 Bad Request", json_bytes({"detail": "Missing websocket key"}))
        return

    response_headers = {
        "Upgrade": "websocket",
        "Connection": "Upgrade",
        "Sec-WebSocket-Accept": websocket_accept_value(key),
    }
    await send_http_response(
        writer,
        "101 Switching Protocols",
        b"",
        content_type="text/plain",
        connection="Upgrade",
        extra_headers=response_headers,
    )

    connection = SocketConnection(reader=reader, writer=writer)
    if room is None:
        await connection.send_json({"type": "ERROR", "payload": {"message": "Match not found"}})
        await connection.close()
        return

    room.connections.add(connection)
    await connection.send_json({"type": "MATCH_STATE", "payload": room.state})

    if room.loop_task is None and not room.finished:
        room.loop_task = asyncio.create_task(run_room_loop(room))

    try:
        while True:
            opcode, payload = await read_ws_frame(reader)
            if opcode == 0x8:
                break
            if opcode == 0x9:
                await send_ws_frame(writer, payload, opcode=0xA)
                continue
            if opcode != 0x1:
                await connection.send_json({"type": "ERROR", "payload": {"message": "Unsupported frame"}})
                continue
            try:
                message = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                await connection.send_json({"type": "ERROR", "payload": {"message": "Invalid message"}})
                continue
            if message.get("type") != "PLAYER_ACTION":
                await connection.send_json({"type": "ERROR", "payload": {"message": "Invalid message"}})
                continue
            action = message.get("payload", {}).get("action")
            if action not in {"up", "down", "left", "right", "idle"}:
                await connection.send_json({"type": "ERROR", "payload": {"message": "Invalid message"}})
                continue
            room.last_action = action
    except (asyncio.IncompleteReadError, ConnectionError, binascii.Error):
        pass
    finally:
        room.connections.discard(connection)
        await connection.close()


async def handle_http(
    method: str,
    path: str,
    headers: Dict[str, str],
    body: bytes,
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    parsed = urlparse(path)
    if headers.get("upgrade", "").lower() == "websocket" and parsed.path.startswith("/ws/matches/"):
        await handle_match_ws(reader, writer, parsed.path, headers)
        return

    if method == "OPTIONS":
        await send_http_response(writer, "204 No Content", b"", content_type="text/plain")
        return

    if method == "GET" and parsed.path == "/health":
        await send_http_response(writer, "200 OK", json_bytes({"status": "ok"}))
        return

    if method == "GET" and parsed.path == "/":
        await send_http_response(
            writer,
            "200 OK",
            json_bytes(
                {
                    "name": "Agent Arena API",
                    "status": "ok",
                    "message": "Backend is running. Open http://localhost:3000 for the game UI.",
                    "health": "/health",
                    "createMatch": "/matches",
                    "websocket": "/ws/matches/{matchId}",
                }
            ),
        )
        return

    if method == "POST" and parsed.path == "/matches":
        settings = None
        if body:
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                await send_http_response(writer, "400 Bad Request", json_bytes({"detail": "Invalid JSON"}))
                return
            if payload:
                settings = normalize_settings(payload.get("settings"))
        match_id = uuid.uuid4().hex[:8]
        create_room(match_id, settings)
        await send_http_response(writer, "200 OK", json_bytes({"matchId": match_id}))
        return

    await send_http_response(writer, "404 Not Found", json_bytes({"detail": "Not Found"}))


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        method, path, headers, body = await read_http_request(reader)
        await handle_http(method, path, headers, body, reader, writer)
    except ConnectionError:
        writer.close()
        await writer.wait_closed()
    except asyncio.IncompleteReadError:
        writer.close()
        await writer.wait_closed()
    finally:
        if not writer.is_closing():
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass


async def main() -> None:
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "8000"))
    server = await asyncio.start_server(handle_client, host, port)
    sockets = ", ".join(str(sock.getsockname()) for sock in (server.sockets or []))
    print(f"Local API server listening on {sockets}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
