#!/usr/bin/env python3
"""
Integration tests for the prompt-improver system
Tests the complete flow from hook to skill
"""
import json
import subprocess
import sys
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
HOOK_SCRIPT = PROJECT_ROOT / "scripts" / "improve-prompt.py"
PLUGIN_JSON = PROJECT_ROOT / ".claude-plugin" / "plugin.json"
SKILL_DIR = PROJECT_ROOT / "skills" / "prompt-improver"

def run_hook(prompt):
    """Run the hook script with given prompt"""
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

def test_plugin_configuration():
    """Test that plugin.json is properly configured"""
    assert PLUGIN_JSON.exists(), "plugin.json not found"

    config = json.loads(PLUGIN_JSON.read_text())

    # Check version is 0.5.1
    assert config["version"] == "0.5.1", f"Expected version 0.5.1, got {config['version']}"

    # Check skills field exists
    assert "skills" in config, "Missing 'skills' field in plugin.json"
    assert isinstance(config["skills"], list), "'skills' should be a list"
    assert len(config["skills"]) > 0, "'skills' list is empty"

    # Check hooks field is NOT present (standard hooks/hooks.json is auto-discovered)
    assert "hooks" not in config, "The 'hooks' field should not be present (standard location is auto-discovered)"

    # Check skill path
    skill_path = config["skills"][0]
    assert skill_path == "./skills/prompt-improver", f"Unexpected skill path: {skill_path}"

    # Verify skill directory exists
    resolved_skill_path = PROJECT_ROOT / skill_path.lstrip("./")
    assert resolved_skill_path.exists(), f"Skill directory not found: {resolved_skill_path}"

    print("✓ Plugin configuration is correct")

def test_trigger_evaluation_flow():
    """Test complete flow when ? prefix triggers evaluation"""
    # Test ? prefix triggers evaluation
    output = run_hook("? add authentication")

    # Should get evaluation wrapper
    context = output["hookSpecificOutput"]["additionalContext"]
    assert "PROMPT EVALUATION" in context or "EVALUATE" in context
    assert "add authentication" in context  # Original prompt content (without prefix)
    assert not context.startswith("?")  # Context should not start with the trigger prefix

    # Should mention skill for vague cases
    assert "skill" in context.lower()

    print("✓ Trigger evaluation flow works (? prefix → evaluation wrapper)")

def test_default_pass_through_flow():
    """Test that default mode passes through unchanged"""
    # Test normal prompt (no prefix) - should pass through
    output = run_hook("add authentication")

    context = output["hookSpecificOutput"]["additionalContext"]
    assert context == "add authentication"  # unchanged
    assert "PROMPT EVALUATION" not in context

    print("✓ Default pass-through flow works (no prefix → unchanged)")

def test_special_prefix_flow():
    """Test that / and # prefixes pass through unchanged"""
    # Test slash command
    output = run_hook("/commit")
    context = output["hookSpecificOutput"]["additionalContext"]
    assert context == "/commit"

    # Test hash prefix (memorize)
    output = run_hook("# note for later")
    context = output["hookSpecificOutput"]["additionalContext"]
    assert context == "# note for later"

    # Test normal prompt passes through
    output = run_hook("just do it")
    context = output["hookSpecificOutput"]["additionalContext"]
    assert context == "just do it"
    assert "skill" not in context.lower()

    print("✓ Special prefix flow works (/ and # preserved, default pass-through)")

def test_skill_file_integrity():
    """Test that all skill files are present and valid"""
    # Check SKILL.md
    skill_md = SKILL_DIR / "SKILL.md"
    assert skill_md.exists(), "SKILL.md missing"

    content = skill_md.read_text()
    assert content.startswith("---\n"), "SKILL.md missing YAML frontmatter"
    assert "name: prompt-improver" in content, "Skill name incorrect"

    # Check reference files
    references_dir = SKILL_DIR / "references"
    assert references_dir.exists(), "references directory missing"

    expected_refs = [
        "question-patterns.md",
        "research-strategies.md",
        "examples.md",
    ]

    for ref in expected_refs:
        ref_file = references_dir / ref
        assert ref_file.exists(), f"Missing reference file: {ref}"

    print("✓ All skill files present and valid")

def test_token_overhead():
    """Test that hook overhead is reasonable"""
    # Test default pass-through (should be zero overhead)
    output = run_hook("test")

    context = output["hookSpecificOutput"]["additionalContext"]
    assert context == "test"  # No wrapper, direct pass-through

    # Test triggered evaluation overhead
    output = run_hook("? test")
    context = output["hookSpecificOutput"]["additionalContext"]

    # Rough character count (tokens ≈ chars/4 for English)
    char_count = len(context)
    estimated_tokens = char_count // 4

    # Triggered evaluation should be ~189-200 tokens
    assert estimated_tokens < 250, \
        f"Evaluation overhead too high: ~{estimated_tokens} tokens (expected <250)"

    print(f"✓ Token overhead: 0 for pass-through, ~{estimated_tokens} for triggered evaluation")

def test_hook_output_consistency():
    """Test that hook output is consistent across different triggered prompts"""
    prompts = [
        "? fix the bug",
        "? add tests",
        "? refactor code",
        "? implement feature X",
    ]

    for prompt in prompts:
        output = run_hook(prompt)

        # All should have same structure
        assert "hookSpecificOutput" in output
        assert "hookEventName" in output["hookSpecificOutput"]
        assert "additionalContext" in output["hookSpecificOutput"]

        # All should have evaluation wrapper
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "EVALUATE" in context or "evaluate" in context.lower()
        # Check original prompt content (without ? prefix)
        original_prompt = prompt[2:]  # strip "? "
        assert original_prompt in context

    print(f"✓ Hook output consistent across {len(prompts)} triggered prompts")

def test_architecture_separation():
    """Test that architecture properly separates concerns"""
    # Hook should be reasonably sized (< 80 lines)
    hook_lines = len(HOOK_SCRIPT.read_text().split("\n"))
    assert hook_lines < 80, f"Hook too large: {hook_lines} lines (expected <80)"

    # Hook should contain evaluation logic
    hook_content = HOOK_SCRIPT.read_text()
    assert "PROMPT EVALUATION" in hook_content or "EVALUATE" in hook_content

    # SKILL.md should contain research and question logic (now 4 phases)
    skill_content = (SKILL_DIR / "SKILL.md").read_text()
    assert "Phase 1" in skill_content or "phase 1" in skill_content.lower()
    assert "Phase 2" in skill_content or "phase 2" in skill_content.lower()
    assert "Research" in skill_content

    # Skill should mention being invoked for vague prompts
    assert "vague" in skill_content.lower()

    print("✓ Architecture properly separates concerns (hook evaluates, skill enriches)")

def run_all_tests():
    """Run all integration tests"""
    tests = [
        test_plugin_configuration,
        test_trigger_evaluation_flow,
        test_default_pass_through_flow,
        test_special_prefix_flow,
        test_skill_file_integrity,
        test_token_overhead,
        test_hook_output_consistency,
        test_architecture_separation,
    ]

    print(f"Running {len(tests)} integration tests...\n")

    failed = []
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed.append((test.__name__, e))
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed.append((test.__name__, e))

    print(f"\n{'='*60}")
    if failed:
        print(f"FAILED: {len(failed)}/{len(tests)} tests failed")
        for name, error in failed:
            print(f"  - {name}: {error}")
        sys.exit(1)
    else:
        print(f"SUCCESS: All {len(tests)} integration tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    run_all_tests()
