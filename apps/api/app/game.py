from __future__ import annotations

import random
from collections import deque
from copy import deepcopy
from typing import Dict, Literal, Tuple, TypedDict

GRID_SIZE = 20
MATCH_DURATION_MS = 120_000
TICK_RATE_MS = 100
TASK_COUNT = 3
DEFAULT_AGENT_SPEED = "slow"
DEFAULT_OBSTACLE_DENSITY = "medium"
AGENT_SPEED_CADENCE = {"slow": 2, "normal": 1, "fast": 1}
WALL_COUNT_BY_DENSITY = {"loose": 42, "medium": 72, "tight": 108}
SWAMP_COUNT_BY_DENSITY = {"loose": 4, "medium": 7, "tight": 10}
FREEZE_TICKS = 40
BOOST_TICKS = 40
SWAMP_STUN_TICKS = 6
CHASER_VISION_RADIUS = 6
EVENT_FREEZE_TICKS = 40
LAYOUT_TRANSFORM_SCHEDULE = {50, 350, 650, 950}
WALL_DECAY_SCHEDULE = {150, 300, 450, 600, 750, 900, 1050}
ACTIONS = ["up", "down", "left", "right", "idle"]
ACTION_DELTAS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
REVERSE_ACTION = {"up": "down", "down": "up", "left": "right", "right": "left"}

AgentSpeed = Literal["slow", "normal", "fast"]
ObstacleDensity = Literal["loose", "medium", "tight"]
Coord = Tuple[int, int]
Orientation = Literal["horizontal", "vertical"]


class MatchSettings(TypedDict):
    agentSpeed: AgentSpeed
    obstacleDensity: ObstacleDensity
    layoutTransform: bool


def default_settings() -> MatchSettings:
    return {"agentSpeed": DEFAULT_AGENT_SPEED, "obstacleDensity": DEFAULT_OBSTACLE_DENSITY, "layoutTransform": False}


def normalize_settings(settings: Dict | None) -> MatchSettings:
    base = default_settings()
    if not settings:
        return base

    agent_speed = settings.get("agentSpeed")
    obstacle_density = settings.get("obstacleDensity")
    layout_transform = settings.get("layoutTransform")
    if agent_speed in AGENT_SPEED_CADENCE:
        base["agentSpeed"] = agent_speed
    if obstacle_density in WALL_COUNT_BY_DENSITY:
        base["obstacleDensity"] = obstacle_density
    if isinstance(layout_transform, bool):
        base["layoutTransform"] = layout_transform
    return base


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def move_position(x: int, y: int, action: str) -> Coord:
    dx, dy = ACTION_DELTAS.get(action, (0, 0))
    return clamp(x + dx, 0, GRID_SIZE - 1), clamp(y + dy, 0, GRID_SIZE - 1)


def sample_free_cell(occupied: set[Coord]) -> Dict[str, int | str]:
    while True:
        x = random.randint(0, GRID_SIZE - 1)
        y = random.randint(0, GRID_SIZE - 1)
        if (x, y) not in occupied:
            occupied.add((x, y))
            return {"id": f"{x}-{y}-{random.randint(1000, 9999)}", "x": x, "y": y}


def wall_id(orientation: Orientation, x: int, y: int) -> str:
    return f"{orientation[0]}-{x}-{y}"


def wall_key(orientation: Orientation, x: int, y: int) -> tuple[str, int, int]:
    return orientation, x, y


def sample_wall(used: set[tuple[str, int, int]]) -> Dict[str, int | str]:
    while True:
        orientation: Orientation = random.choice(["horizontal", "vertical"])
        if orientation == "horizontal":
            x = random.randint(0, GRID_SIZE - 1)
            y = random.randint(0, GRID_SIZE - 2)
        else:
            x = random.randint(0, GRID_SIZE - 2)
            y = random.randint(0, GRID_SIZE - 1)
        key = wall_key(orientation, x, y)
        if key not in used:
            used.add(key)
            return {"id": wall_id(orientation, x, y), "x": x, "y": y, "orientation": orientation}


