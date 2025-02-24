import logging
from collections import deque

def _repr_pkvl(lst: list):
    res = []
    for pkvl in lst:
        res.append(f"{pkvl[0]:.2f} {pkvl[1]:%H:%M:%S}")
    return '[' + ', '.join(res) + ']'

class PriceDetector:
    _logger = logging.getLogger(__name__) # class attribute
    def __init__(self):
        self.prev_price = None
        self.current_price = None
        self.minutes = deque([None], maxlen=2)
        self.peak = None
        self.valley = None
        self.peaks = []
        self.valleys = []

    def process_price(self, price, minute):
        self.prev_price = self.current_price
        self.current_price = price
        self.minutes.append(minute)

        if self.prev_price is not None:
            if self.current_price > self.prev_price:
                # self._handle_price_increase(minute)
                if self.peak is None or self.current_price > self.peak[0]:
                    self.peak = (self.current_price, minute)
                if self.valley is not None:
                    self.valleys.append(self.valley)
                    self.valley = None
            elif self.current_price < self.prev_price:
                # self._handle_price_decrease(minute)
                if self.valley is None or self.current_price < self.valley[0]:
                    self.valley = (self.current_price, minute)
                if self.peak is not None:
                    self.peaks.append(self.peak)
                    self.peak = None
            else:
                self._logger.warning(f"Price unchanged: {price} at {minute:%H:%M:%S}")
        
        return self.prev_price, self.current_price, self.peak, self.valley

    # def _handle_price_increase(self, minute):
    #     if self.peak is None or self.current_price > self.peak:
    #         self.peak = self.current_price
    #     if self.valley is not None:
    #         self.valleys.append((self.valley, minute))
    #         self.valley = None

    # def _handle_price_decrease(self, minute):
    #     if self.valley is None or self.current_price < self.valley:
    #         self.valley = self.current_price
    #     if self.peak is not None:
    #         self.peaks.append(self.peak)
    #         self.peak = None

    def get_peaks(self):
        return self.peaks

    def get_valleys(self):
        return self.valleys

class PD2(PriceDetector):
    def process_price(self, price, minute):
        prev_price, current_price, peak, valley = super().process_price(price, minute)

        if peak and not self.peaks:
            self.peaks.append(peak)
        elif peak and self.peaks and peak[0] >= self.peaks[-1][0]: # if higher peaks
            if len(self.minutes) > 1 and self.peaks[-1][1] == self.minutes[-2]:
                self.peaks.pop()
            self.peaks.append(peak)
        elif peak:
            self.peaks.append(peak)
        self.peak = None
        
        if valley and not self.valleys:
            self.valleys.append(valley)
        elif valley and self.valleys and valley[0] <= self.valleys[-1][0]: # if successively lower valleys
            if len(self.minutes) > 1 and self.valleys[-1][1] == self.minutes[-2]:
                self.valleys.pop()
            self.valleys.append(valley)
        elif valley:
            self.valleys.append(valley)
        self.valley = None
    
        return prev_price, current_price, peak, valley
