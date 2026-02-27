# Bells Fork Inventory Management — Drop-in Technical Spec

## Goal

Upgrade the dealership website’s inventory management while **keeping the current public-site contract unchanged**:

- Public pages load `inventory.json`
- `inventory.json` shape stays:

```json
{
  "lastUpdated": "2026-02-26T00:39:42.377Z",
  "vehicles": [ /* Vehicle[] */ ]
}
```

## Vehicle JSON contract (must remain compatible)

### Required for public display
These are the fields your public inventory grid expects to exist and/or behave safely:

- `vin` (string, 17)
- `year` (number)
- `make` (string)
- `model` (string)
- `price` (number)
- `mileage` (number)
- `type` (string: car|truck|suv|diesel|van)
- `description` (string)

### Optional
- `trim` (string)
- `stockNumber` (string)
- `exteriorColor` / `interiorColor` (string)
- `transmission` (string)
- `engine` / `drivetrain` / `fuelType` (string)
- `mpgCity` / `mpgHighway` (number)
- `features` (string[])
- `badge` (string)
- `status` (available|draft|pending|sold|disabled)
- `dateAdded` (ISO datetime)
- `images` (string[])  // filenames or URLs

## VIN decoding (recommended provider strategy)

### Baseline (free)
- **NHTSA vPIC**: reliable for basic Year/Make/Model/Body/Drive/Fuel

### Enrichment (paid)
- **DataOne** or **MarketCheck** for richer option packages, trims, and normalized equipment.

### Bulk VIN
- Use NHTSA’s batch endpoint (`DecodeVINValuesBatch`) for speed and cost control.

## Bulk + CSV imports

### Import pipeline (production)
1. Upload VINs/CSV
2. Parse + validate → staging tables
3. Detect duplicates
4. Admin review + edits
5. Commit
6. Publish `inventory.json` snapshot

This is represented by:
- `import_jobs`, `staging_vehicles`, `import_job_items` in the SQL DDL
- `/imports/*` endpoints in the OpenAPI spec

## Files in this deliverable

- `admin.html` — local admin demo UI (no backend)
- `vehicle-manager.js` — admin logic (VIN decode, bulk VIN, CSV mapping/import, edit, export)
- `inventory-api.openapi.yaml` — OpenAPI outline for production API
- `inventory-schema.postgres.sql` — Postgres schema for production
- `admin-wireframes.md` — screen list + behavior notes

## Security notes (production)

- Do NOT rely on `robots.txt` to protect admin functionality.
- Admin features must be protected by authentication + RBAC.
- CSV uploads require:
  - size limits
  - strict MIME/content checks
  - safe parsing (stream/chunk)
  - sanitization to prevent CSV injection when exporting.

