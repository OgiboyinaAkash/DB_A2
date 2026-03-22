# SubTask 4 and 5 Verification Report

Generated: 2026-03-22
Workspace: DB_A2 / Module_B

## 1) Most Accessed and Slowest API Endpoints

Source artifacts:
- Module_B/app/benchmark_results/api_benchmark_before.json
- Module_B/app/benchmark_results/api_benchmark_after.json

From server-side aggregated metrics during benchmark runs:
- Most accessed endpoint pattern: `GET /api/project/<table_name>` (240 hits)
- Slowest average endpoint pattern (after run): `GET /api/admin/groups`
- Slowest average endpoint pattern (before run): `GET /api/member-portfolio`

This confirms endpoint-level instrumentation for identifying frequent and slow APIs is active.

## 2) Indexing Strategy Coverage (SubTask 4)

Index definitions are present in:
- Module_B/sql/Databases_A1.sql
- Module_B/sql/sql_performance_benchmark.sql

API query clauses are built in:
- Module_B/app/api/routes.py (`_build_sql_filters_and_order`)
- Module_B/app/sql_project_store.py (`list_records` builds WHERE/ORDER BY SQL)

### Query pattern to index mapping

1. Products by category + price sort
- API pattern: `GET /api/project/products?category_id=...&sort=price_desc`
- SQL clauses: `WHERE CategoryID = ? ORDER BY Price DESC`
- Target index: `idx_product_category_price ON Product(CategoryID, Price)`

2. Customer lookup by email
- API pattern: `GET /api/project/customers?email=...`
- SQL clause: `WHERE Email = ?`
- Target index: `ux_customer_email ON Customer(Email)` (unique)

3. Sales by customer and date sort
- API pattern: `GET /api/project/sales?customer_id=...&sort=sale_date_desc`
- SQL clauses: `WHERE CustomerID = ? ORDER BY SaleDate DESC`
- Target index: `idx_sale_customer_date ON Sale(CustomerID, SaleDate)`

4. Sale items by sale id
- API pattern: `GET /api/project/sale_items?sale_id=...`
- SQL clause: `WHERE SaleID = ?`
- Target index: `idx_saleitem_sale ON SaleItem(SaleID)`

5. Join workloads in benchmark SQL
- SQL pattern: `SaleItem JOIN Product ON ProductID`
- Target indexes: `idx_saleitem_product ON SaleItem(ProductID)` plus table PK on Product

This shows direct alignment with WHERE, JOIN, and ORDER BY access patterns.

## 3) API Benchmark Results (SubTask 5 - API Response Times)

### Before vs After (`avg_ms`)

| Endpoint | Before (ms) | After (ms) | Delta (ms) | Delta % |
|---|---:|---:|---:|---:|
| GET /api/project/products | 14.944 | 12.171 | -2.773 | -18.56% |
| GET /api/project/products?category_id=1&sort=price_desc | 14.315 | 11.697 | -2.618 | -18.29% |
| GET /api/project/products/1 | 12.398 | 7.249 | -5.149 | -41.53% |
| GET /api/project/customers | 11.965 | 14.414 | +2.449 | +20.47% |
| GET /api/project/customers?email=rahul.verma@example.com | 14.242 | 9.832 | -4.410 | -30.96% |
| GET /api/project/sales | 13.062 | 9.269 | -3.793 | -29.04% |
| GET /api/project/sales?customer_id=1&sort=sale_date_desc | 13.760 | 11.566 | -2.194 | -15.94% |
| GET /api/project/sale_items | 14.520 | 10.056 | -4.464 | -30.74% |
| GET /api/project/sale_items?sale_id=10 | 14.727 | 8.663 | -6.064 | -41.18% |
| GET /api/member-portfolio | 16.213 | 11.418 | -4.795 | -29.58% |
| GET /api/admin/groups | 14.178 | 11.693 | -2.485 | -17.53% |

Observation:
- 10 out of 11 sampled endpoints improved in average response time.
- One endpoint (`GET /api/project/customers`) regressed in this sample run.

## 4) SQL Query Execution Time and EXPLAIN (SubTask 5 - SQL)

SQL benchmark workflow is scripted in:
- Module_B/sql/sql_performance_benchmark.sql

The script includes:
- BEFORE: explicit index drops, `EXPLAIN`, query execution, `SHOW PROFILES`
- AFTER: index creation, repeated `EXPLAIN`, repeated query execution, `SHOW PROFILES`

Current run status in this workspace session:
- API benchmark files were generated successfully.
- SQL evidence capture was executed using `capture_sql_evidence.py` and concrete output files were generated.
- MySQL connection currently fails in this environment (`127.0.0.1:3306` refused), so SQL evidence files currently contain explicit failure-state records instead of successful query plans.

Concrete SQL evidence artifacts generated:
- Module_B/app/benchmark_results/sql_capture_status.json
- Module_B/app/benchmark_results/sql_explain_before.json
- Module_B/app/benchmark_results/sql_explain_after.json
- Module_B/app/benchmark_results/sql_profiles_before.json
- Module_B/app/benchmark_results/sql_profiles_after.json

Therefore:
- API response-time before/after evidence: AVAILABLE
- SQL EXPLAIN/profiling evidence files: AVAILABLE (currently failure-state due local MySQL service unavailability)

## 5) Deliverables Produced

Generated now:
- Module_B/app/benchmark_results/api_benchmark_before.json
- Module_B/app/benchmark_results/api_benchmark_after.json
- Module_B/app/benchmark_results/plot_avg_before_after.png
- Module_B/app/benchmark_results/plot_avg_percent_change.png
- Module_B/app/benchmark_results/plot_p95_before_after.png
- Module_B/app/benchmark_results/subtask4_5_report.md
- Module_B/app/benchmark_results/generate_benchmark_plots.py
- Module_B/app/benchmark_results/capture_sql_evidence.py
- Module_B/app/benchmark_results/sql_capture_status.json
- Module_B/app/benchmark_results/sql_explain_before.json
- Module_B/app/benchmark_results/sql_explain_after.json
- Module_B/app/benchmark_results/sql_profiles_before.json
- Module_B/app/benchmark_results/sql_profiles_after.json

Reusable SQL workflow scripts:
- Module_B/sql/sql_performance_benchmark.sql
- Module_B/app/benchmark_results/capture_sql_evidence.py
