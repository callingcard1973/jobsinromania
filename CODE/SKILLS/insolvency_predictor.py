#!/usr/bin/env python3
"""
Insolvency Predictor Skill

Predicts insolvency risk for Romanian companies using ML model
trained on historical insolvency data and ANAF financial indicators.

Usage:
    python3 insolvency_predictor.py --cui 12345678
    python3 insolvency_predictor.py --check-datornici
    python3 insolvency_predictor.py --score-all --limit 1000
    python3 insolvency_predictor.py --train
    python3 insolvency_predictor.py --report
    python3 insolvency_predictor.py --alert --threshold 80

Author: InterJob Team
Location: /opt/ACTIVE/INFRA/SKILLS/insolvency_predictor.py
"""

import os
import sys
import json
import pickle
import logging
from pathlib import Path
from datetime import datetime, date
from typing import Optional, Dict, List, Any, Tuple

# Add shared code path
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
sys.path.insert(0, '/opt/ACTIVE/INSOLVENTA/scripts')

from skills_common import to_ascii, sanitize

# Config
BASE_DIR = Path('/opt/ACTIVE/INSOLVENTA')
MODELS_DIR = BASE_DIR / 'models'
OUTPUT_DIR = BASE_DIR / 'output'
DATA_DIR = BASE_DIR / 'data'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
log = logging.getLogger(__name__)


# ============================================================
# ANAF API Functions (simplified, inline)
# ============================================================

ANAF_API_URL = "https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva"

