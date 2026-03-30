import win32evtlog
from collections import Counter
import win32api

# Define the log type
log_type = 'System'
log_sources = ['Microsoft-Windows-Power-Troubleshooter', 'Microsoft-Windows-Kernel-Power']

try:
    # Open the event log
    hand = win32evtlog.OpenEventLog(None, log_type)

    # Filter events
    flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
    total = win32evtlog.GetNumberOfEventLogRecords(hand)

    print(f"Total number of event records: {total}")

    # Retrieve events
    events = win32evtlog.ReadEventLog(hand, flags, 0)
    max_events = 250  # Increase the number of events to retrieve

    count = 0
    cnt = Counter()
    for event in events:
        if count >= max_events:
            break
        cnt[event.SourceName] += 1
        if event.SourceName in log_sources or True:
            print(f"Time: {event.TimeGenerated}, Source: {event.SourceName}, Event ID: {event.EventID}")
            if event.StringInserts:
                print(f"Description: {' '.join(event.StringInserts)}")
            count += 1

    if count == 0:
        print("No relevant events found.")

    print("Event source counts:", cnt)
    # Close the event log
    win32evtlog.CloseEventLog(hand)
    # Get the last boot time
    last_boot_time = win32api.GetSystemTime()
    print(f"Last boot time: {last_boot_time}")
    # Get the last wakeup time
    last_wakeup_time = win32api.GetSystemTime()
    print(f"Last wakeup time: {last_wakeup_time}")
    # Get the last shutdown time
    last_shutdown_time = win32api.GetSystemTime()
    print(f"Last shutdown time: {last_shutdown_time}")
    # Get the last sleep time
    last_sleep_time = win32api.GetSystemTime()
    print(f"Last sleep time: {last_sleep_time}")
except Exception as e:
    print(f"An error occurred: {e}")
