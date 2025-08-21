from swebench.harness.constants import MAP_REPO_VERSION_TO_SPECS, MAP_REPO_TO_EXT

# Use version=None because your JSONL has "version": null
MAP_REPO_VERSION_TO_SPECS.setdefault("Instagram/MonkeyType", {})[None] = {
    "python": "3.10",
    "install": "python -m pip install -e .",
    "pip_packages": ["pytest"],
    "test_cmd": "pytest -q",
}
MAP_REPO_TO_EXT["Instagram/MonkeyType"] = "py"

print("[swebench_specs_local] Registered spec for Instagram/MonkeyType (version=None)")
