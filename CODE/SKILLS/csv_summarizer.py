#!/usr/bin/env python3
"""
CSV Data Summarizer - Comprehensive CSV analysis with visualizations
Usage: python3 csv_summarizer.py /path/to/file.csv [--output-dir /path/to/output]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

import os
import csv
import re
from pathlib import Path
from datetime import datetime
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Headless mode for Pi
import matplotlib.pyplot as plt
import seaborn as sns

# ============================================================
# DATA TYPE DETECTION
# ============================================================

DATA_TYPES = {
    'contacts': ['email', 'phone', 'contact', 'name', 'company'],
    'sales': ['revenue', 'sales', 'amount', 'price', 'quantity', 'order', 'product'],
    'financial': ['balance', 'transaction', 'account', 'payment', 'invoice', 'credit', 'debit'],
    'hr': ['employee', 'salary', 'department', 'hire', 'position', 'manager'],
    'customer': ['customer', 'client', 'subscriber', 'member', 'user'],
    'survey': ['response', 'rating', 'score', 'feedback', 'satisfaction', 'question'],
    'logs': ['timestamp', 'log', 'error', 'status', 'request', 'response_time'],
    'inventory': ['stock', 'inventory', 'warehouse', 'sku', 'quantity', 'location'],
    'jobs': ['job', 'vacancy', 'position', 'employer', 'salary', 'location', 'apply'],
}

def detect_data_type(df):
    """Auto-detect the type of data in the CSV"""
    cols_lower = [c.lower() for c in df.columns]
    scores = {}

    for dtype, keywords in DATA_TYPES.items():
        score = sum(1 for kw in keywords for col in cols_lower if kw in col)
        if score > 0:
            scores[dtype] = score

    if scores:
        return max(scores, key=scores.get)
    return 'general'

def detect_column_types(df):
    """Classify each column"""
    col_types = {}
    for col in df.columns:
        col_lower = col.lower()

        # Check by name
        if any(x in col_lower for x in ['email', 'mail']):
            col_types[col] = 'email'
        elif any(x in col_lower for x in ['phone', 'tel', 'mobile']):
            col_types[col] = 'phone'
        elif any(x in col_lower for x in ['date', 'time', 'created', 'updated']):
            col_types[col] = 'datetime'
        elif any(x in col_lower for x in ['price', 'amount', 'revenue', 'salary', 'cost']):
            col_types[col] = 'currency'
        elif any(x in col_lower for x in ['url', 'website', 'link']):
            col_types[col] = 'url'
        elif any(x in col_lower for x in ['country', 'city', 'region', 'location', 'address']):
            col_types[col] = 'location'
        elif df[col].dtype in ['int64', 'float64']:
            col_types[col] = 'numeric'
        else:
            col_types[col] = 'text'

    return col_types

# ============================================================
# SUMMARY STATISTICS
# ============================================================

def basic_stats(df):
    """Generate basic statistics"""
    stats = {
        'rows': len(df),
        'columns': len(df.columns),
        'memory_mb': df.memory_usage(deep=True).sum() / 1024 / 1024,
        'missing_total': df.isnull().sum().sum(),
        'missing_pct': (df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100,
        'duplicate_rows': df.duplicated().sum(),
    }
    return stats

def column_stats(df):
    """Per-column statistics"""
    stats = []
    for col in df.columns:
        col_stat = {
            'column': col,
            'dtype': str(df[col].dtype),
            'non_null': df[col].notna().sum(),
            'null': df[col].isna().sum(),
            'null_pct': (df[col].isna().sum() / len(df)) * 100,
            'unique': df[col].nunique(),
        }

        if df[col].dtype in ['int64', 'float64']:
            col_stat.update({
                'min': df[col].min(),
                'max': df[col].max(),
                'mean': df[col].mean(),
                'median': df[col].median(),
                'std': df[col].std(),
            })
        elif df[col].dtype == 'object':
            col_stat['top_value'] = df[col].value_counts().index[0] if len(df[col].value_counts()) > 0 else None
            col_stat['top_count'] = df[col].value_counts().iloc[0] if len(df[col].value_counts()) > 0 else 0

        stats.append(col_stat)

    return stats

# ============================================================
# CORRELATION ANALYSIS
# ============================================================

def correlation_analysis(df):
    """Analyze correlations between numeric columns"""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if len(numeric_cols) < 2:
        return None

    corr_matrix = df[numeric_cols].corr()

    # Find strong correlations
    strong_corrs = []
    for i, col1 in enumerate(numeric_cols):
        for j, col2 in enumerate(numeric_cols):
            if i < j:
                corr = corr_matrix.loc[col1, col2]
                if abs(corr) > 0.5:
                    strong_corrs.append({
                        'col1': col1,
                        'col2': col2,
                        'correlation': round(corr, 3),
                        'strength': 'strong' if abs(corr) > 0.7 else 'moderate'
                    })

    return {
        'matrix': corr_matrix,
        'strong_correlations': sorted(strong_corrs, key=lambda x: -abs(x['correlation']))
    }

# ============================================================
# DISTRIBUTION ANALYSIS
# ============================================================

def distribution_analysis(df):
    """Analyze distributions of numeric columns"""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    distributions = []

    for col in numeric_cols[:10]:  # Limit to 10 columns
        data = df[col].dropna()
        if len(data) < 10:
            continue

        dist = {
            'column': col,
            'skewness': round(data.skew(), 3),
            'kurtosis': round(data.kurtosis(), 3),
            'quartiles': {
                'q1': data.quantile(0.25),
                'q2': data.quantile(0.50),
                'q3': data.quantile(0.75),
            },
            'iqr': data.quantile(0.75) - data.quantile(0.25),
        }

        # Detect distribution shape
        if abs(dist['skewness']) < 0.5:
            dist['shape'] = 'symmetric'
        elif dist['skewness'] > 0:
            dist['shape'] = 'right-skewed'
        else:
            dist['shape'] = 'left-skewed'

        # Detect outliers (IQR method)
        q1, q3 = dist['quartiles']['q1'], dist['quartiles']['q3']
        iqr = dist['iqr']
        outliers = ((data < q1 - 1.5*iqr) | (data > q3 + 1.5*iqr)).sum()
        dist['outliers'] = int(outliers)

        distributions.append(dist)

    return distributions

# ============================================================
# TREND ANALYSIS
# ============================================================

def trend_analysis(df):
    """Detect trends in time-series data"""
    # Find datetime columns
    date_cols = []
    for col in df.columns:
        if 'date' in col.lower() or 'time' in col.lower():
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                if df[col].notna().sum() > len(df) * 0.5:
                    date_cols.append(col)
            except Exception:
                pass

    if not date_cols:
        return None

    date_col = date_cols[0]
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()[:5]

    if not numeric_cols:
        return None

    trends = []
    df_sorted = df.sort_values(date_col).dropna(subset=[date_col])

    for col in numeric_cols:
        data = df_sorted[col].dropna()
        if len(data) < 10:
            continue

        # Simple trend detection using linear regression
        x = np.arange(len(data))
        slope, intercept = np.polyfit(x, data.values, 1)

        # Calculate trend strength
        y_pred = slope * x + intercept
        ss_res = np.sum((data.values - y_pred) ** 2)
        ss_tot = np.sum((data.values - data.mean()) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        trend = {
            'column': col,
            'date_column': date_col,
            'direction': 'increasing' if slope > 0 else 'decreasing',
            'slope': round(slope, 4),
            'r_squared': round(r_squared, 4),
            'confidence': 'high' if r_squared > 0.7 else 'medium' if r_squared > 0.4 else 'low'
        }
        trends.append(trend)

    return trends

# ============================================================
# VISUALIZATIONS
# ============================================================

def create_visualizations(df, output_dir):
    """Generate visualization charts"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    charts = []

    plt.style.use('seaborn-v0_8-whitegrid')

    # 1. Correlation heatmap
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if len(numeric_cols) >= 2:
        fig, ax = plt.subplots(figsize=(10, 8))
        corr = df[numeric_cols[:15]].corr()  # Limit columns
        sns.heatmap(corr, annot=True, fmt='.2f', cmap='RdYlBu_r', center=0, ax=ax)
        ax.set_title('Correlation Heatmap')
        plt.tight_layout()
        path = os.path.join(output_dir, 'correlation_heatmap.png')
        plt.savefig(path, dpi=100)
        plt.close()
        charts.append(('Correlation Heatmap', path))

    # 2. Distribution histograms
    for i, col in enumerate(numeric_cols[:4]):
        fig, ax = plt.subplots(figsize=(8, 5))
        data = df[col].dropna()
        if len(data) > 0:
            sns.histplot(data, kde=True, ax=ax)
            ax.set_title(f'Distribution: {col}')
            ax.set_xlabel(col)
            plt.tight_layout()
            path = os.path.join(output_dir, f'dist_{i}_{col[:20]}.png')
            plt.savefig(path, dpi=100)
            plt.close()
            charts.append((f'Distribution: {col}', path))

    # 3. Top categories bar chart
    cat_cols = df.select_dtypes(include=['object']).columns.tolist()
    for col in cat_cols[:2]:
        if df[col].nunique() < 50 and df[col].nunique() > 1:
            fig, ax = plt.subplots(figsize=(10, 6))
            top_vals = df[col].value_counts().head(15)
            sns.barplot(x=top_vals.values, y=top_vals.index, ax=ax)
            ax.set_title(f'Top Values: {col}')
            ax.set_xlabel('Count')
            plt.tight_layout()
            path = os.path.join(output_dir, f'bar_{col[:20]}.png')
            plt.savefig(path, dpi=100)
            plt.close()
            charts.append((f'Bar Chart: {col}', path))

    # 4. Missing values chart
    missing = df.isnull().sum()
    missing = missing[missing > 0].sort_values(ascending=False).head(15)
    if len(missing) > 0:
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.barplot(x=missing.values, y=missing.index, ax=ax, palette='Reds_r')
        ax.set_title('Missing Values by Column')
        ax.set_xlabel('Count')
        plt.tight_layout()
        path = os.path.join(output_dir, 'missing_values.png')
        plt.savefig(path, dpi=100)
        plt.close()
        charts.append(('Missing Values', path))

    return charts