def build_scheduled_random_events() -> list[Dict[str, int | str]]:
    total_ticks = MATCH_DURATION_MS // TICK_RATE_MS
    bucket_size = total_ticks // 5
    reserved_ticks = sorted(LAYOUT_TRANSFORM_SCHEDULE | WALL_DECAY_SCHEDULE)
    event_types = ["freeze", "boost", "freeze", "boost", random.choice(["freeze", "boost"])]
    random.shuffle(event_types)
    scheduled_events: list[Dict[str, int | str]] = []

    for index, event_type in enumerate(event_types):
        start = index * bucket_size + bucket_size // 4
        end = (index + 1) * bucket_size - bucket_size // 4
        candidates = [
            tick
            for tick in range(start, end)
            if all(abs(tick - reserved_tick) > 35 for reserved_tick in reserved_ticks)
        ]
        chosen_tick = random.choice(candidates) if candidates else start
        scheduled_events.append({"tick": chosen_tick, "type": event_type})

    return sorted(scheduled_events, key=lambda event: int(event["tick"]))


def movement_blocked_by_wall(walls: list[Dict], x: int, y: int, action: str) -> bool:
    if action == "right":
        return any(w["orientation"] == "vertical" and w["x"] == x and w["y"] == y for w in walls)
    if action == "left":
        return x > 0 and any(w["orientation"] == "vertical" and w["x"] == x - 1 and w["y"] == y for w in walls)
    if action == "down":
        return any(w["orientation"] == "horizontal" and w["x"] == x and w["y"] == y for w in walls)
    if action == "up":
        return y > 0 and any(w["orientation"] == "horizontal" and w["x"] == x and w["y"] == y - 1 for w in walls)
    return False


def resolve_move(state: Dict, x: int, y: int, action: str) -> Coord:
    if action not in ACTION_DELTAS:
        return x, y
    if movement_blocked_by_wall(state.get("walls", []), x, y, action):
        return x, y
    return move_position(x, y, action)


def neighbors(state: Dict, x: int, y: int) -> list[tuple[str, Coord]]:
    result: list[tuple[str, Coord]] = []
    for action in ("up", "down", "left", "right"):
        next_x, next_y = resolve_move(state, x, y, action)
        if (next_x, next_y) != (x, y):
            result.append((action, (next_x, next_y)))
    return result


def bfs_path(state: Dict, start: Coord, goal: Coord) -> list[str]:
    if start == goal:
        return []

    queue = deque([start])
    parents: dict[Coord, tuple[Coord | None, str | None]] = {start: (None, None)}

    while queue:
        current = queue.popleft()
        if current == goal:
            break
        for action, neighbor in neighbors(state, current[0], current[1]):
            if neighbor in parents:
                continue
            parents[neighbor] = (current, action)
            queue.append(neighbor)

    if goal not in parents:
        return []

    actions: list[str] = []
    cursor = goal
    while parents[cursor][0] is not None:
        parent, action = parents[cursor]
        if action is None:
            break
        actions.append(action)
        cursor = parent  # type: ignore[assignment]
    actions.reverse()
    return actions


def create_reachable_walls(task_cells: list[Coord], target: int) -> list[Dict]:
    walls: list[Dict] = []
    used: set[tuple[str, int, int]] = set()
    critical_targets = [(1, 1), (GRID_SIZE - 2, GRID_SIZE - 2), *task_cells]

    attempts = 0
    while len(walls) < target and attempts < target * 40:
        attempts += 1
        candidate = sample_wall(used)
        tentative = walls + [candidate]
        probe_state = {"walls": tentative}
        if all(bfs_path(probe_state, (1, 1), target_cell) for target_cell in critical_targets[1:]):
            walls = tentative
        else:
            used.discard(wall_key(candidate["orientation"], candidate["x"], candidate["y"]))  # type: ignore[index]
    return walls


