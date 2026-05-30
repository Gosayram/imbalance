# KB Rollback Runbook

## Scenario: Erroneous flush corrupted KB

### Symptoms
- Incorrect information in wiki sections
- Conflicting decisions in KB
- Retrieval returning wrong context

### Recovery Steps

1. **Check history of affected section**
   ```bash
   imbalance wiki history decisions/002-auth
   ```

2. **View diff between versions**
   ```bash
   imbalance wiki diff decisions/002-auth v1 v3
   ```

3. **Rollback to known good version**
   ```bash
   imbalance wiki rollback decisions/002-auth --to v1
   ```

4. **Or archive the erroneous section**
   ```bash
   imbalance wiki archive decisions/023-use-celery --reason "wrong, using ARQ instead"
   ```

5. **Purge old archived sections (optional)**
   ```bash
   imbalance wiki purge --older-than 30
   ```

### Full KB Recovery

If multiple sections affected:

1. **Create backup first**
   ```bash
   imbalance backup kb-backup-$(date +%Y%m%d).db
   ```

2. **Import from known good export**
   ```bash
   imbalance import known-good-kb.toml --replace
   ```

### Verification
```bash
imbalance wiki conflicts        # Check for unresolved conflicts
imbalance doctor                # Verify DB integrity
imbalance search "test query"   # Verify retrieval works
```

### Prevention
- Use `imbalance kb compact --dry-run` before actual compaction
- Review conflicts with `imbalance wiki conflicts` before release
- Export KB before major changes: `imbalance export --format sqlite backup.db`
