# Case: write and commit inside a locked loop

**File:** `input.al` · **Primary ID:** `AL-LOCK-001`

## Required findings

| ID | Location | Defect |
|---|---|---|
| `AL-LOCK-001` | `SyncCreditLimits`, the `repeat` block | `Commit()` runs inside a loop that holds a table lock. Each commit ends the transaction, so a failure part way through leaves the table half updated, and the lock is taken and released repeatedly. |
| `AL-DATA-001` | `SyncCreditLimits`, `Customer.FindSet(true)` | The read has no filter, so the procedure locks and rewrites every customer record. |

Severity for both: **High** or **Critical**. A run that reports either at Low or Medium fails severity accuracy.

## Acceptable findings

- `Setup.Get()` is called and never used.
- `Validate` inside a loop runs table triggers for each record, which is a performance cost.
- The procedure has no way to report which records it changed.

## False-positive traps

- `GetBlockedCustomerCount` is **correct**. It filters before the read and uses `SetLoadFields`. A finding against it is a false positive.
- `Modify(true)` is correct here. Running triggers is deliberate.

## Grounding requirement

None. Repository inspection is sufficient evidence for both required findings. A run that cites Microsoft Learn is not penalised.
