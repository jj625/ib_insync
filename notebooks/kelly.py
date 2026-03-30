import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Load data
data = pd.read_csv('SPY_pit_1m_20250401_0842_w_deletions.csv')  # Adjust file path as needed
# data = pd.read_csv('SPY_pit_15s_20250422_0834_w_deletions.csv')
k_open = 568  # Adjust indices as needed
k_close = 5251
delta_t = 10  # seconds between trades
m = 10  # number of training samples of returns
n = int((k_close - k_open) * 5 / delta_t)  # number of 5-min intervals
data = data['average'][k_open:k_close]
scale = 10 ** 4

# Initialization
V = [10000]
S = [data.iloc[0]]

for i in range(1, n + 2):
    S.append(data.iloc[int((i - 1) * delta_t / 5)])

# Calculate returns
X = [(S[i + 1] - S[i]) / S[i] for i in range(n)]

# Plot training sample prices over the day
plt.figure()
plt.plot(S, 'k', linewidth=3)
plt.grid()
plt.title('Training Sample Prices Over the Day')
plt.show()

K = []
ELG = []
K_star = []
ELG_star = []
ii = 0

# Loop for training and finding optimal feedback gain
for k in range(n - m - 1):
    for KK in np.arange(-1, 1.01, 0.01):  # Feedback gain range
        ii += 1
        K.append(KK)
        ELG.append(scale * (1 / m) * sum(np.log(1 + KK * np.array(X[k:k + m]))))

    # Find maximum ELG and corresponding K
    a = max(ELG)
    b = ELG.index(a)
    K_star.append(K[b])
    ELG_star.append(a)
    V.append((1 + K_star[-1] * X[m + k]) * V[-1])

# Plot optimal feedback gain
plt.figure()
plt.plot(K_star, 'k', linewidth=3)
plt.grid()
plt.title('Optimal Feedback Versus Trade Number')
plt.xlabel('Feedback Gain K')
plt.show()

# Plot account value
plt.figure()
plt.plot(V, 'k', linewidth=3)
plt.grid()
plt.title('Account Value')
plt.xlabel('Trade Number')
plt.show()