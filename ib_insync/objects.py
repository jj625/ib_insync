"""Object hierarchy."""

from dataclasses import dataclass, field
from datetime import date as date_, time as time_, datetime, timezone
from typing import List, NamedTuple, Optional, Union

from eventkit import Event

from .contract import Contract, ScanData, TagValue, TradingSession
from .util import EPOCH, UNSET_DOUBLE, UNSET_INTEGER, dataclassNonDefaults

nan = float('nan')

import datetime as dt
import numpy as np
_is_numpy_2_or_newer = tuple(map(int, np.__version__.split(".")[:2])) >= (2, 0)
NPNINF = -np.inf if _is_numpy_2_or_newer else np.NINF # type: ignore
import pandas as pd
import logging
import math
import decimal
from enum import IntEnum

logger = logging.getLogger(__name__)

def _decimal_places(v: float) -> int:
    """
    Return number of significant decimal places using arithmetic only.
    ```
    Examples:
    ```
    150.0      → 1  (you'd then max with 2 → 2)
    150.25     → 2
    150.1      → 1  (→ 2)
    150.123    → 3
    0.00000001 → 8
    """
    eps = 1e-9
    frac = v % 1
    if frac < eps or frac > 1 - eps:
        return 0
    for i in range(1, 11):
        v, frac = math.modf(v * 10)  # frac, int parts
        if frac < eps or frac > 1 - eps: # abs(v) < 1e-9
            return i
        # v *= 10
        # if abs(v % 1) < 1e-9:
        #     return i
    return 10
def _fmt_float(v: float, min_places: int) -> str:
    places = max(min_places, _decimal_places(v))
    return f"{v:.{places}f}" # if min_places > 0 else f"{v:.0f}"

@dataclass
class ScannerSubscription:
    numberOfRows: int = -1
    instrument: str = ''
    locationCode: str = ''
    scanCode: str = ''
    abovePrice: float = UNSET_DOUBLE
    belowPrice: float = UNSET_DOUBLE
    aboveVolume: int = UNSET_INTEGER
    marketCapAbove: float = UNSET_DOUBLE
    marketCapBelow: float = UNSET_DOUBLE
    moodyRatingAbove: str = ''
    moodyRatingBelow: str = ''
    spRatingAbove: str = ''
    spRatingBelow: str = ''
    maturityDateAbove: str = ''
    maturityDateBelow: str = ''
    couponRateAbove: float = UNSET_DOUBLE
    couponRateBelow: float = UNSET_DOUBLE
    excludeConvertible: bool = False
    averageOptionVolumeAbove: int = UNSET_INTEGER
    scannerSettingPairs: str = ''
    stockTypeFilter: str = ''


@dataclass
class SoftDollarTier:
    name: str = ''
    val: str = ''
    displayName: str = ''

    def __bool__(self):
        return bool(self.name or self.val or self.displayName)


@dataclass
class Execution:
    execId: str = ''
    time: datetime = field(default=EPOCH)
    acctNumber: str = ''
    exchange: str = ''
    side: str = ''
    shares: float = 0.0
    price: float = 0.0
    permId: int = 0
    clientId: int = 0
    orderId: int = 0
    liquidation: int = 0
    cumQty: float = 0.0
    avgPrice: float = 0.0
    orderRef: str = ''
    evRule: str = ''
    evMultiplier: float = 0.0
    modelCode: str = ''
    lastLiquidity: int = 0
    pendingPriceRevision: bool = False


@dataclass
class CommissionReport:
    execId: str = ''
    commission: float = 0.0
    currency: str = ''
    realizedPNL: float = 0.0
    yield_: float = 0.0
    yieldRedemptionDate: int = 0


@dataclass
class ExecutionFilter:
    clientId: int = 0
    acctCode: str = ''
    time: str = ''
    symbol: str = ''
    secType: str = ''
    exchange: str = ''
    side: str = ''


@dataclass
class BarData:
    _date_s : str = '' # string representation of the date, internal api use only
    date: date_|datetime|pd.Timestamp = EPOCH
    open_: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0
    average: float = 0.0
    barCount: int = 0
    timestamp: datetime|pd.Timestamp = EPOCH # datetime.now(timezone.utc)
    @property
    def open(self) -> float:
        return self.open_
    def date_to_npdatetime64(self) -> np.datetime64:
        if isinstance(self.date, datetime):
            return np.datetime64(self.date.astimezone(tz=None).replace(tzinfo=None)) # convert to naive datetime
        else:
            return np.datetime64(self.date)
    def _str_date(self) -> str: # convert date to string in the format that we want
        if isinstance(self.date, datetime):
            d = self.date.astimezone(tz=None).strftime(f"{r'%Y-%m-%d ' if self.date.date() != datetime.now().date() else ''}" '%H:%M:%S')
        else:
            d = str(self.date)
        return d
    def _repr_(self) -> str:
        if isinstance(self.date, datetime):
            d = self.date.astimezone(tz=None).strftime(f"{r'%Y-%m-%d ' if self.date.date() != datetime.now().date() else ''}" '%H:%M:%S')
            # if self.date.date() == datetime.datetime.now().date():
            #     d = self.date.astimezone().strftime('%H:%M:%S')
            # else:
            #     d = self.date.astimezone().strftime('%Y-%m-%d %H:%M:%S')
        else:
            d = self.date
        ts = f" ts={self.timestamp.astimezone(tz=None).strftime(f'%H:%M:%S,%f')[:-3]}" if self.timestamp != EPOCH else ''
        return f"[{d} o={self.open_:.2f} h={self.high:.2f} l={self.low:.2f} c={self.close:.2f} v={int(self.volume):_} a={self.average:.4f} bc={self.barCount:n}{ts}]"

    def __repr__(self):
        """
    This gives you something like:
    BarData(date=2024-01-15, O=150.25, H=152.1, L=149.8, C=151.45, vol=1200000, avg=150.98, bars=47)
        """
        return (
            f"BarData("
            f"date={self.date}, "
            f"O={_fmt_float(self.open_, 2)}, "
            f"H={_fmt_float(self.high, 2)}, "
            f"L={_fmt_float(self.low, 2)}, "
            f"C={_fmt_float(self.close, 2)}, "
            f"vol={_fmt_float(self.volume, 0)}, "
            f"avg={_fmt_float(self.average, 2)}, "
            f"bars={self.barCount}, "
            f"timestamp={self.timestamp}"
            f")"
        )

