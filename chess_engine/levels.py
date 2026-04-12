"""Skill-level configurations (1–10).

Each level maps to a ``SearchConfig`` plus the set of ``Evaluator`` strategies
to compose.  Higher levels search deeper, use more evaluation components,
and add less noise.
"""

from __future__ import annotations

from dataclasses import dataclass

from chess_engine.evaluation import (
    CompositeEvaluator,
    Evaluator,
    KingSafetyEvaluator,
    MaterialEvaluator,
    MobilityEvaluator,
    PositionalEvaluator,
)
from chess_engine.search import SearchConfig


@dataclass(frozen=True)
class LevelSpec:
    depth: int
    quiescence: bool
    eval_level: int  # 1-5 → controls which strategies are active
    noise: int  # centipawn noise
    ordering: bool
    time: float  # seconds per move


# fmt: off
LEVELS: dict[int, LevelSpec] = {
    1:  LevelSpec(depth=1, quiescence=False, eval_level=1, noise=50, ordering=False, time=1),
    2:  LevelSpec(depth=1, quiescence=False, eval_level=1, noise=30, ordering=False, time=1),
    3:  LevelSpec(depth=2, quiescence=False, eval_level=2, noise=15, ordering=False, time=2),
    4:  LevelSpec(depth=2, quiescence=True,  eval_level=2, noise=10, ordering=True,  time=2),
    5:  LevelSpec(depth=3, quiescence=True,  eval_level=3, noise=5,  ordering=True,  time=3),
    6:  LevelSpec(depth=3, quiescence=True,  eval_level=3, noise=0,  ordering=True,  time=3),
    7:  LevelSpec(depth=3, quiescence=True,  eval_level=4, noise=0,  ordering=True,  time=5),
    8:  LevelSpec(depth=4, quiescence=True,  eval_level=4, noise=0,  ordering=True,  time=5),
    9:  LevelSpec(depth=4, quiescence=True,  eval_level=5, noise=0,  ordering=True,  time=5),
    10: LevelSpec(depth=99, quiescence=True,  eval_level=5, noise=0,  ordering=True,  time=8),
}
# fmt: on


def build_evaluator(spec: LevelSpec) -> Evaluator:
    """Compose the correct set of evaluation strategies for a given level."""
    strategies: list[Evaluator] = [MaterialEvaluator()]
    if spec.eval_level >= 2:
        strategies.append(PositionalEvaluator())
    if spec.eval_level >= 3:
        strategies.append(MobilityEvaluator())
    if spec.eval_level >= 4:
        strategies.append(KingSafetyEvaluator())
    return CompositeEvaluator(strategies, noise=spec.noise)


def build_search_config(spec: LevelSpec) -> SearchConfig:
    """Create a ``SearchConfig`` from a level specification."""
    return SearchConfig(
        max_depth=spec.depth,
        use_quiescence=spec.quiescence,
        use_ordering=spec.ordering,
        check_bonus=(spec.eval_level >= 5),
        time_limit=spec.time,
    )