# ============================================================
# MAIN SUMMARIZER
# ============================================================

def summarize(csv_path, output_dir=None):
    """Generate comprehensive CSV summary"""
    print(f"\n{'='*70}")
    print(f"CSV DATA SUMMARIZER: {Path(csv_path).name}")
    print(f"{'='*70}\n")

    # Read CSV
    try:
        df = pd.read_csv(csv_path, encoding='utf-8', on_bad_lines='skip')
    except Exception:
        df = pd.read_csv(csv_path, encoding='latin-1', on_bad_lines='skip')

    # Auto-detect data type
    data_type = detect_data_type(df)
    col_types = detect_column_types(df)

    print(f"DATA TYPE DETECTED: {data_type.upper()}")
    print(f"Column types: {dict(Counter(col_types.values()))}\n")

    # Basic stats
    stats = basic_stats(df)
    print(f"BASIC STATISTICS:")
    print(f"  Rows: {stats['rows']:,}")
    print(f"  Columns: {stats['columns']}")
    print(f"  Memory: {stats['memory_mb']:.2f} MB")
    print(f"  Missing values: {stats['missing_total']:,} ({stats['missing_pct']:.1f}%)")
    print(f"  Duplicate rows: {stats['duplicate_rows']:,}")

    # Column stats
    print(f"\nCOLUMN DETAILS:")
    col_stats = column_stats(df)
    for cs in col_stats[:15]:
        null_info = f"{cs['null_pct']:.0f}% null" if cs['null_pct'] > 0 else "complete"
        if 'mean' in cs:
            print(f"  {cs['column']}: {cs['dtype']} | {null_info} | mean={cs['mean']:.2f}, std={cs['std']:.2f}")
        else:
            print(f"  {cs['column']}: {cs['dtype']} | {null_info} | {cs['unique']} unique")

    # Correlation analysis
    print(f"\nCORRELATION ANALYSIS:")
    corr = correlation_analysis(df)
    if corr and corr['strong_correlations']:
        for c in corr['strong_correlations'][:5]:
            print(f"  {c['col1']} <-> {c['col2']}: {c['correlation']} ({c['strength']})")
    else:
        print("  No strong correlations found")

    # Distribution analysis
    print(f"\nDISTRIBUTION ANALYSIS:")
    dists = distribution_analysis(df)
    for d in dists[:5]:
        print(f"  {d['column']}: {d['shape']}, skew={d['skewness']}, outliers={d['outliers']}")

    # Trend analysis
    print(f"\nTREND ANALYSIS:")
    trends = trend_analysis(df)
    if trends:
        for t in trends[:5]:
            print(f"  {t['column']}: {t['direction']} (R²={t['r_squared']}, {t['confidence']} confidence)")
    else:
        print("  No time-series data detected")

    # Generate visualizations
    if output_dir:
        print(f"\nGENERATING VISUALIZATIONS...")
        charts = create_visualizations(df, output_dir)
        for name, path in charts:
            print(f"  Created: {path}")

    # Data-type specific insights
    print(f"\n{data_type.upper()}-SPECIFIC INSIGHTS:")
    if data_type == 'contacts' or data_type == 'jobs':
        email_cols = [c for c in df.columns if 'email' in c.lower()]
        for ec in email_cols:
            emails = df[ec].dropna().str.lower()
            valid = emails.str.match(r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$').sum()
            domains = emails.str.split('@').str[1].value_counts().head(5)
            print(f"  {ec}: {valid}/{len(emails)} valid")
            print(f"    Top domains: {dict(domains)}")

    elif data_type == 'sales' or data_type == 'financial':
        amount_cols = [c for c in df.columns if any(x in c.lower() for x in ['amount', 'price', 'revenue', 'total'])]
        for ac in amount_cols[:2]:
            if df[ac].dtype in ['int64', 'float64']:
                print(f"  {ac}: total={df[ac].sum():,.2f}, avg={df[ac].mean():,.2f}")

    print(f"\n{'='*70}\n")

    return {
        'data_type': data_type,
        'stats': stats,
        'columns': col_stats,
        'correlations': corr,
        'distributions': dists,
        'trends': trends
    }

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: csv_summarizer.py <csv_file> [--output-dir <dir>]")
        sys.exit(1)

    csv_path = sys.argv[1]
    output_dir = None

    if '--output-dir' in sys.argv:
        idx = sys.argv.index('--output-dir')
        output_dir = sys.argv[idx + 1]
    else:
        # Default output dir
        output_dir = f"/tmp/csv_summary_{Path(csv_path).stem}"

    summarize(csv_path, output_dir)
