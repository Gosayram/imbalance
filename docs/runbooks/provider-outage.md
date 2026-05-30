# Provider Outage Runbook

## Scenario: OpenRouter/Anthropic unavailable

### Symptoms
- Flush failures in logs
- Circuit breaker open for provider
- Queue depth increasing

### Automatic Behavior
- Circuit breaker opens after 3 consecutive failures
- Flush payload saved to `flush_queue` in SQLite
- Background retry every 15 minutes
- Fallback chain: OpenRouter → Ollama → Anthropic → Queue

### Manual Steps

1. **Check provider health**
   ```bash
   imbalance stats --show provider-health
   imbalance debug cb-status
   ```

2. **Check queue depth**
   ```bash
   imbalance queue status
   ```

3. **Force retry (if provider recovered)**
   ```bash
   imbalance queue retry
   ```

4. **Switch to offline mode (if extended outage)**
   ```bash
   # In imbalance.toml
   [flush]
   mode = "queue_only"
   ```

### Recovery
When provider recovers:
1. Circuit breaker auto-closes after 2 successful calls
2. Queue auto-drains in background
3. Monitor: `imbalance stats --show provider-health`

### Prevention
- Configure multiple providers in `imbalance.toml`
- Set `prefer_free_models = true` for cost control
- Consider local Ollama as fallback
