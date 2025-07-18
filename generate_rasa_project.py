#!/usr/bin/env python3
import os
import json
from collections import OrderedDict, defaultdict
import yaml
import logging
import sys
import glob

# Setup logging for debugging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Helper: create folder if missing
def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)

# Helper: save YAML
def yaml_dump(data, filename):
    def convert_odict(obj):
        if isinstance(obj, OrderedDict):
            return {k: convert_odict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_odict(i) for i in obj]
        elif isinstance(obj, dict):
            return {k: convert_odict(v) for k, v in obj.items()}
        else:
            return obj
    # Write YAML with blank lines between top-level sections for clarity
    yaml_str = yaml.safe_dump(convert_odict(data), sort_keys=False, allow_unicode=True)
    # Add blank lines between top-level keys
    lines = yaml_str.split('\n')
    new_lines = []
    last_was_section = False
    for i, line in enumerate(lines):
        if line and not line.startswith(' '):
            if new_lines and not new_lines[-1].strip() == '':
                new_lines.append('')
            last_was_section = True
        new_lines.append(line)
    yaml_str = '\n'.join(new_lines)
    with open(filename, "w") as f:
        f.write(yaml_str)

# Node class for node metadata
class Node:
    def __init__(self, index, intent, actions, responses, examples, entities, slots=None, fallback_target=None, use_custom_action=False):
        self.index = index
        self.intent = intent
        self.actions = actions
        self.responses = responses
        self.examples = examples
        self.entities = entities
        self.slots = slots or []
        self.fallback_target = fallback_target
        self.use_custom_action = use_custom_action

# Custom Graph class for conversation graph
class Graph:
    def __init__(self):
        self.nodes = {}
        self.adj_list = defaultdict(list)

    def add_node(self, node):
        logger.debug(f"Adding node: index={node.index}, intent={node.intent}")
        self.nodes[node.index] = node

    def add_edge(self, from_index, to_index, trigger_intent):
        if to_index not in self.nodes:
            logger.warning(f"Invalid target index {to_index} for edge from {from_index}")
            return
        logger.debug(f"Adding edge: {from_index} -> {to_index} (trigger={trigger_intent})")
        self.adj_list[from_index].append((to_index, trigger_intent))

    def remove_node(self, index):
        if index not in self.nodes:
            logger.warning(f"Cannot remove node: index {index} not found")
            return
        logger.debug(f"Removing node: index={index}, intent={self.nodes[index].intent}")
        del self.nodes[index]
        del self.adj_list[index]
        for src in self.adj_list:
            self.adj_list[src] = [(tgt, intent) for tgt, intent in self.adj_list[src] if tgt != index]

    def generate_stories(self, max_depth=10, exclude_intents=None):
        if exclude_intents is None:
            exclude_intents = set()
        stories = []
        def dfs(idx, path, visited, depth):
            if depth > max_depth:
                logger.debug(f"Depth limit reached: {depth} > {max_depth}")
                return
            if idx in visited:
                logger.debug(f"Cycle detected at index {idx}: {path}")
                return
            if idx not in self.nodes:
                logger.warning(f"Invalid node index {idx} encountered")
                return
            node = self.nodes[idx]
            path = path + [{"intent": node.intent}]
            # Remove form logic
            # if node.form:
            #     path.append({"action": node.form})
            #     path.append({"active_loop": node.form})
            #     path.append({"active_loop": None})
            if node.actions:
                for action in node.actions:
                    path.append({"action": action})
            logger.debug(f"Visiting node {idx}: intent={node.intent}, path length={len(path)//2}")
            if not self.adj_list[idx]:
                stories.append(path)
                return
            visited.add(idx)
            for target_idx, trigger_intent in self.adj_list[idx]:
                logger.debug(f"Exploring edge: {idx} -> {target_idx} (trigger={trigger_intent})")
                dfs(target_idx, path, visited.copy(), depth + 1)

        has_incoming = set()
        for src in self.adj_list:
            for tgt, _ in self.adj_list[src]:
                has_incoming.add(tgt)

        global_visited = set()
        logger.info("Starting story generation for all subgraphs")
        for idx in sorted(self.nodes.keys()):
            if idx in global_visited or idx in has_incoming:
                continue
            node = self.nodes[idx]
            # Remove form logic
            # if not self.adj_list[idx] and node.intent not in exclude_intents:
            #     story = [{"intent": node.intent}]
            #     if node.form:
            #         story.append({"action": node.form})
            #         story.append({"active_loop": node.form})
            #         story.append({"active_loop": None})
            #     if node.actions:
            #         for action in node.actions:
            #             story.append({"action": action})
            #     stories.append(story)
            #     global_visited.add(idx)
            # elif self.adj_list[idx]:
            #     logger.info(f"Starting DFS for subgraph at node {idx}: intent={node.intent}")
            #     dfs(idx, [], global_visited, 0)
            if not self.adj_list[idx] and node.intent not in exclude_intents:
                story = [{"intent": node.intent}]
                if node.actions:
                    for action in node.actions:
                        story.append({"action": action})
                stories.append(story)
                global_visited.add(idx)
            elif self.adj_list[idx]:
                logger.info(f"Starting DFS for subgraph at node {idx}: intent={node.intent}")
                dfs(idx, [], global_visited, 0)

        logger.info(f"Generated {len(stories)} stories")
        return stories

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_nonempty(prompt):
    while True:
        val = input(prompt).strip()
        if val:
            return val
        print("⚠️  Please enter a non-empty value.")

