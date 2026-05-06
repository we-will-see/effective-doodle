# Excel Named-Range Convention

**Status:** Decided (Option 3 - Sensible Default)
**Date:** 2026-05-06
**Owner:** Automatic Decision

## Convention

```
<metric>_<period>_<scenario>
```

## Examples

| Range Name | Description |
|------------|-------------|
| `revenue_FY26_base` | Revenue for FY26, base case |
| `revenue_FY26_bull` | Revenue for FY26, bull case |
| `ebitda_1QFY26_base` | EBITDA for Q1 FY26, base case |
| `pat_H1FY26_base` | PAT for H1 FY26, base case |
| `gross_margin_FY27_base` | Gross margin % for FY27 |

## Rules

1. **Metric** — Use lowercase, underscores for spaces
   - `revenue`, `ebitda`, `pat`, `gross_margin`, `operating_margin`

2. **Period** — Follow Indian FY convention (ADR-012)
   - `FY26` = April 2025 - March 2026
   - `1QFY26` = April-June 2025
   - `H1FY26` = April-September 2025

3. **Scenario** — Always one of: `base`, `bull`, `bear`
   - `base` = Most likely case
   - `bull` = Upside case
   - `bear` = Downside case

## Per-Company Workbook

Each covered company has one workbook named:
```
<company_display_name>_<YYYYMMDD>.xlsx
```

Example: `Cohance_Lifesciences_20250506.xlsx`

## Notes

- This convention is locked for v1
- Can be revised in decision log if friction observed
- Used by `modeling/excel_adapter` module
- Referenced in ADR-005 (Excel as source of truth)
