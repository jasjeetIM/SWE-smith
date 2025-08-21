# scripts/patch_local_jsonl.py
import os
from datasets import load_dataset
import swebench.harness.utils as hutils

_orig = hutils.load_swebench_dataset

def _load_swebench_dataset_local_aware(name, split, instance_ids=None):
    """
    If `name` is a local file path, load it as a JSON/JSONL dataset.
    Works whether the harness passes (name, split) or (name, split, instance_ids).
    """
    if isinstance(name, str) and os.path.isfile(name):
        ds = load_dataset("json", data_files=name, split="train")
        # Optional: filter to the requested instance_ids
        if instance_ids:
            wanted = set(instance_ids if isinstance(instance_ids, (list, tuple, set)) else [instance_ids])
            ds = ds.filter(lambda ex: ex.get("instance_id") in wanted)
        return ds

    # Fall back to the original loader. Support both old and new signatures.
    try:
        return _orig(name, split, instance_ids)  # newer harness versions
    except TypeError:
        return _orig(name, split)                # older harness versions

# Apply monkey-patch
hutils.load_swebench_dataset = _load_swebench_dataset_local_aware
print("[patch_local_jsonl] Local JSON/JSONL dataset loader enabled")

