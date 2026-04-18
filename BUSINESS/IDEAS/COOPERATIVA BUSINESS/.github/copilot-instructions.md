# Project Guidelines — Gospodarii de Altadata Cooperativa Agricola

This repository contains business planning, legal contracts, and operational documentation for **Gospodarii de Altadata Cooperativa Agricola** (CUI 51957925, registered 12.06.2025). No compiled code—focus is on member agreements, contracts, and governance documents.

## Context

- **Cooperative Purpose**: Integrate small agricultural producers (~680+ from PROs MONTAN registry) into modern supply chains under the "Gospodarii de Altadata" brand
- **Service Model**: Members sign adeziune (adhesion), declaratie PF (personal statement), contract de asociere (3-year partnership), and contract cooperativ (services agreement)
- **Related Projects**: See `../PRODUS MONTAN/` and `../TRASABILITATE PRODUS ALIMENTAR/` for aggregation and traceability strategy

## Code Style

- **Markdown**: Use standard GitHub-flavored Markdown for docs and exports
- **Document Format**: Templates in `TEMPLATE/` use Times New Roman, structured tables for member data
- **Naming**: Maintain numbered prefix pattern (`1.2.Contract...docx`) for document ordering

## Architecture

- **Document Storage**: Active templates in `TEMPLATE/`; archived models in `archive_old/`
- **Member Data Fields**: Name, CUI, production area, planned output, minimum 50% cooperative sale commitment
- **File Organization**: 
  - `TEMPLATE/` — Master copies used for all new members
  - `archive_old/INTER_FRESH/` — Historical INTER FRESH structure (reference only)
  - Root folder — Operational docs (claude.md, README.md describing current state)

## Build and Test

- No build process—documents are edited and versioned via Git
- Validation steps: Review contracts with consiliu (board), collect member signatures, add to registro membri (member registry)

## Project Conventions

- **Document Versioning**: Git tracks `.docx` and exported `.txt` versions; minimize binary edits—prefer Markdown exports when possible
- **Member Workflow**: 
  1. Populate template with member details (CUI, suprafete, plan productie)
  2. Collect signatures (physical + PDF scan)
  3. Archive both copies (paper + digital)
  4. Add entry to electronic registro (planned 2026-Q1)
- **Obligatory References**: All contracts reference Statut (Statute) and ROF (Regulations); both must exist and be enforced
- **Reporting Dependencies**: Members must provide APIA (agricultural agency) data + registrul agricol (farm register) proof

## Integration Points

- **APIA Integration**: Member agricultural data collected for subsidy/grant documentation
- **Related Cooperative Data**: Links to farmer registries in PRODUS MONTAN (produsmontan.ro, RNPM)
- **Traceability System**: Gospodarii de Altadata acts as aggregator for product traceability (EU 178/2002 compliance) — see `../TRASABILITATE PRODUS ALIMENTAR/` for B2B/export requirements

## Security

- **Confidential**: Contains legal contracts, member names, CUI numbers, and financial commitments
- **Repository Access**: Treat as private; redact member personal data before external sharing
- **Compliance**: Documents reflect Romanian cooperative law (Law 566/2004) and agricultural regulations

## Quick References

- **Cooperative Details**: CUI 51957925, Sat Crețești, Str. Principala 157, jud. Ilfov, cod 077186 (founded 12.06.2025)
- **Documents Last Updated**: 2025-03-08 (see claude.md for current operational phase)
- **Key Phase**: Q1 2026 validation with consiliu, signature collection, registry setup
