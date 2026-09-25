"""Tests for the policy router and for the adapter's per-agent click payload."""

from __future__ import annotations

from arcengine import FrameData, GameAction, GameState
from arcengine.enums import ActionInput

from arcagi3.clicker import ClickAgent
from arcagi3.navigator import NavigatorAgent
from arcagi3.router import RoutingAgent
from arcagi3.sdk_adapter import SDKPolicyAdapter, mouse_action

BOARD = [[0] * 8 for _ in range(8)]


def frame(available: tuple[int, ...], state: GameState = GameState.NOT_FINISHED) -> FrameData:
    return FrameData(
        game_id="t",
        frame=[BOARD],
        state=state,
        levels_completed=0,
        win_levels=3,
        action_input=ActionInput(id=GameAction.RESET, data={}),
        guid=None,
        full_reset=False,
        available_actions=list(available),
    )


# --- routing ---------------------------------------------------------------


def test_directions_on_offer_means_walk():
    router = RoutingAgent()
    router.choose_action([], frame((1, 2, 3, 4, 5)))
    assert isinstance(router.chosen, NavigatorAgent)


def test_click_without_directions_means_click():
    router = RoutingAgent()
    router.choose_action([], frame((6,)))
    assert isinstance(router.chosen, ClickAgent)


def test_both_offered_prefers_walking():
    """A game that offers directions is walked even if it also takes clicks."""
    router = RoutingAgent()
    router.choose_action([], frame((1, 2, 3, 4, 6)))
    assert isinstance(router.chosen, NavigatorAgent)


def test_the_choice_is_kept_for_the_whole_game():
    router = RoutingAgent()
    router.choose_action([], frame((6,)))
    first = router.chosen
    router.choose_action([], frame((1, 2, 3, 4)))
    assert router.chosen is first


def test_no_informative_actions_defers_the_choice_and_never_clicks_blind():
    router = RoutingAgent()
    action = router.choose_action([], frame((5,)))
    assert router.chosen is None
    assert action is GameAction.ACTION5


def test_only_a_win_ends_play_so_game_over_is_retried():
    router = RoutingAgent()
    assert router.is_done([], frame((1,), GameState.WIN))
    assert not router.is_done([], frame((1,), GameState.GAME_OVER))


# --- the shared click payload ---------------------------------------------


class RecordingEnv:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    def step(self, action, data=None, reasoning=None):
        self.sent.append(dict(data or {}))
        return "raw"


class FrameworkAgent:
    """Stands in for the runner's Agent: reads the payload off the shared member."""

    def __init__(self) -> None:
        self.arc_env = RecordingEnv()

    def do_action_request(self, action):
        return self.arc_env.step(action, data=action.action_data.model_dump())

    def _convert_raw_frame_data(self, raw):
        return raw


class FixedClicker(ClickAgent):
    def __init__(self, cell: tuple[int, int]) -> None:
        super().__init__()
        self.cell = cell

    def choose_action(self, frames, latest):
        self._target = self.cell
        return GameAction.ACTION6


def clicking_agent(cell: tuple[int, int]):
    class Agent(SDKPolicyAdapter, FrameworkAgent):
        policy_factory = staticmethod(lambda: FixedClicker(cell))

    return Agent()


def test_the_shared_member_really_is_overwritten_by_another_agent():
    """Why the adapter has to carry its own payload at all."""
    a = mouse_action(1, 1)
    mouse_action(5, 5)
    assert a.action_data.model_dump()["x"] == 5


def test_each_agent_sends_its_own_click_when_games_interleave():
    """Game A chooses, game B chooses, then A's request goes out — as Swarm threads can."""
    game_a, game_b = clicking_agent((1, 2)), clicking_agent((5, 6))
    click_a = game_a.choose_action([], frame((6,)))
    click_b = game_b.choose_action([], frame((6,)))

    game_a.do_action_request(click_a)
    game_b.do_action_request(click_b)

    assert game_a.arc_env.sent == [{"game_id": "", "x": 2, "y": 1}]
    assert game_b.arc_env.sent == [{"game_id": "", "x": 6, "y": 5}]


def test_non_click_actions_go_through_the_runner_unchanged():
    agent = clicking_agent((1, 2))
    agent.do_action_request(GameAction.ACTION1)
    assert agent.arc_env.sent == [{"game_id": ""}]
