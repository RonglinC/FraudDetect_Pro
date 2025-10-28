# Prompt: EDA script for creditcard.csv 

Goal
Create a reproducible quick EDA to understand the key features of creditcard.csv before model training.

Dataset location
- Default CSV file is: backend/data/creditcard.csv

Tasks

1) Create backend/eda/eda.py that:
   - loads the CSV from DATA_PATH or fallback to backend/data/creditcard.csv
   - prints:
       * total rows
       * fraud rate
       * column list
   - computes & prints basic stats for:
       * Time (sec since first transaction)
       * Amount (money value)
       Including: mean, median, std, min, max, 1% and 99% quantiles
   - plots histograms for Amount:
       * linear scale split by Class
       * log1p scale split by Class
   - plots fraud vs normal histograms for PCA features V1, V2, V3
   - save all charts to: backend/reports/eda/
       * amount_dist_linear.png
       * amount_dist_log.png
       * v1_dist.png, v2_dist.png, v3_dist.png
   - write a summary markdown report:
       backend/reports/eda/README.md
       Include:
         - printed stats
         - fraud rate
         - short findings about PCA signals
         - image paths embedded or listed

2) Update Makefile with:
   - eda: run the script

Constraints
- Use pandas + matplotlib only
- Do not fail if matplotlib backend issues occur; fallback to Agg if needed
- If CSV missing: print clear error and exit(1)

Deliverables
- Show unified diffs only
- Ask for confirmation before applying changes
