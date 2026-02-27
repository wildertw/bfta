# Bells Fork Inventory Admin — Wireframe List (v1)

This wireframe list matches the **existing public-site JSON contract**:

```json
{ "lastUpdated": "<ISO>", "vehicles": [ /* Vehicle[] */ ] }
```

…and preserves the vehicle fields your current `inventory-loader.js` expects:

- `vin`, `year`, `make`, `model`, `trim`, `price`, `mileage`, `type`, `description`
- `features[]`, `badge`, `status`, `dateAdded`, `images[]`
- optional: `stockNumber`, `engine`, `drivetrain`, `fuelType`, `mpgCity`, `mpgHighway`

---

## 1) Inventory (List View)

**Purpose:** Manage current inventory (search, filter, edit, delete).

**UI elements**
- Search: year/make/model/vin/stock
- Status filter: All / Available / Draft / Pending / Sold
- Table columns:
  - Photo (first image or placeholder)
  - Vehicle (Year Make Model + Trim)
  - VIN / Stock
  - Miles
  - Price
  - Status badge
  - Actions: Edit / Delete

**Behavior**
- Sort by `dateAdded` (desc)
- Duplicate indicators (VIN collisions) shown during imports

---

## 2) Add / Edit (VIN)

### Step 1: VIN Decode
- VIN input + Decode button
- Validations:
  - exactly 17 chars
  - exclude I/O/Q
- Decoded summary panel:
  - year, make, model, trim, body, drive, fuel

### Step 2: Details Form
- Required:
  - Year, Make, Model, Price, Mileage, Type, Description
- Optional:
  - Trim, Stock #
  - Engine, Transmission, Drivetrain, Fuel Type
  - MPG City/Highway
  - Exterior/Interior Color
  - Features (comma list)
  - Badge
  - Status (Available/Draft/Pending/Sold)
  - Date Added
  - Images[] (stored as filenames or URLs)

### Live Preview (right rail)
- A card preview approximating the public inventory display

**Behavior**
- Save commits a vehicle record
- Audit trail entry is written

---

## 3) Bulk VIN

**Purpose:** Paste a list of VINs → batch decode → review results → add as drafts.

**UI elements**
- Textarea for VINs (one per line)
- Decode button
- Progress bar + counts (ok/dup/errors)
- Results table:
  - checkbox
  - VIN
  - Year
  - Make
  - Model
  - Type
  - Status (OK / DUPLICATE / ERROR)

**Behavior**
- Invalid VINs are flagged before decode
- Uses NHTSA batch decode endpoint for speed
- “Add checked” imports records as **Draft** by default

---

## 4) CSV Import

**Purpose:** Import 100s/1000s of vehicles safely with mapping + progress.

**UI elements**
- CSV upload
- Mapping builder:
  - dropdown per target field (VIN/Year/Make/Model/Price/etc.)
  - auto-suggestions based on header synonyms
- Preview grid (first N rows mapped)
- Progress bar (bytes processed)
- Error summary + download error report CSV

**Behavior**
- Parses in chunks (stream-like) to handle large files
- Validates VIN per row
- Duplicate VIN updates existing by default (configurable in production)
- Imports as Draft by default

---

## 5) Audit Log

**Purpose:** Full traceability of inventory changes.

**UI elements**
- Table:
  - When
  - Action (create/update/delete/import/export)
  - Vehicle label
  - VIN / Stock
  - By

**Behavior**
- Filterable in production (by entity, user, timeframe)

---

## Production note

This wireframe list is UI-only. The **production** system should use:

- Auth + RBAC
- DB-backed vehicles + audit
- Import jobs with staging + commit

See `inventory-api.openapi.yaml` and `inventory-schema.postgres.sql` for the backend contract.
