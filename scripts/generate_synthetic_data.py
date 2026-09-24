"""
scripts/generate_synthetic_data.py
===================================
Script to generate synthetic clean and messy datasets for DataPilot benchmarking
and manual testing.

Outputs:
  - scripts/sample_data/clean_data.csv
  - scripts/sample_data/messy_data.csv
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


def generate_clean_dataset(n_rows: int = 500, random_state: int = 42) -> pd.DataFrame:
    """Generate a clean synthetic dataset with realistic correlations."""
    np.random.seed(random_state)
    
    dates = pd.date_range(start="2024-01-01", periods=n_rows, freq="D")
    regions = np.random.choice(["North", "South", "East", "West"], size=n_rows)
    
    # Correlated metrics: sales, marketing_spend, customer_count, avg_order_value, profit
    marketing_spend = np.random.uniform(500, 5000, size=n_rows)
    sales = marketing_spend * 2.5 + np.random.normal(0, 300, size=n_rows)
    customer_count = sales / np.random.uniform(25, 35, size=n_rows)
    avg_order_value = sales / customer_count
    profit = sales * 0.25 - marketing_spend * 0.1 + np.random.normal(0, 50, size=n_rows)

    df = pd.DataFrame({
        "transaction_date": dates.astype(str),
        "region": regions,
        "marketing_spend": np.round(marketing_spend, 2),
        "sales": np.round(sales, 2),
        "customer_count": np.round(customer_count, 0).astype(int),
        "avg_order_value": np.round(avg_order_value, 2),
        "profit": np.round(profit, 2),
    })
    return df


def generate_messy_dataset(n_rows: int = 500, random_state: int = 42) -> tuple[pd.DataFrame, list[int]]:
    """
    Generate a messy dataset with nulls, duplicates, mixed types, and 5 known injected outliers.
    
    Injected outlier row indices: 12, 45, 102, 250, 410.
    """
    df = generate_clean_dataset(n_rows=n_rows, random_state=random_state)
    np.random.seed(random_state + 1)
    
    # 1. Inject 5 known extreme outliers in 'sales' and 'profit'
    injected_indices = [12, 45, 102, 250, 410]
    df.loc[12, "sales"] = 99999.00
    df.loc[45, "marketing_spend"] = 85000.00
    df.loc[102, "profit"] = -45000.00
    df.loc[250, "customer_count"] = 15000
    df.loc[410, "sales"] = 120000.00

    # 2. Inject missing values (~12% missing rate in marketing_spend and profit)
    null_mask_mkt = np.random.rand(n_rows) < 0.12
    null_mask_mkt[injected_indices] = False  # preserve outliers
    df.loc[null_mask_mkt, "marketing_spend"] = np.nan

    null_mask_prof = np.random.rand(n_rows) < 0.10
    null_mask_prof[injected_indices] = False
    df.loc[null_mask_prof, "profit"] = np.nan

    # 3. Inject duplicate rows (25 duplicate rows)
    dup_rows = df.iloc[:25].copy()
    df = pd.concat([df, dup_rows], ignore_index=True)

    # 4. Inject object/string values into numeric col (type mismatch)
    df.loc[30, "avg_order_value"] = "N/A"
    df.loc[80, "avg_order_value"] = "UNKNOWN"

    return df, injected_indices


def main() -> None:
    out_dir = Path(__file__).parent / "sample_data"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    clean_df = generate_clean_dataset()
    clean_path = out_dir / "clean_data.csv"
    clean_df.to_csv(clean_path, index=False)
    print(f"Generated clean dataset: {clean_path} ({len(clean_df)} rows)")

    messy_df, outliers = generate_messy_dataset()
    messy_path = out_dir / "messy_data.csv"
    messy_df.to_csv(messy_path, index=False)
    print(f"Generated messy dataset: {messy_path} ({len(messy_df)} rows, injected outliers at {outliers})")


if __name__ == "__main__":
    main()