def create_match_state(settings: Dict | None = None) -> Dict:
    resolved_settings = normalize_settings(settings)
    occupied: set[Coord] = {(1, 1), (GRID_SIZE - 2, GRID_SIZE - 2)}
    tasks = [{**sample_free_cell(occupied), "completed": False} for _ in range(TASK_COUNT)]
    swamps = [sample_free_cell(occupied) for _ in range(SWAMP_COUNT_BY_DENSITY[resolved_settings["obstacleDensity"]])]
    walls = create_reachable_walls(
        [(task["x"], task["y"]) for task in tasks], WALL_COUNT_BY_DENSITY[resolved_settings["obstacleDensity"]]
    )
    return {
        "tick": 0,
        "remainingMs": MATCH_DURATION_MS,
        "status": "running",
        "winner": None,
        "gridSize": GRID_SIZE,
        "settings": resolved_settings,
        "human": {"x": 1, "y": 1, "score": 0},
        "agent": {"x": GRID_SIZE - 2, "y": GRID_SIZE - 2, "score": 0},
        "walls": walls,
        "swamps": swamps,
        "tasks": tasks,
        "latestEvent": "Runner must finish all tasks and survive for 60 seconds.",
        "humanStunTicks": 0,
        "agentStunTicks": 0,
        "agentBoostTicks": 0,
        "agentVisionRadius": CHASER_VISION_RADIUS,
        "agentLastSeen": None,
        "agentPatrolDirection": "left",
        "agentStuckTicks": 0,
        "activeEventType": None,
        "eventDisplayTicks": 0,
        "layoutTransformTicks": 0,
        "layoutTransformPendingCount": 0,
        "highlightedWalls": [],
        "completedTransforms": 0,
        "pendingEventAction": None,
        "scheduledEvents": build_scheduled_random_events(),
    }


def is_swamp(state: Dict, x: int, y: int) -> bool:
    return any(item["x"] == x and item["y"] == y for item in state.get("swamps", []))


def can_agent_see_runner(state: Dict) -> bool:
    agent = (state["agent"]["x"], state["agent"]["y"])
    human = (state["human"]["x"], state["human"]["y"])
    path = bfs_path(state, agent, human)
    return bool(path) and len(path) <= state.get("agentVisionRadius", CHASER_VISION_RADIUS)


def choose_patrol_action(state: Dict) -> str:
    start = (state["agent"]["x"], state["agent"]["y"])
    preferred = state.get("agentPatrolDirection", "left")
    valid_actions = [action for action, _neighbor in neighbors(state, start[0], start[1])]
    if not valid_actions:
        return "idle"

    if preferred in valid_actions:
        return preferred

    non_reverse = [action for action in valid_actions if action != REVERSE_ACTION.get(preferred)]
    if non_reverse:
        action = random.choice(non_reverse)
    else:
        action = random.choice(valid_actions)
    state["agentPatrolDirection"] = action
    return action


def choose_agent_action(state: Dict) -> str:
    agent = (state["agent"]["x"], state["agent"]["y"])
    human = (state["human"]["x"], state["human"]["y"])

    if can_agent_see_runner(state):
        state["agentLastSeen"] = {"x": human[0], "y": human[1]}
        path = bfs_path(state, agent, human)
        if path:
            state["agentPatrolDirection"] = path[0]
            return path[0]

    last_seen = state.get("agentLastSeen")
    if isinstance(last_seen, dict):
        target = (last_seen["x"], last_seen["y"])
        if target != agent:
            path = bfs_path(state, agent, target)
            if path:
                state["agentPatrolDirection"] = path[0]
                return path[0]

    if state.get("agentStuckTicks", 0) >= 2:
        for action in ("up", "right", "down", "left"):
            next_x, next_y = resolve_move(state, agent[0], agent[1], action)
            if (next_x, next_y) != agent:
                state["agentPatrolDirection"] = action
                state["agentStuckTicks"] = 0
                return action

    return choose_patrol_action(state)


def should_move_agent(state: Dict) -> bool:
    if state["agentBoostTicks"] > 0:
        return True
    cadence = AGENT_SPEED_CADENCE[state["settings"]["agentSpeed"]]
    return state["tick"] % cadence == 0


