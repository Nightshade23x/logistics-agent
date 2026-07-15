from pathlib import Path
import random

root = Path(".")
base_train = root / "training" / "data" / "train.jsonl"
edge_extra = root / "training" / "data" / "router_edge_train_extra.jsonl"
frontend_manual = root / "training" / "data" / "frontend_manual_eval.jsonl"
v4_targeted = root / "training" / "data" / "router_v4_targeted_extra.jsonl"
output = root / "training" / "data" / "train_v4_balanced.jsonl"

records = []

base_lines = [line for line in base_train.read_text(encoding="utf-8").splitlines() if line.strip()]
edge_lines = [line for line in edge_extra.read_text(encoding="utf-8").splitlines() if line.strip()]
frontend_lines = [line for line in frontend_manual.read_text(encoding="utf-8").splitlines() if line.strip()]
targeted_lines = [line for line in v4_targeted.read_text(encoding="utf-8").splitlines() if line.strip()]

records.extend(base_lines)
records.extend(edge_lines)

# Anchor normal frontend behavior.
records.extend(frontend_lines)
records.extend(frontend_lines)

# Stronger weight for the exact failure patterns.
records.extend(targeted_lines)
records.extend(targeted_lines)
records.extend(targeted_lines)

random.seed(44)
random.shuffle(records)

output.write_text("\n".join(records) + "\n", encoding="utf-8")

print(f"Base train: {len(base_lines)}")
print(f"Edge extra: {len(edge_lines)}")
print(f"Frontend anchors x2: {len(frontend_lines) * 2}")
print(f"V4 targeted x3: {len(targeted_lines) * 3}")
print(f"Wrote V4 train: {len(records)} records to {output}")
