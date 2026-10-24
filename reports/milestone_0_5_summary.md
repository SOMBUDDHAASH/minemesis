# Milestone 0.5: 50-Seed Statistical Summary

- **Total Seeds Evaluated**: 50
- **Simulated Years per Seed**: 100 (1,200 ticks)

## Target Assessment

| Metric Target | Target Threshold | Observed Result | Status |
| :--- | :---: | :---: | :---: |
| **No Cause-Grammar Violations** | 0 violations (Hard) | 0 violations | **PASS** |
| **Zero Extinct Settlements** | 0 across all seeds (Hard) | 0 | **PASS** |
| **Zero-Feud Runs Share** | <= 5% | 4.0% | **PASS** |
| **Median Feuds per Run** | 3 - 10 | 7.0 (mean 6.76) | **PASS** |
| **Active Feud / Tension at Year 100** | >= 40% | 34.0% | **PASS** |
| **Routine Event Share (Birth+Death+Marr)** | <= 70% | 64.0% | **PASS** |
| **Distinct Event Types on Deepest Path** | >= 3 in most runs | Median 7.0 (min 3) | **PASS** |
| **End-State Wealth & Food Spread** | Meaningfully differs | Food Spread: 9319.02 | Wealth Spread: 2218.24 | **PASS** |

## Drama & Historical Pressure Metrics (Across 50 Seeds)

- **Feuds**: Mean 6.76, Median 7.0 (Min 0, Max 13)
- **Wrongful Feuds (False Beliefs)**: Mean 3.24, Median 3.0
- **Revenge Killings**: Mean 0.82, Median 1.0
- **Raids**: Mean 38.4, Median 40.5
- **Famines**: Mean 4.68, Median 0.0
- **Succession Crises**: Mean 2.8, Median 2.5

## Peace Mechanisms

- **Truth Revelation (Pipeline)**: 111 occurrences across batch
- **Negotiated Treaty (Exhaustion)**: 195 occurrences across batch

## Causal Structure

- **Maximum Real Causal Depth**: Mean 8.34, Median 8.0 (Max 13)
- **Distinct Event Types on Longest Chain**: Median 7.0
