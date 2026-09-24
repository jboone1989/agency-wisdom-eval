from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from .external_jsonl import ExternalContestantClient


def choice_map(info: dict[str, Any]) -> dict[str, str]:
    game_state = info.get("game_state")
    if not isinstance(game_state, dict):
        raise ValueError("MACHIAVELLI info missing game_state")
    choices = game_state.get("choice_texts")
    if not isinstance(choices, list) or not choices:
        raise ValueError("MACHIAVELLI info missing choice_texts")
    return {str(index): str(text) for index, text in enumerate(choices)}


def run_machiavelli(
    contestant_command: Sequence[str],
    *,
    traj_dir: str | Path,
    games: Sequence[str] | None = None,
    num_episodes: int = 1,
    max_traj_length: int = 1000,
) -> list[Path]:
    """Run Ferro through the official MACHIAVELLI env and save native trajectories."""
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
            env = MachiavelliEnv(game=game, agent_name="Ferro/AWE")
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
                        },
                    )
                    reward = 0
                    done = False
                    step_count = 0
                    while not done and step_count < int(max_traj_length):
                        actions = choice_map(info)
                        decision = client.choose(
                            observation=str(obs),
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
                            outcome=str(obs),
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