@dataclass
class RealTimeBar:
    time: datetime = EPOCH
    endTime: int = -1
    open_: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    wap: float = 0.0
    count: int = 0


@dataclass
class TickAttrib:
    canAutoExecute: bool = False
    pastLimit: bool = False
    preOpen: bool = False


@dataclass
class TickAttribBidAsk:
    bidPastLow: bool = False
    askPastHigh: bool = False


@dataclass
class TickAttribLast:
    pastLimit: bool = False
    unreported: bool = False


@dataclass
class HistogramData:
    price: float = 0.0
    count: int = 0


@dataclass
class NewsProvider:
    code: str = ''
    name: str = ''


@dataclass
class DepthMktDataDescription:
    exchange: str = ''
    secType: str = ''
    listingExch: str = ''
    serviceDataType: str = ''
    aggGroup: int = UNSET_INTEGER

    def __repr__(self):
        attrs = dataclassNonDefaults(self)
        clsName = self.__class__.__qualname__
        s = ', '.join(f'{k}={v!r}' for k, v in attrs.items())
        return f'{clsName}({s})'
    __str__ = __repr__

@dataclass
class PnL:
    account: str = ''
    modelCode: str = ''
    dailyPnL: float = nan
    unrealizedPnL: float = nan
    realizedPnL: float = nan


@dataclass
class TradeLogEntry:
    time: datetime
    status: str = ''
    message: str = ''
    errorCode: int = 0

    def __repr__(self):
        attrs = dataclassNonDefaults(self)
        clsName = self.__class__.__qualname__

        def _fmt(k, v):
            if isinstance(v, dt.datetime):
                return v.astimezone().isoformat()
            elif isinstance(v, dt.date):
                return v.isoformat()
            elif isinstance(v, dt.time):
                return v.isoformat()
            else:
                return repr(v)
        s = ', '.join(f'{k}={_fmt(k, v)}' for k, v in attrs.items())
        return f'{clsName}({s})'

@dataclass
class PnLSingle:
    account: str = ''
    modelCode: str = ''
    conId: int = 0
    dailyPnL: float = nan
    unrealizedPnL: float = nan
    realizedPnL: float = nan
    position: float = 0
    value: float = nan


@dataclass
class HistoricalSession:
    startDateTime: str = ''
    endDateTime: str = ''
    refDate: str = ''


@dataclass
class HistoricalSchedule:
    startDateTime: str = ''
    endDateTime: str = ''
    timeZone: str = ''
    sessions: List[HistoricalSession] = field(default_factory=list)


@dataclass
class WshEventData:
    conId: int = UNSET_INTEGER
    filter: str = ''
    fillWatchlist: bool = False
    fillPortfolio: bool = False
    fillCompetitors: bool = False
    startDate: str = ''
    endDate: str = ''
    totalLimit: int = UNSET_INTEGER


class AccountValue(NamedTuple):
    account: str
    tag: str
    value: str
    currency: str
    modelCode: str
    lastUpdateTime: datetime
    def __repr__(self):
        parts = [f"account={self.account!r}", f"tag={self.tag!r}", f"value={self.value!r}"]
        if self.currency:
            parts.append(f"currency={self.currency!r}")
        if self.modelCode:
            parts.append(f"modelCode={self.modelCode!r}")
        parts.append(f"lastUpdateTime='{self.lastUpdateTime.astimezone().isoformat()}'")
        return f"AccountValue({', '.join(parts)})"

class TickByTickTypeEnum(IntEnum):
    LAST = 1
    ALLLAST = 2
    BID_ASK = 3
    MIDPOINT = 4

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"

