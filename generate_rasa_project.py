#!/usr/bin/env python3
import os
import json
from collections import OrderedDict
# import requests  # No longer needed


# -----------------------------------


# -----------------------------------

# Helper: create folder if missing
def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)

# Helper: save YAML
def yaml_dump(data, filename):
    import yaml
    def convert_odict(obj):
        if isinstance(obj, OrderedDict):
            return {k: convert_odict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_odict(i) for i in obj]
        elif isinstance(obj, dict):
            return {k: convert_odict(v) for k, v in obj.items()}
        else:
            return obj
    with open(filename, "w") as f:
        yaml.safe_dump(convert_odict(data), f, sort_keys=False)

# --- Remove LLM functions and replace with static fallback logic ---

def generate_nlu_examples(intent):
    # Return static fallback examples
    return [f"Example {i+1} for {intent}" for i in range(NUM_NLU_EX)]

# 1) Load config JSON
with open("bot_config.json") as f:
    cfg = json.load(f)
steps = cfg.get("steps", [])
if not steps:
    raise RuntimeError("No steps in bot_config.json")

# 2) Make folders
mkdir("data")
mkdir(os.path.join("actions"))

# 3) Build domain.yml
domain = OrderedDict([
    ("version", "3.1"),
    ("intents", []),
    ("entities", []),
    ("slots", {}),
    ("responses", OrderedDict())
])

# collect intents & entities
for step in steps:
    intent = step["intent"]
    if intent not in domain["intents"]:
        domain["intents"].append(intent)
    # entities
    for ent in step.get("entities", []):
        if isinstance(ent, dict):
            ent_name = ent.get("name")
        else:
            ent_name = ent
        if ent_name and ent_name not in domain["entities"]:
            domain["entities"].append(ent_name)
# fallback intent
if "nlu_fallback" not in domain["intents"]:
    domain["intents"].append("nlu_fallback")

# slots = entities
for ent in domain["entities"]:
    domain["slots"][ent] = {"type": "text"}

# responses (utter_{intent})
for step in steps:
    intent = step["intent"]
    base = step["response"]
    domain["responses"][f"utter_{intent}"] = [{"text": base}]
# default fallback
domain["responses"]["utter_default"] = [{"text": "Sorry, I didn't get that. Could you rephrase?"}]

# cleanup empty sections
if not domain["entities"]: del domain["entities"]
if not domain["slots"]: del domain["slots"]

yaml_dump(domain, "domain.yml")

# 4) Build data/nlu.yml
nlu = ["version: \"3.1\"", "nlu:"]
seen = set()
for step in steps:
    intent = step["intent"]
    if intent in seen:
        continue
    seen.add(intent)
    nlu.append(f"- intent: {intent}")
    nlu.append("  examples: |")
    examples = generate_nlu_examples(intent)
    for ex in examples:
        nlu.append(f"    - {ex}")
# fallback
nlu.append("- intent: nlu_fallback")
nlu.append("  examples: |")
nlu.append("    - Sorry, can you rephrase that?")
nlu.append("    - I didn't understand.")

with open("data/nlu.yml", "w") as f:
    f.write("\n".join(nlu) + "\n")

# 5) Build data/stories.yml

def build_stories_from_config(steps, max_depth=10):
    stories = []
    def dfs(idx, path, visited, depth):
        if depth > max_depth or idx in visited:
            return
        step = steps[idx]
        # Add user intent and bot action for this step
        path = path + [
            {"intent": step["intent"]},
            {"action": f"{'action_' if step.get('use_custom_action') else 'utter_'}{step['intent']}"}
        ]
        if not step.get("paths"):
            # End of story
            stories.append(path)
            return
        visited = visited | {idx}
        for i, p in enumerate(step["paths"]):
            tgt = p["target"] - 1  # 1-based to 0-based
            if 0 <= tgt < len(steps):
                dfs(tgt, path, visited, depth+1)
    dfs(0, [], set(), 0)
    return stories

story_paths = build_stories_from_config(steps)
stories_yaml = {"version": "3.1", "stories": [
    {"story": f"story_{i+1}", "steps": s} for i, s in enumerate(story_paths)
]}
yaml_dump(stories_yaml, "data/stories.yml")

# 6) Build data/rules.yml
rules = {"version":"3.1","rules":[]}
# fallback rule
rules["rules"].append({
    "rule":"fallback_rule",
    "steps":[{"intent":"nlu_fallback"},{"action":"action_default_fallback"}]
})
yaml_dump(rules, "data/rules.yml")

# 7) Build config.yml
config = OrderedDict([
    ("language","en"),
    ("pipeline",[
        {"name":"WhitespaceTokenizer"},
        {"name":"RegexFeaturizer"},
        {"name":"LexicalSyntacticFeaturizer"},
        {"name":"CountVectorsFeaturizer"},
        {"name":"CountVectorsFeaturizer","analyzer":"char_wb","min_ngram":1,"max_ngram":4},
        {"name":"DIETClassifier","epochs":100},
        {"name":"EntitySynonymMapper"},
        {"name":"ResponseSelector","epochs":100}
    ]),
    ("policies",[
        {"name":"RulePolicy","core_fallback_threshold":0.4,
         "core_fallback_action_name":"action_default_fallback",
         "enable_fallback_prediction":True},
        {"name":"MemoizationPolicy"},
        {"name":"TEDPolicy","max_history":5,"epochs":100}
    ])
])
yaml_dump(config, "config.yml")

print("✅ Rasa project files generated!")

# **Run Instructions:**

# 1. Put your `bot_config.json` in the same folder.
# 2. Ensure Ollama is running and the `mistral` model is loaded:  
#    ```bash
#    ollama pull misc/mistral-7b
