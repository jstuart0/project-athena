# Benchmark Results Directory

This directory stores benchmark results from the Project Athena orchestrator.

## Purpose

Track performance improvements by comparing baseline and optimized benchmark runs.

## Usage

1. **Run baseline benchmark:**
   ```bash
   python3 scripts/benchmark_runner.py --output results/baseline-2025-11-14.json
   ```

2. **Apply optimizations** (see implementation plan)

3. **Run optimized benchmark:**
   ```bash
   python3 scripts/benchmark_runner.py --output results/optimized-2025-11-14.json
   ```

4. **Compare results:**
   ```bash
   python3 scripts/compare_benchmarks.py results/baseline-2025-11-14.json results/optimized-2025-11-14.json
   ```

## File Naming Convention

- `baseline-YYYY-MM-DD.json` - Baseline performance before optimizations
- `optimized-YYYY-MM-DD.json` - Performance after optimizations
- `benchmark-TIMESTAMP.json` - Ad-hoc benchmark runs

## Result Structure

Each JSON file contains:
- Timestamp and configuration
- Summary statistics (total, successful, avg time, target rate)
- Per-category breakdown
- Individual query results with timings

## Note

JSON result files are gitignored to avoid committing large result sets.
Keep important baseline/optimized results backed up separately.