class TickTypeEnum(IntEnum):
    BID_SIZE = 0
    BID = 1
    ASK = 2
    ASK_SIZE = 3
    LAST = 4
    LAST_SIZE = 5
    HIGH = 6
    LOW = 7
    VOLUME = 8
    CLOSE = 9
    BID_OPTION_COMPUTATION = 10
    ASK_OPTION_COMPUTATION = 11
    LAST_OPTION_COMPUTATION = 12
    MODEL_OPTION = 13
    OPEN = 14
    LOW_13_WEEK = 15
    HIGH_13_WEEK = 16
    LOW_26_WEEK = 17
    HIGH_26_WEEK = 18
    LOW_52_WEEK = 19
    HIGH_52_WEEK = 20
    AVG_VOLUME = 21
    OPEN_INTEREST = 22
    OPTION_HISTORICAL_VOL = 23
    OPTION_IMPLIED_VOL = 24
    OPTION_BID_EXCH = 25
    OPTION_ASK_EXCH = 26
    OPTION_CALL_OPEN_INTEREST = 27
    OPTION_PUT_OPEN_INTEREST = 28
    OPTION_CALL_VOLUME = 29
    OPTION_PUT_VOLUME = 30
    INDEX_FUTURE_PREMIUM = 31
    BID_EXCH = 32
    ASK_EXCH = 33
    AUCTION_VOLUME = 34
    AUCTION_PRICE = 35
    AUCTION_IMBALANCE = 36
    MARK_PRICE = 37
    BID_EFP_COMPUTATION = 38
    ASK_EFP_COMPUTATION = 39
    LAST_EFP_COMPUTATION = 40
    OPEN_EFP_COMPUTATION = 41
    HIGH_EFP_COMPUTATION = 42
    LOW_EFP_COMPUTATION = 43
    CLOSE_EFP_COMPUTATION = 44
    LAST_TIMESTAMP = 45
    SHORTABLE = 46
    FUNDAMENTAL_RATIOS = 47
    RT_VOLUME = 48
    HALTED = 49
    BID_YIELD = 50
    ASK_YIELD = 51
    LAST_YIELD = 52
    CUST_OPTION_COMPUTATION = 53
    TRADE_COUNT = 54
    TRADE_RATE = 55
    VOLUME_RATE = 56
    LAST_RTH_TRADE = 57
    RT_HISTORICAL_VOL = 58
    IB_DIVIDENDS = 59
    BOND_FACTOR_MULTIPLIER = 60
    REGULATORY_IMBALANCE = 61
    NEWS_TICK = 62
    SHORT_TERM_VOLUME_3_MIN = 63
    SHORT_TERM_VOLUME_5_MIN = 64
    SHORT_TERM_VOLUME_10_MIN = 65
    DELAYED_BID = 66
    DELAYED_ASK = 67
    DELAYED_LAST = 68
    DELAYED_BID_SIZE = 69
    DELAYED_ASK_SIZE = 70
    DELAYED_LAST_SIZE = 71
    DELAYED_HIGH = 72
    DELAYED_LOW = 73
    DELAYED_VOLUME = 74
    DELAYED_CLOSE = 75
    DELAYED_OPEN = 76
    RT_TRD_VOLUME = 77
    CREDITMAN_MARK_PRICE = 78
    CREDITMAN_SLOW_MARK_PRICE = 79
    DELAYED_BID_OPTION = 80
    DELAYED_ASK_OPTION = 81
    DELAYED_LAST_OPTION = 82
    DELAYED_MODEL_OPTION = 83
    LAST_EXCH = 84
    LAST_REG_TIME = 85
    FUTURES_OPEN_INTEREST = 86
    AVG_OPT_VOLUME = 87
    DELAYED_LAST_TIMESTAMP = 88
    SHORTABLE_SHARES = 89
    DELAYED_HALTED = 90
    REUTERS_2_MUTUAL_FUNDS = 91
    ETF_NAV_CLOSE = 92
    ETF_NAV_PRIOR_CLOSE = 93
    ETF_NAV_BID = 94
    ETF_NAV_ASK = 95
    ETF_NAV_LAST = 96
    ETF_FROZEN_NAV_LAST = 97
    ETF_NAV_HIGH = 98
    ETF_NAV_LOW = 99
    SOCIAL_MARKET_ANALYTICS = 100
    ESTIMATED_IPO_MIDPOINT = 101
    FINAL_IPO_LAST = 102
    DELAYED_YIELD_BID = 103
    DELAYED_YIELD_ASK = 104
    NOT_SET = 105

    def __repr__(self):
        return self.name  # or f"TickTypeEnum.{self.name}"

class TickData(NamedTuple):
    time: datetime
    tickType: int
    price: float
    size: float

    def __repr__(self):
        name: TickTypeEnum = TickTypeEnum(self.tickType)
        tickType_str = f'tickType={name.name}'
        time_str = f'time={self.time.astimezone().isoformat()}'
        # if self.size is plain integer, format as integer
        size_str = f'size={int(self.size)}' if self.size.is_integer() else f'size={self.size}'
        match self.tickType, self.size, self.price:
            case TickTypeEnum.LAST | TickTypeEnum.BID | TickTypeEnum.ASK | TickTypeEnum.HIGH | TickTypeEnum.LOW | TickTypeEnum.OPEN | TickTypeEnum.CLOSE | TickTypeEnum.MARK_PRICE | TickTypeEnum.OPTION_IMPLIED_VOL | TickTypeEnum.AUCTION_PRICE | TickTypeEnum.HIGH_13_WEEK | TickTypeEnum.LOW_13_WEEK | TickTypeEnum.HIGH_26_WEEK | TickTypeEnum.LOW_26_WEEK | TickTypeEnum.HIGH_52_WEEK | TickTypeEnum.LOW_52_WEEK | TickTypeEnum.ETF_FROZEN_NAV_LAST | TickTypeEnum.ETF_NAV_ASK | TickTypeEnum.ETF_NAV_BID | TickTypeEnum.ETF_NAV_LAST | TickTypeEnum.ETF_NAV_CLOSE | TickTypeEnum.ETF_NAV_PRIOR_CLOSE, 0, _:
                return f"TickData({time_str}, {tickType_str}, price={self.price})"
            case TickTypeEnum.VOLUME | TickTypeEnum.OPTION_CALL_VOLUME | TickTypeEnum.OPTION_PUT_VOLUME | TickTypeEnum.FUTURES_OPEN_INTEREST | TickTypeEnum.OPTION_CALL_OPEN_INTEREST | TickTypeEnum.OPTION_PUT_OPEN_INTEREST | TickTypeEnum.REGULATORY_IMBALANCE | TickTypeEnum.AUCTION_VOLUME | TickTypeEnum.AVG_OPT_VOLUME | TickTypeEnum.AVG_VOLUME | TickTypeEnum.SHORTABLE_SHARES, _, -1.0:
                return f"TickData({time_str}, {tickType_str}, {size_str})"
            case TickTypeEnum.HALTED, 0, 0:
                return f"TickData({time_str}, {tickType_str})"
            case _, _, _:
                return f"TickData({time_str}, {tickType_str}, price={self.price}, {size_str})"

class HistoricalTick(NamedTuple):
    time: datetime
    price: float
    size: float


