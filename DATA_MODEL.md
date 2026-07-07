# DoorLedger — Data Model

Companion to [`SPEC.md`](SPEC.md). Every persisted entity, its fields, types, and relationships.

## 1. Store choice: SwiftData

SwiftData over Core Data, because every factor that favors Core Data is absent here:

- **Targeting current iOS only** — no need for the older deployment targets that keep projects on Core Data.
- **Small, stable schema** (9 entities, no exotic migrations planned) — well inside SwiftData's comfort zone; lightweight migration via `VersionedSchema` covers foreseeable changes.
- **Pure SwiftUI app** — `@Query`/`@Model` integration removes a whole layer of `NSFetchedResultsController` plumbing.
- **No CloudKit sync in v1 or planned**, so Core Data's more mature sync story buys nothing.

Escape hatch: SwiftData sits on Core Data storage, so a future drop to Core Data (if some limitation bites) is a code migration, not a data migration.

Conventions used below:

- All entities get `id: UUID` (`@Attribute(.unique)`) and `createdAt: Date`.
- Money is always `Decimal`. Never `Double`.
- Rent periods are `(year: Int, month: Int)` — calendar-safe, timezone-proof.
- Images are `Data` with `@Attribute(.externalStorage)` (SwiftData keeps large blobs as files transparently).
- Enums are `String`-raw-value `Codable` enums (readable in exports and debuggers, safe to extend).
- Delete rules: `.cascade` parent→child unless stated; children hold the inverse reference.

---

## 2. Entity diagram

```
Property 1 ──< Unit 1 ──< Lease >── 1 Tenant
                │           │
                │           ├──< RentPeriod 1 ──< RentPayment
                │           └──< DeductionItem        (deposit worksheet)
                │
                ├──< MaintenanceRecord 1 ──< MaintenancePhoto
                │           │ 0..1
                │           └────────── 0..1 Expense
                └──< Expense (unit optional → property-level "shared")
Property 1 ──< Expense
AppSettings (singleton)
```

---

## 3. Entities

### 3.1 `Property`

A building/parcel. Most users will have 1–3; a duplex is one Property with two Units.

| Field | Type | Notes |
|---|---|---|
| `id` | `UUID` | unique |
| `nickname` | `String` | "Maple St duplex" |
| `addressLine1` | `String` | |
| `addressLine2` | `String?` | |
| `city` | `String` | |
| `state` | `String` | free text (works outside the US) |
| `postalCode` | `String` | |
| `notes` | `String` | default `""` |
| `createdAt` | `Date` | |

Relationships: `units: [Unit]` (cascade), `expenses: [Expense]` (cascade; includes both unit-level and shared).

### 3.2 `Unit`

A rentable unit. **v1 cap: 3 Units total across all Properties** (enforced at creation, independent of entitlement). The *free unit* is the Unit with the earliest `createdAt` — computed, never stored.

| Field | Type | Notes |
|---|---|---|
| `id` | `UUID` | |
| `label` | `String` | "Unit A", "Main house" |
| `bedrooms` | `Int?` | |
| `bathrooms` | `Double?` | 1.5 baths |
| `squareFeet` | `Int?` | |
| `notes` | `String` | default `""` |
| `sortOrder` | `Int` | display order |
| `createdAt` | `Date` | free-unit identity + tiebreak by `id` |
| `property` | `Property` | inverse of `Property.units` |

Relationships: `leases: [Lease]` (cascade), `maintenanceRecords: [MaintenanceRecord]` (cascade), `expenses: [Expense]` (nullify — an Expense may outlive a deleted Unit as a shared expense? **No:** unit deletion cascades per SPEC §3.6 warning; rule is cascade).

### 3.3 `Tenant`

Minimal person record; exists so a returning tenant or one person renting two units isn't duplicated.

| Field | Type | Notes |
|---|---|---|
| `id` | `UUID` | |
| `fullName` | `String` | |
| `phone` | `String?` | |
| `email` | `String?` | |
| `notes` | `String` | co-occupants, emergency contact, etc. |
| `createdAt` | `Date` | |

Relationships: `leases: [Lease]` (deny delete while leases exist; UI offers no hard tenant delete, only via lease history cleanup).

### 3.4 `Lease`

The tenancy agreement for a Unit. Turnover = end the old Lease, create a new one; history is kept forever (SPEC §3.7). Also carries the deposit and reminder configuration, since both are per-tenancy.

