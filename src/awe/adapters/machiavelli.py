from __future__ import annotations

import inspect
from pathlib import Path
import re
from typing import Any, Sequence

from .external_jsonl import ExternalContestantClient


_INPUT_TEXT_PLACEHOLDER_RE = re.compile(r"\buser_input(?:_2)?\b", re.IGNORECASE)


def normalize_machiavelli_text(
    text: str,
    *,
    input_text_value: str | None = None,
) -> str:
    """Normalize maintained-runner placeholders only in contestant-visible text.

    CAIS simple-evals intentionally substitutes ChoiceScript input_text values
    with user_input/user_input_2 so the environment can run non-interactively.
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
    info: dict[str, Any],
    *,
    input_text_value: str | None = None,
) -> dict[str, str]:
    game_state = info.get("game_state")
    if not isinstance(game_state, dict):
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


def _build_env(MachiavelliEnv, *, game: str):
    """Construct an original or maintained MACHIAVELLI environment.

    aypan17 uses ``agent_name`` for contestant provenance; the maintained
    CAIS simple-evals vendored environment uses ``model_name``. Detect the
    upstream contract explicitly and fail closed for unknown signatures.
    """
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
    """Instantiate either the original or modern maintained MACHIAVELLI env.

    The original aypan17 implementation names the provenance field agent_name;
    Center for AI Safety's maintained simple-evals integration names it
    model_name. Both retain the native trajectory/evaluator semantics.
    """
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
    """Run Ferro through a pinned MACHIAVELLI env and save native trajectories."""
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
                    client.begin_episode(
                        benchmark_id="machiavelli",
                        episode_id=f"{game}:{episode_idx}",
                        title=str(info.get("title") or game),
                        metadata={
                            "game": game,
                            "summary": info.get("summary"),
                            "player_character": info.get("player_character"),
                            "game_achievements": info.get("game_achievements"),
                            "max_points": info.get("max_points"),
                            "input_text_value": input_text_value,
                        },
                    )
                    reward = 0
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
                            context={
                                "reward_from_previous_step": reward,
                                "game_state": info.get("game_state"),
                            },
                        )
                        action_id = str(decision["action_id"])
                        action_index = int(action_id)
                        obs, reward, done, next_info = env.step(action_index)
                        next_state = next_info.get("game_state")
                        next_state = next_state if isinstance(next_state, dict) else {}
                        client.outcome(
                            action=actions[action_id],
                            outcome=normalize_machiavelli_text(
                                str(obs),
                                input_text_value=input_text_value,
                            ),
                            public_state={
                                "reward": reward,
                                "done": done,
                                "new_achievements": next_state.get("new_achievements", []),
                                "points": next_state.get("points"),
                            },
                        )
                        info = next_info
                        step_count += 1

                    outdir = root / "Ferro_AWE" / game
                    outdir.mkdir(parents=True, exist_ok=True)
                    outfile = outdir / f"{env.trajectory.timestamp}.pkl"
                    env.trajectory.save(outfile)
                    outputs.append(outfile)
            finally:
                env.close()
    return outputs
