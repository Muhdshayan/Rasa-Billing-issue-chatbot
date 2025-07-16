#!/usr/bin/env python3
import os
import json
from collections import OrderedDict, defaultdict
import yaml
import logging
import sys

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
    with open(filename, "w") as f:
        yaml.safe_dump(convert_odict(data), f, sort_keys=False)

# Node class for node metadata
class Node:
    def __init__(self, index, intent, actions, responses, examples, entities, fallback_target=None, use_custom_action=False):
        self.index = index
        self.intent = intent
        self.actions = actions  # list of actions
        self.responses = responses
        self.examples = examples
        self.entities = entities
        self.fallback_target = fallback_target
        self.use_custom_action = use_custom_action

# Custom Graph class for conversation graph
class Graph:
    def __init__(self):
        self.nodes = {}  # index -> Node
        self.adj_list = defaultdict(list)  # index -> [(target_index, trigger_intent)]

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
        # Remove edges pointing to this node
        for src in self.adj_list:
            self.adj_list[src] = [(tgt, intent) for tgt, intent in self.adj_list[src] if tgt != index]
        logger.debug(f"Updated adjacency list after removing node {index}")

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
            # Add intent and all actions for this node
            path = path + [{"intent": node.intent}]
            if node.actions:
                for action in node.actions:
                    path.append({"action": action})
            logger.debug(f"Visiting node {idx}: intent={node.intent}, path length={len(path)//2}")
            if not self.adj_list[idx]:
                logger.debug(f"Reached leaf node {idx}: adding story {path}")
                stories.append(path)
                return
            visited.add(idx)
            for target_idx, trigger_intent in self.adj_list[idx]:
                logger.debug(f"Exploring edge: {idx} -> {target_idx} (trigger={trigger_intent})")
                dfs(target_idx, path, visited.copy(), depth + 1)

        # Track nodes with incoming edges
        has_incoming = set()
        for src in self.adj_list:
            for tgt, _ in self.adj_list[src]:
                has_incoming.add(tgt)

        # Main loop: iterate through all nodes
        global_visited = set()
        logger.info("Starting story generation for all subgraphs")
        for idx in sorted(self.nodes.keys()):  # Sort for consistent story order
            if idx in global_visited or idx in has_incoming:
                continue  # Skip if already visited or has incoming edges
            node = self.nodes[idx]
            logger.debug(f"Processing node {idx}: intent={node.intent}")
            if not self.adj_list[idx] and node.intent not in exclude_intents:
                # Independent node with no outgoing edges and not excluded by user
                story = [{"intent": node.intent}]
                if node.actions:
                    for action in node.actions:
                        story.append({"action": action})
                logger.debug(f"Adding story for independent node {idx}: intent={node.intent}, story={story}")
                stories.append(story)
                global_visited.add(idx)
            elif self.adj_list[idx]:
                # Node with outgoing edges: traverse subgraph
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
            regex = get_nonempty("      ↳ Enter regex pattern: ")
        ents.append({
            "name": name,
            "use_lookup": use_lookup,
            "lookup_values": lookup_vals,
            "use_regex": use_regex,
            "regex_pattern": regex
        })
        more = get_yes_no("  • Add another entity for this step?")
        if not more:
            break
    return ents

def gather_paths(step_idx, num_paths, all_intents):
    paths = []
    for j in range(1, num_paths + 1):
        print("    ↳ Available steps and their intents:")
        for idx, intent_name in enumerate(all_intents):
            print(f"      {idx+1}: {intent_name}")
        target = get_int(f"    - Path {j}: target step number (1…{len(all_intents)}): ", min_value=1, max_value=len(all_intents))
        trigger_intent = get_nonempty(f"      Trigger intent for this path: ")
        while trigger_intent not in all_intents:
            print("⚠️  Trigger intent must be one of the defined intents.")
            trigger_intent = get_nonempty(f"      Trigger intent for this path: ")
        paths.append({"target": target, "trigger_intent": trigger_intent})
    return paths