def fetch_anaf_info(cui_list: List[str]) -> List[Dict]:
    """Fetch basic company info from ANAF TVA API."""
    import requests

    results = []

    for i in range(0, len(cui_list), 500):
        batch = cui_list[i:i+500]
        payload = [{"cui": int(cui), "data": date.today().strftime("%Y-%m-%d")}
                   for cui in batch if cui.isdigit()]

        try:
            resp = requests.post(ANAF_API_URL, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            for item in data.get('found', []):
                general = item.get('date_generale', {})
                tva = item.get('inregistrare_scop_Tva', {})

                results.append({
                    'cui': str(general.get('cui', '')),
                    'denumire': to_ascii(general.get('denumire', '')),
                    'adresa': to_ascii(general.get('adresa', '')),
                    'stare': general.get('stare_inregistrare', ''),
                    'data_inregistrare': general.get('data_inregistrare', ''),
                    'platitor_tva': 'DA' if tva.get('scpTVA', False) else 'NU',
                    'data_tva_end': tva.get('data_sfarsit_ScpTVA', ''),
                })

        except Exception as e:
            log.warning(f"ANAF API error: {e}")

    return results


# ============================================================
# Feature Calculation (inline)
# ============================================================

SECTOR_RISK = {
    '41': 0.8, '42': 0.7, '43': 0.75, '55': 0.7, '56': 0.8, '47': 0.6,
    '46': 0.5, '49': 0.5, '10': 0.5, '25': 0.5,
    '62': 0.3, '86': 0.2, '85': 0.2, '64': 0.3,
}

JUDET_RISK = {
    'B': 0.7, 'CJ': 0.4, 'TM': 0.4, 'CT': 0.5, 'IS': 0.5, 'BV': 0.4,
}

# ============================================================
# SOE (State-Owned Enterprise) Detection
# ============================================================

SOE_PATTERNS = [
    'regie autonoma', 'companie nationala', 'societate nationala',
    'administratia nationala', 'autoritatea', 'cnair', 'transgaz',
    'transelectrica', 'hidroelectrica', 'nuclearelectrica', 'romgaz',
    'posta romana', 'cfr', 'metrorex', 'tarom', 'aeroporturi',
    'complexul energetic', 'termoelectrica', 'electrocentrale',
]


def is_state_company(name: str) -> bool:
    """Detect if company is state-owned enterprise based on name patterns."""
    if not name:
        return False
    name_lower = name.lower()
    for pattern in SOE_PATTERNS:
        if pattern in name_lower:
            return True
    # Check for "RA" suffix (Regie Autonoma)
    if name_lower.strip().endswith(' ra'):
        return True
    # Check for "CN " prefix (Companie Nationala)
    if name_lower.strip().startswith('cn '):
        return True
    return False

def calculate_company_age(data_inregistrare: str) -> int:
    if not data_inregistrare:
        return 10
    try:
        for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y']:
            try:
                reg_date = datetime.strptime(data_inregistrare, fmt)
                return max(0, min((datetime.now() - reg_date).days // 365, 100))
            except ValueError:
                continue
    except:
        pass
    return 10

def extract_judet_from_address(address: str) -> str:
    if not address:
        return ''
    address = address.upper()
    if 'BUCURESTI' in address or 'SECTOR' in address:
        return 'B'
    counties = {
        'CLUJ': 'CJ', 'TIMIS': 'TM', 'CONSTANTA': 'CT', 'IASI': 'IS',
        'BRASOV': 'BV', 'PRAHOVA': 'PH', 'DOLJ': 'DJ', 'ARGES': 'AG',
        'BIHOR': 'BH', 'SIBIU': 'SB', 'ALBA': 'AB', 'MURES': 'MS',
    }
    for name, code in counties.items():
        if name in address:
            return code
    return ''


def build_features(cui: str) -> Optional[Dict]:
    """Build feature dict for a single CUI."""
    import psycopg2

    # Fetch from ANAF
    anaf_data = fetch_anaf_info([cui])
    if not anaf_data:
        return None

    row = anaf_data[0]

    features = {
        'cui': cui,
        'denumire': row.get('denumire', ''),
        'company_age': calculate_company_age(row.get('data_inregistrare', '')),
    }

    features['is_young_company'] = 1 if features['company_age'] < 3 else 0

    stare = str(row.get('stare', '')).upper()
    features['is_active'] = 1 if stare in ['INREGISTRAT', 'ACTIV', ''] else 0
    features['is_radiat'] = 1 if 'RADIAT' in stare else 0

    features['is_platitor_tva'] = 1 if row.get('platitor_tva') == 'DA' else 0
    features['is_split_tva'] = 0
    features['tva_status_changed'] = 1 if row.get('data_tva_end') else 0

    adresa = row.get('adresa', '')
    judet = extract_judet_from_address(adresa)
    features['judet_risk'] = JUDET_RISK.get(judet, 0.45)
    features['is_bucuresti'] = 1 if judet == 'B' else 0

    # Get sector from DB
    try:
        conn = psycopg2.connect(dbname='interjob_master', user='tudor')
        cur = conn.cursor()
        cur.execute("""
            SELECT sector, is_insolvent FROM companies
            WHERE cui = %s AND country = 'RO' LIMIT 1
        """, (cui,))
        result = cur.fetchone()
        conn.close()

        if result:
            sector = result[0] or ''
            features['is_already_insolvent'] = 1 if result[1] else 0
        else:
            sector = ''
            features['is_already_insolvent'] = 0
    except:
        sector = ''
        features['is_already_insolvent'] = 0

    features['sector_risk'] = SECTOR_RISK.get(str(sector)[:2], 0.5)
    features['is_high_risk_sector'] = 1 if str(sector)[:2] in ['41', '42', '43', '55', '56'] else 0

    return features


# ============================================================
# Model Functions
# ============================================================

def load_model(enhanced: bool = False) -> Tuple[Any, list]:
    """Load trained model (basic or enhanced)."""
    if enhanced:
        model_path = MODELS_DIR / 'insolvency_enhanced_xgb.pkl'
        if not model_path.exists():
            log.warning("Enhanced model not found, falling back to basic model")
            enhanced = False

    if not enhanced:
        model_path = MODELS_DIR / 'insolvency_xgb.pkl'

    if not model_path.exists():
        return None, None

    with open(model_path, 'rb') as f:
        data = pickle.load(f)

    if enhanced:
        # Enhanced model saved directly
        return data, None
    else:
        return data['model'], data['feature_names']


def predict_risk(cui: str) -> Optional[Dict]:
    """Predict risk score for a single CUI."""
    import numpy as np

    model, feature_names = load_model()
    if model is None:
        log.error("Model not found. Run --train first.")
        return None

    features = build_features(cui)
    if features is None:
        log.error(f"Could not fetch data for CUI {cui}")
        return None

    # Build feature vector
    X = np.array([[features.get(f, 0) for f in feature_names]])

    # Predict
    prob = model.predict_proba(X)[0][1]
    risk_score = int(prob * 100)

    if risk_score >= 75:
        risk_level = 'CRITICAL'
    elif risk_score >= 50:
        risk_level = 'HIGH'
    elif risk_score >= 25:
        risk_level = 'MEDIUM'
    else:
        risk_level = 'LOW'

    # Top factors
    top_factors = []
    for i, fname in enumerate(feature_names):
        value = features.get(fname, 0)
        if value > 0:
            importance = model.feature_importances_[i]
            impact = value * importance * 25
            top_factors.append((fname, impact, value))

    top_factors.sort(key=lambda x: -x[1])

    return {
        'cui': cui,
        'denumire': features.get('denumire', ''),
        'risk_score': risk_score,
        'risk_level': risk_level,
        'probability': float(prob),
        'top_factors': top_factors[:5],
    }


def get_bilant_data(cui: str) -> Optional[Dict]:
    """Get balance sheet data from database."""
    import psycopg2

    try:
        conn = psycopg2.connect(dbname='interjob_master', user='tudor')
        cur = conn.cursor()
        cur.execute("""
            SELECT year, cifra_afaceri, profit_net, nr_angajati,
                   active_imobilizate, active_circulante, caen
            FROM bilant_years
            WHERE cui = %s
            ORDER BY year DESC
            LIMIT 1
        """, (int(cui),))
        result = cur.fetchone()
        conn.close()

        if result:
            return {
                'year': result[0],
                'cifra_afaceri': result[1] or 0,
                'profit_net': result[2] or 0,
                'nr_angajati': result[3] or 0,
                'active_imobilizate': result[4] or 0,
                'active_circulante': result[5] or 0,
                'caen': result[6] or '',
            }
    except Exception as e:
        log.debug(f"Bilant fetch error: {e}")

    return None


def get_datornici_status(cui: str) -> Dict:
    """Check if company is on ANAF tax debtors list."""
    import psycopg2

    result = {
        'on_list': False,
        'total_obligatii': 0,
        'total_accesorii': 0,
        'tip_contribuabil': '',
        'data_raportare': '',
    }

    try:
        conn = psycopg2.connect(dbname='interjob_master', user='tudor')
        cur = conn.cursor()
        cur.execute("""
            SELECT total_obligatii, total_accesorii, tip_contribuabil, data_raportare
            FROM datornici_anaf
            WHERE cui = %s
            ORDER BY data_raportare DESC
            LIMIT 1
        """, (int(cui),))
        row = cur.fetchone()
        conn.close()

        if row:
            result = {
                'on_list': True,
                'total_obligatii': row[0] or 0,
                'total_accesorii': row[1] or 0,
                'tip_contribuabil': row[2] or '',
                'data_raportare': str(row[3]) if row[3] else '',
            }
    except Exception as e:
        log.debug(f"Datornici fetch error: {e}")

    return result


def get_consecutive_losses(cui: str) -> Dict:
    """Check if company has consecutive years of losses."""
    import psycopg2

    result = {
        'has_consecutive_losses': False,
        'loss_years': [],
        'total_losses': 0,
    }

    try:
        conn = psycopg2.connect(dbname='interjob_master', user='tudor')
        cur = conn.cursor()
        cur.execute("""
            SELECT year, profit_net
            FROM bilant_years
            WHERE cui = %s AND profit_net < 0
            ORDER BY year DESC
            LIMIT 5
        """, (int(cui),))
        rows = cur.fetchall()
        conn.close()

        if len(rows) >= 2:
            years = [r[0] for r in rows]
            # Check for consecutive years (e.g., 2024, 2023)
            if len(years) >= 2 and years[0] - years[1] == 1:
                result['has_consecutive_losses'] = True
                result['loss_years'] = years[:2]
                result['total_losses'] = sum(abs(r[1]) for r in rows[:2])
    except Exception as e:
        log.debug(f"Consecutive losses fetch error: {e}")

    return result


def print_risk_report(result: Dict):
    """Print formatted risk report."""
    print()
    print("=" * 60)
    print(f"RISK SCORE: {result['denumire']} (CUI: {result['cui']})")
    print("=" * 60)
    print()

    # Check if SOE
    is_soe = is_state_company(result.get('denumire', ''))
    if is_soe:
        print("TYPE: State-Owned Enterprise (SOE)")
        print("Note: SOE companies may have implicit government support")
        print()

    print(f"Risk Score: {result['risk_score']}/100 ({result['risk_level']})")
    print(f"Probability: {result['probability']:.2%}")
    print()

    # Check datornici status (ANAF tax debtors list)
    datornici = get_datornici_status(result['cui'])
    if datornici['on_list']:
        print("*** ALERT: ON ANAF TAX DEBTORS LIST ***")
        print(f"  - Total datorii: {datornici['total_obligatii']:,.0f} RON")
        if datornici['total_accesorii']:
            print(f"  - Accesorii:     {datornici['total_accesorii']:,.0f} RON")
        if datornici['tip_contribuabil']:
            print(f"  - Tip contribuabil: {datornici['tip_contribuabil']}")
        if datornici['data_raportare']:
            print(f"  - Data raportare: {datornici['data_raportare']}")
        print()

    # Check consecutive losses
    losses = get_consecutive_losses(result['cui'])
    if losses['has_consecutive_losses']:
        print("*** WARNING: CONSECUTIVE YEARS OF LOSSES ***")
        print(f"  - Loss years: {', '.join(map(str, losses['loss_years']))}")
        print(f"  - Total losses: {losses['total_losses']:,.0f} RON")
        print()

    # Show bilant data if available
    bilant = get_bilant_data(result['cui'])
    if bilant:
        print(f"Financial Data ({bilant['year']}):")
        print(f"  - Cifra afaceri: {bilant['cifra_afaceri']:,.0f} RON")
        print(f"  - Profit net:    {bilant['profit_net']:,.0f} RON")
        print(f"  - Angajati:      {bilant['nr_angajati']}")
        total_assets = bilant['active_imobilizate'] + bilant['active_circulante']
        if total_assets > 0:
            roa = bilant['profit_net'] / total_assets
            print(f"  - ROA:           {roa:.2%}")
        print()

    print("Top Risk Factors:")
    for fname, impact, value in result['top_factors']:
        print(f"  - {fname}: {value} (+{impact:.1f} pts)")
    print()

    if result['risk_level'] == 'CRITICAL':
        print("Recommendation: AVOID - very high probability of insolvency")
    elif result['risk_level'] == 'HIGH':
        print("Recommendation: CAUTION - elevated insolvency risk")
    elif result['risk_level'] == 'MEDIUM':
        print("Recommendation: MONITOR - moderate risk factors present")
    else:
        print("Recommendation: OK - low insolvency risk")

    # Additional warnings
    warnings = []
    if datornici['on_list']:
        warnings.append("Tax debts to ANAF indicate cash flow problems")
    if losses['has_consecutive_losses']:
        warnings.append("Consecutive losses indicate structural issues")
    if is_soe:
        warnings.append("SOE status may delay but not prevent insolvency")

    if warnings:
        print()
        print("Additional Notes:")
        for w in warnings:
            print(f"  - {w}")
    print()


# ============================================================
# Commands
# ============================================================

def cmd_check_cui(cui: str, json_output: bool = False):
    """Check risk for single CUI."""
    result = predict_risk(cui)
    if result is None:
        print(f"Could not analyze CUI {cui}")
        return

    if json_output:
        result['top_factors'] = [[f, float(i), float(v)] for f, i, v in result['top_factors']]
        # Add datornici and consecutive losses data
        result['datornici'] = get_datornici_status(cui)
        result['consecutive_losses'] = get_consecutive_losses(cui)
        result['bilant'] = get_bilant_data(cui)
        result['is_soe'] = is_state_company(result.get('denumire', ''))
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_risk_report(result)


def cmd_train():
    """Train or retrain the model."""
    print("Training insolvency prediction model...")

    # Run pipeline
    os.chdir(BASE_DIR / 'scripts')

    # Step 1: Export insolvency data
    print("\n1. Exporting insolvency data...")
    os.system('python3 01_fetch_datornici.py --export-insolvency')

    # Step 2: Fetch ANAF data
    print("\n2. Fetching ANAF data (sample)...")
    os.system('python3 02_fetch_bilant.py --insolvency --limit 5000')
    os.system('python3 02_fetch_bilant.py --companies --limit 10000')

    # Step 3: Build features
    print("\n3. Building feature matrix...")
    os.system('python3 03_build_features.py')

    # Step 4: Train model
    print("\n4. Training XGBoost model...")
    os.system('python3 04_train_model.py')

    print("\nTraining complete!")


def cmd_score_all(limit: int = 1000):
    """Score random companies from database."""
    import psycopg2
    import pandas as pd
    import numpy as np

    model, feature_names = load_model()
    if model is None:
        print("Model not found. Run --train first.")
        return

    print(f"Loading {limit} companies from database...")

    conn = psycopg2.connect(dbname='interjob_master', user='tudor')
    cur = conn.cursor()
    cur.execute("""
        SELECT cui FROM companies
        WHERE country = 'RO' AND cui IS NOT NULL AND cui ~ '^[0-9]+$'
        AND is_insolvent = FALSE
        ORDER BY RANDOM() LIMIT %s
    """, (limit,))
    cuis = [row[0] for row in cur.fetchall()]
    conn.close()

    print(f"Scoring {len(cuis)} companies...")

    results = []
    for i, cui in enumerate(cuis):
        if i % 100 == 0:
            print(f"  Progress: {i}/{len(cuis)}")

        features = build_features(cui)
        if not features:
            continue

        X = np.array([[features.get(f, 0) for f in feature_names]])
        prob = model.predict_proba(X)[0][1]
        risk_score = int(prob * 100)

        results.append({
            'cui': cui,
            'denumire': features.get('denumire', ''),
            'risk_score': risk_score,
            'risk_level': 'CRITICAL' if risk_score >= 75 else 'HIGH' if risk_score >= 50 else 'MEDIUM' if risk_score >= 25 else 'LOW',
        })

    df = pd.DataFrame(results).sort_values('risk_score', ascending=False)

    output_file = OUTPUT_DIR / f"risk_scores_{datetime.now().strftime('%Y%m%d')}.csv"
    df.to_csv(output_file, index=False)

    print(f"\nSaved {len(df)} scores to {output_file}")
    print("\n=== RISK SUMMARY ===")
    print(df['risk_level'].value_counts().to_string())
    print("\nTop 10 highest risk:")
    print(df[['cui', 'denumire', 'risk_score', 'risk_level']].head(10).to_string(index=False))


def cmd_report():
    """Generate top 100 high risk report."""
    output_files = list(OUTPUT_DIR.glob('risk_scores_*.csv'))
    if not output_files:
        print("No risk scores found. Run --score-all first.")
        return

    import pandas as pd

    latest = max(output_files, key=lambda x: x.stat().st_mtime)
    df = pd.read_csv(latest)

    print(f"\n=== RISK REPORT ({latest.name}) ===")
    print(f"Total scored: {len(df)}")
    print(f"\nRisk distribution:")
    print(df['risk_level'].value_counts().to_string())

    high_risk = df[df['risk_score'] >= 50].head(100)
    print(f"\n=== TOP 100 HIGH RISK COMPANIES ===")
    for _, row in high_risk.iterrows():
        print(f"{row['cui']:>12} | {row['risk_score']:>3} | {row['risk_level']:<8} | {row['denumire'][:40]}")


def cmd_alert(threshold: int = 80):
    """Send Telegram alert for high risk companies."""
    try:
        from alerting import send_telegram
    except ImportError:
        print("Alerting module not available")
        return

    import pandas as pd

    output_files = list(OUTPUT_DIR.glob('risk_scores_*.csv'))
    if not output_files:
        print("No risk scores found. Run --score-all first.")
        return

    latest = max(output_files, key=lambda x: x.stat().st_mtime)
    df = pd.read_csv(latest)

    critical = df[df['risk_score'] >= threshold]

    if len(critical) == 0:
        print(f"No companies above threshold {threshold}")
        return

    msg = f"🚨 *INSOLVENCY ALERT*\n\n"
    msg += f"Found {len(critical)} companies with risk >= {threshold}:\n\n"

    for _, row in critical.head(10).iterrows():
        msg += f"• `{row['cui']}` - {row['denumire'][:30]} ({row['risk_score']})\n"

    if len(critical) > 10:
        msg += f"\n_...and {len(critical) - 10} more_"

    send_telegram(msg)
    print(f"Sent alert for {len(critical)} companies")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Insolvency Risk Predictor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 insolvency_predictor.py --cui 12345678
    python3 insolvency_predictor.py --train
    python3 insolvency_predictor.py --score-all --limit 500
    python3 insolvency_predictor.py --report
    python3 insolvency_predictor.py --alert --threshold 80
        """
    )

    parser.add_argument('--cui', type=str, help='Check risk for single CUI')
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    parser.add_argument('--train', action='store_true', help='Train/retrain the model')
    parser.add_argument('--score-all', action='store_true', help='Score random companies from DB')
    parser.add_argument('--limit', type=int, default=1000, help='Limit for --score-all')
    parser.add_argument('--report', action='store_true', help='Show top 100 high risk report')
    parser.add_argument('--alert', action='store_true', help='Send Telegram alert for high risk')
    parser.add_argument('--threshold', type=int, default=80, help='Risk threshold for --alert')
    parser.add_argument('--check-datornici', action='store_true', help='Update debtors list (not implemented - requires CAPTCHA)')

    args = parser.parse_args()

    if args.cui:
        cmd_check_cui(args.cui, args.json)
    elif args.train:
        cmd_train()
    elif args.score_all:
        cmd_score_all(args.limit)
    elif args.report:
        cmd_report()
    elif args.alert:
        cmd_alert(args.threshold)
    elif args.check_datornici:
        print("Datornici ANAF requires manual CAPTCHA solving.")
        print("Use: python3 /opt/ACTIVE/INSOLVENTA/scripts/01_fetch_datornici.py --playwright")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
