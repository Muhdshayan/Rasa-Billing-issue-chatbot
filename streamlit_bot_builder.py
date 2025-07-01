import streamlit as st
import ollama
import json
import yaml
import zipfile
import io
import re
from typing import Dict, List

# Call Mistral LLM using ollama.chat
def call_mistral(prompt, stop=None):
    try:
        response = ollama.chat(
            model='mistral:7b',
            messages=[
                {
                    'role': 'user',
                    'content': prompt,
                },
            ],
            options={"temperature": 0.7}
        )
        if "message" in response and "content" in response["message"]:
            return response["message"]["content"].strip()
        else:
            st.error(f"Unexpected response format: {response}")
            return "Please provide your input manually."
            
    except Exception as e:
        st.error(f"Error calling Ollama API: {e}")
        return "Please provide your input manually."

# Chatbot spec structure
def get_empty_spec():
    return {
        "use_case": "",
        "steps": [],
        "entities": [],
        "intents": [],
        "responses": [],
        "stories": [],
        "nlu_examples": []
    }

field_order = [
    "use_case",
    "steps",
    "entities", 
    "intents",
    "responses",
    "stories",
    "nlu_examples"
]

prompt_templates = {
    "use_case": """You're helping build a Rasa chatbot step-by-step for any use case.\nStart by asking the creator: \n'What is the chatbot's purpose or use-case?'""",
    "steps": """So far, the Rasa chatbot is for: "{use_case}".\nAsk the user: "What are the main steps or actions the bot should handle? (e.g., greet user, collect information, process request)" """,
    "entities": """The Rasa chatbot is for: "{use_case}".\nThe main steps are: {steps}.\nAsk: "What information should the bot extract from the user? (e.g., name, order_id)" """,
    "intents": """The Rasa chatbot is for: "{use_case}".\nThe main steps are: {steps}.\nEntities: {entities}.\nAsk: "What are the main user intents? (e.g., place_order, check_status)" """,
    "responses": """The Rasa chatbot is for: "{use_case}".\nSteps: {steps}.\nEntities: {entities}.\nIntents: {intents}.\nAsk: "What should the bot say at each step? (Provide example responses for each step, semicolon-separated.)" """,
    "stories": """The Rasa chatbot is for: "{use_case}".\nSteps: {steps}.\nEntities: {entities}.\nIntents: {intents}.\nResponses: {responses}.\nAsk: "Describe a typical conversation flow (story) between user and bot, step by step, including user inputs and bot responses." """,
    "nlu_examples": """The Rasa chatbot is for: "{use_case}".\nIntents: {intents}.\nThe LLM will generate example utterances for each intent. Review the generated examples below and edit if needed (one set of examples per intent, semicolon-separated)."""
}

def update_spec(chatbot_spec, field, user_input):
    if field in ["steps", "entities", "intents"]:
        chatbot_spec[field] = [x.strip() for x in user_input.split(",") if x.strip()]
    elif field in ["responses", "nlu_examples"]:
        chatbot_spec[field] = [x.strip() for x in user_input.split(";") if x.strip()]
    elif field == "stories":
        chatbot_spec[field] = [user_input.strip()]
    else:
        chatbot_spec[field] = user_input.strip()

def extract_entities_from_stories(story_text, entities):
    """Extract entity values from story text using simple pattern matching."""
    extracted_slots = []
    for entity in entities:
        entity_key = entity.replace(" ", "_")
        # Look for entity mentions in user inputs (e.g., "account number 987654321" or "$100")
        pattern = rf"{entity}\s*[:=]?\s*([^\s.]+)" if entity in ["account number", "transaction amount"] else rf"\b{entity}\b\s*([^\s.]+)"
        matches = re.findall(pattern, story_text, re.IGNORECASE)
        if matches:
            extracted_slots.append({"slot_was_set": {entity_key: matches[0]}})
    return extracted_slots

