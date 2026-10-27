from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"

categories = ["Manual Support", "Standard AI Bot", "Self-Healing Agent"]
mttr_hours = [24, 4, 0.5]
accuracy_percent = [95, 70, 92]

x = np.arange(len(categories))
width = 0.35

fig, ax1 = plt.subplots(figsize=(10, 6))
ax1.bar(x - width / 2, mttr_hours, width, color="skyblue")
ax1.set_xlabel("Support System")
ax1.set_ylabel("MTTR (Hours)", color="skyblue")
ax1.tick_params(axis="y", labelcolor="skyblue")
ax1.set_xticks(x)
ax1.set_xticklabels(categories)

ax2 = ax1.twinx()
ax2.bar(x + width / 2, accuracy_percent, width, color="salmon")
ax2.set_ylabel("Accuracy (%)", color="salmon")
ax2.tick_params(axis="y", labelcolor="salmon")
ax2.set_ylim(0, 100)

plt.title("Performance Benchmark: Self-Healing Agent vs. Traditional Systems")
fig.tight_layout()
plt.savefig(DOCS_DIR / "performance_benchmarks.png")
print("Saved docs/performance_benchmarks.png")
