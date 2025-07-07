import json
import os
import sys

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_nonempty(prompt):
    """Prompt until a non-empty string is given."""
    while True:
        val = input(prompt).strip()
        if val:
            return val
        print("⚠️  Please enter a non-empty value.")

def get_int(prompt, min_value=None, max_value=None):
    """Prompt until a valid integer is given (and within optional bounds)."""
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
    """Prompt until user enters Y/N."""
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
        trigger_intent = get_nonempty(f"      Trigger intent for this path (e.g. 'ask_billing'): ")
        while trigger_intent not in all_intents:
            print("⚠️  Trigger intent must be one of the defined intents.")
            trigger_intent = get_nonempty(f"      Trigger intent for this path (e.g. 'ask_billing'): ")
        paths.append({"target": target, "trigger_intent": trigger_intent})
    return paths

def review_and_edit(bot):
    while True:
        clear_screen()
        print("\n===== Review Your Bot Configuration =====\n")
        print(f"Bot Name: {bot['name']}")
        print(f"Description: {bot['description']}")
        print(f"Total Steps: {len(bot['steps'])}\n")
        for i, step in enumerate(bot['steps']):
            print(f"Step {i+1}:")
            print(f"  Intent: {step['intent']}")
            print(f"  Examples: {step['examples']}")
            print(f"  Responses: {step['responses']}")
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
            return True
        elif choice == 'e':
            idx = get_int(f"Enter step number to edit (1-{len(bot['steps'])}): ", 1, len(bot['steps'])) - 1
            edit_step(bot, idx)
        elif choice == 'a':
            add_step(bot)
        elif choice == 'r':
            remove_step(bot)
        elif choice == 'q':
            print("Exiting without saving.")
            sys.exit(0)
        else:
            print("Invalid option. Try again.")
            input("Press Enter to continue...")

def add_step(bot):
    print("\nAdd a new step/intent:")
    intent = get_nonempty(f"  New intent name: ")
    # Check for duplicates
    if any(s['intent'] == intent for s in bot['steps']):
        print("⚠️  Intent already exists. Please use a unique intent name.")
        input("Press Enter to continue...")
        return
    i = len(bot['steps'])
    # Gather info for the new step
    print(f"\n── New Step {i+1} ──")
    # Examples
    examples = []
    print(f"  a) Enter example utterances for '{intent}' (enter blank to finish):")
    while True:
        example = input("    - ").strip()
        if not example:
            break
        examples.append(example)
    # Responses
    responses = []
    print(f"  b) Enter responses for '{intent}' (enter blank to finish):")
    while True:
        response = input("    - ").strip()
        if not response:
            break
        responses.append(response)
    step = {
        "index": i,
        "intent": intent,
        "action": f"utter_{intent}",
        "responses": responses,
        "examples": examples,
        "num_outgoing_paths": 0,
        "fallback_target": None,
        "entities": [],
        "next": []
    }
    # Fallback
    if get_yes_no("  c) Will you define a fallback path for this step?"):
        print("    ↳ Available steps:")
        for idx, s in enumerate(bot['steps'] + [step]):
            print(f"      {idx}: {s['intent']}")
        step["fallback_target"] = get_int("    ↳ Fallback target step index: ", min_value=0, max_value=i)
    # Entities
    if get_yes_no("  d) Does this step use Entities?"):
        step["entities"] = gather_entities(i+1)
    # Outgoing paths
    num_paths = get_int(f"  e) Number of outgoing paths from step {i+1}: ", min_value=0)
    step["num_outgoing_paths"] = num_paths
    if num_paths > 0:
        all_intents = [s['intent'] for s in bot['steps']] + [intent]
        step["next"] = gather_paths(i+1, num_paths, all_intents)
    bot['steps'].append(step)
    print(f"Step '{intent}' added! Press Enter to continue...")
    input()

def remove_step(bot):
    if not bot['steps']:
        print("No steps to remove.")
        input("Press Enter to continue...")
        return
    print("\nRemove a step/intent:")
    for i, step in enumerate(bot['steps']):
        print(f"  {i+1}: {step['intent']}")
    idx = get_int(f"Enter step number to remove (1-{len(bot['steps'])}): ", 1, len(bot['steps'])) - 1
    removed_intent = bot['steps'][idx]['intent']
    bot['steps'].pop(idx)
    # Update all references in paths and fallbacks
    for step in bot['steps']:
        # Update fallback_target
        if step.get('fallback_target') == idx:
            step['fallback_target'] = None
        elif isinstance(step.get('fallback_target'), int) and step['fallback_target'] > idx:
            step['fallback_target'] -= 1
        # Update next paths
        if 'next' in step and step['next']:
            new_next = []
            for path in step['next']:
                # Remove paths pointing to the removed step
                if path['target'] == idx + 1:
                    continue
                # Adjust target indices
                elif path['target'] > idx + 1:
                    path['target'] -= 1
                # Remove trigger_intent if it matches removed intent
                if path['trigger_intent'] == removed_intent:
                    continue
                new_next.append(path)
            step['next'] = new_next
    print(f"Step '{removed_intent}' removed! Press Enter to continue...")
    input()

