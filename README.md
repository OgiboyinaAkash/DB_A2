# DB_A2 Project Guide

This repository contains two modules:

- `Module_A`: B+ Tree vs Brute-Force indexing and performance analysis.
- `Module_B`: Local API development, RBAC, SQL indexing, and benchmark evidence.

## Project Structure

```text
DB_A2/
├─ Module_A/
│  ├─ report.ipynb
│  ├─ requirements.txt
│  └─ database/
│     ├─ bplustree.py
│     ├─ bruteforce.py
│     ├─ db_init.py
│     ├─ db_manager.py
│     ├─ performance_analyzer.py
│     ├─ table.py
│     ├─ main.ipynb
│     ├─ Plots/
│     └─ visualizations/
│        └─ product_tree.dot
├─ Module_B/
│  ├─ report.ipynb
│  ├─ requirements.txt
│  ├─ app/
│  │  ├─ app.py
│  │  ├─ api_performance_benchmark.py
│  │  ├─ auth_manager.py
│  │  ├─ group_manager.py
│  │  ├─ member_manager.py
│  │  ├─ sql_project_store.py
│  │  ├─ api/
│  │  │  └─ routes.py
│  │  ├─ frontend/
│  │  │  ├─ index.html
│  │  │  ├─ app.js
│  │  │  ├─ apiService.js
│  │  │  └─ styles.css
│  │  └─ benchmark_results/
│  │     ├─ api_benchmark_before.json
│  │     ├─ api_benchmark_after.json
│  │     ├─ sql_capture_status.json
│  │     ├─ sql_explain_before.json
│  │     ├─ sql_explain_after.json
│  │     ├─ sql_profiles_before.json
│  │     ├─ sql_profiles_after.json
│  │     ├─ capture_sql_evidence.py
│  │     └─ generate_benchmark_plots.py
│  ├─ sql/
│  │  ├─ Databases_A1.sql
│  │  ├─ member_project_schema.sql
│  │  └─ sql_performance_benchmark.sql
│  └─ logs/
│     └─ audit.log.txt
└─ .gitignore
```

## Prerequisites

- Python 3.10+
- MySQL 8.x (for Module B SQL-backed benchmarking)
- Graphviz (recommended for tree visualization support)

## 1) Environment Setup

Run from repository root (`DB_A2`):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r Module_A\requirements.txt
pip install -r Module_B\requirements.txt
```

## 2) Execute Module A

### Option A: Run notebook report

1. Open `Module_A/report.ipynb` in VS Code or Jupyter.
2. Select your Python kernel (`.venv`).
3. Run cells top-to-bottom.

### Option B: Run analysis from code (optional)

Use `Module_A/database/performance_analyzer.py` through notebook cells in `report.ipynb` to:

- compare B+ Tree vs brute-force for `insert/search/range_query/delete`
- generate memory/time summaries
- display plots from the plots directory

## 3) Execute Module B

### Step 1: Prepare MySQL schema/data

Load SQL files in MySQL Workbench or CLI:

1. `Module_B/sql/Databases_A1.sql`
2. `Module_B/sql/member_project_schema.sql` (if using member-project SQL extension)

Optional benchmark script file:

- `Module_B/sql/sql_performance_benchmark.sql`

### Step 2: Configure DB connection (if needed)

PowerShell example:

```powershell
$env:MYSQL_HOST="127.0.0.1"
$env:MYSQL_PORT="3306"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="<your_password>"
$env:MYSQL_DATABASE="outlet_management"
```

### Step 3: Start local API + frontend

```powershell
Set-Location Module_B\app
python app.py
```

Open in browser:

- `http://127.0.0.1:5000`

### Step 4: Run API benchmark (before/after)

From repository root (`DB_A2`):

```powershell
python Module_B\app\api_performance_benchmark.py --phase before --base-url http://127.0.0.1:5000 --output-dir Module_B\app\benchmark_results
python Module_B\app\api_performance_benchmark.py --phase after --base-url http://127.0.0.1:5000 --output-dir Module_B\app\benchmark_results
```

### Step 5: Capture SQL EXPLAIN/profile evidence

```powershell
python Module_B\app\benchmark_results\capture_sql_evidence.py
```

### Step 6: Generate benchmark plots

```powershell
python Module_B\app\benchmark_results\generate_benchmark_plots.py
```

## 4) Reports and Outputs

- Module A report notebook: `Module_A/report.ipynb`
- Module B report notebook: `Module_B/report.ipynb`
- Module B benchmark evidence: `Module_B/app/benchmark_results/`
- Module B audit logs: `Module_B/logs/audit.log.txt`

## Troubleshooting

- If SQL evidence capture fails with connection errors, verify MySQL is running and environment variables are correct.
- If API benchmark fails at login, ensure the API server is running first.
- If graph images do not appear in notebooks, run plotting cells/scripts to regenerate PNG files.
