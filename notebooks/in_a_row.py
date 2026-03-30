import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load data
data = pd.read_csv('./data/SPY_pit_5s_20250428_1148.csv')

# Define parameters
k_open = 2  
k_close = 90580  # 15000
N = 5
S = data['close'][k_open:k_close].values
n = len(S)

# Initialization
V_0 = 10000
U = V_0
u = np.zeros(n)
V = np.zeros(n)
V[0] = V_0
IAR = 0

# Trading algorithm
for k in range(1, n-1):
    if S[k] > S[k-1]:
        IAR += 1
    else:
        IAR = 0

    if IAR >= N:
        u[k] = np.sign(k - 9360) * U  # REVERSION
    else:
        u[k] = 0

    X_k = (S[k+1] - S[k]) / S[k]
    V[k+1] = V[k] + X_k * u[k]

# Plot price evolution
plt.figure(figsize=(10, 5))
plt.plot(S, 'k', linewidth=3)
plt.grid()
plt.title('Trading Prices Over the Period')
plt.xlabel('Trade Number')
plt.ylabel('Price')
plt.show()

# Plot account value evolution
plt.figure(figsize=(10, 5))
plt.plot(V, 'k', linewidth=3)
plt.grid()
plt.title('Account Value')
plt.xlabel('Trade Number')
plt.ylabel('Value')
plt.show()