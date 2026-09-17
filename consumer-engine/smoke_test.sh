#!/usr/bin/env bash
# Proves the skeleton (validate → score → verdict) runs on synthetic agent output. No API calls.
set -e
rm -rf runs/_fixture && cp -r examples/fixture_run runs/_fixture
python -m engine.engine validate runs/_fixture
python -m engine.engine score    runs/_fixture
python -m engine.engine verdict  runs/_fixture > /dev/null && echo "smoke test passed → runs/_fixture/VERDICT.md"