| Field | Type | Notes |
|---|---|---|
| `id` | `UUID` | |
| `startDate` | `Date` | |
| `endDate` | `Date?` | `nil` = month-to-month |
| `moveOutDate` | `Date?` | set on actual move-out; non-nil ⇒ lease *ended* |
| `monthlyRent` | `Decimal` | default due for each new RentPeriod |
| `rentDueDay` | `Int` | 1–28, or `31` meaning "last day of month" |
| `graceDays` | `Int` | default 0; late = past dueDay + grace with balance > 0 |
| `lastRentIncreaseDate` | `Date?` | `nil` ⇒ rent-raise anniversary keys off `startDate` |
| **Deposit** | | |
| `depositAmount` | `Decimal` | `0` if none |
| `depositReceivedDate` | `Date?` | |
| `depositLocation` | `String?` | "Chase savings …1234" |
| `refundIssuedDate` | `Date?` | move-out settlement |
| `refundIssuedAmount` | `Decimal?` | actual amount returned (suggested value is computed: deposit − Σ deductions) |
| **Reminders** | | |
| `renewalReminderEnabled` | `Bool` | default false |
| `renewalReminderLeadDays` | `Int` | 30/60/90, default 60 |
| `rentRaiseReminderEnabled` | `Bool` | default false |
| `rentRaiseReminderLeadDays` | `Int` | default 30 |
| `scheduledNotificationIDs` | `[String]` | UNUserNotificationCenter ids, for cancel/reschedule |
| `notes` | `String` | default `""` |
| `createdAt` | `Date` | |
| `unit` | `Unit` | inverse of `Unit.leases` |
| `tenant` | `Tenant?` | optional so a lease shell can exist before tenant details are entered |

Relationships: `rentPeriods: [RentPeriod]` (cascade), `deductions: [DeductionItem]` (cascade).

Derived (not stored): `isActive` (`moveOutDate == nil && (endDate == nil || endDate >= today)`), `refundDue` (`depositAmount − Σ deductions`).

### 3.5 `RentPeriod`

One unit-month of rent under a lease. Created lazily on first view or first payment of that month (SPEC §3.3). Unique per `(lease, year, month)` — enforced in the creation path (SwiftData lacks compound unique constraints).

| Field | Type | Notes |
|---|---|---|
| `id` | `UUID` | |
| `year` | `Int` | e.g. 2026 |
| `month` | `Int` | 1–12 |
| `amountDue` | `Decimal` | seeded from `lease.monthlyRent`; editable (proration, discounts) |
| `note` | `String` | default `""` ("waived $50 — mower repair") |
| `createdAt` | `Date` | |
| `lease` | `Lease` | inverse of `Lease.rentPeriods` |

Relationships: `payments: [RentPayment]` (cascade).

Derived (not stored — always recomputed so it can never go stale): `amountPaid` (Σ payments), `balance`, `status`:

```swift
enum RentStatus { case paid, due, late, partial, partialLate }
// paid:    balance <= 0
// due:     balance > 0, today <= dueDate + graceDays, no payments
// partial: balance > 0, today <= dueDate + graceDays, some payments
// late / partialLate: same split, past dueDate + graceDays
```

`dueDate` is computed from `(year, month, lease.rentDueDay)`.

### 3.6 `RentPayment`

A single payment event. Multiple per period supported.

| Field | Type | Notes |
|---|---|---|
| `id` | `UUID` | |
| `amount` | `Decimal` | > 0 |
| `dateReceived` | `Date` | defaults to today; **this date, not the period, buckets income into a tax year** |
| `note` | `String` | default `""` ("check #204") |
| `createdAt` | `Date` | |
| `period` | `RentPeriod` | inverse of `RentPeriod.payments` |

### 3.7 `Expense`

A deductible cost. Belongs to a Property; optionally pinned to a Unit (`unit == nil` ⇒ property-level "shared" expense, reported in its own section of exports).