def get_int(prompt, min_value=None, max_value=None):
    while True:
        val = input(prompt).strip()
        if not val.isdigit():
            print("⚠️  Enter a valid integer.")
            continue
        iv = int(val)
        if min_value is not None and iv < min_value:
            print(f"⚠️  Enter an integer ≥ {min_value}.")
            continue
        if max_value is not None and iv > max_value:
            print(f"⚠️  Enter an integer ≤ {max_value}.")
            continue
        return iv

def get_yes_no(prompt):
    while True:
        val = input(prompt + " [y/n]: ").strip().lower()
        if val in ("y", "yes"):
            return True
        if val in ("n", "no"):
            return False
        print("⚠️  Please enter 'y' or 'n'.")

def gather_entities(step_idx):
    ents = []
    while True:
        name = get_nonempty(f"  • Entity name for step {step_idx}: ")
        example_value = get_nonempty(f"    ↳ Example value for entity '{name}': ")
        use_lookup = get_yes_no("    ↳ Use lookup table for this entity?")
        lookup_vals = []
        if use_lookup:
            print("      ↳ Enter lookup values one per line. Blank line to finish.")
            while True:
                v = input("        - ").strip()
                if not v:
                    break
                lookup_vals.append(v)
        use_regex = get_yes_no("    ↳ Use regex pattern for this entity?")
        regex = None
        if use_regex:
            regex = get_nonempty("      ↳ Enter regex pattern (e.g., \\d{{10}} for 10-digit phone): ")
        ents.append({
            "name": name,
            "example": example_value,
            "use_lookup": use_lookup,
            "lookup_values": lookup_vals,
            "use_regex": use_regex,
            "regex_pattern": regex
        })
        more = get_yes_no("  • Add another entity for this step?")
        if not more:
            break
    return ents

def gather_slots(step_idx, all_entities):
    slots = []
    while True:
        name = get_nonempty(f"  • Slot name for step {step_idx}: ")
        slot_type = get_nonempty("    ↳ Slot type (e.g., text, float, categorical): ")
        influence_conversation = get_yes_no("    ↳ Should this slot influence the conversation?")
        if name in all_entities:
            mapping = {"type": "from_entity", "entity": name}
        else:
            mapping = {"type": "custom"}
        slot = {
            "name": name,
            "type": slot_type,
            "influence_conversation": influence_conversation,
            "mapping": mapping
        }
        slots.append(slot)
        more = get_yes_no("  • Add another slot for this step?")
        if not more:
            break
    return slots

