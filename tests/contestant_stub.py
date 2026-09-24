from __future__ import annotations

import json
import sys

for line in sys.stdin:
    request = json.loads(line)
    kind = request.get("type")
    if kind == "close":
        break
    if kind in {"begin_scenario", "outcome"}:
        print('{"ok":true}', flush=True)
        continue
    if kind == "decide":
        actions = request.get("actions") or {}
        chosen = "best" if "best" in actions else next(iter(actions))
        print(json.dumps({"action_id": chosen, "declared_confidence": 0.9}), flush=True)
        continue
    print('{"ok":false}', flush=True)
