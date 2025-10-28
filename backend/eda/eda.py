import os
import sys
import pandas as pd
import numpy as np
import matplotlib
try:
    import matplotlib.pyplot as plt
except Exception:
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

def main():
    # Get data path
    data_path = os.environ.get("DATA_PATH", "backend/data/creditcard.csv")
    if not os.path.exists(data_path):
        print(f"ERROR: CSV not found at {data_path}")
        sys.exit(1)
    df = pd.read_csv(data_path)
    total_rows = len(df)
    print(f"Total rows: {total_rows}")
    fraud_rate = df['Class'].mean()
    print(f"Fraud rate: {fraud_rate:.6f}")
    print("Columns:", list(df.columns))

    # Stats for Time and Amount
    stats = {}
    for col in ["Time", "Amount"]:
        if col in df.columns:
            vals = df[col]
            stats[col] = {
                "mean": float(np.mean(vals)),
                "median": float(np.median(vals)),
                "std": float(np.std(vals)),
                "min": float(np.min(vals)),
                "max": float(np.max(vals)),
                "q01": float(np.quantile(vals, 0.01)),
                "q99": float(np.quantile(vals, 0.99)),
            }
            print(f"{col} stats:", stats[col])
        else:
            print(f"Column {col} not found in data.")

    # Prepare output dir
    outdir = "backend/reports/eda"
    os.makedirs(outdir, exist_ok=True)

    # Amount histograms (linear and log1p), split by Class
    for scale, fname in [("linear", "amount_dist_linear.png"), ("log", "amount_dist_log.png")]:
        plt.figure(figsize=(8,4))
        for label, group in df.groupby("Class"):
            vals = group["Amount"]
            if scale == "log":
                vals = np.log1p(vals)
            plt.hist(vals, bins=50, alpha=0.6, label=f"Class {label}", density=True)
        plt.title(f"Amount distribution ({scale})")
        plt.xlabel("log(Amount+1)" if scale=="log" else "Amount")
        plt.ylabel("Density")
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(outdir, fname))
        plt.close()

    # PCA features V1, V2, V3 histograms by Class
    pca_feats = ["V1", "V2", "V3"]
    for v in pca_feats:
        if v in df.columns:
            plt.figure(figsize=(8,4))
            for label, group in df.groupby("Class"):
                plt.hist(group[v], bins=50, alpha=0.6, label=f"Class {label}", density=True)
            plt.title(f"{v} distribution by Class")
            plt.xlabel(v)
            plt.ylabel("Density")
            plt.legend()
            plt.tight_layout()
            plt.savefig(os.path.join(outdir, f"{v.lower()}_dist.png"))
            plt.close()

    # Write summary markdown
    md_path = os.path.join(outdir, "README.md")
    with open(md_path, "w") as f:
        f.write("# EDA Summary for creditcard.csv\n\n")
        f.write(f"**Total rows:** {total_rows}\n\n")
        f.write(f"**Fraud rate:** {fraud_rate:.6f}\n\n")
        f.write("## Columns\n")
        f.write(", ".join(df.columns) + "\n\n")
        f.write("## Basic Stats\n")
        for col in stats:
            f.write(f"### {col}\n")
            for k, v in stats[col].items():
                f.write(f"- {k}: {v}\n")
            f.write("\n")
        f.write("## Plots\n")
        f.write("- Amount (linear): ![amount_dist_linear](amount_dist_linear.png)\n")
        f.write("- Amount (log1p): ![amount_dist_log](amount_dist_log.png)\n")
        for v in pca_feats:
            if v in df.columns:
                f.write(f"- {v}: ![{v.lower()}_dist]({v.lower()}_dist.png)\n")
        f.write("\n## Findings\n")
        f.write("- Fraud rate is low; class imbalance is present.\n")
        f.write("- Amount distribution is right-skewed; log transform helps visualization.\n")
        f.write("- PCA features V1-V3 show different distributions for fraud vs normal; some separation is visible.\n")
        f.write("\n")

if __name__ == "__main__":
    main()
