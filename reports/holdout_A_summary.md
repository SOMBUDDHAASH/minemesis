# Hold-out A: 50-Seed Statistical Summary (Seeds 1000-1049)

- **Total Seeds Evaluated**: 50 (Seeds 1000 - 1049)
- **Simulated Years per Seed**: 100 (1,200 ticks)

## Target Assessment

| Metric Target | Target Threshold | Observed Result | Status |
| :--- | :---: | :---: | :---: |
| **Zero Extinct Settlements** | 0 across all seeds (Hard) | 1 | FAIL |
| **Zero-Feud Runs Share** | <= 5% | 0.0% | PASS |
| **Median Feuds per Run** | 3 - 10 | 7.0 (mean 7.5) | PASS |
| **Active Feud / Tension at Year 100** | >= 40% | 52.0% | PASS |
| **Routine Event Share (Birth+Death+Marr)** | <= 70% | 63.0% | PASS |
| **Distinct Event Types on Deepest Path** | >= 3 in most runs | Median 7.0 (min 3) | PASS |
| **End-State Wealth & Food Spread** | Meaningfully differs | Food Spread: 10280.42 | Wealth Spread: 2068.88 | PASS |

## Drama & Historical Pressure Metrics

- **Feuds**: Mean 7.5, Median 7.0 (Min 2, Max 14)
- **Wrongful Feuds (False Beliefs)**: Mean 3.76, Median 4.0
- **Revenge Killings**: Mean 0.98, Median 1.0
- **Raids**: Mean 41.2, Median 40.0
- **Famines**: Mean 6.14, Median 0.0
- **Succession Crises**: Mean 2.56, Median 2.0

## Peace Mechanisms

- **Truth Revelation (Pipeline)**: 132 occurrences across batch
- **Negotiated Treaty (Exhaustion)**: 203 occurrences across batch

## Causal Structure

- **Maximum Real Causal Depth**: Mean 8.58, Median 8.0 (Max 13)
- **Distinct Event Types on Longest Chain**: Median 7.0
