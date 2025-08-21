# sitecustomize.py
# Auto-load local SWE-bench repo spec + local JSONL loader
try:
    import scripts.swebench_specs_local   # registers "Instagram/MonkeyType"
    import scripts.patch_local_jsonl      # enables local JSONL path for dataset_name
    import scripts.patch_namespace_none
    import scripts.patch_base_conda_download   
except Exception as e:
    import sys, traceback
    print("Warning loading local SWE-bench patches:", e, file=sys.stderr)
    traceback.print_exc()
