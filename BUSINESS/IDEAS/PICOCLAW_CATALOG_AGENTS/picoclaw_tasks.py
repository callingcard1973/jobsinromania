#!/usr/bin/env python3
"""
Plugin PicoClaw: task types pentru Agent 3 (Catalog) si Agent 5 (Data Quality).
Pune in /opt/ACTIVE/INFRA/GOVERNOR/tasks/ si PicoClaw le incarca automat.
"""

PLUGIN_TASK_TYPES = ["catalog_update", "data_quality_check"]

TASK_SCHEMAS = {
    "catalog_update": {
        "description": "Regenereaza cataloage HTML angajatori pe 9 domenii x 20 tari din PostgreSQL. Deploy pe A2 Hosting.",
        "payload": {
            "domains": "lista domenii (optional, default=toate 9)",
            "deploy": "true/false — deploy pe A2 dupa generare (default=false)",
        },
        "example": {"domains": ["factoryjobs.eu", "buildjobs.eu"], "deploy": False},
        "script": "/opt/ACTIVE/WEB/CATALOGS/generate_catalogs_raspibig.py",
        "cron": "0 3 * * 0 (duminica 3 AM)",
    },
    "data_quality_check": {
        "description": "Valideaza emailuri, detecteaza duplicate si companii radiate in master_romania_companies.",
        "payload": {
            "table": "tabela de verificat (default=master_romania_companies)",
            "fix": "true/false — aplica corectii sau doar raport (default=false/dry-run)",
        },
        "example": {"table": "master_romania_companies", "fix": False},
        "script": "/opt/ACTIVE/AGENTS/agent_data_quality.py",
        "cron": "0 4 * * 6 (sambata 4 AM)",
    },
}


def handle_catalog_update(payload, llm_client=None):
    """Handler PicoClaw: ruleaza catalog generator."""
    import subprocess
    script = "/opt/ACTIVE/WEB/CATALOGS/generate_catalogs_raspibig.py"
    result = subprocess.run(
        ["python3", script],
        capture_output=True, text=True, timeout=600,
        cwd="/opt/ACTIVE/WEB/CATALOGS"
    )
    return {
        "status": "success" if result.returncode == 0 else "error",
        "stdout": result.stdout[-2000:],  # ultimele 2000 caractere
        "stderr": result.stderr[-500:] if result.stderr else None,
    }


def handle_data_quality_check(payload, llm_client=None):
    """Handler PicoClaw: ruleaza data quality check."""
    import subprocess
    table = payload.get("table", "master_romania_companies")
    fix = payload.get("fix", False)
    args = ["python3", "/opt/ACTIVE/AGENTS/agent_data_quality.py", "--table", table]
    if fix:
        args.append("--fix")
    else:
        args.append("--dry-run")

    result = subprocess.run(args, capture_output=True, text=True, timeout=300)
    return {
        "status": "success" if result.returncode == 0 else "error",
        "stdout": result.stdout[-2000:],
        "stderr": result.stderr[-500:] if result.stderr else None,
    }


TASK_REGISTRY = {
    "catalog_update": handle_catalog_update,
    "data_quality_check": handle_data_quality_check,
}
