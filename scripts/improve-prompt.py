#!/usr/bin/env python3
"""
Claude Code Prompt Improver Hook
Evaluates prompts for clarity and invokes the prompt-improver skill for vague cases.

Architecture: Default pass-through, use '?' prefix to trigger evaluation.
"""
import json
import sys

# Configuration
TRIGGER_PREFIX = '?'  # Prefix to trigger evaluation

# Load input from stdin
try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
    sys.exit(1)

prompt = input_data.get("prompt", "")

def output_json(text):
    """Output text in UserPromptSubmit JSON format"""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": text
        }
    }
    print(json.dumps(output))

# Check for trigger conditions
# 1. Trigger evaluation with ? prefix
# 2. Slash commands (built-in or custom)
# 3. Memorize feature (# prefix)

if prompt.startswith(TRIGGER_PREFIX):
    # User requested evaluation - remove trigger prefix and add wrapper
    clean_prompt = prompt[len(TRIGGER_PREFIX):].strip()
    escaped_prompt = clean_prompt.replace("\\", "\\\\").replace('"', '\\"')

    wrapped_prompt = f"""PROMPT EVALUATION

Original user request: "{escaped_prompt}"

EVALUATE: Is this prompt clear enough to execute, or does it need enrichment?

PROCEED IMMEDIATELY if:
- Detailed/specific OR you have sufficient context OR can infer intent

ONLY USE SKILL if genuinely vague (e.g., "fix the bug" with no context):
- If vague:
  1. First, preface with brief note: "Hey! The Prompt Improver Hook flagged your prompt as a bit vague because [specific reason: ambiguous scope/missing context/unclear target/etc]."
  2. Then use the prompt-improver skill to research and generate clarifying questions
- The skill will guide you through research, question generation, and execution
- Trust user intent by default. Check conversation history before using the skill.

If clear, proceed with the original request. If vague, invoke the skill."""

    output_json(wrapped_prompt)
    sys.exit(0)

if prompt.startswith("/"):
    # Slash command - pass through unchanged
    output_json(prompt)
    sys.exit(0)

if prompt.startswith("#"):
    # Memorize feature - pass through unchanged
    output_json(prompt)
    sys.exit(0)

# Default: pass through unchanged (no evaluation)
output_json(prompt)
sys.exit(0)
