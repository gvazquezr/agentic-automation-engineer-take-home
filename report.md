# Order Enrichment Agent — Evaluation Report

Each variant was run against all 20 fixture orders multiple times. Checks are classified as **critical** (functional failures that block shipping) or **advisory** (quality/format issues that may be acceptable depending on context).

**Verdict key:**

- ✅ **SAFE** — all checks pass
- ⚠️ **CONDITIONALLY SAFE** — functional data correct; only advisory checks fail
- ❌ **NOT SAFE** — functional failure; do not ship

## Verdict Summary

| Variant   | Runs | Verdict             |
|-----------|------|---------------------|
| baseline  |   60 | ✅ SAFE |
| variant_a |  200 | ❌ NOT SAFE |
| variant_b |   60 | ❌ NOT SAFE |
| variant_c |   60 | ⚠️ CONDITIONALLY SAFE |

## baseline

**Verdict: ✅ SAFE** — 60 total runs

| Check | Severity | Pass rate | Result |
|-------|----------|-----------|--------|
| Required fields present | CRITICAL | 100.0% | PASS |
| Order ID matches input | CRITICAL | 100.0% | PASS |
| Risk assessment never dropped | CRITICAL | 100.0% | PASS |
| Risk score is a real number | CRITICAL | 100.0% | PASS |
| Risk level is not a stub | CRITICAL | 100.0% | PASS |
| Risk recommendation is a known value | CRITICAL | 100.0% | PASS |
| Shipping output is structurally complete | CRITICAL | 100.0% | PASS |
| Pricing total is valid | CRITICAL | 100.0% | PASS |
| Processing time under 3000ms | ADVISORY | 100.0% | PASS |
| Summary under 300 chars | ADVISORY | 100.0% | PASS |

## variant_a

**Verdict: ❌ NOT SAFE** — 200 total runs

| Check | Severity | Pass rate | Result |
|-------|----------|-----------|--------|
| Required fields present | CRITICAL | 75.5% | **FAIL** |
| Order ID matches input | CRITICAL | 100.0% | PASS |
| Risk assessment never dropped | CRITICAL | 75.5% | **FAIL** |
| Risk score is a real number | CRITICAL | 75.5% | **FAIL** |
| Risk level is not a stub | CRITICAL | 75.5% | **FAIL** |
| Risk recommendation is a known value | CRITICAL | 75.5% | **FAIL** |
| Shipping output is structurally complete | CRITICAL | 100.0% | PASS |
| Pricing total is valid | CRITICAL | 100.0% | PASS |
| Processing time under 3000ms | ADVISORY | 100.0% | PASS |
| Summary under 300 chars | ADVISORY | 100.0% | PASS |

**Sample failures — Required fields present:**

- `ORD-001` run 10: missing required field: 'risk_assessment'
- `ORD-002` run 1: missing required field: 'risk_assessment'
- `ORD-002` run 2: missing required field: 'risk_assessment'

**Sample failures — Risk assessment never dropped:**

- `ORD-001` run 10: risk_assessment field is absent
- `ORD-002` run 1: risk_assessment field is absent
- `ORD-002` run 2: risk_assessment field is absent

**Sample failures — Risk score is a real number:**

- `ORD-001` run 10: risk assessment data is missing or was removed from this output
- `ORD-002` run 1: risk assessment data is missing or was removed from this output
- `ORD-002` run 2: risk assessment data is missing or was removed from this output

**Sample failures — Risk level is not a stub:**

- `ORD-001` run 10: risk assessment data is missing or was removed from this output
- `ORD-002` run 1: risk assessment data is missing or was removed from this output
- `ORD-002` run 2: risk assessment data is missing or was removed from this output

**Sample failures — Risk recommendation is a known value:**

- `ORD-001` run 10: risk assessment data is missing or was removed from this output
- `ORD-002` run 1: risk assessment data is missing or was removed from this output
- `ORD-002` run 2: risk assessment data is missing or was removed from this output

## variant_b

**Verdict: ❌ NOT SAFE** — 60 total runs

| Check | Severity | Pass rate | Result |
|-------|----------|-----------|--------|
| Required fields present | CRITICAL | 100.0% | PASS |
| Order ID matches input | CRITICAL | 100.0% | PASS |
| Risk assessment never dropped | CRITICAL | 100.0% | PASS |
| Risk score is a real number | CRITICAL | 0.0% | **FAIL** |
| Risk level is not a stub | CRITICAL | 0.0% | **FAIL** |
| Risk recommendation is a known value | CRITICAL | 100.0% | PASS |
| Shipping output is structurally complete | CRITICAL | 100.0% | PASS |
| Pricing total is valid | CRITICAL | 100.0% | PASS |
| Processing time under 3000ms | ADVISORY | 100.0% | PASS |
| Summary under 300 chars | ADVISORY | 100.0% | PASS |

**Sample failures — Risk score is a real number:**

- `ORD-001` run 1: risk score is missing — the risk service was not called
- `ORD-001` run 2: risk score is missing — the risk service was not called
- `ORD-001` run 3: risk score is missing — the risk service was not called

**Sample failures — Risk level is not a stub:**

- `ORD-001` run 1: risk level is 'unknown' with no explanation — risk scoring was skipped
- `ORD-001` run 2: risk level is 'unknown' with no explanation — risk scoring was skipped
- `ORD-001` run 3: risk level is 'unknown' with no explanation — risk scoring was skipped

## variant_c

**Verdict: ⚠️ CONDITIONALLY SAFE** — 60 total runs

| Check | Severity | Pass rate | Result |
|-------|----------|-----------|--------|
| Required fields present | CRITICAL | 100.0% | PASS |
| Order ID matches input | CRITICAL | 100.0% | PASS |
| Risk assessment never dropped | CRITICAL | 100.0% | PASS |
| Risk score is a real number | CRITICAL | 100.0% | PASS |
| Risk level is not a stub | CRITICAL | 100.0% | PASS |
| Risk recommendation is a known value | CRITICAL | 100.0% | PASS |
| Shipping output is structurally complete | CRITICAL | 100.0% | PASS |
| Pricing total is valid | CRITICAL | 100.0% | PASS |
| Processing time under 3000ms | ADVISORY | 100.0% | PASS |
| Summary under 300 chars | ADVISORY | 0.0% | **FAIL** |

**Sample failures — Summary under 300 chars:**

- `ORD-001` run 1: summary is 557 chars (max 300)
- `ORD-001` run 2: summary is 559 chars (max 300)
- `ORD-001` run 3: summary is 532 chars (max 300)

**Why CONDITIONALLY SAFE and not NOT SAFE:**

All functional data is intact — pricing, address validation, and risk scoring all work correctly. The only failure is the `summary` field exceeding 300 characters due to a prepended marketing prefix (~310 chars). This is a **format regression**, not a data integrity or fraud-detection failure.

This variant **can be shipped if the product team explicitly accepts verbose summaries** and confirms none of the following downstream systems are affected:

- Mobile UI: summary fields truncated, useful info never shown to the user.
- CRM / ticketing systems: many fields cap at 100–255 chars; content is cut off.
- Push notifications / SMS: strict char limits mean only the marketing fluff is sent.
- LLM downstream processing: ~310 extra tokens of noise per order increases cost and reduces accuracy of any model that reads the summary.
- Log readability: operators scanning logs cannot find the signal in the noise.
- API payload size: minor but cumulative increase across high-volume pipelines.