class HistoricalTickBidAsk(NamedTuple):
    time: datetime
    tickAttribBidAsk: TickAttribBidAsk
    priceBid: float
    priceAsk: float
    sizeBid: float
    sizeAsk: float


class HistoricalTickLast(NamedTuple):
    time: datetime
    tickAttribLast: TickAttribLast
    price: float
    size: float
    exchange: str
    specialConditions: str


class TickByTickAllLast(NamedTuple):
    tickType: int
    time: datetime
    price: float
    size: float
    tickAttribLast: TickAttribLast
    exchange: str
    specialConditions: str

    def __repr__(self):
        match self.tickType: 
            case 1:
                tt_str = "Last"
            case 2:
                tt_str = "AllLast"
            case _:
                tt_str = "Unknown"
                logger.warning(f"Unknown tickType: {self.tickType}")

        tickType_str = f'tickType={self.tickType}({tt_str})'
        time_str = f'time={self.time.astimezone():%H:%M:%S.%f}'
        size_str = f'size={int(self.size)}' if self.size.is_integer() else f'size={self.size}'
        exch_str_opt = f', exchange={self.exchange}' if self.exchange else ''
        specialConditions_str_opt = f', specialConditions={self.specialConditions}' if self.specialConditions else ''
        return f"TickByTickAllLast({time_str}, {tickType_str}, price={self.price}, {size_str}{exch_str_opt}{specialConditions_str_opt})"


class TickByTickBidAsk(NamedTuple):
    time: datetime
    bidPrice: float
    askPrice: float
    bidSize: float
    askSize: float
    tickAttribBidAsk: TickAttribBidAsk

    def __repr__(self):
        time_str = f'time={self.time.astimezone():%H:%M:%S.%f}'
        bidSize_str = f'bidSize={int(self.bidSize)}' if self.bidSize.is_integer() else f'bidSize={self.bidSize}'
        askSize_str = f'askSize={int(self.askSize)}' if self.askSize.is_integer() else f'askSize={self.askSize}'
        return f"TickByTickBidAsk({time_str}, bidPrice={self.bidPrice}, askPrice={self.askPrice}, {bidSize_str}, {askSize_str})"



class TickByTickMidPoint(NamedTuple):
    time: datetime
    midPoint: float

    def __repr__(self):
        time_str = f'time={self.time.astimezone():%H:%M:%S.%f}'
        return f"TickByTickMidPoint({time_str}, midPoint={self.midPoint})"


class MktDepthData(NamedTuple):
    time: datetime
    position: int
    marketMaker: str
    operation: int
    side: int
    price: float
    size: float


class DOMLevel(NamedTuple):
    price: float
    size: float
    marketMaker: str


class PriceIncrement(NamedTuple):
    lowEdge: float
    increment: float


class PortfolioItem(NamedTuple):
    contract: Contract
    position: float
    marketPrice: float
    marketValue: float
    averageCost: float
    unrealizedPNL: float
    realizedPNL: float
    account: str


class Position(NamedTuple):
    account: str
    contract: Contract
    position: float
    avgCost: float

# @dataclass
class PositionMulti(NamedTuple):
    # reqId: int
    account: str
    contract: Contract
    position: float
    avgCost: float
    modelCode: str
    lastUpdateTime: datetime

class Fill(NamedTuple):
    contract: Contract
    execution: Execution
    commissionReport: CommissionReport
    time: datetime


class OptionComputation(NamedTuple):
    tickAttrib: int
    impliedVol: Optional[float]
    delta: Optional[float]
    optPrice: Optional[float]
    pvDividend: Optional[float]
    gamma: Optional[float]
    vega: Optional[float]
    theta: Optional[float]
    undPrice: Optional[float]


class OptionChain(NamedTuple):
    exchange: str
    underlyingConId: int
    tradingClass: str
    multiplier: str
    expirations: List[str]
    strikes: List[float]


class Dividends(NamedTuple):
    past12Months: Optional[float]
    next12Months: Optional[float]
    nextDate: Optional[date_]
    nextAmount: Optional[float]


class NewsArticle(NamedTuple):
    articleType: int
    articleText: str


class HistoricalNews(NamedTuple):
    time: datetime
    providerCode: str
    articleId: str
    headline: str


class NewsTick(NamedTuple):
    timeStamp: int
    providerCode: str
    articleId: str
    headline: str
    extraData: str


class NewsBulletin(NamedTuple):
    msgId: int
    msgType: int
    message: str
    origExchange: str


class FamilyCode(NamedTuple):
    accountID: str
    familyCodeStr: str


class SmartComponent(NamedTuple):
    bitNumber: int
    exchange: str
    exchangeLetter: str


class ConnectionStats(NamedTuple):
    startTime: float
    duration: float
    numBytesRecv: int
    numBytesSent: int
    numMsgRecv: int
    numMsgSent: int


