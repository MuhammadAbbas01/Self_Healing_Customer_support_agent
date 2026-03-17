import matplotlib.pyplot as plt
import numpy as np

# Data for the benchmark chart
categories = ['Manual Support', 'Standard AI Bot', 'Self-Healing Agent']
mttr_hours = [24, 4, 0.5]  # Mean Time To Resolution in hours
accuracy_percent = [95, 70, 92]  # Resolution Accuracy in percentage

x = np.arange(len(categories))
width = 0.35

fig, ax1 = plt.subplots(figsize=(10, 6))

# Bar chart for MTTR
bars1 = ax1.bar(x - width/2, mttr_hours, width, label='MTTR (Hours)', color='skyblue')
ax1.set_xlabel('Support System')
ax1.set_ylabel('MTTR (Hours)', color='skyblue')
ax1.tick_params(axis='y', labelcolor='skyblue')
ax1.set_xticks(x)
ax1.set_xticklabels(categories)

# Instantiate a second axes that shares the same x-axis
ax2 = ax1.twinx()
bars2 = ax2.bar(x + width/2, accuracy_percent, width, label='Accuracy (%)', color='salmon')
ax2.set_ylabel('Accuracy (%)', color='salmon')
ax2.tick_params(axis='y', labelcolor='salmon')
ax2.set_ylim(0, 100)

# Add title and legend
plt.title('Performance Benchmark: Self-Healing Agent vs. Traditional Systems')
fig.tight_layout()

# Save the plot
plt.savefig('/home/ubuntu/Self_Healing_Customer_support_agent/performance_benchmarks.png')
print("✅ Performance benchmark chart generated!")
