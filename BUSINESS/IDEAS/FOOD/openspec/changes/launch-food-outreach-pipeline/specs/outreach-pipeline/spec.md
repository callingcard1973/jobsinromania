# Outreach Pipeline Specification

## Purpose

This specification defines how the FOOD workspace SHALL move from strategy documents into a first controlled buyer-outreach workflow.

## Requirements

### Requirement: Workspace Roles Must Stay Explicit

The system MUST define which workspace owns supply, aggregation, buyer intelligence, and outreach execution so the first outreach wave is assembled without role confusion.

#### Scenario: Assigning responsibilities for the first outreach wave

- GIVEN the FOOD workspace contains `PRODUSMONTAN`, `COOPERATIVA BUSINESS`, `ZAI_SUPERMARKETS`, `SUPERMARKETS_CLAUDE`, and outreach planning documents
- WHEN the first outreach pipeline is prepared
- THEN `PRODUSMONTAN` SHALL be treated as the supply source
- AND the cooperative materials SHALL be treated as the contracting and invoicing wrapper
- AND `ZAI_SUPERMARKETS` SHALL be treated as the commercial list-packaging layer
- AND `SUPERMARKETS_CLAUDE` SHALL be treated as the enrichment and market-intelligence layer

#### Scenario: Avoiding codebase-role overlap during execution planning

- GIVEN multiple supermarket-related workspaces exist
- WHEN an execution task references buyer data or campaign preparation
- THEN the workflow MUST state which workspace is authoritative for that task
- AND the workflow MUST NOT require blind script merging between supermarket workspaces

### Requirement: Seller Readiness Must Gate Buyer Outreach

The system MUST require seller readiness validation before a buyer wave is considered ready to send.

#### Scenario: Seller pack is ready for outreach

- GIVEN a first-wave seller list exists
- WHEN the outreach pack is marked ready
- THEN each selected seller MUST have current availability, pricing, packaging format, shelf-life, and invoice readiness recorded
- AND cold-chain products SHALL be excluded unless logistics readiness is confirmed

#### Scenario: Buyer outreach is blocked by missing seller data

- GIVEN one or more selected sellers do not have readiness details confirmed
- WHEN a user attempts to finalize the buyer outreach wave
- THEN the workflow SHALL mark the pack incomplete
- AND the missing seller data SHALL be listed as a prerequisite

### Requirement: Buyer Outreach Pack Must Be Complete

The system MUST define a minimum asset set for the first outreach wave.

#### Scenario: Building a valid buyer outreach pack

- GIVEN the workspace is preparing the first buyer wave
- WHEN the pack is finalized
- THEN it MUST include a cooperative presentation
- AND it MUST include a seller sheet
- AND it MUST include a SKU and indicative pricing sheet
- AND it MUST include a delivery coverage note
- AND it MUST include a compliance checklist
- AND it MUST include at least one outreach email and one buyer brief

#### Scenario: Missing outreach asset

- GIVEN one of the required outreach assets is absent
- WHEN the pack is reviewed
- THEN the workflow SHALL report the missing asset
- AND the pack SHALL remain not ready

### Requirement: Buyer Waves Must Follow Execution Order

The system SHOULD sequence buyer outreach by operational difficulty and expected learning value.

#### Scenario: Running the first outreach wave

- GIVEN wholesale, retail, and alternative-channel buyer groups are defined
- WHEN the first live sequence is planned
- THEN wholesale-first targets SHALL be prioritized before national retail-chain outreach
- AND retail outreach SHALL follow after feedback from the wholesale wave is incorporated
- AND alternative channels MAY be used in parallel to secure earlier pilot orders

#### Scenario: Using response feedback to refine the offer

- GIVEN a first buyer wave has generated responses
- WHEN the second wave is prepared
- THEN pricing, pack sizes, and paperwork notes SHOULD be updated based on the response feedback

### Requirement: Source Of Truth Must Remain On Raspibig

The system MUST keep the authoritative outreach workflow artifacts on raspibig.

#### Scenario: Updating change artifacts

- GIVEN local and remote copies of the FOOD workspace exist
- WHEN SDD artifacts or outreach documents are created or updated
- THEN the corresponding files MUST be synced to `/opt/ACTIVE/FOOD`
- AND the remote copies SHALL be treated as authoritative for continuation work

#### Scenario: Remote verification after artifact creation

- GIVEN a new outreach artifact has been added locally
- WHEN synchronization completes
- THEN the artifact SHALL be verified on raspibig before the change is considered current