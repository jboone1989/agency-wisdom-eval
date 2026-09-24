from __future__ import annotations
import json, sys
for line in sys.stdin:
    request=json.loads(line)
    kind=request.get("type")
    if kind=="close":
        break
    if kind=="begin_scenario":
        print('{"ok":true}', flush=True)
    elif kind=="decide":
        print('{"ok":false,"error":"LLMProviderError","detail":"no viable route"}', flush=True)
    else:
        print('{"ok":true}', flush=True)