def complete_tasks(state: Dict) -> None:
    human = state["human"]
    for task in state["tasks"]:
        if not task["completed"] and task["x"] == human["x"] and task["y"] == human["y"]:
            task["completed"] = True
            human["score"] += 1
            state["latestEvent"] = f"Task secured: {human['score']}/{TASK_COUNT} objectives complete."
            state["activeEventType"] = "task"
            state["eventDisplayTicks"] = 10


def apply_swamp_effects(state: Dict, previous_positions: dict[str, Coord]) -> None:
    for actor_key, stun_key in (("human", "humanStunTicks"), ("agent", "agentStunTicks")):
        actor = state[actor_key]
        if previous_positions[actor_key] == (actor["x"], actor["y"]):
            continue
        if is_swamp(state, actor["x"], actor["y"]):
            state[stun_key] = max(state[stun_key], SWAMP_STUN_TICKS)
            state["latestEvent"] = (
                "Runner hit a swamp and is stuck for a moment."
                if actor_key == "human"
                else "Chaser got dragged down by a swamp."
            )


def trigger_random_event(state: Dict, event: str) -> None:
    if event == "freeze":
        state["agentStunTicks"] = max(state["agentStunTicks"], FREEZE_TICKS)
        state["latestEvent"] = "Random event: the chaser is frozen."
        state["activeEventType"] = "freeze"
    elif event == "boost":
        state["agentBoostTicks"] = max(state["agentBoostTicks"], BOOST_TICKS)
        state["latestEvent"] = "Random event: the chaser bursts into a sprint."
        state["activeEventType"] = "boost"
    state["eventDisplayTicks"] = EVENT_FREEZE_TICKS


