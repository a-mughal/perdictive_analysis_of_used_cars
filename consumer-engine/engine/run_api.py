"""
Standalone runner: drives the five agents through the Anthropic API when Claude Code is not in use.

  export ANTHROPIC_API_KEY=...
  python -m engine.run_api "magnetic cable clips" --model claude-fable-5-1 [--url ...] [--buyer "..."]

Each agent gets: its .claude/agents/<name>.md body as system prompt, the knowledge files it needs,
the brief, and the previous agents' JSON — exactly what CLAUDE.md says the orchestrator must relay.
Web research uses the API's built-in web_search tool. Output is validated and, on failure, the
agent is asked once to repair only the failing fields.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from . import engine as E

ROOT = E.ROOT
AGENTS = ROOT / ".claude" / "agents"
KNOW = ROOT / "knowledge"

KNOWLEDGE_FOR = {
    "scout": ["02_amazon_buyer_journey.md"],
    "buyer": ["01_consumer_psychology.md", "02_amazon_buyer_journey.md"],
    "innovaty": ["01_consumer_psychology.md", "02_amazon_buyer_journey.md", "03_innovation_playbook.md"],
    "genius": ["04_unit_economics_and_forecasting.md"],
    "critic": ["01_consumer_psychology.md", "02_amazon_buyer_journey.md", "03_innovation_playbook.md", "04_unit_economics_and_forecasting.md"],
}
INPUTS_FOR = {
    "scout": [], "buyer": ["scout"], "innovaty": ["scout", "buyer"],
    "genius": ["scout", "buyer", "innovaty"], "critic": ["scout", "buyer", "innovaty", "genius"],
}
NEEDS_WEB = {"scout": True, "buyer": False, "innovaty": True, "genius": True, "critic": True}


def agent_system(name: str) -> str:
    text = (AGENTS / f"{name}.md").read_text(encoding="utf-8")
    body = re.sub(r"^---.*?---\s*", "", text, flags=re.S)  # strip frontmatter
    return body + ("\n\nYou cannot write files in this mode. Return ONLY the JSON object, no prose, no fences.")


def build_prompt(name: str, run_dir: Path) -> str:
    parts = [f"# Phase: {name}\nOutput contract: schemas/{name}.json (below)."]
    parts.append("## brief.json\n" + (run_dir / "brief.json").read_text(encoding="utf-8"))
    for k in KNOWLEDGE_FOR[name]:
        parts.append(f"## knowledge/{k}\n" + (KNOW / k).read_text(encoding="utf-8"))
    for prev in INPUTS_FOR[name]:
        p = run_dir / f"{prev}.json"
        parts.append(f"## {prev}.json\n" + p.read_text(encoding="utf-8"))
    parts.append(f"## schemas/{name}.json\n" + (E.SCHEMAS / f"{name}.json").read_text(encoding="utf-8"))
    parts.append("## schemas/_range.json\n" + (E.SCHEMAS / "_range.json").read_text(encoding="utf-8"))
    parts.append(f"Return only the JSON object for schemas/{name}.json, nothing else.")
    return "\n\n".join(parts)


def extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def call(client, model: str, system: str, prompt: str, web: bool, max_tokens: int = 16000) -> str:
    tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 15}] if web else []
    msg = client.messages.create(model=model, max_tokens=max_tokens, system=system,
                                 messages=[{"role": "user", "content": prompt}], tools=tools or None)
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


def run_agent(client, model, name, run_dir: Path):
    print(f"→ {name} …", flush=True)
    system, prompt = agent_system(name), build_prompt(name, run_dir)
    out = call(client, model, system, prompt, NEEDS_WEB[name])
    try:
        data = extract_json(out)
    except Exception as e:  # noqa: BLE001
        print(f"   {name}: could not parse JSON ({e}); asking for repair")
        out = call(client, model, system, prompt + f"\n\nYour previous output was not valid JSON: {e}. Return only the JSON object.", False)
        data = extract_json(out)
    E.dump(data, run_dir / f"{name}.json")
    errs = E._jsonschema_validate(data, name) + E._range_rule_errors(data) + E._quote_rule_errors(data)
    if errs:
        print(f"   {name}: {len(errs)} validation problem(s); requesting repair of those fields only")
        fix = call(client, model, system,
                   prompt + "\n\nYour previous JSON:\n" + json.dumps(data) +
                   "\n\nFix ONLY these problems and return the full corrected JSON object:\n- " + "\n- ".join(errs[:40]), False)
        data = extract_json(fix)
        E.dump(data, run_dir / f"{name}.json")
    print(f"   {name}.json written")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("product")
    ap.add_argument("--url")
    ap.add_argument("--buyer", help="one-sentence target buyer", default=None)
    ap.add_argument("--budget", type=float, default=0)
    ap.add_argument("--model", default="claude-fable-5-1")
    ap.add_argument("--only", nargs="*", choices=E.AGENT_FILES, help="run a subset (inputs must exist)")
    a = ap.parse_args(argv)

    try:
        import anthropic
    except ImportError:
        sys.exit("pip install anthropic")
    client = anthropic.Anthropic()

    slug = E.slugify(a.product)
    run_dir = ROOT / "runs" / slug
    if not (run_dir / "brief.json").exists():
        E.cmd_init(run_dir, a.product, a.url)
        brief = E.load(run_dir / "brief.json")
        if a.buyer:
            brief["target_buyer"]["description"] = a.buyer
        if a.budget:
            brief["seller_constraints"]["launch_budget_usd"] = a.budget
        E.dump(brief, run_dir / "brief.json")

    for name in (a.only or E.AGENT_FILES):
        run_agent(client, a.model, name, run_dir)

    E.cmd_score(run_dir)
    E.cmd_verdict(run_dir)


if __name__ == "__main__":
    main()
