from pathlib import Path
import random

root = Path(".")
base_train = root / "training" / "data" / "train.jsonl"
edge_extra = root / "training" / "data" / "router_edge_train_extra.jsonl"
output = root / "training" / "data" / "train_v2_edge.jsonl"

records = []

for path in [base_train, edge_extra]:
    lines = path.read_text(encoding="utf-8").splitlines()
    records.extend([line for line in lines if line.strip()])

random.seed(42)
random.shuffle(records)

output.write_text("\n".join(records) + "\n", encoding="utf-8")

print(f"Base train: {len(base_train.read_text(encoding='utf-8').splitlines())}")
print(f"Edge extra: {len(edge_extra.read_text(encoding='utf-8').splitlines())}")
print(f"Wrote V2 train: {len(records)} records to {output}")
