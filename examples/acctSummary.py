import asyncio
import inspect
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

logger = logging.getLogger(__name__)
import os, sys
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    # sys.path.append(parent_dir)
    sys.path.insert(0, parent_dir)
    logger.info(f"{parent_dir} added to sys.path")

from ib_insync import IB, util, AccountValue
import time
from ib_insync.contract import *  # noqa
logger.info(inspect.getfile(IB))
logging.getLogger('ib_insync').setLevel(logging.WARNING) # shut up ib_insync logging

onAcctSummaryEventCount = 0

class myClass:
    def __init__(self, ib: IB):
        self.ib = ib
        self.ib.accountSummaryEvent += self.onAcctSummaryDebounce3Async

    account_summary_event_count = 0
    _logger = logging.getLogger("myClass")

    async def onAcctSummaryDebounce1Async(self, acctVal):
        # this event fires in succession for each tag. 
        # we debounce logging to only margin-related tags, once after the last one.
        # Debounce margin-related account summary logs so we emit one consolidated log
        # after the last tag update in a rapid succession.
        if not hasattr(self, "_acct_summary_buffer"):
            self._acct_summary_buffer = {}  # tag -> value, plus '_account' for account id
            self._acct_summary_debounce_task = None
            self._acct_summary_debounce_delay = 0.1  # seconds to wait for "last" event

        # capture original tag/value/account
        _tag = getattr(acctVal, "tag", "") or ""
        _tag_l = _tag.lower()
        _value = getattr(acctVal, "value", "")
        _account = getattr(acctVal, "account", None)

        # we only care about margin-related tags; ignore everything else
        if "margin" not in _tag_l:
            # no-op: still allow caller to increment event counter (happens after this block)
            return

        # store latest margin value
        self._acct_summary_buffer[_tag] = _value
        self._acct_summary_buffer["_account"] = _account

        # prevent the per-tag immediate log that follows this placeholder by clearing the tag
        # (we already captured it above)
        try:
            acctVal.tag = ""
        except Exception:
            # best-effort; if we cannot mutate acctVal, continue anyway (duplicate per-tag logging may occur)
            pass

        # cancel any pending flush and schedule a new one
        task = getattr(self, "_acct_summary_debounce_task", None)
        if task and not task.done():
            task.cancel()

        async def _flush_account_summary():
            try:
                await asyncio.sleep(self._acct_summary_debounce_delay)
                # build consolidated message
                account = self._acct_summary_buffer.pop("_account", None)
                items = ", ".join(f"{k}: {v}" for k, v in self._acct_summary_buffer.items())
                if items:
                    # use the current event count (incremented just after this placeholder)
                    self._logger.info(f"[EVENT] accountSummaryEvent (debounced) - {account}: {items}")
            except asyncio.CancelledError:
                return
            except Exception:
                self._logger.exception("Error flushing debounced account summary")
            finally:
                # clear buffer and reset task handle
                self._acct_summary_buffer.clear()
                self._acct_summary_debounce_task = None

        self._acct_summary_debounce_task = asyncio.create_task(_flush_account_summary())
        self.account_summary_event_count += 1
        # if 'margin' in acctVal.tag.lower():
        #     self._logger.info(
        #         f"[EVENT] accountSummaryEvent #{self.account_summary_event_count} - {acctVal.account}, "
        #         f"{acctVal.tag} {acctVal.value}")


    async def onAcctSummaryDebounce2Async(self, acctVal):
        # adaptive per-account debounce: learn inter-event intervals and adjust delay

        # initialize container and defaults
        if not hasattr(self, "_acct_summary_state"):
            # state: account -> {"buffer": {tag: value}, "seq": int, "task": Task|None,
            #                      "last_event_ts": float, "ema": float}
            self._acct_summary_state = {}
            # global defaults / bounds
            self._acct_summary_debounce_delay = 0.1  # initial default
            self._acct_summary_min_delay = 0.02     # don't go below 20ms
            self._acct_summary_max_delay = 1.0      # don't exceed 1s
            self._acct_summary_safety = 1.5         # multiply EMA by this factor
            self._acct_summary_ema_alpha = 0.25     # smoothing for EMA of inter-arrival
            self._acct_summary_reset_after = 60.0   # reset learning after long idle (seconds)

        _tag = getattr(acctVal, "tag", "") or ""
        _tag_l = _tag.lower()
        _value = getattr(acctVal, "value", "")
        _account = getattr(acctVal, "account", None)
        account_key = str(_account)

        # only consider margin-related tags
        if "margin" not in _tag_l:
            return

        # ensure per-account state
        state = self._acct_summary_state.setdefault(
            account_key, {"buffer": {}, "seq": 0, "task": None, "last_event_ts": None, "ema": None}
        )

        # update sequence and buffer
        state["seq"] += 1
        seq = state["seq"]
        state["buffer"][_tag] = _value

        # best-effort: prevent immediate per-tag logging by clearing tag on acctVal
        try:
            acctVal.tag = ""
        except Exception:
            pass

        # adaptive delay computation using EMA of inter-arrival times
        now = time.monotonic()
        last_ts = state.get("last_event_ts")
        ema = state.get("ema")
        reset_after = self._acct_summary_reset_after

        if last_ts is None or (now - last_ts) > reset_after:
            # no recent history -> initialize EMA to default
            ema = self._acct_summary_debounce_delay
        else:
            # compute inter-arrival and update EMA
            delta = max(1e-6, now - last_ts)
            if ema is None:
                ema = delta
            else:
                alpha = self._acct_summary_ema_alpha
                ema = alpha * delta + (1 - alpha) * ema

        state["last_event_ts"] = now
        state["ema"] = ema

        # derive debounce delay from EMA with safety multiplier and bounds
        delay = ema * self._acct_summary_safety
        delay = max(self._acct_summary_min_delay, min(self._acct_summary_max_delay, delay))

        # schedule a flush that checks the sequence token when it runs
        async def _flush(account_local, seq_local, delay_local):
            try:
                await asyncio.sleep(delay_local)
                # if a newer event for this account arrived, skip this flush
                cur_state = self._acct_summary_state.get(account_local)
                if not cur_state or cur_state.get("seq") != seq_local:
                    return
                buf = cur_state.get("buffer", {})
                items = ", ".join(f"{k}: {v}" for k, v in buf.items())
                if items:
                    self._logger.info(f"[EVENT] accountSummaryEvent (debounced) - {account_local}: {items}")
            except Exception:
                self._logger.exception("Error flushing debounced account summary")
            finally:
                # only clear buffer and clear task handle if the seq still matches
                st = self._acct_summary_state.get(account_local)
                if st and st.get("seq") == seq_local:
                    st["buffer"].clear()
                    st["task"] = None

        # create task (no need to cancel previous; token avoids race)
        state["task"] = asyncio.create_task(_flush(account_key, seq, delay))

        # increment per-instance event count
        self.account_summary_event_count += 1

    async def onAcctSummaryDebounce3Async(self, acctVal: AccountValue):
    
        _tag = acctVal.tag
        _value = acctVal.value
        _account = acctVal.account
        _account_key = str(_account)

        async def time_ns_isofmt(ts_ns):
            secs = ts_ns // 1_000_000_000
            ns = ts_ns % 1_000_000_000
            base = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(secs))
            ns_s = f"{ns:09d}"
            ns_grouped = f"{ns_s[0:3]},{ns_s[3:6]},{ns_s[6:9]}"
            return f"{base}.{ns_grouped}"
        async def _watcher():
            # keep waiting until _arrival_time stops growing
            t1 = time.monotonic_ns()
            _prev_arrival = len(self._arrival_time) if self._arrival_time else 0
            while True:
                await asyncio.sleep(self._acct_summary_debounce_delay) # wait debounce delay
                t2 = time.monotonic_ns()
                _new_arrival = len(self._arrival_time) if self._arrival_time else 0
                if _new_arrival == _prev_arrival:
                    # no new arrival during wait -> flush
                    break
                else:
                    # new arrival -> continue waiting
                    _prev_arrival = _new_arrival

            # collected events
            # for _account_key, state in self._acct_summary_state.items():
            #     if not state["buffer"]:
            #         continue
            #     logger.info(f"[EVENT] accountSummaryEvent (debounced) - {_account_key}: {state}")
            logger.info(f"[EVENT] accountSummaryEvent (debounced) - {await time_ns_isofmt(self._arrival_time[0])} to {await time_ns_isofmt(self._arrival_time[-1])}")
            
            # clear everything
            # delattr(self, "_acct_summary_state")
            # delattr(self, "_arrival_time")
            # delattr(self, "_account_summary_debounce_delay")
            self._acct_summary_state.clear()
            self._arrival_time.clear()
            self._watcher_task = None

        if not hasattr(self, "_acct_summary_state"):
            self._acct_summary_state = {}
            self._acct_summary_debounce_delay = 0.1  # seconds to wait for "last" event
            self._arrival_time = []
            self._watcher_task = None
            # start watcher task
            self._watcher_task = asyncio.create_task(_watcher())
        if self._watcher_task is None:
            # restart watcher task
            self._watcher_task = asyncio.create_task(_watcher())

        self._arrival_time.append(time.time_ns())
        
        # ensure per-account state
        state = self._acct_summary_state.setdefault(
            _account_key, {"buffer": {}, "seq": 0}
        )

        # update sequence and buffer
        state["seq"] += 1
        seq = state["seq"]
        # append tag/value to buffer
        state["buffer"][_tag] = _value

        return

