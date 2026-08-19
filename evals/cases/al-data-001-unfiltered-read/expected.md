# Case: unfiltered read with CalcFields inside a nested loop

**File:** `input.al` · **Primary ID:** `AL-DATA-001`

## Required findings

| ID | Location | Defect |
|---|---|---|
| `AL-DATA-001` | `BuildTurnover`, `Item.FindSet()` | The outer read has no filter. The procedure reads every item, and the nested read then walks every ledger entry for each one. |
| `AL-DATA-002` | `BuildTurnover`, `Item.CalcFields(Inventory)` | `CalcFields` runs inside the inner loop, so the same FlowField is recalculated once per ledger entry instead of once per item. It is not used by the calculation at all. |

Severity: **High** for `AL-DATA-001`, **Medium** or **High** for `AL-DATA-002`.

A reviewer that reports only one of the two has a recall of 0.5 on this case.

## Acceptable findings

- Neither record uses `SetLoadFields`, and both read full records.
- The totals could come from a single query or a sum instead of two nested loops.
- `Format(Value)` loses decimal precision information in the buffer.

## False-positive traps

- `InsertBuffer` is **correct** for a temporary record. `Init` then `Insert` on a temporary table is the right pattern, and a finding that demands `Insert(true)` here is a false positive.
- The inner `SetRange` on `"Item No."` is correct. Only the outer read is unfiltered.

## Grounding requirement

`AL-DATA-002` should cite evidence for the claim that `CalcFields` recalculates on each call. Microsoft Learn or repository inspection both count. An unverified claim fails grounding accuracy.
