# Data Sources & Sampling Documentation

This document describes the database tables used for different graph views and the data recording intervals.

## Graph Data Sources

The application uses a tiered strategy to balance performance and data resolution.

### High Frequency Views
**Time Ranges:** 24H, 1W, 1M, 3M
**Table Used:** `NetWorthSnapshot`

- **24H**: All snapshots from the last 24 hours (15 min intervals).
- **1W**: Snapshots from the last 7 days. Sampled to ~6 hour intervals if data points > 40.
- **1M**: Snapshots from the last 30 days. Sampled to ~1 day intervals if data points > 60.
- **3M**: Snapshots from the last 90 days. Sampled to ~1 day intervals if data points > 60.

### Low Frequency / Long-Term Views
**Time Ranges:** 6M, 1Y, Max
**Table Used:** `MonthlyFinancialRecord`

- **6M, 1Y, Max**: Uses monthly "closed book" records. These are stored on the 1st of each month.

## Data Recording Intervals

### High Frequency Snapshots
- **Frequency**: Every 15 minutes (intended schedule).
- **Service Method**: `AnalyticsService.capture_snapshot()`
- **Retention Policy**:
    - **< 24 Hours**: Keep all data (15 min resolution).
    - **24 Hours - 7 Days**: Downsampled to 6-hour intervals.
    - **> 7 Days**: Downsampled to 12-hour intervals.

### Monthly Records
- **Frequency**: Once per month (1st of the month).
- **Service Method**: `NetWorthService.save_networth_snapshot()`
- **Purpose**: Permanent, low-resolution history for year-over-year tracking.
