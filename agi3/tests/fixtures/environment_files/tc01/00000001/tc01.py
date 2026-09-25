"""A two-level clicking game in the real ARC-AGI-3 on-disk format.

A fixture for the offline pipeline, like tw01: it measures nothing. It takes
only ACTION6 (a click at x, y). Clicking the colour-3 block clears the level;
the colour-7 blocks are distractors and do nothing. The target moves between
levels, so a click must carry the right coordinates to succeed.
"""

from arcengine import ARCBaseGame, Camera, GameAction, Level, Sprite


def _block(colour: int, name: str, x: int, y: int) -> Sprite:
    return Sprite([[colour] * 4 for _ in range(4)], name=name, x=x, y=y, layer=1)

def _level(target: tuple[int, int]) -> Level:
    sprites = [
        _block(7, "distractor-a", 8, 8),
        _block(7, "distractor-b", 50, 50),
        _block(3, "target", *target),
    ]
    return Level(sprites=sprites, grid_size=(64, 64))

class Tc01(ARCBaseGame):
    def __init__(self, seed: int = 0) -> None:
        super().__init__(
            game_id="tc01",
            levels=[_level((30, 12)), _level((12, 44))],
            camera=Camera(background=0),
            available_actions=[6],
            seed=seed,
        )

    def step(self) -> None:
        if self.action.id is GameAction.ACTION6:
            x = int(self.action.data.get("x", -1))
            y = int(self.action.data.get("y", -1))
            target = self.current_level.get_sprites_by_name("target")[0]
            if target.x <= x < target.x + 4 and target.y <= y < target.y + 4:
                self.next_level()
        self.complete_action()
