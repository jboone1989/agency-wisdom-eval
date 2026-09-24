from __future__ import annotations

import inspect
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from .external_jsonl import ExternalContestantClient


_INPUT_TEXT_PLACEHOLDER_RE = re.compile(r"\buser_input(?:_2)?\b", re.IGNORECASE)


def normalize_machiavelli_text(
    text: str,
    *,
    input_text_value: str | None = None,
) -> str:
    """Normalize maintained-runner placeholders only in contestant-visible text.

    CAIS simple-evals substitutes ChoiceScript input_text values with
    user_input/user_input_2 so the environment can run non-interactively.
    When an evaluation driver knows the intended free-text value, present that
    value to the contestant while leaving native environment state and
    trajectory untouched.
    """
    rendered = str(text)
    replacement = str(input_text_value or "").strip()
    if not replacement:
        return rendered
    return _INPUT_TEXT_PLACEHOLDER_RE.sub(replacement, rendered)


def choice_map(
    info: Mapping[str, Any],
    *,
    input_text_value: str | None = None,
) -> dict[str, str]:
    game_state = info.get("game_state")
    if not isinstance(game_state, Mapping):
        raise ValueError("MACHIAVELLI info missing game_state")
    choices = game_state.get("choice_texts")
    if not isinstance(choices, list) or not choices:
        raise ValueError("MACHIAVELLI info missing choice_texts")
    return {
        str(index): normalize_machiavelli_text(
            str(text), input_text_value=input_text_value
        )
        for index, text in enumerate(choices)
    }


def public_episode_metadata(info: Mapping[str, Any], *, game: str) -> dict[str, str]:
    """Return only metadata shown to the official language-model contestant.

    The upstream info object also contains evaluator and game-engine state such
    as stats, achievements and points. Passing that state to Ferro would make
    external evidence incomparable with the official benchmark.
    """
    summary = info.get("short_summary")
    if summary is None:
        summary = info.get("summary")
    return {
        "game": str(game),
        "title": str(info.get("title") or game),
        "summary": str(summary or ""),
        "player_character": str(info.get("player_character") or ""),
    }


def _build_env(MachiavelliEnv, *, game: str):
    """Construct an original or maintained MACHIAVELLI environment."""
    parameters = inspect.signature(MachiavelliEnv.__init__).parameters
    if "agent_name" in parameters:
        return MachiavelliEnv(game=game, agent_name="Ferro/AWE")
    if "model_name" in parameters:
        return MachiavelliEnv(game=game, model_name="Ferro/AWE")
    raise RuntimeError(
        "unsupported MACHIAVELLI environment constructor: expected "
        "agent_name or model_name provenance parameter"
    )


def create_machiavelli_env(env_class: type, *, game: str):
    """Instantiate either the original or maintained MACHIAVELLI env."""
    parameters = inspect.signature(env_class).parameters
    kwargs: dict[str, Any] = {"game": game}
    if "agent_name" in parameters:
        kwargs["agent_name"] = "Ferro/AWE"
    elif "model_name" in parameters:
        kwargs["model_name"] = "Ferro/AWE"
    else:
        raise RuntimeError(
            "unsupported MACHIAVELLI environment constructor: "
            "expected agent_name or model_name provenance field"
        )
    return env_class(**kwargs)


def run_machiavelli(
    contestant_command: Sequence[str],
    *,
    traj_dir: str | Path,
    games: Sequence[str] | None = None,
    num_episodes: int = 1,
    max_traj_length: int = 1000,
    input_text_value: str | None = None,
) -> list[Path]:
    """Run Ferro through a pinned MACHIAVELLI env and save native trajectories.

    Ferro receives the public game description, current scene and choice texts.
    It does not receive hidden game-state stats, evaluator metrics, rewards,
    points or achievement state.

    Benchmark turns are not written into Ferro durable memory through the
    external outcome channel. AWE longitudinal suites are the place to measure
    learning across evaluation episodes; MACHIAVELLI evidence stays comparable
    to the upstream stateless-per-episode protocol.
    """
    try:
        from machiavelli.config import MachiavelliConfig
        from machiavelli.game.machiavelli_env import MachiavelliEnv
    except ImportError as exc:
        raise RuntimeError("MACHIAVELLI upstream package is not installed") from exc

    cfg = MachiavelliConfig()
    selected_games = list(games or cfg.games_test)
    root = Path(traj_dir)
    outputs: list[Path] = []

    with ExternalContestantClient(contestant_command) as client:
        for game in selected_games:
            env = create_machiavelli_env(MachiavelliEnv, game=game)
            try:
                for episode_idx in range(int(num_episodes)):
                    obs, info = env.reset(seed=episode_idx)
                    metadata = public_episode_metadata(info, game=game)
                    client.begin_episode(
                        benchmark_id="machiavelli",
                        episode_id=f"{game}:{episode_idx}",
                        title=metadata["title"],
                        metadata=metadata,
                    )
                    done = False
                    step_count = 0
                    while not done and step_count < int(max_traj_length):
                        actions = choice_map(
                            info,
                            input_text_value=input_text_value,
                        )
                        decision = client.choose(
                            observation=normalize_machiavelli_text(
                                str(obs),
                                input_text_value=input_text_value,
                            ),
                            actions=actions,
                        )
                        action_id = str(decision["action_id"])
                        action_index = int(action_id)
                        obs, _reward, done, info = env.step(action_index)
                        step_count += 1

                    outdir = root / "Ferro_AWE" / game
                    outdir.mkdir(parents=True, exist_ok=True)
                    outfile = outdir / f"{env.trajectory.timestamp}.pkl"
                    env.trajectory.save(outfile)
                    outputs.append(outfile)
            finally:
                env.close()
    return outputs
