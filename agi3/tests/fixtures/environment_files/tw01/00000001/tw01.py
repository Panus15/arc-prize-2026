"""A two-level walking game in the real ARC-AGI-3 on-disk format.

It exists so the offline pipeline — Arcade in OFFLINE mode, the official
runner's Agent loop, our adapter — can be exercised end to end without the
network.  It is not a model of any real game and nothing is measured on it.

The player (colour 9) moves two cells per action; touching the goal
(colour 3) clears the level.
"""

from arcengine import ARCBaseGame, Camera, GameAction, Level, Sprite

STEP = 2
MOVES = {
    GameAction.ACTION1: (0, -STEP),
    GameAction.ACTION2: (0, STEP),
    GameAction.ACTION3: (-STEP, 0),
    GameAction.ACTION4: (STEP, 0),
}


def _level(goal_x: int) -> Level:
    player = Sprite([[9, 9], [9, 9]], name="player", x=10, y=30, layer=2)
    goal = Sprite([[3, 3], [3, 3]], name="goal", x=goal_x, y=30, layer=1)
    return Level(sprites=[player, goal], grid_size=(64, 64))


class Tw01(ARCBaseGame):
    def __init__(self, seed: int = 0) -> None:
        super().__init__(
            game_id="tw01",
            levels=[_level(30), _level(50)],
            camera=Camera(background=0),
            available_actions=[1, 2, 3, 4],
            seed=seed,
        )

    def step(self) -> None:
        dx, dy = MOVES.get(self.action.id, (0, 0))
        player = self.current_level.get_sprites_by_name("player")[0]
        goal = self.current_level.get_sprites_by_name("goal")[0]
        player.set_position(
            max(0, min(62, player.x + dx)),
            max(0, min(62, player.y + dy)),
        )
        if abs(player.x - goal.x) < 2 and abs(player.y - goal.y) < 2:
            self.next_level()
        self.complete_action()