def generate_rasa_files(chatbot_spec):
    # domain.yml
    domain = {
        "version": "3.1",
        "intents": chatbot_spec["intents"] + ["greet"],
        "entities": [entity.replace(" ", "_") for entity in chatbot_spec["entities"]],
        "responses": {
            f"utter_{step.replace(' ', '_')}": [{"text": response}] 
            for step, response in zip(chatbot_spec["steps"], chatbot_spec["responses"])
        },
        "session_config": {
            "session_expiration_time": 60,
            "carry_over_slots_to_new_session": True
        }
    }
    
    # data/nlu.yml
    nlu = {
        "version": "3.1",
        "nlu": [
            {
                "intent": intent,
                "examples": "\n".join(f"- {example.strip()}" for example in examples.split(",") if example.strip())
            } for intent, examples in zip(chatbot_spec["intents"], chatbot_spec["nlu_examples"])
        ] + [
            {
                "intent": "greet",
                "examples": "- hi\n- hello\n- hey"
            }
        ]
    }
    
    # data/rules.yml
    rules = {
        "version": "3.1",
        "rules": [
            {
                "rule": "Greet user",
                "steps": [
                    {"intent": "greet"},
                    {"action": "utter_greet_user"}
                ]
            }
        ]
    }
    
    # data/stories.yml
    story_steps = []
    story_lines = chatbot_spec["stories"][0].split(". ")
    for i, line in enumerate(story_lines):
        if line.startswith("User:"):
            intent = chatbot_spec["intents"][min(i // 2, len(chatbot_spec["intents"]) - 1)] if i // 2 < len(chatbot_spec["intents"]) else "greet"
            story_steps.append({"intent": intent})
            # Extract entities from user input
            user_input = line.replace("User:", "").strip()
            extracted_slots = extract_entities_from_stories(user_input, chatbot_spec["entities"])
            story_steps.extend(extracted_slots)
        elif line.startswith("Bot:"):
            action = f"utter_{chatbot_spec['steps'][min(i // 2, len(chatbot_spec['steps']) - 1)].replace(' ', '_')}" if i // 2 < len(chatbot_spec["steps"]) else "utter_greet_user"
            story_steps.append({"action": action})
    
    stories = {
        "version": "3.1",
        "stories": [
            {
                "story": chatbot_spec["use_case"].replace(" ", "_"),
                "steps": story_steps
            }
        ]
    }
    
    # Create zip archive
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("domain.yml", yaml.dump(domain, sort_keys=False))
        zip_file.writestr("data/nlu.yml", yaml.dump(nlu, sort_keys=False))
        zip_file.writestr("data/rules.yml", yaml.dump(rules, sort_keys=False))
        zip_file.writestr("data/stories.yml", yaml.dump(stories, sort_keys=False))
    
    zip_buffer.seek(0)
    return zip_buffer

def main():
    st.set_page_config(
        page_title="Rasa Chatbot Builder",
        page_icon="🤖",
        layout="wide"
    )
    
    st.title("🤖 Rasa Chatbot Builder")
    st.markdown("Build your Rasa chatbot step by step with AI assistance")
    
    # Initialize session state
    if 'chatbot_spec' not in st.session_state:
        st.session_state.chatbot_spec = get_empty_spec()
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 0
    if 'ai_suggestions' not in st.session_state:
        st.session_state.ai_suggestions = {}
    
    # Sidebar for progress
    with st.sidebar:
        st.header("Progress")
        for i, field in enumerate(field_order):
            if st.session_state.chatbot_spec[field]:
                st.success(f"✅ {field.replace('_', ' ').title()}")
            elif i == st.session_state.current_step:
                st.info(f"🔄 {field.replace('_', ' ').title()}")
            else:
                st.write(f"⏳ {field.replace('_', ' ').title()}")
        
        st.divider()
        
        if st.button("Reset Builder", type="secondary"):
            st.session_state.chatbot_spec = get_empty_spec()
            st.session_state.current_step = 0
            st.session_state.ai_suggestions = {}
            st.rerun()
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        current_field = field_order[st.session_state.current_step]
        
        st.header(f"Step {st.session_state.current_step + 1}: {current_field.replace('_', ' ').title()}")
        
        # Get AI suggestion if not already generated
        if current_field not in st.session_state.ai_suggestions:
            if current_field == "use_case":
                prompt = prompt_templates[current_field]
            elif current_field == "nlu_examples":
                prompt = f"""
                You are helping build a Rasa chatbot for: "{st.session_state.chatbot_spec['use_case']}".
                The intents are: {', '.join(st.session_state.chatbot_spec['intents'])}.
                For each intent, generate 5 example utterances that users might say to trigger that intent.
                Format the output as a JSON object where each intent is a key, and the value is a list of 5 utterances.
                Example:
                {{
                  "check_balance": [
                    "How much is in my account?",
                    "What's my balance?",
                    "Show me my account balance.",
                    "Can you tell me my current balance?",
                    "Check my savings account."
                  ],
                  "transfer_money": [
                    "Send $100 to my savings.",
                    "Transfer money to another account.",
                    "Move $50 to account 123456.",
                    "I want to transfer $200.",
                    "Can you send money to my friend?"
                  ]
                }}
                Return only the JSON object, no additional text.
                """
                try:
                    suggestion = call_mistral(prompt)
                    try:
                        # Parse JSON and format as semicolon-separated strings
                        examples_dict = json.loads(suggestion)
                        formatted_examples = []
                        for intent in st.session_state.chatbot_spec["intents"]:
                            examples = examples_dict.get(intent, [])
                            formatted_examples.append(", ".join(examples))
                        st.session_state.ai_suggestions[current_field] = "; ".join(formatted_examples)
                    except json.JSONDecodeError:
                        st.session_state.ai_suggestions[current_field] = "Failed to generate examples; please enter manually."
                except Exception:
                    st.session_state.ai_suggestions[current_field] = "Failed to generate examples; please enter manually."
            else:
                prompt = prompt_templates[current_field].format(
                    use_case=st.session_state.chatbot_spec["use_case"],
                    steps=", ".join(st.session_state.chatbot_spec["steps"]),
                    entities=", ".join(st.session_state.chatbot_spec["entities"]),
                    intents=", ".join(st.session_state.chatbot_spec["intents"]),
                    responses="; ".join(st.session_state.chatbot_spec["responses"])
                )
                st.session_state.ai_suggestions[current_field] = call_mistral(prompt)
        
        # Display AI suggestion
        with st.expander("🤖 AI Suggestion", expanded=True):
            suggestion = st.session_state.ai_suggestions.get(current_field, "No suggestion available yet.")
            st.write(suggestion)
        
        # Input field
        if current_field in ["steps", "entities", "intents"]:
            user_input = st.text_area(
                f"Enter {current_field.replace('_', ' ').title()} (comma-separated):",
                placeholder="e.g., greet user, collect information, process request",
                height=100
            )
        elif current_field in ["responses", "nlu_examples"]:
            user_input = st.text_area(
                f"Enter {current_field.replace('_', ' ').title()} (semicolon-separated, one set per intent for NLU examples):",
                placeholder="e.g., Hello! How can I help you?; Your request is processed; (for responses) or How much is in my account?, What's my balance?, ...; Send $100 to my savings., Transfer money... (for nlu_examples)",
                height=150
            )
        elif current_field == "stories":
            user_input = st.text_area(
                f"Enter {current_field.replace('_', ' ').title()}:",
                placeholder="Describe a typical conversation flow (e.g., User: I need help. Bot: How can I assist you? ...)",
                height=200
            )
        else:
            user_input = st.text_input(
                f"Enter {current_field.replace('_', ' ').title()}:",
                placeholder="e.g., Customer support chatbot for any domain"
            )
        
        # Navigation buttons
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        
        with col_btn1:
            if st.session_state.current_step > 0:
                if st.button("← Previous"):
                    st.session_state.current_step -= 1
                    st.rerun()
        
        with col_btn2:
            if user_input.strip():
                if st.button("Save & Continue →"):
                    update_spec(st.session_state.chatbot_spec, current_field, user_input)
                    if st.session_state.current_step < len(field_order) - 1:
                        st.session_state.current_step += 1
                    st.rerun()
        
        with col_btn3:
            if st.button("Skip for now"):
                if st.session_state.current_step < len(field_order) - 1:
                    st.session_state.current_step += 1
                st.rerun()
    
    with col2:
        st.header("Current Spec")
        
        # Display current chatbot spec
        for field in field_order:
            if st.session_state.chatbot_spec[field]:
                with st.expander(f"{field.replace('_', ' ').title()}", expanded=False):
                    if isinstance(st.session_state.chatbot_spec[field], list):
                        for item in st.session_state.chatbot_spec[field]:
                            st.write(f"• {item}")
                    else:
                        st.write(st.session_state.chatbot_spec[field])
        
        # Export buttons
        if all(st.session_state.chatbot_spec[field] for field in field_order):
            st.success("🎉 Rasa chatbot spec is complete!")
            
            # Download JSON
            json_str = json.dumps(st.session_state.chatbot_spec, indent=2)
            st.download_button(
                label="📥 Download Spec (JSON)",
                data=json_str,
                file_name="chatbot_spec.json",
                mime="application/json"
            )
            
            # Download Rasa files as zip
            zip_buffer = generate_rasa_files(st.session_state.chatbot_spec)
            st.download_button(
                label="📥 Download Rasa Files (ZIP)",
                data=zip_buffer,
                file_name="rasa_chatbot_files.zip",
                mime="application/zip"
            )
            
            # Display final spec
            st.json(st.session_state.chatbot_spec)

if __name__ == "__main__":
    main()