# Remove gather_form and all form-related logic
# Remove form argument from Node class and its usage
class Node:
    def __init__(self, index, intent, actions, responses, examples, entities, slots=None, fallback_target=None, use_custom_action=False):
        self.index = index
        self.intent = intent
        self.actions = actions
        self.responses = responses
        self.examples = examples
        self.entities = entities
        self.slots = slots or []
        self.fallback_target = fallback_target
        self.use_custom_action = use_custom_action

def collect_step_data(index, intent=None, existing_step=None, all_intents=None):
    step = existing_step.copy() if existing_step else {}
    if intent is not None:
        step['intent'] = intent
    else:
        step['intent'] = get_nonempty(f"  Intent name for step {index+1}: ")
    examples = []
    print(f"  a) Enter example utterances for '{step['intent']}' (enter blank to finish):")
    while True:
        example = input("    - ").strip()
        if not example:
            break
        examples.append(example)
    if examples:
        step['examples'] = examples
    actions = []
    responses = []
    print(f"  b) Enter actions and their responses for '{step['intent']}' (enter blank action to finish):")
    action_count = 1
    while True:
        action = input(f"    - Action {action_count}: ").strip()
        if not action:
            break
        is_custom = get_yes_no("      ↳ Is this a custom action (requires Python code)?")
        response = None
        if not is_custom:
            response = get_nonempty(f"      ↳ Response for '{action}': ")
        actions.append(action)
        responses.append(response)
        step['use_custom_action'] = step.get('use_custom_action', False) or is_custom
        action_count += 1
    if actions:
        step['actions'] = actions
        step['responses'] = responses
    if get_yes_no("  c) Does this step use slots?"):
        all_entities = [ent["name"] if isinstance(ent, dict) else ent for ent in step.get("entities", [])]
        step["slots"] = gather_slots(index+1, all_entities)
    else:
        step["slots"] = []
    # Remove form prompt
    # step["form"] = gather_form(index+1)
    step["form"] = None
    if get_yes_no("  d) Will you define a fallback path for this step?"):
        print("    ↳ Available steps:")
        for idx, name in enumerate(all_intents or []):
            print(f"      {idx}: {name}")
        step["fallback_target"] = get_int("    ↳ Fallback target step index: ", min_value=0, max_value=index)
    else:
        step["fallback_target"] = None
    if get_yes_no("  e) Does this step use entities?"):
        step["entities"] = gather_entities(index+1)
    else:
        step["entities"] = []
    num_paths = get_int(f"  f) Number of outgoing paths from step {index+1}: ", min_value=0)
    step["num_outgoing_paths"] = num_paths
    step["next"] = []
    for i in range(num_paths):
        print("    ↳ Available steps:")
        for idx, intent_name in enumerate(all_intents):
            print(f"      {idx+1}: {intent_name}")
        target = get_int(f"    ↳ Target step index for outgoing path {i+1} (1-{len(all_intents)}): ", min_value=1, max_value=len(all_intents))
        while True:
            trigger_intent = get_nonempty(f"    ↳ Trigger intent for outgoing path {i+1} (choose from above): ")
            if trigger_intent in all_intents:
                break
            print("      ⚠️  Please enter a valid intent from the list above.")
        step["next"].append({"trigger_intent": trigger_intent, "target": target})
    return step