def begin_layout_transform(state: Dict) -> None:
    if not state["settings"].get("layoutTransform"):
        return
    walls = state["walls"]
    if not walls:
        return
    removal_count = max(10, len(walls) // 3)
    highlighted = random.sample(walls, min(removal_count, len(walls)))
    state["highlightedWalls"] = [wall["id"] for wall in highlighted]
    state["layoutTransformPendingCount"] = max(8, len(walls) - len(highlighted))
    state["layoutTransformTicks"] = EVENT_FREEZE_TICKS
    state["completedTransforms"] += 1
    state["latestEvent"] = "Layout transform incoming. Maze shift in progress."
    state["activeEventType"] = "transform"
    state["eventDisplayTicks"] = EVENT_FREEZE_TICKS
    state["pendingEventAction"] = "transform"


def apply_layout_transform(state: Dict) -> None:
    state["walls"] = create_reachable_walls(
        [(task["x"], task["y"]) for task in state["tasks"]],
        state["layoutTransformPendingCount"],
    )
    state["highlightedWalls"] = []
    state["layoutTransformPendingCount"] = 0
    state["latestEvent"] = "Layout transform complete. Surviving walls have shifted."
    state["activeEventType"] = "transform"
    state["eventDisplayTicks"] = 0
    state["layoutTransformTicks"] = 0
    state["pendingEventAction"] = None


def begin_wall_decay(state: Dict) -> None:
    walls = state["walls"]
    if len(walls) <= 8:
        return
    removal_count = max(6, len(walls) // 5)
    highlighted = random.sample(walls, min(removal_count, len(walls)))
    state["highlightedWalls"] = [wall["id"] for wall in highlighted]
    state["layoutTransformTicks"] = EVENT_FREEZE_TICKS
    state["latestEvent"] = "Wall decay detected. Highlighted barriers are about to collapse."
    state["activeEventType"] = "decay"
    state["eventDisplayTicks"] = EVENT_FREEZE_TICKS
    state["pendingEventAction"] = "decay"


def apply_wall_decay(state: Dict) -> None:
    highlighted = set(state["highlightedWalls"])
    state["walls"] = [wall for wall in state["walls"] if wall["id"] not in highlighted]
    state["highlightedWalls"] = []
    state["latestEvent"] = "Wall decay complete. Some barriers have vanished."
    state["activeEventType"] = "decay"
    state["eventDisplayTicks"] = 0
    state["layoutTransformTicks"] = 0
    state["pendingEventAction"] = None


def resolve_actor_move(state: Dict, actor_key: str, stun_key: str, action: str) -> bool:
    actor = state[actor_key]
    if state[stun_key] > 0:
        state[stun_key] -= 1
        return False
    next_x, next_y = resolve_move(state, actor["x"], actor["y"], action)
    moved = (next_x, next_y) != (actor["x"], actor["y"])
    actor["x"] = next_x
    actor["y"] = next_y
    return moved


def step_state(state: Dict, human_action: str) -> Dict:
    if state["status"] != "running":
        return deepcopy(state)

    new_state = deepcopy(state)
    special_event_active = new_state.get("pendingEventAction") in {"transform", "decay"} or (
        new_state.get("activeEventType") in {"freeze", "boost"} and new_state["eventDisplayTicks"] > 0
    )
    if new_state["eventDisplayTicks"] > 0:
        new_state["eventDisplayTicks"] -= 1
        if new_state["layoutTransformTicks"] > 0:
            new_state["layoutTransformTicks"] -= 1
        if special_event_active:
            if new_state["eventDisplayTicks"] == 0:
                if new_state.get("pendingEventAction") == "transform":
                    apply_layout_transform(new_state)
                elif new_state.get("pendingEventAction") == "decay":
                    apply_wall_decay(new_state)
            return new_state

    previous_positions = {
        "human": (new_state["human"]["x"], new_state["human"]["y"]),
        "agent": (new_state["agent"]["x"], new_state["agent"]["y"]),
    }

    resolve_actor_move(new_state, "human", "humanStunTicks", human_action)

    if new_state["agentBoostTicks"] > 0:
        new_state["agentBoostTicks"] -= 1

    agent_action = choose_agent_action(new_state) if should_move_agent(new_state) else "idle"
    agent_moved = resolve_actor_move(new_state, "agent", "agentStunTicks", agent_action)

    if should_move_agent(new_state) and not agent_moved and new_state["agentStunTicks"] == 0:
        new_state["agentStuckTicks"] = new_state.get("agentStuckTicks", 0) + 1
    else:
        new_state["agentStuckTicks"] = 0

    apply_swamp_effects(new_state, previous_positions)
    complete_tasks(new_state)

    if (new_state["human"]["x"], new_state["human"]["y"]) == (new_state["agent"]["x"], new_state["agent"]["y"]):
        new_state["status"] = "finished"
        new_state["winner"] = "agent"
        new_state["agent"]["score"] = 1
        new_state["latestEvent"] = "The chaser caught the runner."

    new_state["tick"] += 1
    new_state["remainingMs"] = max(0, new_state["remainingMs"] - TICK_RATE_MS)

    scheduled_event = next((event for event in new_state["scheduledEvents"] if event["tick"] == new_state["tick"]), None)
    if new_state["status"] == "running" and scheduled_event is not None:
        trigger_random_event(new_state, str(scheduled_event["type"]))

    if (
        new_state["status"] == "running"
        and new_state["settings"].get("layoutTransform")
        and new_state["tick"] in LAYOUT_TRANSFORM_SCHEDULE
    ):
        begin_layout_transform(new_state)

    if (
        new_state["status"] == "running"
        and new_state["settings"].get("layoutTransform")
        and new_state["tick"] in WALL_DECAY_SCHEDULE
    ):
        begin_wall_decay(new_state)

    if new_state["remainingMs"] <= 0 and new_state["status"] == "running":
        new_state["status"] = "finished"
        if all(task["completed"] for task in new_state["tasks"]):
            new_state["winner"] = "human"
            new_state["latestEvent"] = "The runner survived and completed every task."
        else:
            new_state["winner"] = "agent"
            new_state["latestEvent"] = "Time is up. The runner failed to finish the objectives."

    return new_state


def decide_winner(state: Dict) -> str:
    winner = state.get("winner")
    if winner in {"human", "agent"}:
        return winner
    return "draw"
