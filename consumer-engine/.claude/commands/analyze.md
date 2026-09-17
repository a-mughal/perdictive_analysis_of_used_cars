---
description: Run the full Consumer Engine on a product (name, Amazon URL, or brief.json path)
---
Run the Consumer Engine protocol in CLAUDE.md on: $ARGUMENTS

Steps:
1. Create `runs/<slug>/` and `brief.json` via `python -m engine.engine init`.
2. Ask the user at most TWO clarifying questions only if the brief is missing target price band
   or target buyer. Otherwise infer and record assumptions in `brief.json.assumptions`.
3. Execute phases 1–8 exactly as CLAUDE.md specifies, validating after every agent.
4. Finish by reading VERDICT.md to the user in ≤ 12 lines and proposing one next action.
