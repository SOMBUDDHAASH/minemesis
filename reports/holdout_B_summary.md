# Batch Statistical Summary (holdout_B)

- **Total Seeds Evaluated**: 50
- **Simulated Years per Seed**: 100 (1,200 ticks)

## Target Assessment

| Metric Target | Target Threshold | Observed Result | Status |
| :--- | :---: | :---: | :---: |
| **No World Extinction** | 0 world extinctions (Hard) | 1 extinctions | **FAIL** |
| **Zero-Feud Runs Share** | <= 5% | 0.0% | **PASS** |
| **Median Feuds per Run** | 3 - 10 | 7.0 (mean 7.3) | **PASS** |
| **Active Feud / Tension at Year 100** | >= 40% | 68.0% | **PASS** |
| **Routine Event Share (Birth+Death+Marr)** | <= 70% | 59.0% | **PASS** |
| **Conflict Chain Depth & Diversity** | Depth >= 3, Types >= 3 | Median Depth 7.0, Types 4.0 | **PASS** |
| **Famine Occurrence Share** | 30% - 80% of runs | 58.0% of runs | **PASS** |
| **End-State Food Stock Cap** | <= 3.5 years consumption | Mean max 2.08 years | **PASS** |
| **End-State Economic Spread** | Differ meaningfully | Food Ratio: 74.49x | Wealth Ratio: 3.2x | **PASS** |

## Drama & Historical Pressure Metrics (Across 50 Seeds)

- **Feuds**: Mean 7.3, Median 7.0 (Min 1, Max 15)
- **Wrongful Feuds (False Beliefs)**: Mean 3.64, Median 3.0
- **Revenge Killings**: Mean 1.16, Median 1.0
- **Raids**: Mean 42.18, Median 41.5
- **Famines**: Mean 10.46, Median 8.0 (58.0% of runs experienced famine)
- **Succession Crises**: Mean 3, Median 3.0
- **Settlement Collapses**: 38 total across 31 runs (Mean 0.76)
- **Migrations**: 38 total logged migrations

## Peace Mechanisms

- **Truth Revelation (Pipeline)**: 132 occurrences across batch
- **Negotiated Treaty (Exhaustion)**: 172 occurrences across batch

## Causal Structure

- **Conflict Causal Depth**: Mean 6.56, Median 7.0 (Max 12)
- **Distinct Conflict Types on Path**: Median 4.0 (Min 3)
- **Maximum Causal Depth (All Events)**: Mean 7.76, Median 8.0 (Max 12)
