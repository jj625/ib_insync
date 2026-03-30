# tasks queueing up on accountSummaryEvent 
import asyncio
import inspect
import logging
import pprint
import random
from typing import ClassVar
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

logger = logging.getLogger(__name__)
import os, sys
# parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# if parent_dir not in sys.path:
#     # sys.path.append(parent_dir)
#     sys.path.insert(0, parent_dir)
#     logger.info(f"{parent_dir} added to sys.path")
import eventkit
logger.info(inspect.getfile(eventkit))
from ib_insync import IB, util, AccountValue
import time
from ib_insync.contract import *  # noqa
logger.info(inspect.getfile(IB))

# add file logging (debug to file, keep console at INFO from basicConfig)
_dirname, _basename = os.path.split(__file__)
log_file = os.path.join(_dirname, f'{os.path.splitext(_basename)[0]}.log')
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s:%(name)s:%(message)s'))
logging.getLogger().addHandler(file_handler)

# set ib_insync logging level to DEBUG to capture detailed logs in file
# keep ib_insync console logging at WARNING to reduce noise
logging.getLogger('ib_insync').setLevel(logging.DEBUG)
# Add a console handler at WARNING level for ib_insync to reduce noise
ib_insync_console_handler = logging.StreamHandler()
ib_insync_console_handler.setLevel(logging.WARNING)
logging.getLogger('ib_insync').addHandler(ib_insync_console_handler)


class myClass:
    def __init__(self, ib: IB):
        self.ib = ib
        self.ib.accountSummaryEvent += self.onAcctSummary
        self.account_summary_event_count = 0
        self.func = onAcctSummary

    logger: ClassVar[logging.Logger] = logging.getLogger("myClass")

    async def onAcctSummary(self, acctVal: AccountValue):
        self.account_summary_event_count += 1
        # list active coroutines
        delay = random.uniform(1,5)
        self.logger.info(f"Active coroutines [{self.account_summary_event_count}]: {len(asyncio.all_tasks())}, scheduling delay of {delay:.3f} seconds")       
        await asyncio.sleep(delay) # this should not block other events from being processed

        func = onAcctSummary
        if not hasattr(func, "_state"):
            setattr(func, "_state", {})
            func._state = {}
        _tag = acctVal.tag
        _value = acctVal.value
        _account = acctVal.account
        _account_key = str(_account)

        def time_ns_isofmt(ts_ns):
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
            self.logger.info(f"[EVENT] accountSummaryEvent (debounced) - ==== Begin Batch ====")
            self.logger.info(f"[EVENT] accountSummaryEvent (debounced) - {time_ns_isofmt(self._arrival_time[0])} to {time_ns_isofmt(self._arrival_time[-1])}")
            self.logger.info(f"[EVENT] accountSummaryEvent (debounced) - total events: {len(self._arrival_time)}")
            self.logger.info(f"[EVENT] accountSummaryEvent (debounced) - {len(self._acct_summary_state)} accounts affected")
            # count the number of leaf nodes (tags) across all accounts
            total_tags = sum(len(state["buffer"]) for state in self._acct_summary_state.values())
            self.logger.info(f"[EVENT] accountSummaryEvent (debounced) - total tags updated: {total_tags}")
            self.logger.info(f"[EVENT] accountSummaryEvent (debounced) - details per account:")
            for _account_key, state in self._acct_summary_state.items():
                if not state["buffer"]:
                    continue
                items = ", ".join(f"{k}: {v}" for k, v in state["buffer"].items())
                self.logger.info(f"    {_account_key}: {items}")
            self.logger.info(f"[EVENT] accountSummaryEvent (debounced) -\n{pprint.pformat(self._acct_summary_state)}")
            # calculate largest gap between arrivals
            if len(self._arrival_time) >= 2:
                gaps = [j - i for i, j in zip(self._arrival_time[:-1], self._arrival_time[1:])]
                max_gap_ns = max(gaps)
                max_gap_idx = gaps.index(max_gap_ns)
                self.logger.info(f"[EVENT] accountSummaryEvent (debounced) - largest gap between arrivals: {max_gap_ns/1_000_000:.3f} ms between "
                            f"{time_ns_isofmt(self._arrival_time[max_gap_idx])} and {time_ns_isofmt(self._arrival_time[max_gap_idx+1])}")
            # report gaps sorted descending
            if len(self._arrival_time) >= 2:
                gaps = [j - i for i, j in zip(self._arrival_time[:-1], self._arrival_time[1:])]
                gap_info = [(j - i, time_ns_isofmt(i), time_ns_isofmt(j)) for i, j in zip(self._arrival_time[:-1], self._arrival_time[1:])]
                gap_info_sorted = sorted(gap_info, key=lambda x: x[0], reverse=True)
                self.logger.info(f"[EVENT] accountSummaryEvent (debounced) - top 5 largest gaps between arrivals:")
                for gap_ns, t_start, t_end in gap_info_sorted[:5]:
                    self.logger.info(f"    {gap_ns/1_000_000:.3f} ms between {t_start} and {t_end}")
            self.logger.info(f"[EVENT] accountSummaryEvent (debounced) ==== End of Batch ====")
            # clear everything
            # delattr(self, "_acct_summary_state")
            # delattr(self, "_arrival_time")
            # delattr(self, "_account_summary_debounce_delay")
            self._acct_summary_state.clear()
            self._arrival_time.clear()
            self._watcher_task = None

            # log active coroutines after processing
            self.logger.info(f"Active coroutines [out]: {len(asyncio.all_tasks())}")
            return

        if not hasattr(self, "_acct_summary_state"):
            setattr(self, "_acct_summary_state", {})
            assert self._acct_summary_state == {}
            self._acct_summary_debounce_delay = 0.3  # seconds to wait for "last" event
            self._arrival_time = []
            self._watcher_task = None
        
        # Only create watcher task if none exists or previous one is done
        if self._watcher_task is None or self._watcher_task.done():
            self._watcher_task = asyncio.create_task(_watcher())
        else:
            # watcher task already running
            pass

        self._arrival_time.append(time.time_ns())
        # logger.info(f"[EVENT] accountSummaryEvent #{self.account_summary_event_count} - {_account}, {_tag} {_value}")
        
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

onAcctSummaryEventCount = 0
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
    (host, port, clientId) = ('127.0.0.1', 7497, random.randint(9000, 9998))
    connectInfo = (host, port, clientId)
    ib = IB()
    myC = myClass(ib)
    # ib.accountSummaryEvent += onAcctSummary
    ib.connect(*connectInfo)
    logger.info(f"Managed Accounts: {ib.managedAccounts()}")

    logger.info("=== ib.accountSummary() ===")
    summary = ib.accountSummary() # will trigger accountSummaryEvent

    # print account summary
    logger.info( len(summary) )
    # logger.info(pprint.pformat(summary))
    # for av in summary:
    #     logger.info(f"{av.account}, {av.tag}, {av.value}")
    
    # av = ib.accountValues()
    # logger.info("=== ib.accountValues() ===")
    # logger.info(pprint.pformat(av))
    
    # create a dummy asyncio awaitable that does nothing to keep the event loop running
    async def aw():
        while True:
            await asyncio.sleep(1)
    try:
        IB.run(aw(), timeout=60*2)
    except TimeoutError:
        logger.warning('timeout')
    finally:
        logger.info(f"Account Summary events received: {onAcctSummaryEventCount}")
        ib.disconnect()
