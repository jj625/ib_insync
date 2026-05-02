
import random

import numpy as np

import numpy as np
# import matplotlib.pyplot as plt

class DynamicCompressedHistogramNP:
    """
    Faithful dynamic compressed histogram with NumPy storage.
    Maintains at most `max_bins` bins.
    Each bin is represented by:
        lo[i], hi[i], count[i]
    """

    def __init__(self, max_bins=20):
        self.max_bins = max_bins
        self.lo = np.array([], dtype=float)
        self.hi = np.array([], dtype=float)
        self.count = np.array([], dtype=float)

    # ------------------------------------------------------------
    # Core helpers
    # ------------------------------------------------------------

    def _find_bin(self, x):
        """Return index of bin containing x, or insertion point."""
        for i in range(len(self.lo)):
            if self.lo[i] <= x <= self.hi[i]:
                return i
            if x < self.lo[i]:
                return i
        return len(self.lo)

    def _split_bin(self, i):
        """Split bin i into two equal-width bins."""
        lo, hi, c = self.lo[i], self.hi[i], self.count[i]
        mid = 0.5 * (lo + hi)

        # proportional redistribution
        width = hi - lo
        if width > 0:
            left_frac = (mid - lo) / width
        else:
            left_frac = 0.5

        c_left = c * left_frac
        c_right = c - c_left

        # replace bin i with left half
        self.lo[i] = lo
        self.hi[i] = mid
        self.count[i] = c_left

        # insert right half
        self.lo = np.insert(self.lo, i + 1, mid)
        self.hi = np.insert(self.hi, i + 1, hi)
        self.count = np.insert(self.count, i + 1, c_right)

    def _merge_closest_bins(self):
        """Merge the two adjacent bins with smallest width increase."""
        widths = self.hi - self.lo
        merge_costs = self.hi[1:] - self.lo[:-1]  # width of merged bin

        i = np.argmin(merge_costs)

        # merge bins i and i+1
        self.hi[i] = self.hi[i + 1]
        self.count[i] += self.count[i + 1]

        # delete bin i+1
        self.lo = np.delete(self.lo, i + 1)
        self.hi = np.delete(self.hi, i + 1)
        self.count = np.delete(self.count, i + 1)

    # ------------------------------------------------------------
    # Update
    # ------------------------------------------------------------

    def update(self, x):
        """Insert a new value x into the histogram."""
        if x < 0:
            raise ValueError("This implementation assumes non-negative data.")

        # Case 1: no bins yet
        if len(self.lo) == 0:
            self.lo = np.array([x], dtype=float)
            self.hi = np.array([x], dtype=float)
            self.count = np.array([1.0], dtype=float)
            return

        # Find bin or insertion point
        i = self._find_bin(x)

        # Case 2: x falls inside an existing bin
        if i < len(self.lo) and self.lo[i] <= x <= self.hi[i]:
            self.count[i] += 1.0

        # Case 3: x creates a new bin
        else:
            self.lo = np.insert(self.lo, i, x)
            self.hi = np.insert(self.hi, i, x)
            self.count = np.insert(self.count, i, 1.0)

        # If too many bins, merge
        while len(self.lo) > self.max_bins:
            self._merge_closest_bins()

        # Optional: split bins that are too wide
        widths = self.hi - self.lo
        avg_width = widths.mean()

        for j in range(len(self.lo)):
            if widths[j] > 2 * avg_width:
                self._split_bin(j)
                break  # split only one per update

    # ------------------------------------------------------------
    # Percentile
    # ------------------------------------------------------------

    def percentile(self, p):
        """
        Return the p-th percentile (0–100) using linear interpolation
        inside histogram bins.
        """
        if len(self.count) == 0:
            return None

        if not (0 <= p <= 100):
            raise ValueError("Percentile must be between 0 and 100.")

        total = self.count.sum()
        target = (p / 100.0) * total

        cum = 0.0
        for lo, hi, c in zip(self.lo, self.hi, self.count):
            if cum + c >= target:
                # interpolate inside this bin
                if c == 0 or hi == lo:
                    return lo
                frac = (target - cum) / c
                return lo + frac * (hi - lo)
            cum += c

        # fallback: return max value
        return self.hi[-1]

    def percentile_of(self, y) -> float:
        """
        Given a value y, return the percentile (0–100) of y
        based on the current histogram.
        Uses linear interpolation inside the bin.
        """
        if len(self.count) == 0:
            return 0

        total = self.count.sum()
        if total == 0:
            return 0

        # Find the bin containing y
        # If y is outside the histogram range, clamp to edges
        if y <= self.lo[0]:
            return 0.0
        if y >= self.hi[-1]:
            return 100.0

        # Find bin index
        idx = None
        for i in range(len(self.lo)):
            if self.lo[i] <= y <= self.hi[i]:
                idx = i
                break
            if y < self.lo[i]:
                idx = i
                break

        if idx is None:
            return 100.0

        # Mass strictly below this bin
        cum = self.count[:idx].sum()

        # Fraction inside the bin
        lo, hi, c = self.lo[idx], self.hi[idx], self.count[idx]
        if hi > lo and c > 0:
            frac = (y - lo) / (hi - lo)
            cum += frac * c
        else:
            # degenerate bin (zero width or zero count)
            cum += 0

        return 100.0 * cum / total

    # ------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------

    def plot(self, ax=None):
        """Plot the histogram as a bar chart."""
        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 4))

        widths = self.hi - self.lo
        ax.bar(self.lo, self.count, width=widths, align='edge', edgecolor='black')

        ax.set_xlabel("Value")
        ax.set_ylabel("Count")
        ax.set_title("Dynamic Compressed Histogram")

        return ax

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