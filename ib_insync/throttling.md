jj625: explain this logic at at very high level, ignore minor stuff and logging stuff

GitHub Copilot: Looking at the `sendMsg` method in the `client.py` file, here's the high-level logic:

## Request Throttling System

This method implements a **rate limiting mechanism** to prevent overwhelming the Interactive Brokers API with too many requests at once.

### Key Components:

1. **Rate Limit Enforcement**: 
   - Allows maximum `MaxRequests` (45) per `RequestsInterval` (1 second)
   - Uses two queues: `_timeQ` (timestamps) and `_msgQ` (pending messages)

2. **Core Logic Flow**:
   - **Clean old timestamps**: Remove timestamps older than the interval window
   - **Queue new message**: Add incoming message to the pending queue
   - **Send what's allowed**: Send as many queued messages as the rate limit permits
   - **Schedule delayed sending**: If messages remain queued, schedule a callback to try sending them later

3. **Throttling States**:
   - **Normal state**: Messages sent immediately when under the rate limit
   - **Throttling state**: Messages queued and sent later when rate limit is hit
   - Emits `throttleStart`/`throttleEnd` events to notify when throttling begins/ends

### Purpose:
This prevents API disconnections due to exceeding Interactive Brokers' request rate limits, ensuring reliable communication by automatically pacing outgoing requests.

jj625: ok, now explain the code in detail. i still don't quite follow the implementation.

GitHub Copilot: Looking at the `sendMsg` method in detail, let me break down the implementation step by step:

## Data Structures
- `self._timeQ`: A deque storing timestamps of when messages were sent
- `self._msgQ`: A deque storing messages waiting to be sent
- `MaxRequests = 45`: Maximum requests allowed per interval
- `RequestsInterval = 1`: Time window in seconds (1 second)

## Step-by-Step Implementation

### 1. Initialize and Clean Old Timestamps
```python
loop = getLoop()
t = loop.time()  # Current time
times = self._timeQ
msgs = self._msgQ
while times and t - times[0] > self.RequestsInterval:
    times.popleft()  # Remove timestamps older than 1 second
```
This removes timestamps that are outside the current 1-second window, effectively "sliding" the time window.

### 2. Queue New Message
```python
if msg:
    msgs.append(msg)  # Add new message to pending queue
```
If there's a message to send, add it to the message queue.

### 3. Send Available Messages
```python
while msgs and (len(times) < self.MaxRequests or not self.MaxRequests):
    msg = msgs.popleft()  # Take next message from queue
    self.conn.sendMsg(self._prefix(msg.encode()))  # Actually send it
    times.append(t)  # Record the timestamp of this send
```
This loop continues while:
- There are messages to send (`msgs` is not empty)
- AND we haven't hit the rate limit (`len(times) < 45`) OR throttling is disabled (`not self.MaxRequests`)

For each message sent, it records the current timestamp in `times`.

### 4. Handle Throttling State
```python
if msgs:  # Still have unsent messages
    if not self._isThrottling:
        self._isThrottling = True
        self.throttleStart.emit()  # Notify listeners we're throttling
    
    # Schedule retry when the oldest timestamp expires
    loop.call_at(
        times[0] + self.RequestsInterval,  # When oldest timestamp + 1 second
        lambda: self.sendMsg(''))  # Call sendMsg again with empty string
```

If messages remain in the queue (rate limit hit), it:
- Sets throttling state if not already set
- Schedules a callback for when the oldest timestamp will be outside the 1-second window
- The callback calls `sendMsg('')` (empty string) to try sending queued messages again

### 5. Handle End of Throttling
```python
else:  # No more messages to send
    if self._isThrottling:
        self._isThrottling = False
        self.throttleEnd.emit()  # Notify listeners throttling ended
```

## The Key Insight: Self-Scheduling

The clever part is the recursive scheduling:
```python
lambda: self.sendMsg('')
```

When rate-limited, it schedules itself to run again when the oldest timestamp expires (after 1 second). The empty string `''` triggers the method to process any queued messages without adding a new message.

## Example Timeline

1. **t=0.0s**: Send 45 messages instantly (under limit)
2. **t=0.1s**: 46th message arrives → goes to queue, throttling starts
3. **t=1.0s**: Scheduled callback fires → oldest timestamp (t=0.0s) expires
4. **t=1.0s**: Process queued message → send it immediately
5. **t=1.0s**: No more queued messages → throttling ends

This creates a sliding window rate limiter that automatically processes queued messages as soon as the rate limit allows.