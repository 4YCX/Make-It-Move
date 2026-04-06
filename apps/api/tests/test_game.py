import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.game import CHASER_VISION_RADIUS, GRID_SIZE, TASK_COUNT, create_match_state, decide_winner, step_state


class GameFlowTests(unittest.TestCase):
    def test_create_match_state_has_expected_defaults(self):
        state = create_match_state()

        self.assertEqual(state["status"], "running")
        self.assertEqual(state["winner"], None)
        self.assertEqual(state["gridSize"], GRID_SIZE)
        self.assertEqual(state["settings"], {"agentSpeed": "slow", "obstacleDensity": "medium", "layoutTransform": False})
        self.assertEqual(state["human"], {"x": 1, "y": 1, "score": 0})
        self.assertEqual(state["agent"], {"x": GRID_SIZE - 2, "y": GRID_SIZE - 2, "score": 0})
        self.assertEqual(len(state["tasks"]), TASK_COUNT)
        self.assertGreater(len(state["walls"]), 0)
        self.assertGreater(len(state["swamps"]), 0)
        self.assertEqual(state["agentVisionRadius"], CHASER_VISION_RADIUS)
        self.assertEqual(state["settings"]["layoutTransform"], False)
        self.assertEqual(state["remainingMs"], 120000)
        self.assertEqual(len(state["scheduledEvents"]), 5)

    def test_create_match_state_accepts_settings(self):
        state = create_match_state({"agentSpeed": "normal", "obstacleDensity": "tight", "layoutTransform": True})

        self.assertEqual(state["settings"], {"agentSpeed": "normal", "obstacleDensity": "tight", "layoutTransform": True})
        self.assertGreater(len(state["walls"]), len(create_match_state({"obstacleDensity": "loose"})["walls"]))

    @patch("app.game.choose_agent_action", return_value="idle")
    def test_runner_completes_task_and_score_increases(self, _mock_choose_agent_action):
        state = create_match_state()
        state["tasks"] = [{"id": "task-1", "x": 2, "y": 1, "completed": False}]
        state["walls"] = []
        state["swamps"] = []

        next_state = step_state(state, "right")

        self.assertEqual(next_state["human"]["x"], 2)
        self.assertEqual(next_state["human"]["score"], 1)
        self.assertTrue(next_state["tasks"][0]["completed"])

    @patch("app.game.choose_agent_action", return_value="idle")
    def test_swamp_applies_stun(self, _mock_choose_agent_action):
        state = create_match_state()
        state["tasks"] = []
        state["walls"] = []
        state["swamps"] = [{"id": "swamp-1", "x": 2, "y": 1}]

        next_state = step_state(state, "right")

        self.assertEqual(next_state["human"]["x"], 2)
        self.assertGreater(next_state["humanStunTicks"], 0)

    @patch("app.game.choose_agent_action", return_value="left")
    def test_slow_agent_moves_every_other_tick(self, _mock_choose_agent_action):
        state = create_match_state({"agentSpeed": "slow"})
        state["tasks"] = []
        state["walls"] = []
        state["swamps"] = []

        first_state = step_state(state, "idle")
        second_state = step_state(first_state, "idle")

        self.assertEqual(first_state["agent"]["x"], GRID_SIZE - 3)
        self.assertEqual(second_state["agent"]["x"], GRID_SIZE - 3)

    @patch("app.game.choose_agent_action", return_value="idle")
    def test_walls_block_runner_movement(self, _mock_choose_agent_action):
        state = create_match_state()
        state["tasks"] = []
        state["walls"] = [{"id": "v-1-1", "x": 1, "y": 1, "orientation": "vertical"}]
        state["swamps"] = []

        next_state = step_state(state, "right")

        self.assertEqual(next_state["human"]["x"], 1)
        self.assertEqual(next_state["human"]["y"], 1)

    @patch("app.game.choose_agent_action", return_value="idle")
    def test_random_event_can_freeze_agent(self, _mock_choose_agent_action):
        state = create_match_state()
        state["tasks"] = []
        state["walls"] = []
        state["swamps"] = []
        state["scheduledEvents"] = [{"tick": 80, "type": "freeze"}]
        state["tick"] = 79

        next_state = step_state(state, "idle")

        self.assertGreater(next_state["agentStunTicks"], 0)
        self.assertIn("frozen", next_state["latestEvent"])

    @patch("app.game.choose_agent_action", return_value="idle")
    def test_time_runs_out_and_runner_loses_without_tasks(self, _mock_choose_agent_action):
        state = create_match_state()
        state["remainingMs"] = 100
        state["tasks"] = [{"id": "task-1", "x": 10, "y": 10, "completed": False}]
        state["walls"] = []
        state["swamps"] = []

        next_state = step_state(state, "idle")

        self.assertEqual(next_state["remainingMs"], 0)
        self.assertEqual(next_state["status"], "finished")
        self.assertEqual(next_state["winner"], "agent")

    def test_generated_map_keeps_tasks_reachable(self):
        state = create_match_state({"obstacleDensity": "tight"})
        for task in state["tasks"]:
            self.assertNotEqual((task["x"], task["y"]), (1, 1))

    def test_layout_transform_starts_on_schedule(self):
        state = create_match_state({"layoutTransform": True})
        state["tick"] = 49

        next_state = step_state(state, "idle")

        self.assertGreater(next_state["layoutTransformTicks"], 0)
        self.assertGreater(len(next_state["highlightedWalls"]), 0)

    def test_decide_winner(self):
        self.assertEqual(decide_winner({"winner": "human"}), "human")
        self.assertEqual(decide_winner({"winner": "agent"}), "agent")
        self.assertEqual(decide_winner({"winner": None}), "draw")


if __name__ == "__main__":
    unittest.main()
