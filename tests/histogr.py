
import random

import numpy as np

class VolumeSpikeHistogramNP:
    def __init__(self, vmin=0, vmax=3500, bins=20):
        self.vmin = vmin
        self.vmax = vmax
        self.bins = bins
        self.width = (vmax - vmin) / bins

        self.hist = np.zeros(bins, dtype=np.float64)
        self.total = 0.0

    def _bin_index(self, vol):
        # compute raw index
        idx = int((vol - self.vmin) / self.width)
        # clip to valid range
        return max(0, min(self.bins - 1, idx))

    def update(self, vol):
        idx = self._bin_index(vol)

        # tail probability BEFORE updating
        if self.total == 0:
            p = 1.0
        else:
            p = self.hist[idx:].sum() / self.total

        # update histogram
        self.hist[idx] += 1.0
        self.total += 1.0

        return p, idx

    def spike(self, vol, threshold=0.01):
        p, idx = self.update(vol)
        return p < threshold, p, idx

if __name__ == "__main__":
    vsh = VolumeSpikeHistogramNP(0, 100, 10)
    for i in range(10):
        x = random.randint(0, 100)
        print(f'Iteration i={i}, x={x}')
        print(vsh.update(x))
        print(vsh.hist)