def onAcctSummary(av):
    global onAcctSummaryEventCount
    onAcctSummaryEventCount += 1
    # print(av.tag, av.value)
    # filter for tag that has substring 'margin'
    if 'margin' in av.tag.lower():
        logger.info(f"[EVENT] onAcctSummary {av.account}, {av.tag}, {av.value}")

def closeEvent(self, ev):
    loop = util.getLoop()
    loop.stop()


if __name__ == '__main__':
    (host, port, clientId) = ('127.0.0.1', 7496, 9999)
    connectInfo = (host, port, clientId)
    ib = IB()
    # ib.accountSummaryEvent += onAcctSummary
    ib.connect(*connectInfo)

    myC = myClass(ib)

    logger.info("=== ib.accountSummary() ===")
    summary = ib.accountSummary() # will trigger accountSummaryEvent

    # # print account summary
    # logger.info( len(summary) )
    # for av in summary:
    #     logger.info(f"{av.account}, {av.tag}, {av.value}")
    
    
    # create a dummy asyncio awaitable that does nothing to keep the event loop running
    async def aw():
        while True:
            await asyncio.sleep(1)
    try:
        IB.run(aw(), timeout=60*60)
    except TimeoutError:
        logger.warning('timeout')
    finally:
        logger.info(f"Account Summary events received: {onAcctSummaryEventCount}")
        ib.disconnect()