class BarDataList(List[BarData]):
    """
    List of :class:`.BarData` that also stores all request parameters.

    Events:

        * ``updateEvent``
          (bars: :class:`.BarDataList`, hasNewBar: bool)
        * ``historicalDataEndHook``

    """

    reqId: int
    contract: Contract
    endDateTime: Union[datetime, date_, str, None]
    durationStr: str
    barSizeSetting: str
    whatToShow: str
    useRTH: bool
    formatDate: int
    keepUpToDate: bool
    chartOptions: List[TagValue]

    def _repr_(self) -> str:
        # return f"{self.__class__.__name__}({super().__repr__()})"
        return '[' + ', '.join([f'{bar._repr_()}' for bar in self]) + ']'

    def _npbufsize(self, **kwargs) -> int:
        """
        Calculate the buffer size for numpy store from durationStr and barSizeSetting.
        """

        logmsg = [f"'{self.durationStr}' '{self.barSizeSetting}'"]
        if hasattr(self, '_tradingHours'):
            th: TradingSession = self._tradingHours
            rthfactor = (th.end - th.start).total_seconds() / 3600 # in hours
            logmsg.append(f"_tradingHours={th}")
        elif hasattr(self, 'useRTH'):
            logmsg.append(f"useRTH={self.useRTH}")
            rthfactor_pad = kwargs.get('rthfactor_pad', 0)
            if len(self) > 0:
                start_date_str = self[0].date.astimezone(tz=None) if isinstance(self[0].date, (datetime, pd.Timestamp)) else self[0].date
                end_date_str = self[-1].date.astimezone(tz=None) if isinstance(self[-1].date, (datetime, pd.Timestamp)) else self[-1].date
                logmsg.append(f"len(self)={len(self)} self.date={start_date_str}..{end_date_str}")
                if isinstance(self[0].date, (datetime, pd.Timestamp)) and self[0].date.astimezone(tz=None).time() == time_(18, 0): # MBT, ES 6pm - 5pm
                    # logmsg.append(f"assuming 23 hours trading time")
                    rthfactor_pad = 7.0
            # logmsg.append(f"rthfactor_pad={rthfactor_pad}")
            if self.useRTH:
                rthfactor = 6.5 + rthfactor_pad # 6.5 hours per US trading day, 9:30am to 4pm
            else:
                rthfactor = 16 + rthfactor_pad # assume 12 hours per trading day, 4am to 8pm
        else:
            rthfactor = 0
        logmsg.append(f"rthfactor={rthfactor}")

        dur_sec = dur_day = dur_week = dur_month = dur_year = 0
        if hasattr(self, 'durationStr'):
            if self.durationStr.endswith(' S'):
                dur_sec = int(self.durationStr[:-2]) # number of seconds
                # round to nearest days
                dur_day = math.ceil(dur_sec / 3600 / 24)
            elif self.durationStr.endswith(' D'):
                dur_day = int(self.durationStr[:-2]) * 1 # 1 trading day
            elif self.durationStr.endswith(' W'):
                dur_week = int(self.durationStr[:-2]) * 5 # equals 5 trading days
            elif self.durationStr.endswith(' M'):
                dur_month = int(self.durationStr[:-2]) * 21 # equals 21 trading days
            elif self.durationStr.endswith(' Y'):
                dur_year = int(self.durationStr[:-2]) * 252 # equals 252 trading days

        num_bars = 100 # 4680 # default buffer size

        if hasattr(self, 'barSizeSetting'):
            if self.barSizeSetting.endswith(' min'):
                barsz_min = int(self.barSizeSetting[:-4])
                num_bars = math.ceil(dur_day * rthfactor * 60 / barsz_min)
            elif self.barSizeSetting.endswith(' mins'):
                barsz_min = int(self.barSizeSetting[:-5])
                num_bars = math.ceil(dur_day * rthfactor * 60 / barsz_min)
            elif self.barSizeSetting.endswith(' secs'):
                barsz_sec = int(self.barSizeSetting[:-5])
                num_bars = math.ceil(dur_day * rthfactor * 60 * 60 / barsz_sec)
            elif self.barSizeSetting.endswith(' hour'):
                barsz_hr = int(self.barSizeSetting[:-5])
                num_bars = math.ceil(dur_day * rthfactor * barsz_hr)
            elif self.barSizeSetting.endswith(' hours'):
                barsz_hr = int(self.barSizeSetting[:-6])
                num_bars = math.ceil(dur_day * rthfactor * barsz_hr)
            elif self.barSizeSetting.endswith(' day'):
                barsz_day = int(self.barSizeSetting[:-4])
                num_bars = math.ceil(dur_day * rthfactor * barsz_day)

        # eg: 1 day dur, 5 sec barSize/interval, 6.5 hours trading time, RTH -> 6.5 * 60 * 12 = 4680
        # eg: 1 day dur, 1 min barSize/interval, 6.5 hours trading time, RTH -> 6.5 * 60 = 390
        logmsg.append(f"num_bars={num_bars}")
        self._logger.info(f"_npbufsize: " + ', '.join(logmsg))
        return num_bars

    def __init__(self, *args, durationStr: str='', barSizeSetting: str='', useRTH: Optional[bool]=None,
            from_df: Optional[pd.DataFrame] = None):
        super().__init__(*args)
        self.updateEvent = Event('updateEvent')
        self._logger = logging.getLogger('ib_insync.objects')

        # must be set from reqHistoricalDataExt
        self._historicalDataEndHook = Event('BarDataList::historicalDataEndHook')
        # self._historicalDataUpdateHook = Event('BarDataList::historicalDataUpdateHook')
        # self.historicalDataHook = Event('BarDataList::historicalDataHook')
        self._npidx = -1
        self._npidx_rth_start = -1
        self._npidx_rth_end = -1
        self.buffer_size = 0

        if durationStr:
            self.durationStr = durationStr
        if barSizeSetting:
            self.barSizeSetting = barSizeSetting
        if useRTH is not None:
            self.useRTH = useRTH
        if from_df is not None:
            required_columns = ['date', 'open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in from_df.columns]
            if missing_columns:
                raise ValueError(f"from_df is missing columns: {', '.join(missing_columns)}")
            for _, row in from_df.iterrows():
                self.append(BarData(
                    date=row.date,
                    open_=row.open,
                    high=row.high,
                    low=row.low,
                    close=row.close,
                    volume=row.get('volume', 0),
                    average=row.get('average', 0.0),
                    barCount=row.get('barCount', 0),
                    # timestamp=row.timestamp
                ))
        setattr(BarDataList._init_npdata, 'doOnce', True)
        if len(self) > 0:
            self._init_npdata('', '')

    def __eq__(self, other):
        return self is other

    def __hash__(self): # type: ignore[override]
        return id(self)

    @property
    def np_data(self):
        return {
            'date': self.npdate_[:self._npidx],
            'open_prices': self.open_prices[:self._npidx],
            'high_prices': self.high_prices[:self._npidx],
            'low_prices': self.low_prices[:self._npidx],
            'close_prices': self.close_prices[:self._npidx],
            'average': self._average[:self._npidx]
        }

    def get_npdate(self, onlyRTH=True):
        if onlyRTH and not self.useRTH:
            return self.npdate_[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
        else:
            return self.npdate_[:self._npidx]

    @property
    def npdate(self):
        return self.npdate_[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]

    def get_npopen(self, onlyRTH=True):
        if onlyRTH and not self.useRTH:
            return self.open_prices[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
        else:
            return self.open_prices[:self._npidx]

    @property
    def npopen(self):
        return self.open_prices[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]

    def get_nphigh(self, onlyRTH=True):
        if onlyRTH and not self.useRTH:
            return self.high_prices[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
        else:
            return self.high_prices[:self._npidx]

    @property
    def nphigh(self):
        return self.high_prices[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]

    def get_nplow(self, onlyRTH=True):
        if onlyRTH and not self.useRTH:
            return self.low_prices[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
        else:
            return self.low_prices[:self._npidx]

    @property
    def nplow(self):
        return self.low_prices[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]

    def get_npclose(self, onlyRTH=True):
        if onlyRTH and not self.useRTH:
            return self.close_prices[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
        else:
            return self.close_prices[:self._npidx]

    @property
    def npclose(self):
        return self.close_prices[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]

    def get_npaverage(self, onlyRTH=True):
        if onlyRTH and not self.useRTH:
            return self._average[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
        else:
            return self._average[:self._npidx]

    @property
    def npaverage(self):
        return self._average[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]

    def get_npvolume(self, onlyRTH=True):
        if onlyRTH and not self.useRTH:
            return self._volume[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
        else:
            return self._volume[:self._npidx]

    @property
    def npvolume(self):
        return self._volume[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]

    def get_npbarCount(self, onlyRTH=True):
        if onlyRTH and not self.useRTH:
            return self._barCount[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
        else:
            return self._barCount[:self._npidx]

    @property
    def npbarCount(self):
        return self._barCount[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]

    def get_log_open(self, onlyRTH=True):
        if onlyRTH and not self.useRTH:
            return self.log_open_prices[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
        else:
            return self.log_open_prices[:self._npidx]

    @property
    def log_open(self):
        return self.log_open_prices[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
    
    def get_log_high(self, onlyRTH=True):
        if onlyRTH and not self.useRTH:
            return self.log_high_prices[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
        else:
            return self.log_high_prices[:self._npidx]

    @property
    def log_high(self):
        return self.log_high_prices[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
    
    def get_log_low(self, onlyRTH=True):
        if onlyRTH and not self.useRTH:
            return self.log_low_prices[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
        else:
            return self.log_low_prices[:self._npidx]

    @property
    def log_low(self):
        return self.log_low_prices[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
    
    def get_log_close(self, onlyRTH=True):
        if onlyRTH and not self.useRTH:
            return self.log_close_prices[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
        else:
            return self.log_close_prices[:self._npidx]

    @property
    def log_close(self):
        return self.log_close_prices[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
    
    def get_log_volume(self, onlyRTH=True):
        if onlyRTH and not self.useRTH:
            return self.log_volume_[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
        else:
            return self.log_volume_[:self._npidx]

    @property
    def log_volume(self):
        return self.log_volume_[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
    
    def get_log_average(self, onlyRTH=True):
        if onlyRTH and not self.useRTH:
            return self.log_average_[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
        else:
            return self.log_average_[:self._npidx]

    @property
    def log_average(self):
        return self.log_average_[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
    
    def get_log_high_low(self, onlyRTH=True):
        if onlyRTH and not self.useRTH:
            return self.log_high_low_[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
        else:
            return self.log_high_low_[:self._npidx]

    @property
    def log_high_low(self):
        return self.log_high_low_[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
    
    def get_log_close_open(self, onlyRTH=True):
        if onlyRTH and not self.useRTH:
            return self.log_close_open_[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
        else:
            return self.log_close_open_[:self._npidx]

    @property
    def log_close_open(self):
        return self.log_close_open_[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
    
    def get_log_high_open(self, onlyRTH=True):
        if onlyRTH and not self.useRTH:
            return self.log_high_open_[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
        else:
            return self.log_high_open_[:self._npidx]

    @property
    def log_high_open(self):
        return self.log_high_open_[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
    
    def get_log_high_close(self, onlyRTH=True):
        if onlyRTH and not self.useRTH:
            return self.log_high_close_[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
        else:
            return self.log_high_close_[:self._npidx]

    @property
    def log_high_close(self):
        return self.log_high_close_[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
    
    def get_log_low_open(self, onlyRTH=True):
        if onlyRTH and not self.useRTH:
            return self.log_low_open_[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
        else:
            return self.log_low_open_[:self._npidx]

    @property
    def log_low_open(self):
        return self.log_low_open_[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
    
    def get_log_low_close(self, onlyRTH=True):
        if onlyRTH and not self.useRTH:
            return self.log_low_close_[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
        else:
            return self.log_low_close_[:self._npidx]

    @property
    def log_low_close(self):
        return self.log_low_close_[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
    
    def get_log_close_close(self, onlyRTH=True):
        if onlyRTH and not self.useRTH:
            return self.log_close_close_[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]
        else:
            return self.log_close_close_[:self._npidx]

    @property
    def log_avg_avg(self):
        return self.log_avg_avg_[self._npidx_rth_start:min(self._npidx_rth_end, self._npidx)]

    def _init_npdata(self, _start: str, _end: str, **kwargs):
        """
        Called from wrapper.historicalDataEnd before historicalDataEndHook event
        Also called from resampler initialization to hold resampled BarDataList
        """
        # _npbufsize() acceptable kwargs: rthfactor_pad
        # if rtfactor_pad is provided, pass it to _npbufsize(), if not, pass nothing to _npbufsize()
        # global NPMKTOPEN, NPMKTCLOSE, MKTOPEN, MKTCLOSE
        # if BarDataList._init_npdata.doOnce:
        #     BarDataList._init_npdata.doOnce = not BarDataList._init_npdata.doOnce
        #     for k, v in globals().items():
        #         if k in ['NPMKTOPEN', 'NPMKTCLOSE', 'MKTOPEN', 'MKTCLOSE']:
        #             self._logger.info(f"{k}={v}")
        # self._logger.info(f"{globals()}")
        # self._logger.info(f"{MKTOPEN} {MKTCLOSE} {NPMKTOPEN} {NPMKTCLOSE}")
        if '_tradingHours' in kwargs:
            self._tradingHours: TradingSession = kwargs['_tradingHours']
            kwargs.pop('_tradingHours')
        if '_rth' in kwargs:
            self._rth: TradingSession = kwargs['_rth']
            kwargs.pop('_rth')
        else:
            self._rth = TradingSession(
                start=datetime.combine(datetime.today(), time_(9, 30)).astimezone(),
                end=datetime.combine(datetime.today(), time_(16, 0)).astimezone()
            )
        self.buffer_size = self._npbufsize(**kwargs)
        # self.buffer_size = self._npbufsize() # 4680 # 1 day data, 5 sec interval, 6.5 hours trading time, RTH
        if len(self) == 0:
            self._logger.warning(f"len(self)==0, buffer_size={self.buffer_size}")
            # return
        # self.buffer_size = self._npbufsize() # 4680 # 1 day data, 5 sec interval, 6.5 hours trading time, RTH
        self.npdate_ = np.empty(self.buffer_size, dtype='datetime64[s]')
        self.open_prices = np.zeros(self.buffer_size)
        self.high_prices = np.zeros(self.buffer_size)
        self.low_prices = np.zeros(self.buffer_size)
        self.close_prices = np.zeros(self.buffer_size)
        self._volume = np.zeros(self.buffer_size, dtype=int)
        self._average = np.zeros(self.buffer_size)
        self._barCount = np.zeros(self.buffer_size, dtype=int)

        self.log_open_prices = np.zeros(self.buffer_size)
        self.log_high_prices = np.zeros(self.buffer_size)
        self.log_low_prices = np.zeros(self.buffer_size)
        self.log_close_prices = np.zeros(self.buffer_size)
        self.log_volume_ = np.zeros(self.buffer_size)
        self.log_average_ = np.zeros(self.buffer_size)

        self.log_high_low_ = np.zeros(self.buffer_size)
        self.log_close_open_ = np.zeros(self.buffer_size)
        self.log_high_open_ = np.zeros(self.buffer_size)
        self.log_high_close_ = np.zeros(self.buffer_size)
        self.log_low_open_ = np.zeros(self.buffer_size)
        self.log_low_close_ = np.zeros(self.buffer_size)
        self.log_close_close_ = np.zeros(self.buffer_size)
        self.log_avg_avg_ = np.zeros(self.buffer_size)

        self._npidx = 0

        if self.useRTH:
            # buffer is guaranteed to be filled with RTH data
            self._npidx_rth_start = 0
            self._npidx_rth_end = self.buffer_size
        else:
            # buffer contains more than just RTH data
            self._npidx_rth_start = -1 # we don't know yet
            self._npidx_rth_end = self._npidx

        for bar in self:
            self._add_npdata(bar)

        #     # global NPMKTOPEN, NPMKTCLOSE, MKTOPEN, MKTCLOSE
        #     # self._logger.debug(f"self.npdate_: {min(self.npdate_)} {max(self.npdate_)}")
        #     # dt = pd.to_datetime(self.npdate_[-1])
        #     # if NPMKTOPEN > self.npdate_[-1]:
        #     #     MKTOPEN = datetime.combine(dt, time_(9, 30)).astimezone()
        #     #     MKTCLOSE = datetime.combine(dt, time_(4, 0)).astimezone()
        #     #     NPMKTOPEN = np.datetime64(MKTOPEN, 's')
        #     #     NPMKTCLOSE = np.datetime64(MKTCLOSE, 's')
        #     i = np.ravel(np.where(self.npdate_ == NYNPMKTOPEN))
        #     self._logger.debug(f"_init_npdata: mktopen {NYNPMKTOPEN} @ {i}")
        #     if len(i) > 0:
        #         self._npidx_rth_start = i[0]
        #     else:
        #         self._npidx_rth_start = -1
       
        # i = np.ravel(np.where(self.npdate_ == NYNPMKTCLOSE))
        # self._logger.debug(f"_init_npdata: mktclose {NYNPMKTCLOSE} @ {i}")
        # if len(i) > 0:
        #     self._npidx_rth_end = i[0]
        # else:
        #     self._npidx_rth_end = self.buffer_size


    def _set_npdata(self, idx: int, bar: BarData):
        """
        Set numpy data at [idx] from BarData.
        """
        if isinstance(bar.date, datetime):
            self.npdate_[idx] = bar.date.astimezone(tz=None).replace(tzinfo=None) # convert to naive datetime
        else:
            self.npdate_[idx] = np.datetime64(bar.date)
        self.open_prices[idx] = bar.open_
        self.high_prices[idx] = bar.high
        self.low_prices[idx] = bar.low
        self.close_prices[idx] = bar.close
        self._volume[idx] = bar.volume
        self._average[idx] = bar.average
        self._barCount[idx] = bar.barCount

        self.log_open_prices[idx] = np.log(bar.open_) if bar.open_ > 0 else NPNINF
        self.log_high_prices[idx] = np.log(bar.high) if bar.high > 0 else NPNINF
        self.log_low_prices[idx] = np.log(bar.low) if bar.low > 0 else NPNINF
        self.log_close_prices[idx] = np.log(bar.close) if bar.close > 0 else NPNINF
        self.log_volume_[idx] = np.log(bar.volume) if bar.volume > 0 else NPNINF
        self.log_average_[idx] = np.log(bar.average) if bar.average > 0 else NPNINF

        self.log_high_low_[idx] = np.log(bar.high / bar.low)
        self.log_close_open_[idx] = np.log(bar.close / bar.open_)
        self.log_high_open_[idx] = np.log(bar.high / bar.open_)
        self.log_high_close_[idx] = np.log(bar.high / bar.close)
        self.log_low_open_[idx] = np.log(bar.low / bar.open_)
        self.log_low_close_[idx] = np.log(bar.low / bar.close)
        if idx > 0:
            self.log_close_close_[idx] = np.log(bar.close / self.close_prices[idx-1])
            self.log_avg_avg_[idx] = np.log(bar.average / self._average[idx-1])
        else:
            self.log_close_close_[idx] = 0. # np.log(bar.close / bar.open_)
            self.log_avg_avg_[idx] = 0. # np.log(bar.average / bar.open_)
        # self.log_prevopen_close[idx] = np.log(bar.open_ / bar.close)

    def _add_npdata(self, newbar: BarData):
        """
        to ensure data consistency between the underlying list and numpy arrays
        wrapper.historicalDataUpdate calls _add_npdata and _set_last_npdata()
        when adding data to list
        """
        if self._npidx >= self.buffer_size:
            start_date_str = self[0].date.astimezone(tz=None) if isinstance(self[0].date, (datetime, pd.Timestamp)) else self[0].date
            end_date_str = self[-1].date.astimezone(tz=None) if isinstance(self[-1].date, (datetime, pd.Timestamp)) else self[-1].date
            self._logger.error(f"buffer overflow: {self._npidx} >= {self.buffer_size}"
                + f", self.date {start_date_str}..{end_date_str}"
                + f", self.npdate_ {self.npdate_[0]}..{self.npdate_[self.buffer_size-1]}"
                + f", self.npdate_(rth) {self.npdate_[self._npidx_rth_start]}..{self.npdate_[self._npidx_rth_end-1]}" if self._npidx_rth_start >= 0 else ''
            )
            self._npidx = 0
        # idx = self._npidx # % self.buffer_size
        self._set_npdata(self._npidx, newbar)
        self._npidx += 1

        # when we add a new bar, we need to update the rth_start and rth_end index
        if self.useRTH:
            return # no need to update rth_start and rth_end
        else:
            # global MKTOPEN, MKTCLOSE
            # if newbar.date == MKTOPEN:
            if newbar.date == self._rth.start:
                # this should only trigger once
                self._npidx_rth_start = self._npidx - 1
            # if newbar.date < MKTCLOSE:
            if newbar.date < self._rth.end:
                # this should be triggered whenever _npidx is updated, until MKTCLOSE
                self._npidx_rth_end = self._npidx # no minus one since it's the tail index (python slice)
    
    def _set_last_npdata(self, bar: BarData):
        """
        to ensure data consistency between the underlying list and numpy arrays
        wrapper.historicalDataUpdate calls _add_npdata and _set_last_npdata()
        when adding data to list
        """
        idx = (self._npidx - 1) # % self.buffer_size
        bd_tmp = bar.date_to_npdatetime64() # np.datetime64(bar.date.astimezone(tz=None).replace(tzinfo=None), 's') # convert to naive datetime
        if self.npdate_[idx] != bd_tmp:
            if not hasattr(self, '_warning_count'):
                self._warning_count = 0
            if self._warning_count < 3:
                self._logger.warning(f"date mismatch: {self.npdate_[idx]} != {bd_tmp}")
                self._warning_count += 1
        # assert self.date[idx] == bar.date #.replace(tzinfo=None)
        self._set_npdata(idx, bar)

class RealTimeBarList(List[RealTimeBar]):
    """
    List of :class:`.RealTimeBar` that also stores all request parameters.

    Events:

        * ``updateEvent``
          (bars: :class:`.RealTimeBarList`, hasNewBar: bool)
    """

    reqId: int
    contract: Contract
    barSize: int
    whatToShow: str
    useRTH: bool
    realTimeBarsOptions: List[TagValue]

    def __init__(self, *args):
        super().__init__(*args)
        self.updateEvent = Event('updateEvent')

    def __eq__(self, other):
        return self is other

    def __hash__(self): # type: ignore[override]
        return id(self)


class ScanDataList(List[ScanData]):
    """
    List of :class:`.ScanData` that also stores all request parameters.

    Events:
        * ``updateEvent`` (:class:`.ScanDataList`)
    """

    reqId: int
    subscription: ScannerSubscription
    scannerSubscriptionOptions: List[TagValue]
    scannerSubscriptionFilterOptions: List[TagValue]

    def __init__(self, *args):
        super().__init__(*args)
        self.updateEvent = Event('updateEvent')

    def __eq__(self, other):
        return self is other

    def __hash__(self): # type: ignore[override]
        return id(self)


class DynamicObject:

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        clsName = self.__class__.__name__
        kwargs = ', '.join(f'{k}={v!r}' for k, v in self.__dict__.items())
        return f'{clsName}({kwargs})'


class FundamentalRatios(DynamicObject):
    """
    See:
    https://web.archive.org/web/20200725010343/https://interactivebrokers.github.io/tws-api/fundamental_ratios_tags.html
    """

    pass
