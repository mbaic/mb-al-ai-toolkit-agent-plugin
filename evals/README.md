# Evaluation corpus

`scripts/validate.py` answers one question: **does the package load?** It says nothing about whether the review is any good. A plugin can validate perfectly and still produce a reviewer that misses a table lock and invents an API.

This directory answers the second question: **does the reviewer produce correct findings, with sound evidence, at an acceptable false-positive rate?**

## Status

First iteration. The cases are written and the scoring method is defined. The runs are manual, because the review runs inside a Copilot client and this repository ships no model runner. Record each run in `results/` with the client, the model, and the date.

Do not treat a passing case as proof of quality until several models have run the corpus.

## Layout

```
evals/
├── README.md                 this file: method and scoring
├── cases/
│   └── <case-id>/
│       ├── input.al          the AL under review
│       └── expected.md       what a correct review must find
└── results/                  one file per run
```

## What a case defines

Each `expected.md` states four things:

1. **Required findings.** The reviewer must report each one. A miss is a false negative.
2. **Acceptable findings.** Legitimate to report, and not required. These never count against a run.
3. **False-positive traps.** Correct AL that a weak reviewer flags anyway. Reporting one is a false positive.
4. **Grounding requirement.** Whether the finding must cite Microsoft Learn as evidence, or whether repository inspection is enough.

A required finding is matched by its **ID and location**, never by its wording. Two models phrase the same defect differently, and the corpus must not reward one phrasing.

## Scoring

For one run over the corpus:

| Measure | Definition |
|---|---|
| Recall | required findings reported ÷ required findings total |
| Precision | required and acceptable findings ÷ all findings reported |
| False-positive rate | traps reported ÷ traps total |
| Severity accuracy | findings at the expected severity ÷ required findings reported |
| Grounding accuracy | findings whose evidence matches the requirement ÷ findings that require grounding |
| Invention rate | findings that reference an AL API that does not exist ÷ all findings reported |

**Invention rate must be zero.** Every other measure is a trade-off. This one is not, because the skill states that inventing an AL API has no exception, and a reviewer that invents an API is worse than no reviewer at all.

## How to run a case

1. Open the client with the plugin installed.
2. Start a session in a scratch repository holding one case's `input.al`.
3. Ask for a review of that file in plain words, so the skill loads.
4. Record the findings verbatim.
5. Score against `expected.md`, and write the result to `results/`.

Change one variable at a time. A run that changes the model and the skill together tells you nothing about either.

## Adding a case

A case earns its place when it separates a good reviewer from a weak one. A defect that every model finds measures nothing.

Prefer a defect that:

- is real AL, taken from a pattern you have actually seen in a code review;
- has one clear correct answer;
- is silent at run time, so a compiler will not catch it either;
- has a nearby correct construct that tempts a false positive.

Keep each `input.al` short. A case that needs 200 lines is testing reading comprehension, not AL review.