def review_and_edit(bot, step_intents):
    while True:
        clear_screen()
        print("\n===== Review Your Bot Configuration =====\n")
        total_steps = bot.get('total_steps', len(bot['steps']))
        print(f"Bot Name: {bot['name']}")
        print(f"Description: {bot['description']}")
        print(f"Total Steps: {len(bot['steps'])}/{total_steps}\n")
        for i, step in enumerate(bot['steps']):
            print(f"Step {i+1}:")
            print(f"  Intent: {step['intent']}")
            print(f"  Examples: {step.get('examples', [])}")
            print(f"  Actions and Responses:")
            actions = step.get('actions', [])
            responses = step.get('responses', [])
            for j, (action, response) in enumerate(zip(actions, responses)):
                print(f"    {j+1}. Action: {action} -> Response: {response if response else 'Custom Action'}")
            print(f"  Slots: {step.get('slots', [])}")
            print(f"  Form: {step.get('form', None)}")
            print(f"  Entities: {step.get('entities', [])}")
            print(f"  Outgoing Paths: {step.get('next', [])}")
            print(f"  Fallback Target: {step.get('fallback_target')}")
            print()
        print("Options:")
        print("  [s] Save and finish")
        print("  [e] Edit a step")
        print("  [a] Add a new step/intent")
        print("  [r] Remove a step/intent")
        print("  [q] Quit without saving")
        choice = input("Choose an option: ").strip().lower()
        if choice == 's':
            return
        elif choice == 'e':
            idx = get_int(f"Enter step number to edit (1-{len(bot['steps'])}): ", 1, len(bot['steps'])) - 1
            all_intents = [s['intent'] for s in bot['steps']]
            updated_step = collect_step_data(idx, existing_step=bot['steps'][idx], all_intents=all_intents)
            bot['steps'][idx] = updated_step
            save_bot_data(bot, selected_file)
        elif choice == 'a':
            intent = get_nonempty(f"  New intent name: ")
            if any(s['intent'] == intent for s in bot['steps']):
                print("⚠️  Intent already exists. Please use a unique intent name.")
                input("Press Enter to continue...")
                continue
            i = len(bot['steps'])
            all_intents = [s['intent'] for s in bot['steps']] + [intent]
            step = collect_step_data(i, intent, all_intents=all_intents)
            bot['steps'].append(step)
            save_bot_data(bot, selected_file)
        elif choice == 'r':
            if not bot['steps']:
                print("No steps to remove.")
                input("Press Enter to continue...")
                continue
            print("\nRemove a step/intent:")
            for i, step in enumerate(bot['steps']):
                print(f"  {i+1}: {step['intent']}")
            idx = get_int(f"Enter step number to remove (1-{len(bot['steps'])}): ", 1, len(bot['steps'])) - 1
            removed_intent = bot['steps'][idx]['intent']
            bot['steps'].pop(idx)
            for step in bot['steps']:
                if step.get('fallback_target') == idx:
                    step['fallback_target'] = None
                elif isinstance(step.get('fallback_target'), int) and step['fallback_target'] > idx:
                    step['fallback_target'] -= 1
                if 'next' in step and step['next']:
                    new_next = []
                    for path in step['next']:
                        if path['target'] == idx + 1:
                            continue
                        elif path['target'] > idx + 1:
                            path['target'] -= 1
                        if path['trigger_intent'] == removed_intent:
                            continue
                        new_next.append(path)
                    step['next'] = new_next
            print(f"Step '{removed_intent}' removed! Press Enter to continue...")
            save_bot_data(bot, selected_file)
            input()
        elif choice == 'q':
            print("Exiting without saving.")
            sys.exit(0)
        else:
            print("Invalid option. Try again.")
            input("Press Enter to continue...")

def select_json_file():
    json_files = [f for f in glob.glob("*.json") if not f.startswith("__")]
    if not json_files:
        print("No .json files found in the root directory. Starting fresh.")
        return None
    print("\nAvailable .json files in the root directory:")
    for idx, fname in enumerate(json_files):
        print(f"  [{idx+1}] {fname}")
    while True:
        choice = input(f"Select a file to load as bot config (1-{len(json_files)}) or press Enter to start fresh: ").strip()
        if not choice:
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(json_files):
            return json_files[int(choice)-1]
        print("Invalid selection. Try again.")

