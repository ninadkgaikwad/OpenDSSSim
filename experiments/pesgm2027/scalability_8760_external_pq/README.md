# OpenDSSSim 8760 External-PQ Native-Control Scalability V02

This experiment uses existing OpenDSSSim capabilities only.

Input profile SHA256:

`2E4447CE612E1ECBFBC891F5A75F23F67AC7C11AF40E9FAAA75491CB5DC0BD2C`

The same 8760 hourly multiplier drives all load P/Q values on all three feeders.
A05 multiplier mode preserves each load's native baseline PF exactly.

The requested OpenDSSSim history level is H3. H3 records are streamed to gzip JSONL.

## Preflight

```powershell
python experiments\pesgm2027\scalability_8760_external_pq\run_external_pq_native_h3.py `
    --repo-root . `
    --preflight-only
```

## Required 3-step H3 pilot

```powershell
$Out = "$HOME\Downloads\OpenDSSSim_Scalability8760_V02_PILOT_$(Get-Date -Format yyyyMMdd_HHmmss)"

python experiments\pesgm2027\scalability_8760_external_pq\run_external_pq_native_h3.py `
    --repo-root . `
    --output-root $Out `
    --steps 3 `
    --warmup-steps 0
```

Review the pilot summaries and projected H3 storage/runtime before launching full science.

## Full 8760 campaign — only after pilot review

```powershell
$Out = "$HOME\Downloads\OpenDSSSim_Scalability8760_V02_FULL_$(Get-Date -Format yyyyMMdd_HHmmss)"

python experiments\pesgm2027\scalability_8760_external_pq\run_external_pq_native_h3.py `
    --repo-root . `
    --output-root $Out `
    --steps 8760 `
    --warmup-steps 24 `
    --repetitions 1
```