def edit_step(bot, idx):
    step = bot['steps'][idx]
    print(f"\nEditing Step {idx+1}")
    step['intent'] = get_nonempty(f"  a) Intent name for step {idx+1} [{step['intent']}]: ") or step['intent']
    # Examples
    print(f"  b) Enter example utterances for '{step['intent']}' (enter blank to finish):")
    examples = []
    while True:
        example = input("    - ").strip()
        if not example:
            break
        examples.append(example)
    if examples:
        step['examples'] = examples
    # Responses
    print(f"  c) Enter responses for '{step['intent']}' (enter blank to finish):")
    responses = []
    while True:
        response = input("    - ").strip()
        if not response:
            break
        responses.append(response)
    if responses:
        step['responses'] = responses
    # Fallback
    if get_yes_no("  d) Will you define a fallback path for this step?"):
        print("    ↳ Available steps:")
        for idx2, intent_name in enumerate([s['intent'] for s in bot['steps']]):
            print(f"      {idx2}: {intent_name}")
        step['fallback_target'] = get_int("    ↳ Fallback target step index: ", min_value=0, max_value=len(bot['steps'])-1)
    else:
        step['fallback_target'] = None
    # Entities
    if get_yes_no("  e) Does this step use Entities?"):
        step['entities'] = gather_entities(idx+1)
    else:
        step['entities'] = []
    # Outgoing paths
    num_paths = get_int(f"  f) Number of outgoing paths from step {idx+1}: ", min_value=0)
    step['num_outgoing_paths'] = num_paths
    if num_paths > 0:
        step['next'] = gather_paths(idx+1, num_paths, [s['intent'] for s in bot['steps']])
    else:
        step['next'] = []
    print(f"Step {idx+1} updated! Press Enter to continue...")
    input()

def main():
    clear_screen()
    print("\n🎯 Welcome to the Rasa Chatbot Step-by-Step Builder!\n")
    bot = {}
    bot["name"] = get_nonempty("0) Chatbot Name: ")
    bot["description"] = get_nonempty("1) Bot Description: ")
    total_steps = get_int("2) Number of Steps (nodes): ", min_value=1)
    bot["steps"] = []

    # First, collect all intent names
    print("\nEnter intent names for each step:")
    step_intents = []
    for i in range(total_steps):
        intent = get_nonempty(f"  Intent name for step {i+1}: ")
        step_intents.append(intent)

    # Now, for each step, collect the rest of the info
    for i in range(total_steps):
        clear_screen()
        print(f"\n── Step {i+1} / {total_steps} ──")
        intent = step_intents[i]
        # Examples
        examples = []
        print(f"  a) Enter example utterances for '{intent}' (enter blank to finish):")
        while True:
            example = input("    - ").strip()
            if not example:
                break
            examples.append(example)
        # Responses
        responses = []
        print(f"  b) Enter responses for '{intent}' (enter blank to finish):")
        while True:
            response = input("    - ").strip()
            if not response:
                break
            responses.append(response)
        step = {
            "index": i,
            "intent": intent,
            "action": f"utter_{intent}",
            "responses": responses,
            "examples": examples,
            "num_outgoing_paths": 0,
            "fallback_target": None,
            "entities": [],
            "next": []
        }
        # Fallback
        if get_yes_no("  c) Will you define a fallback path for this step?"):
            print("    ↳ Available steps:")
            for idx, intent_name in enumerate(step_intents):
                print(f"      {idx}: {intent_name}")
            step["fallback_target"] = get_int("    ↳ Fallback target step index: ", min_value=0, max_value=i)
        # Entities
        if get_yes_no("  d) Does this step use Entities?"):
            step["entities"] = gather_entities(i+1)
        # Outgoing paths
        num_paths = get_int(f"  e) Number of outgoing paths from step {i+1}: ", min_value=0)
        step["num_outgoing_paths"] = num_paths
        if num_paths > 0:
            step["next"] = gather_paths(i+1, num_paths, step_intents)
        bot["steps"].append(step)
    # Review and edit
    review_and_edit(bot)
    # Save
    with open("bot_config.json", "w") as f:
        json.dump(bot, f, indent=2)
    print("\n💾 Saved as bot_config.json")
    print("\n🚀 You're all set to pass this JSON to your parser/generator!\n")

if __name__ == "__main__":
    main()