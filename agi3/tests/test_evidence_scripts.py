"""The mock half of failure one, pinned: the figure the writeup now quotes.

The real half needs the recorded runs, which are not in the repository; the
script itself reports them. Here only what our own environments produce.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from object_matching import mock_rate  # noqa: E402

from arcagi3.mock import MockEnvironment  # noqa: E402
from arcagi3.noisy_mock import NoisyEnvironment  # noqa: E402


def test_the_quiet_mock_nearly_always_shows_one_clean_movement():
    moves, sole = mock_rate(MockEnvironment, 500)
    assert (moves, sole) == (500, 474)  # 94.8%, quoted as 95%


def test_the_noisy_mock_never_does():
    moves, sole = mock_rate(NoisyEnvironment, 500)
    assert moves == 500 and sole == 0