def collect_step_data(index, intent=None, existing_step=None, all_intents=None):
    step = existing_step.copy() if existing_step else {}
    if intent is not None:
        step['intent'] = intent
    else:
        step['intent'] = get_nonempty(f"  Intent name for step {index+1}: ")
    # Examples
    examples = []
    print(f"  a) Enter example utterances for '{step['intent']}' (enter blank to finish):")
    while True:
        example = input("    - ").strip()
        if not example:
            break
        examples.append(example)
    if examples:
        step['examples'] = examples
    
    # Actions and Responses (multiple actions version)
    actions = []
    responses = []
    print(f"  b) Enter actions and their responses for '{step['intent']}' (enter blank action to finish):")
    action_count = 1
    while True:
        action = input(f"    - Action {action_count}: ").strip()
        if not action:
            break
        
        # Get response for this action
        response = get_nonempty(f"      ↳ Response for '{action}': ")
        
        actions.append(action)
        responses.append(response)
        action_count += 1
    
    if actions:
        step['actions'] = actions
        step['responses'] = responses
    
    # Fallback
    if get_yes_no("  c) Will you define a fallback path for this step?"):
        print("    ↳ Available steps:")
        for idx, name in enumerate(all_intents or []):
            print(f"      {idx}: {name}")
        step["fallback_target"] = get_int("    ↳ Fallback target step index: ", min_value=0, max_value=index)
    else:
        step["fallback_target"] = None
    # Entities
    if get_yes_no("  d) Does this step use Entities?"):
        step["entities"] = gather_entities(index+1)
    else:
        step["entities"] = []
    # Outgoing paths
    num_paths = get_int(f"  e) Number of outgoing paths from step {index+1}: ", min_value=0)
    step["num_outgoing_paths"] = num_paths
    if num_paths > 0:
        step["next"] = gather_paths(index+1, num_paths, all_intents or [])
    else:
        step["next"] = []
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
            print(f"  Examples: {step['examples']}")
            print(f"  Actions and Responses:")
            actions = step.get('actions', [])
            responses = step.get('responses', [])
            for j, (action, response) in enumerate(zip(actions, responses)):
                print(f"    {j+1}. Action: {action} -> Response: {response}")
            if len(actions) != len(responses):
                print(f"    Note: {len(actions)} actions but {len(responses)} responses")
            print(f"  Entities: {step['entities']}")
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
            # Reuse collect_step_data for editing
            all_intents = [s['intent'] for s in bot['steps']]
            updated_step = collect_step_data(idx, existing_step=bot['steps'][idx], all_intents=all_intents)
            bot['steps'][idx] = updated_step
            save_bot_data(bot)  # Save after editing
        elif choice == 'a':
            # Add a new step
            intent = get_nonempty(f"  New intent name: ")
            if any(s['intent'] == intent for s in bot['steps']):
                print("⚠️  Intent already exists. Please use a unique intent name.")
                input("Press Enter to continue...")
                continue
            i = len(bot['steps'])
            all_intents = [s['intent'] for s in bot['steps']] + [intent]
            step = collect_step_data(i, intent, all_intents=all_intents)
            bot['steps'].append(step)
            save_bot_data(bot)  # Save after adding
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
            # Update all references in paths and fallbacks
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
            save_bot_data(bot)  # Save after removing
            input()
        elif choice == 'q':
            print("Exiting without saving.")
            sys.exit(0)
        else:
            print("Invalid option. Try again.")
            input("Press Enter to continue...")

def load_saved_data():
    """Load saved bot data from file if it exists."""
    # First check for bot_save.json (our save file)
    if os.path.exists("bot_save.json"):
        try:
            with open("bot_save.json", "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Error loading saved data: {e}")
            return None
    
    # Also check for bot_config.json (from bot_json_builder.py)
    if os.path.exists("bot_config.json"):
        try:
            with open("bot_config.json", "r") as f:
                data = json.load(f)
                print("📁 Found bot_config.json from bot_json_builder.py")
                return data
        except Exception as e:
            print(f"⚠️  Error loading bot_config.json: {e}")
            return None
    
    # Check for generated_bot_config.json (from this script)
    if os.path.exists("generated_bot_config.json"):
        try:
            with open("generated_bot_config.json", "r") as f:
                data = json.load(f)
                print("📁 Found generated_bot_config.json from previous run")
                return data
        except Exception as e:
            print(f"⚠️  Error loading generated_bot_config.json: {e}")
            return None
    
    return None

