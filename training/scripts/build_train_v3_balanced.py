from pathlib import Path
import random

root = Path(".")
base_train = root / "training" / "data" / "train.jsonl"
edge_extra = root / "training" / "data" / "router_edge_train_extra.jsonl"
frontend_manual = root / "training" / "data" / "frontend_manual_eval.jsonl"
output = root / "training" / "data" / "train_v3_balanced.jsonl"

records = []

records.extend([line for line in base_train.read_text(encoding="utf-8").splitlines() if line.strip()])
records.extend([line for line in edge_extra.read_text(encoding="utf-8").splitlines() if line.strip()])

# Repeat frontend manual examples as anchors so V3 does not forget normal frontend behavior.
frontend_lines = [line for line in frontend_manual.read_text(encoding="utf-8").splitlines() if line.strip()]
records.extend(frontend_lines)
records.extend(frontend_lines)

random.seed(43)
random.shuffle(records)

output.write_text("\n".join(records) + "\n", encoding="utf-8")

print(f"Base train: {len(base_train.read_text(encoding='utf-8').splitlines())}")
print(f"Edge extra: {len(edge_extra.read_text(encoding='utf-8').splitlines())}")
print(f"Frontend anchors x2: {len(frontend_lines) * 2}")
print(f"Wrote V3 train: {len(records)} records to {output}")
