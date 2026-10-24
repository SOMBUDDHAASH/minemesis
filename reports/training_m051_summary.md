# Batch Statistical Summary (training_m051)

- **Total Seeds Evaluated**: 50
- **Simulated Years per Seed**: 100 (1,200 ticks)

## Target Assessment

| Metric Target | Target Threshold | Observed Result | Status |
| :--- | :---: | :---: | :---: |
| **No World Extinction** | 0 world extinctions (Hard) | 0 extinctions | **PASS** |
| **Zero-Feud Runs Share** | <= 5% | 0.0% | **PASS** |
| **Median Feuds per Run** | 3 - 10 | 8.0 (mean 7.84) | **PASS** |
| **Active Feud / Tension at Year 100** | >= 40% | 68.0% | **PASS** |
| **Routine Event Share (Birth+Death+Marr)** | <= 70% | 59.0% | **PASS** |
| **Conflict Chain Depth & Diversity** | Depth >= 3, Types >= 3 | Median Depth 7.0, Types 4.0 | **PASS** |
| **Famine Occurrence Share** | 30% - 80% of runs | 70.0% of runs | **PASS** |
| **End-State Food Stock Cap** | <= 3.5 years consumption | Mean max 2.02 years | **PASS** |
| **End-State Economic Spread** | Differ meaningfully | Food Ratio: 54.31x | Wealth Ratio: 2.26x | **PASS** |

## Drama & Historical Pressure Metrics (Across 50 Seeds)

- **Feuds**: Mean 7.84, Median 8.0 (Min 2, Max 15)
- **Wrongful Feuds (False Beliefs)**: Mean 3.82, Median 4.0
- **Revenge Killings**: Mean 1.08, Median 1.0
- **Raids**: Mean 45.44, Median 43.5
- **Famines**: Mean 9.8, Median 7.0 (70.0% of runs experienced famine)
- **Succession Crises**: Mean 2.64, Median 3.0
- **Settlement Collapses**: 39 total across 32 runs (Mean 0.78)
- **Migrations**: 39 total logged migrations

## Peace Mechanisms

- **Truth Revelation (Pipeline)**: 132 occurrences across batch
- **Negotiated Treaty (Exhaustion)**: 195 occurrences across batch

## Causal Structure

- **Conflict Causal Depth**: Mean 6.98, Median 7.0 (Max 11)
- **Distinct Conflict Types on Path**: Median 4.0 (Min 3)
- **Maximum Causal Depth (All Events)**: Mean 8.28, Median 8.0 (Max 13)
