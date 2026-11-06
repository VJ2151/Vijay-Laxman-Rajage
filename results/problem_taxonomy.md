# NYC 311 Data Quality Problem Taxonomy (Rule 3)

Each of the 12 corruption problem types is assigned exactly ONE primary detection level.

| Problem ID | Problem Description | Primary Level | Secondary / Derived Level | Injection Scope | Ground Truth Target |
|---|---|---|---|---|---|
| **a** | Renamed or dropped column | **Batch** | None | Schema modification across batch | `batch_flag: bool` |
| **b** | Column type change (numeric to string/mixed) | **Batch** | None | Column dtype cast across batch | `batch_flag: bool` |
| **c** | Date format switch mid-batch (ISO to US slash) | **Batch** | Row (parse failures) | Injects non-standard date strings | `batch_flag: bool` |
| **d** | Latitude and longitude swapped | **Row** | Batch (out-of-bounds share) | Swaps lat and lon columns for % of rows | `row_mask: bool pd.Series` |
| **e** | Exact duplicate records | **Row** | Batch (duplicate count) | Duplicates % of rows | `row_mask: bool pd.Series` |
| **f** | Near-duplicate records (jittered timestamp/text) | **Row** | Batch (cluster rate) | Duplicates rows with slight edits | `row_mask: bool pd.Series` |
| **g** | Agency null spike | **Batch** | Group (agency level) | Sets zip/coords to null for single agency | `batch_flag: bool` |
| **h** | Closed date before created date | **Row** | Batch (temporal inversion rate) | Sets closed_date = created_date - delta | `row_mask: bool pd.Series` |
| **i** | ZIP code inconsistent with borough | **Row** | Batch (mismatch rate) | Replaces ZIP with another borough's ZIP | `row_mask: bool pd.Series` |
| **j** | Complaint type inconsistent with descriptor | **Row** | Batch (cross-category rate) | Swaps descriptor from unrelated category | `row_mask: bool pd.Series` |
| **k** | Resolution contradicts status | **Row** | Batch (semantic mismatch rate) | Puts 'pending' in closed resolution | `row_mask: bool pd.Series` |
| **l** | Synthetic PII inserted into free text | **Row** | Batch (privacy breach rate) | Injects synthetic names/phones/emails | `row_mask: bool pd.Series` |
