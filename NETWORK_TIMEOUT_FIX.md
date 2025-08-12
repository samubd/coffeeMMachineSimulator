# Network Timeout Fix for Astarte API Client

## Problem Description

The coffee machine simulator was experiencing a critical network issue where:

1. **Initial Timeout**: When trying to fetch recipes from `services.sanremomachines.com`, a connection timeout would occur
2. **System-Wide Impact**: After the timeout, ALL subsequent calls to that server would fail with timeout errors
3. **Persistent Issue**: The problem persisted even when using browser or curl from the same machine
4. **Recovery Method**: Only a full PC reboot would restore connectivity to the server

## Root Cause Analysis

The issue was caused by improper HTTP connection management in the `astarte_api_client.py` file:

### Original Problems:
1. **No Connection Timeouts**: Requests had no explicit timeout settings, allowing them to hang indefinitely
2. **Poor Connection Pooling**: The `requests` library's default connection pooling could get into a bad state
3. **No Session Management**: Each request created new connections without proper cleanup
4. **No Error Recovery**: When timeouts occurred, connections weren't properly closed
5. **System Resource Exhaustion**: Lingering TCP connections could exhaust system resources

## Solution Implemented

### 1. Proper Session Management
```python
# Create a configured session with proper settings
self.session = self._create_configured_session()
```

### 2. Connection Pool Configuration
```python
adapter = HTTPAdapter(
    max_retries=retry_strategy,
    pool_connections=10,  # Number of connection pools to cache
    pool_maxsize=10,      # Maximum connections per pool
    pool_block=False      # Don't block when pool is full
)
```

### 3. Explicit Timeouts
```python
response = self.session.get(
    url, 
    headers=headers,
    timeout=(10, 30)  # 10s connect, 30s read timeout
)
```

### 4. Retry Strategy
```python
retry_strategy = Retry(
    total=3,  # Total number of retries
    status_forcelist=[429, 500, 502, 503, 504],
    backoff_factor=1,
    raise_on_status=False
)
```

### 5. Connection Cleanup on Errors
```python
except requests.exceptions.Timeout as e:
    print(f"Timeout error for recipes {group}: {e}")
    # Force close any lingering connections
    self.session.close()
    self.session = self._create_configured_session()
    return None
```

### 6. Force Connection Close Headers
```python
headers = {
    'Authorization': f'Bearer {self.access_token}',
    'Connection': 'close'  # Force connection close
}
```

## Key Improvements

1. **Timeout Protection**: All requests now have explicit connect and read timeouts
2. **Connection Cleanup**: Proper session cleanup prevents resource leaks
3. **Error Recovery**: When timeouts occur, the session is recreated to ensure clean state
4. **Connection Pooling**: Controlled connection pooling prevents resource exhaustion
5. **Retry Logic**: Intelligent retry strategy for transient failures

## Testing

Use the provided `test_network_fix.py` script to verify the fix:

```bash
python test_network_fix.py
```

The test will:
- Attempt to fetch recipes for all groups
- Measure response times
- Handle timeouts gracefully
- Clean up connections properly
- Verify that the system remains responsive

## Prevention of System-Wide Issues

The fix prevents system-wide network issues by:

1. **Limiting Connection Lifetime**: Connections are properly closed after use
2. **Resource Management**: Connection pools have size limits
3. **Timeout Enforcement**: Requests cannot hang indefinitely
4. **Clean Error Handling**: Failed connections are properly cleaned up
5. **Session Recreation**: Fresh sessions are created after errors

## Files Modified

- `astarte_api_client.py`: Main fix implementation
- `test_network_fix.py`: Test script to verify the fix
- `NETWORK_TIMEOUT_FIX.md`: This documentation

## Usage Notes

- The API client now automatically handles connection management
- Timeouts are set to reasonable values (10s connect, 30s read)
- Failed connections are automatically cleaned up
- No changes needed to existing code using the API client

## Monitoring

To monitor the effectiveness of the fix:

1. Watch for timeout messages in logs
2. Verify that timeouts don't cause system-wide connectivity issues
3. Check that the test script completes successfully
4. Confirm browser/curl access to services.sanremomachines.com remains functional after timeouts

## Future Considerations

- Consider implementing exponential backoff for retries
- Add metrics collection for connection health monitoring
- Implement circuit breaker pattern for repeated failures
- Consider using async HTTP clients for better resource utilization