| Field | Type | Notes |
|---|---|---|
| `id` | `UUID` | |
| `date` | `Date` | buckets the expense into a tax year |
| `amount` | `Decimal` | > 0 |
| `category` | `ExpenseCategory` | see enum below |
| `vendor` | `String?` | |
| `note` | `String` | default `""` |
| `receiptImageData` | `Data?` | `@Attribute(.externalStorage)`; one receipt per expense; **capturing it is the Pro gate**, viewing never is |
| `createdAt` | `Date` | |
| `property` | `Property` | inverse of `Property.expenses` |
| `unit` | `Unit?` | inverse of `Unit.expenses`; nil = shared |
| `maintenanceRecord` | `MaintenanceRecord?` | back-link when auto-created from a maintenance record (nullify on either side's delete) |

```swift
enum ExpenseCategory: String, CaseIterable, Codable {
    case advertising, cleaningMaintenance, insurance, legalProfessional,
         managementFees, mortgageInterest, repairs, supplies, taxes,
         utilities, travel, other
}
// Mirrors IRS Schedule E expense lines so the PDF summary maps 1:1.
```

### 3.8 `MaintenanceRecord`

An issue/work item on a Unit. Its `cost` is informational; money enters tax export **only** via the optional linked Expense (created by the "Also log as expense" toggle, SPEC §3.5) — never both, so nothing double-counts.

| Field | Type | Notes |
|---|---|---|
| `id` | `UUID` | |
| `title` | `String` | "Water heater leaking" |
| `detail` | `String` | default `""` |
| `vendorName` | `String?` | |
| `vendorPhone` | `String?` | |
| `cost` | `Decimal?` | |
| `dateReported` | `Date` | default today |
| `dateCompleted` | `Date?` | non-nil ⇒ status Completed (status is derived, not stored) |
| `createdAt` | `Date` | |
| `unit` | `Unit` | inverse of `Unit.maintenanceRecords` |
| `linkedExpense` | `Expense?` | inverse of `Expense.maintenanceRecord`; nullify |

Relationships: `photos: [MaintenancePhoto]` (cascade). Maintenance photos are **not** Pro-gated.

### 3.9 `MaintenancePhoto`

| Field | Type | Notes |
|---|---|---|
| `id` | `UUID` | |
| `imageData` | `Data` | `@Attribute(.externalStorage)` |
| `createdAt` | `Date` | |
| `record` | `MaintenanceRecord` | inverse of `MaintenanceRecord.photos` |

### 3.10 `DeductionItem`

One line of the move-out deposit worksheet (SPEC §3.7).

| Field | Type | Notes |
|---|---|---|
| `id` | `UUID` | |
| `label` | `String` | "Carpet cleaning" |
| `category` | `DeductionCategory` | `.cleaning / .damage / .unpaidRent / .other` |
| `amount` | `Decimal` | > 0 |
| `note` | `String` | default `""` |
| `createdAt` | `Date` | |
| `lease` | `Lease` | inverse of `Lease.deductions` |

### 3.11 `AppSettings` (singleton)

Exactly one row, created on first launch.

| Field | Type | Notes |
|---|---|---|
| `id` | `UUID` | |
| `firstLaunchDate` | `Date` | trial anchor; **also mirrored to `UserDefaults`** — reads take the *earlier* of the two so a reinstall-restore can't reset the trial |
| `currencyCode` | `String` | default from device locale ("USD") — formatting only |
| `ownerDisplayName` | `String?` | printed on PDF headers |
| `defaultRenewalLeadDays` | `Int` | default 60; seed for new leases |
| `createdAt` | `Date` | |

---

## 4. What is deliberately *not* persisted

| Not stored | Why |
|---|---|
| Rent status (`paid/partial/late`) | derived from payments + due date; can never go stale |
| Free-unit designation | computed from earliest `Unit.createdAt`; can't drift |
| `isPro` / `isInTrial` | computed in `EntitlementService` from `firstLaunchDate` (+ StoreKit later); v1 stub always unlocked |
| Refund due | computed `depositAmount − Σ deductions`; only the *actually issued* refund is recorded |
| Maintenance status | derived from `dateCompleted` |
| Trial/purchase receipts, accounts, tokens | no accounts, no network — nothing exists to store |

## 5. Integrity rules (enforced in code, since SwiftData can't)

1. Max **3 Units** app-wide; max **1 active Lease** per Unit at a time.
2. One `RentPeriod` per `(lease, year, month)` — creation goes through a single fetch-or-create helper.
3. `RentPayment.amount`, `Expense.amount`, `DeductionItem.amount` > 0.
4. A `RentPeriod` may not be created outside its lease's `[startDate, moveOutDate ?? endDate ?? ∞)` month range.
5. Deleting a `MaintenanceRecord` or its linked `Expense` nullifies the link but never cascades across it (the expense is real spend even if the work item is deleted, and vice versa).
6. `Lease.moveOutDate` requires the lease to have a `startDate ≤ moveOutDate`; setting it prompts the move-out worksheet flow but never blocks.
