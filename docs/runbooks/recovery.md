# Recovery Runbook

## Scenario: Machine crash / power loss during flush

### Symptoms
- Session status stuck at `pending_flush`
- Pending session file exists in `pending/` directory
- No recent entries in `flush_log`

### Recovery Steps

1. **Check daemon status**
   ```bash
   imbalance daemon status
   ```

2. **Start daemon (will auto-recover pending sessions)**
   ```bash
   imbalance daemon start
   ```

3. **Verify recovery**
   ```bash
   imbalance session list
   imbalance queue status
   ```

4. **Manual recovery if daemon fails**
   ```bash
   imbalance queue recover
   ```

### Verification
- All pending sessions should show status `flushed`
- Queue should be empty
- Check logs: `tail -f /tmp/imbalance-daemon.log`

### Prevention
- Use `imbalance daemon install` for auto-start on boot
- Enable WAL mode (default) for SQLite integrity
