# scripts/patch_namespace_none.py
import swebench.harness.run_evaluation as re
try:
    # Some versions expose a module-level constant; set it to None
    if hasattr(re, "DEFAULT_NAMESPACE"):
        re.DEFAULT_NAMESPACE = None
    # Also patch argparse default after parser creation if needed
    if hasattr(re, "get_args_parser"):
        p = re.get_args_parser()
        # Only do this if the arg exists and currently has a default
        if any(a.dest == "namespace" for a in p._actions):
            for a in p._actions:
                if a.dest == "namespace":
                    a.default = None
                    break
    print("[patch_namespace_none] Default namespace set to None")
except Exception as e:
    print("[patch_namespace_none] Skipped:", e)
