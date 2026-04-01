#!/usr/bin/env python3
"""
Tests for the prompt-improver hook
Tests trigger prefix, pass-through mode, and JSON output format
"""
import json
import subprocess
import sys
from pathlib import Path

# Path to the hook script
HOOK_SCRIPT = Path(__file__).parent.parent / "scripts" / "improve-prompt.py"

def run_hook(prompt):
    """Run the hook script with given prompt and return parsed output"""
    input_data = json.dumps({"prompt": prompt})

    result = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input=input_data,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise Exception(f"Hook failed: {result.stderr}")

    return json.loads(result.stdout)

def test_trigger_question_mark():
    """Test that ? prefix triggers evaluation and strips the prefix"""
    output = run_hook("? fix the bug")

    assert "hookSpecificOutput" in output
    assert output["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"

    context = output["hookSpecificOutput"]["additionalContext"]

    # Should contain evaluation prompt
    assert "PROMPT EVALUATION" in context
    assert "fix the bug" in context
    assert "EVALUATE:" in context or "evaluate" in context.lower()

    # Should mention using the skill for vague cases
    assert "prompt-improver skill" in context.lower() or "skill" in context.lower()

    print("✓ Question mark trigger test passed")

def test_pass_through_slash():
    """Test that / prefix passes through unchanged (slash commands)"""
    output = run_hook("/commit")

    assert "hookSpecificOutput" in output
    context = output["hookSpecificOutput"]["additionalContext"]
    assert context == "/commit"
    print("✓ Slash command pass-through test passed")

def test_pass_through_hash():
    """Test that # prefix passes through unchanged (memorize feature)"""
    output = run_hook("# remember to use TypeScript")

    assert "hookSpecificOutput" in output
    context = output["hookSpecificOutput"]["additionalContext"]
    assert context == "# remember to use TypeScript"
    print("✓ Hash prefix pass-through test passed")

def test_default_pass_through():
    """Test that normal prompts pass through unchanged (no evaluation)"""
    output = run_hook("fix the bug")

    assert "hookSpecificOutput" in output
    assert output["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"

    context = output["hookSpecificOutput"]["additionalContext"]

    # Should NOT contain evaluation prompt (default pass-through)
    assert "PROMPT EVALUATION" not in context
    assert context == "fix the bug"

    print("✓ Default pass-through test passed")

def test_json_output_format():
    """Test that output follows correct JSON schema"""
    output = run_hook("test prompt")

    # Verify structure
    assert isinstance(output, dict)
    assert "hookSpecificOutput" in output
    assert isinstance(output["hookSpecificOutput"], dict)

    hook_output = output["hookSpecificOutput"]
    assert "hookEventName" in hook_output
    assert "additionalContext" in hook_output
    assert hook_output["hookEventName"] == "UserPromptSubmit"
    assert isinstance(hook_output["additionalContext"], str)

    print("✓ JSON output format test passed")

def test_empty_prompt():
    """Test handling of empty prompt (pass-through)"""
    output = run_hook("")

    assert "hookSpecificOutput" in output
    context = output["hookSpecificOutput"]["additionalContext"]

    # Should pass through unchanged (no evaluation)
    assert context == ""
    print("✓ Empty prompt test passed")

def test_multiline_prompt():
    """Test handling of multiline prompts (pass-through)"""
    prompt = """refactor the auth system
to use async/await
and add error handling"""

    output = run_hook(prompt)

    assert "hookSpecificOutput" in output
    context = output["hookSpecificOutput"]["additionalContext"]

    # Should pass through unchanged (no evaluation)
    assert context == prompt
    print("✓ Multiline prompt test passed")

def test_special_characters():
    """Test handling of special characters in prompts"""
    output = run_hook('fix the "bug" in user\'s code & database')

    assert "hookSpecificOutput" in output
    context = output["hookSpecificOutput"]["additionalContext"]

    # Should pass through unchanged (no evaluation)
    assert 'fix the "bug" in user\'s code & database' in context
    print("✓ Special characters test passed")

def run_all_tests():
    """Run all tests"""
    tests = [
        test_trigger_question_mark,
        test_pass_through_slash,
        test_pass_through_hash,
        test_default_pass_through,
        test_json_output_format,
        test_empty_prompt,
        test_multiline_prompt,
        test_special_characters,
    ]

    print(f"Running {len(tests)} hook tests...\n")

    failed = []
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed.append((test.__name__, e))

    print(f"\n{'='*60}")
    if failed:
        print(f"FAILED: {len(failed)}/{len(tests)} tests failed")
        for name, error in failed:
            print(f"  - {name}: {error}")
        sys.exit(1)
    else:
        print(f"SUCCESS: All {len(tests)} hook tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    run_all_tests()
