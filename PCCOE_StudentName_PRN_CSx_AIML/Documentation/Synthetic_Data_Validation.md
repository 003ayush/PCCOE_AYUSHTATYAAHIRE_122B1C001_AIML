# Data Provenance and Validation Report

> **Read this before citing the data.** Fields copied word-for-word from UN R155 must be
> distinguished from fields mapped by us. In reports, label `stride_category` and
> `typical_assets` as **"mapped by us"**, never as regulation content.

## 1. Source of the threat library

- **Regulation:** UN Regulation No. 155, as published in the Official Journal of the
  European Union L 82, 9.3.2021 (CELEX 42021X0387), fetched from EUR-Lex. (The UNECE
  PDF copy returned HTTP 403 and was not used.)
- **Generator:** `Code/scripts/build_threat_library.py` writes
  `Input_Data/threat_library.json`. Re-run it if the source data changes; its output
  is deterministic (60 records, verified by re-run).
- **Record count:** 60 threats, IDs `THREAT-001`–`THREAT-060` (sequential, no gaps).

## 2. What comes from the regulation, word for word

| Field | Source |
|---|---|
| Threat text (`title` = high-level threat, `description` = sub-level text) | Annex 5, Part A, Table A1 |
| `un_r155_reference` (e.g. `Annex 5, Part A, Table A1, ref 12.1`) | Exact Table A1 numbering |
| `standard_mitigations` (M1–M24 wording) | Annex 5, Parts B and C |

Note: the `M` table in the build script has no `M17` entry. This is currently harmless
— no selected threat references M17 — but if a future threat needs M17, its official
wording must be added first.

## 3. What was mapped by us (reviewer: check these)

| Field | Basis | Status |
|---|---|---|
| `stride_category` | Annex 5 does not use STRIDE; tagged by our judgement | Needs review |
| `typical_assets` | Linked to `asset_catalogue.json` names by our judgement | Needs review |

Mix: Tampering 22, Information Disclosure 12, Elevation of Privilege 10, Spoofing 9,
Denial of Service 5, Repudiation 2. All tags are valid STRIDE categories and every
`typical_assets` name resolves against the 12-asset catalogue (checked by script —
no dangling references).

## 4. What was deliberately left out (TCU out of scope)

- Vehicle-to-vehicle communication: refs 4.2, 8.2, 11.2.
- EV charging: ref 25.2.
- Physical loss of data: the 30.x refs.
- Back-end server-side threats: refs 1.3, 3.1, 3.4 (a TCU-side analysis; server
  threats belong to a back-end TARA, not this one).
- Parent 14 has no sub-refs in the file, and ref 22.1 is absent — confirm against
  Table A1 whether these exist and were intentionally excluded.

Verified by script: none of the excluded refs appear in the file.

## 5. Earlier files changed (breaking change)

- The original 5 threats (and the 20 drafted ones) are gone. **The old `THREAT-001`–
  `THREAT-005` IDs now point to different threats** (refs 1.1, 1.2, 2.1, 3.2, 3.3).
  Anything recorded against the old IDs (notes, approvals, test fixtures) is stale.
- `asset_catalogue.json` expanded from 4 to 12 assets (`ASSET-05`–`ASSET-12` are
  synthetic additions: Security Event Logs, Boot Configuration and Root of Trust,
  Personal Data, Diagnostic Interface, Remote Command Channel, Cellular Connectivity
  Service, Positioning Data (GNSS), Stored Application Software). Review them against
  the TCU design. Schema note: `ASSET-05` uses `Non-repudiation`, which has been added
  to the `SecurityProperty` enum in `app/schemas.py` to match.
- `tcu_architecture.json` extended with synthetic components C-06 (External Flash),
  C-07 (SIM/eSIM), C-08 (Bluetooth/Wi-Fi) and interfaces I-06 (OBD-II Diagnostics),
  I-07 (GNSS Antenna Link), I-08 (MCU–Flash QSPI), I-09 (Short-range Wireless).
  Validated: the full 8-component / 9-interface file passes `Architecture` schema
  validation, and the 60-record library loads through the RAG `load_records` path.