def load_saved_data(selected_file=None):
    if selected_file and os.path.exists(selected_file):
        try:
            with open(selected_file, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Error loading {selected_file}: {e}")
            return None
    return None

def save_bot_data(bot, selected_file):
    try:
        filename = selected_file or f"{bot.get('name', 'bot_save').replace(' ', '_')}.json"
        with open(filename, "w") as f:
            json.dump(bot, f, indent=2)
        print(f"💾 Progress saved to {filename}")
    except Exception as e:
        print(f"⚠️  Error saving data: {e}")

def save_final_config(bot):
    try:
        bot_name = bot.get("name", "generated_bot").replace(" ", "_")
        filename = f"{bot_name}_config.json"
        with open(filename, "w") as f:
            json.dump(bot, f, indent=2)
        print(f"\U0001F4BE Final configuration saved to {filename}")
    except Exception as e:
        print(f"\u26A0\uFE0F  Error saving final configuration: {e}")

def generate_actions_py(slots, forms, actions, bot_steps):
    actions_code = [
        "from rasa_sdk import Action, Tracker",
        "from rasa_sdk.executor import CollectingDispatcher",
        "from rasa_sdk.events import SlotSet",
        "from typing import Any, Dict, List, Text",
        "import re",
        "import requests",
        "import logging",
        "",
        "# Setup logging for debugging",
        "logging.basicConfig(level=logging.DEBUG, format=\"%(asctime)s - %(levelname)s - %(message)s\")",
        "logger = logging.getLogger(__name__)",
        ""
    ]

    for action in actions:
        if action.startswith("utter_") or action.startswith("validate_"):
            continue
        class_name = ''.join([w.capitalize() for w in action.split('_')])
        actions_code.append(f"class {class_name}(Action):")
        actions_code.append(f"    def name(self) -> Text:")
        actions_code.append(f"        return \"{action}\"")
        actions_code.append("")
        actions_code.append(f"    def run(self, dispatcher: CollectingDispatcher,\n            tracker: Tracker,\n            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:")
        actions_code.append(f"        # TODO: Implement logic for {action}")
        actions_code.append(f"        return []")
        actions_code.append("")

    with open("actions/actions.py", "w") as f:
        f.write("\n".join(actions_code) + "\n")

def generate_dummy_nlu_examples(bot, step_intents):
    print("\n--- Add dummy NLU examples for each intent ---")
    for i, intent in enumerate(step_intents):
        step = next((s for s in bot["steps"] if s["intent"] == intent), None)
        if step is None:
            continue
        try:
            num_variations = int(input(f"How many dummy variations for intent '{intent}'? (enter 0 for none): ").strip())
        except Exception:
            num_variations = 0
        if num_variations > 0:
            existing = step.get("examples", [])
            dummy_examples = [f"{intent}{j+1}" for j in range(num_variations)]
            step["examples"] = existing + dummy_examples

def main():
    clear_screen()
    print("\n🎯 Welcome to the Rasa Chatbot Step-by-Step Builder & Generator!\n")
    print("⚠️  You will need to manually edit actions/actions.py to add your API key and endpoints.\n")

    selected_file = select_json_file()
    saved_bot = load_saved_data(selected_file)
    if saved_bot:
        print("📁 Found saved bot data!")
        print(f"Bot Name: {saved_bot.get('name', 'Unknown')}")
        print(f"Description: {saved_bot.get('description', 'Unknown')}")
        total_steps = saved_bot.get('total_steps', len(saved_bot.get('steps', [])))
        completed_steps = len(saved_bot.get('steps', []))
        print(f"Progress: {completed_steps}/{total_steps} steps completed")
        if "intent_names" in saved_bot:
            print(f"Intent names: {', '.join(saved_bot['intent_names'])}")
        if get_yes_no("Do you want to continue from saved data?"):
            bot = saved_bot
            step_intents = bot.get("intent_names", [step['intent'] for step in bot['steps']])
        else:
            bot = {"steps": []}
            step_intents = []
    else:
        bot = {"steps": []}
        step_intents = []

    # Only prompt for these if not already present
    if "name" not in bot or not bot["name"]:
        bot["name"] = get_nonempty("Enter bot name: ")
    if "description" not in bot or not bot["description"]:
        bot["description"] = get_nonempty("Enter bot description: ")
    if "total_steps" not in bot or not isinstance(bot["total_steps"], int):
        bot["total_steps"] = get_int("Enter total number of steps (intents) for your bot: ", min_value=1)

    # Collect all intent names up front, only if not already present
    if "intent_names" in bot and isinstance(bot["intent_names"], list) and len(bot["intent_names"]) == bot["total_steps"]:
        step_intents = bot["intent_names"]
    else:
        step_intents = []
        print(f"\n📝 Enter the names of all {bot['total_steps']} intents for {bot['name']}")
        for i in range(bot["total_steps"]):
            while True:
                intent = get_nonempty(f"  Intent name for step {i+1}: ")
                if intent in step_intents:
                    print("⚠️  Intent already exists. Please use a unique intent name.")
                else:
                    step_intents.append(intent)
                    break
        # Save after all intent names are entered
        bot["intent_names"] = step_intents
        save_bot_data(bot, selected_file)

    # Collect step data for each intent
    bot["steps"] = bot.get("steps", [])
    for i, intent in enumerate(step_intents):
        if i < len(bot["steps"]):
            continue
        print(f"\nDefining step {i+1}/{bot['total_steps']} (intent: {intent})")
        step = collect_step_data(i, intent=intent, all_intents=step_intents)
        bot["steps"].append(step)
        save_bot_data(bot, selected_file)

    review_and_edit(bot, step_intents)
    save_final_config(bot)

    # Ask for dummy NLU examples and append them
    generate_dummy_nlu_examples(bot, step_intents)

    mkdir("data")
    mkdir("actions")

    graph = Graph()
    for idx, step_data in enumerate(bot["steps"]):
        node = Node(
            index=idx,
            intent=step_data["intent"],
            actions=step_data.get("actions", []),
            responses=step_data.get("responses", []),
            examples=step_data.get("examples", []),
            entities=step_data.get("entities", []),
            slots=step_data.get("slots", []),
            fallback_target=step_data.get("fallback_target"),
            use_custom_action=step_data.get("use_custom_action", False)
        )
        graph.add_node(node)
    for idx, step_data in enumerate(bot["steps"]):
        for path in step_data.get("next", []):
            graph.add_edge(idx, path["target"]-1, path["trigger_intent"])

    domain = OrderedDict([
        ("version", "3.1"),
        ("intents", []),
        ("entities", []),
        ("slots", OrderedDict()),
        # Remove forms
        # ("forms", OrderedDict()),
        ("actions", []),
        ("responses", OrderedDict())
    ])

    all_slots = set()
    all_forms = set()
    all_actions = set()
    # Collect all entity names for mapping
    all_entity_names = set()
    for step in bot["steps"]:
        for ent in step.get("entities", []):
            ent_name = ent.get("name") if isinstance(ent, dict) else ent
            if ent_name:
                all_entity_names.add(ent_name)
    for step in bot["steps"]:
        intent = step["intent"]
        if intent not in domain["intents"]:
            domain["intents"].append(intent)
        for ent in step.get("entities", []):
            ent_name = ent.get("name") if isinstance(ent, dict) else ent
            if ent_name and ent_name not in domain["entities"]:
                domain["entities"].append(ent_name)
        for slot in step.get("slots", []):
            slot_name = slot["name"]
            if slot_name not in domain["slots"]:
                slot_def = {
                    "type": slot["type"],
                    "influence_conversation": slot["influence_conversation"],
                    "mappings": [slot["mapping"]]
                }
                domain["slots"][slot_name] = slot_def
                all_slots.add(slot_name)
        # Remove form logic
        # if step.get("form"):
        #     form_name = step["form"]["name"]
        #     required_slots = {}
        #     for slot in step["form"]["required_slots"]:
        #         if slot in domain["entities"]:
        #             required_slots[slot] = [{"type": "from_entity", "entity": slot}]
        #         else:
        #             required_slots[slot] = [{"type": "from_text"}]
        #     domain["forms"][form_name] = {"required_slots": required_slots}
        #     all_forms.add(form_name)
        #     all_actions.add(form_name)
        #     all_actions.add(f"validate_{form_name}")
        actions = step.get("actions", [])
        responses = step.get("responses", [])
        for i, action in enumerate(actions):
            if action:
                all_actions.add(action)
                if action.startswith("utter_") and i < len(responses) and responses[i]:
                    domain["responses"][action] = [{"text": responses[i]}]
    if "nlu_fallback" not in domain["intents"]:
        domain["intents"].append("nlu_fallback")
    domain["actions"] = sorted(list(all_actions))
    domain["responses"]["utter_default"] = [{"text": "Sorry, I didn't get that. Could you rephrase?"}]
    if not domain["entities"]:
        del domain["entities"]
    yaml_dump(domain, "domain.yml")

    nlu = ["version: \"3.1\"", "nlu:"]
    seen_intents = set()
    regex_entities = {}
    lookup_entities = {}
    for step in bot["steps"]:
        intent = step["intent"]
        if intent not in seen_intents:
            seen_intents.add(intent)
            nlu.append(f"- intent: {intent}")
            nlu.append("  examples: |")
            examples = step.get("examples", [])
            for ex in examples:
                nlu.append(f"    - {ex}")
            nlu.append("")  # Blank line after each intent
        for ent in step.get("entities", []):
            ent_name = ent["name"]
            if ent.get("use_regex") and ent.get("regex_pattern"):
                if ent_name not in regex_entities:
                    regex_entities[ent_name] = ent["regex_pattern"]
                elif regex_entities[ent_name] != ent["regex_pattern"]:
                    print(f"Warning: Conflicting regex patterns for entity {ent_name}")
            if ent.get("use_lookup") and ent.get("lookup_values"):
                if ent_name not in lookup_entities:
                    lookup_entities[ent_name] = set(ent["lookup_values"])
                else:
                    lookup_entities[ent_name].update(ent["lookup_values"])
    # Add regex entities
    for ent_name, regex_pattern in regex_entities.items():
        nlu.append(f"- regex: {ent_name}")
        nlu.append("  examples: |")
        nlu.append(f"    - {regex_pattern}")
        nlu.append("")  # Blank line after each regex
    # Add lookup tables
    for ent_name, values in lookup_entities.items():
        nlu.append(f"- lookup: {ent_name}")
        nlu.append("  examples: |")
        for val in values:
            nlu.append(f"    - {val}")
        nlu.append("")  # Blank line after each lookup
    nlu.append("- intent: nlu_fallback")
    nlu.append("  examples: |")
    nlu.append("    - Sorry, can you rephrase that?")
    nlu.append("    - I didn't understand.")
    nlu.append("")
    with open("data/nlu.yml", "w") as f:
        f.write("\n".join(nlu) + "\n")

    exclude_intents = set()
    story_paths = graph.generate_stories(max_depth=10, exclude_intents=exclude_intents)
    stories_yaml = {"version": "3.1", "stories": []}
    for i, s in enumerate(story_paths):
        story_steps = []
        for step in s:
            if "intent" in step:
                intent_step = {"intent": step["intent"]}
                node = next((n for n in bot["steps"] if n["intent"] == step["intent"]), None)
                if node and node.get("entities"):
                    intent_entities = []
                    for ent in node["entities"]:
                        ent_name = ent["name"] if isinstance(ent, dict) else ent
                        ent_example = ent.get("example") if isinstance(ent, dict) else None
                        if ent_example:
                            intent_entities.append({ent_name: ent_example})
                        else:
                            intent_entities.append({ent_name: ""})
                    if intent_entities:
                        intent_step["entities"] = intent_entities
                story_steps.append(intent_step)
            if "action" in step:
                # Do NOT attach entities to action steps
                story_steps.append({"action": step["action"]})
        stories_yaml["stories"].append({"story": f"story_{i+1}", "steps": story_steps})
    yaml_dump(stories_yaml, "data/stories.yml")
    # Add blank lines between stories
    with open("data/stories.yml", "r") as f:
        lines = f.readlines()
    new_lines = []
    for line in lines:
        new_lines.append(line)
        if line.strip().startswith("- story:") and len(new_lines) > 1:
            new_lines.append("\n")
    with open("data/stories.yml", "w") as f:
        f.writelines(new_lines)

    rules = {"version": "3.1", "rules": []}
    rules["rules"].append({
        "rule": "fallback_rule",
        "steps": [{"intent": "nlu_fallback"}, {"action": "action_default_fallback"}]
    })
    # Remove form rules
    # for form in all_forms:
    #     rules["rules"].append({
    #         "rule": f"Activate {form}",
    #         "steps": [
    #             {"intent": bot["steps"][0]["intent"]},
    #             {"action": form},
    #             {"active_loop": form}
    #         ]
    #     })
    #     rules["rules"].append({
    #         "rule": f"Submit {form}",
    #         "condition": [{"active_loop": form}],
    #         "steps": [
    #             {"action": form},
    #             {"active_loop": None}
    #         ]
    #     })
    yaml_dump(rules, "data/rules.yml")

    # Write config.yml to match Talha files/config.yml
    config = OrderedDict([
        ("version", "3.1"),
        ("language", "en"),
        ("pipeline", [
            {"name": "WhitespaceTokenizer"},
            {"name": "RegexFeaturizer"},
            {"name": "LexicalSyntacticFeaturizer"},
            {"name": "CountVectorsFeaturizer"},
            {"name": "CountVectorsFeaturizer", "analyzer": "char_wb", "min_ngram": 1, "max_ngram": 4},
            {"name": "DIETClassifier", "epochs": 150},
            {"name": "EntitySynonymMapper"},
            {"name": "ResponseSelector", "epochs": 100}
        ]),
        ("policies", [
            {"name": "RulePolicy", "core_fallback_threshold": 0.2, "core_fallback_action_name": "action_default_fallback", "enable_fallback_prediction": True},
            {"name": "MemoizationPolicy"},
            {"name": "TEDPolicy", "max_history": 7, "epochs": 150}
        ])
    ])
    yaml_dump(config, "config.yml")

    generate_actions_py(all_slots, all_forms, all_actions, bot["steps"])

    # If there are any custom actions, create endpoints.yml
    has_custom_action = any(a for a in all_actions if not a.startswith("utter_"))
    if has_custom_action:
        with open("endpoints.yml", "w") as f:
            f.write("action_endpoint:\n  url: \"http://localhost:5055/webhook\"\n")

    print("✅ Rasa project files generated!")
    print("\n📁 Files created:")
    print("   📄 <bot_name>_config.json - Your complete bot configuration")
    print("   📄 domain.yml - Rasa domain file with intents, entities, slots, forms, responses")
    print("   📄 data/nlu.yml - Training data for intents and examples")
    print("   📄 data/stories.yml - Conversation flows and stories")
    print("   📄 data/rules.yml - Rules for forms and fallback handling")
    print("   📄 config.yml - Rasa pipeline and policy configuration")
    print("   📄 actions/actions.py - Custom actions and form validation")
    print("\n⚠️  Please edit actions/actions.py to add your API key and endpoints.")

if __name__ == "__main__":
    main()