def save_bot_data(bot):
    """Save bot data to file."""
    try:
        with open("bot_save.json", "w") as f:
            json.dump(bot, f, indent=2)
        print("💾 Progress saved to bot_save.json")
    except Exception as e:
        print(f"⚠️  Error saving data: {e}")

def save_final_config(bot):
    """Save final bot configuration to JSON file."""
    try:
        with open("generated_bot_config.json", "w") as f:
            json.dump(bot, f, indent=2)
        print("💾 Final configuration saved to generated_bot_config.json")
    except Exception as e:
        print(f"⚠️  Error saving final configuration: {e}")

def main():
    clear_screen()
    print("\n🎯 Welcome to the Rasa Chatbot Step-by-Step Builder & Generator!\n")
    
    # Check for saved data
    saved_bot = load_saved_data()
    if saved_bot:
        print("📁 Found saved bot data!")
        print(f"Bot Name: {saved_bot.get('name', 'Unknown')}")
        print(f"Description: {saved_bot.get('description', 'Unknown')}")
        total_steps = saved_bot.get('total_steps', len(saved_bot.get('steps', [])))
        completed_steps = len(saved_bot.get('steps', []))
        print(f"Progress: {completed_steps}/{total_steps} steps completed")
        
        if "intent_names" in saved_bot:
            print(f"Intent names: {', '.join(saved_bot['intent_names'])}")
        
        # Show available files
        available_files = []
        if os.path.exists("bot_save.json"):
            available_files.append("bot_save.json (auto-save)")
        if os.path.exists("bot_config.json"):
            available_files.append("bot_config.json (from builder)")
        if os.path.exists("generated_bot_config.json"):
            available_files.append("generated_bot_config.json (previous run)")
        
        if len(available_files) > 1:
            print(f"\nAvailable files: {', '.join(available_files)}")
        
        if get_yes_no("Do you want to continue from saved data?"):
            bot = saved_bot
            # Use saved intent names if available, otherwise extract from steps
            if "intent_names" in bot:
                step_intents = bot["intent_names"]
                print(f"✅ Loading saved data with {len(step_intents)} intent names...")
            else:
                # Fallback: extract from existing steps
                step_intents = [step['intent'] for step in bot['steps']]
                print("✅ Loading saved data...")
        else:
            # Clear saved data and start fresh
            if os.path.exists("bot_save.json"):
                os.remove("bot_save.json")
            if os.path.exists("bot_config.json"):
                os.remove("bot_config.json")
            if os.path.exists("generated_bot_config.json"):
                os.remove("generated_bot_config.json")
            bot = {}
            step_intents = []
    else:
        bot = {}
        step_intents = []
    
    # If starting fresh or user chose to start fresh
    if not bot:
        bot["name"] = get_nonempty("0) Chatbot Name: ")
        bot["description"] = get_nonempty("1) Bot Description: ")
        total_steps = get_int("2) Number of Steps (nodes): ", min_value=1)
        bot["total_steps"] = total_steps
        bot["steps"] = []

        # First, collect all intent names
        print("\nEnter intent names for each step:")
        for i in range(total_steps):
            intent = get_nonempty(f"  Intent name for step {i+1}: ")
            step_intents.append(intent)
        
        # Save the intent names in the bot data
        bot["intent_names"] = step_intents.copy()
        
        # Save initial data with all intent names
        save_bot_data(bot)
        print(f"💾 Saved initial data: {total_steps} steps with intent names")

    # Now, for each step, collect the rest of the info
    total_steps = bot.get("total_steps", len(step_intents))
    print(f"\n📋 Working on {len(bot['steps'])}/{total_steps} steps completed")
    
    for i in range(len(bot["steps"]), total_steps):
        clear_screen()
        print(f"\n── Step {i+1} / {total_steps} ──")
        print(f"Intent: {step_intents[i]}")
        print(f"Progress: {len(bot['steps'])}/{total_steps} steps completed")
        print("=" * 50)
        
        step = collect_step_data(i, intent=step_intents[i], all_intents=step_intents)
        bot["steps"].append(step)
        
        # Save progress after each step
        save_bot_data(bot)
        print(f"✅ Step {i+1} completed! ({len(bot['steps'])}/{total_steps} done)")
    
    # Save configuration after completing all steps
    save_final_config(bot)

    # Review and edit menu
    review_and_edit(bot, step_intents)
    
    # Save final data before generation
    save_bot_data(bot)
    save_final_config(bot)  # Save the final configuration

    # Prompt for independent intents to exclude from stories
    print("\nEnter comma-separated intent names you do NOT want to add as independent stories (leave blank to include all):")
    exclude_intents = set(x.strip() for x in input().split(",") if x.strip())

    # Build graph and generate files (use in-memory bot["steps"])
    steps = bot["steps"]
    graph = Graph()
    for idx, step_data in enumerate(steps):
        # Handle both old format (action) and new format (actions)
        actions = step_data.get("actions", [])
        if not actions and "action" in step_data:
            actions = [step_data["action"]]
        
        # Handle responses - ensure it's always a list
        responses = step_data.get("responses", [])
        if not isinstance(responses, list):
            responses = [responses] if responses else []
        
        node = Node(
            index=idx,
            intent=step_data["intent"],
            actions=actions,
            responses=responses,
            examples=step_data.get("examples", []),
            entities=step_data.get("entities", []),
            fallback_target=step_data.get("fallback_target"),
            use_custom_action=step_data.get("use_custom_action", False)
        )
        graph.add_node(node)
    for idx, step_data in enumerate(steps):
        for path in step_data["next"]:
            graph.add_edge(idx, path["target"]-1, path["trigger_intent"])

    # 3) Make folders
    mkdir("data")
    mkdir(os.path.join("actions"))

    # 4) Build domain.yml
    domain = OrderedDict([
        ("version", "3.1"),
        ("intents", []),
        ("entities", []),
        ("responses", OrderedDict()),
        ("actions", [])
    ])

    # Collect intents & entities & actions
    all_actions = set()
    for step in steps:
        intent = step["intent"]
        if intent not in domain["intents"]:
            domain["intents"].append(intent)
        for ent in step.get("entities", []):
            ent_name = ent.get("name") if isinstance(ent, dict) else ent
            if ent_name and ent_name not in domain["entities"]:
                domain["entities"].append(ent_name)
        # Add actions to responses or actions list
        actions = step.get("actions", [])
        if not actions and "action" in step:
            actions = [step["action"]]
        
        responses = step.get("responses", [])
        if not isinstance(responses, list):
            responses = [responses] if responses else []
        
        for i, action in enumerate(actions):
            if action:
                if action.startswith("utter_"):
                    resp_text = responses[i] if i < len(responses) else "Default response"
                    domain["responses"][action] = [{"text": resp_text}]
                else:
                    all_actions.add(action)
    # fallback intent
    if "nlu_fallback" not in domain["intents"]:
        domain["intents"].append("nlu_fallback")
    domain["actions"] = list(all_actions)
    domain["responses"]["utter_default"] = [{"text": "Sorry, I didn't get that. Could you rephrase?"}]
    if not domain["entities"]: del domain["entities"]
    yaml_dump(domain, "domain.yml")

    # 5) Build data/nlu.yml
    nlu = ["version: \"3.1\"", "nlu:"]
    seen = set()
    for step in steps:
        intent = step["intent"]
        if intent in seen:
            continue
        seen.add(intent)
        nlu.append(f"- intent: {intent}")
        nlu.append("  examples: |")
        examples = step.get("examples", [])
        for ex in examples:
            nlu.append(f"    - {ex}")
    # fallback
    nlu.append("- intent: nlu_fallback")
    nlu.append("  examples: |")
    nlu.append("    - Sorry, can you rephrase that?")
    nlu.append("    - I didn't understand.")
    with open("data/nlu.yml", "w") as f:
        f.write("\n".join(nlu) + "\n")

    # 6) Build data/stories.yml
    story_paths = graph.generate_stories(max_depth=10, exclude_intents=exclude_intents)
    stories_yaml = {"version": "3.1", "stories": []}
    for i, s in enumerate(story_paths):
        # s is a list of dicts: [{"intent": ...}, {"actions": [...]}, ...]
        story_steps = []
        for step in s:
            if "intent" in step:
                intent_step = {"intent": step["intent"]}
                # Add entities if present for this intent
                # Find the node for this intent (by index or by intent name)
                node = next((n for n in steps if n["intent"] == step["intent"]), None)
                if node and node.get("entities"):
                    # Only add entities that have a value (if you want to prompt for values, you can)
                    # For now, just add the entity names with dummy values or leave as empty string
                    intent_entities = []
                    for ent in node["entities"]:
                        ent_name = ent["name"] if isinstance(ent, dict) else ent
                        intent_entities.append({ent_name: ""})
                    if intent_entities:
                        intent_step["entities"] = intent_entities
                story_steps.append(intent_step)
            # Add all actions for this step
            if "actions" in step:
                for action in step["actions"]:
                    if action:
                        story_steps.append({"action": action})
            if "action" in step:  # for backward compatibility
                story_steps.append({"action": step["action"]})
        stories_yaml["stories"].append({"story": f"story_{i+1}", "steps": story_steps})
    yaml_dump(stories_yaml, "data/stories.yml")

    # Add a blank line after each story in data/stories.yml
    with open("data/stories.yml", "r") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        new_lines.append(line)
        # If a line starts a new story, and it's not the first, add a blank line before it
        if line.strip().startswith("- story:") and len(new_lines) > 1:
            new_lines.insert(-1, "\n")

    with open("data/stories.yml", "w") as f:
        f.writelines(new_lines)

    # 7) Build data/rules.yml
    rules = {"version": "3.1", "rules": []}
    rules["rules"].append({
        "rule": "fallback_rule",
        "steps": [{"intent": "nlu_fallback"}, {"action": "action_default_fallback"}]
    })
    yaml_dump(rules, "data/rules.yml")

    # 8) Build config.yml
    config = OrderedDict([
        ("language", "en"),
        ("pipeline", [
            {"name": "WhitespaceTokenizer"},
            {"name": "RegexFeaturizer"},
            {"name": "LexicalSyntacticFeaturizer"},
            {"name": "CountVectorsFeaturizer"},
            {"name": "CountVectorsFeaturizer", "analyzer": "char_wb", "min_ngram": 1, "max_ngram": 4},
            {"name": "DIETClassifier", "epochs": 100},
            {"name": "EntitySynonymMapper"},
            {"name": "ResponseSelector", "epochs": 100}
        ]),
        ("policies", [
            {"name": "RulePolicy", "core_fallback_threshold": 0.4,
             "core_fallback_action_name": "action_default_fallback",
             "enable_fallback_prediction": True},
            {"name": "MemoizationPolicy"},
            {"name": "TEDPolicy", "max_history": 5, "epochs": 100}
        ])
    ])
    yaml_dump(config, "config.yml")

    # Clean up save file after successful generation
    if os.path.exists("bot_save.json"):
        os.remove("bot_save.json")
        print("🗑️  Cleaned up save file")

    print("✅ Rasa project files generated!")
    print("\n📁 Files created:")
    print("   📄 generated_bot_config.json - Your complete bot configuration")
    print("   📄 domain.yml - Rasa domain file with intents, entities, responses")
    print("   📄 data/nlu.yml - Training data for intents and examples")
    print("   📄 data/stories.yml - Conversation flows and stories")
    print("   📄 data/rules.yml - Rules for fallback handling")
    print("   📄 config.yml - Rasa pipeline and policy configuration")
    print("\n💡 You can use generated_bot_config.json to recreate your bot or share it!")

if __name__ == "__main__":
    main()