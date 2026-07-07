# DoorLedger — v1 Specification

A private, offline-first rent-and-records app for landlords with 1–3 self-managed rental units. It replaces a spreadsheet; it is deliberately **not** a property-management platform.

- **Platform:** Native iOS (current iOS), SwiftUI, SwiftData.
- **Local-first:** All data on-device. No backend, no accounts, no network calls in v1.
- **No integrations:** No payment/ACH, banking, or screening services.
- **Out of scope (v1 and beyond, per product direction):** online rent collection, tenant portals, tenant screening, e-sign, messaging, multi-user, Android, cloud sync.

Companion document: [`DATA_MODEL.md`](DATA_MODEL.md) — entities, fields, relationships.

---

## 1. Product principles

1. **Faster than the spreadsheet.** Recording this month's rent for a unit is at most two taps from launch.
2. **Your data is never hostage.** Nothing the user entered is ever locked, hidden, or deleted by entitlement state. Gating only ever blocks *new* Pro-feature actions.
3. **Boring and trustworthy.** Money values are exact (`Decimal`), history is append-friendly, exports are plain CSV/PDF the user's accountant can open.
4. **Private by construction.** The app makes zero network requests. Photos and records live only in the app's container (included in the user's own device backups).

---

## 2. App structure & navigation

`TabView` with five tabs, each owning its own `NavigationStack`:

| Tab | Icon (SF Symbol) | Purpose |
|---|---|---|
| **Home** | `house` | This-month dashboard: rent status per unit, overdue flags, upcoming reminders |
| **Rent** | `dollarsign.circle` | The rent ledger: month-by-month history and payment recording per unit |
| **Expenses** | `receipt` | Expense log with categories and receipt photos |
| **Maintenance** | `wrench.and.screwdriver` | Maintenance/issue log with vendor, cost, photos |
| **More** | `ellipsis.circle` | Properties & units, tenants & leases, deposits, reminders, tax export, settings |

Sheets are used for all create/edit forms; pushes are used for drill-down (list → detail).

### Screen index

```
Home
Rent
 └─ Rent Ledger (per unit) ── Month Detail ── Record Payment (sheet)
Expenses
 ├─ Add/Edit Expense (sheet, camera capture inside)
 └─ Expense Detail (receipt viewer)
Maintenance
 ├─ Add/Edit Maintenance Record (sheet, photos)
 └─ Maintenance Detail
More
 ├─ Properties & Units ── Property Detail ── Unit Detail (add/edit sheets)
 ├─ Tenants & Leases ── Lease Detail ── Move-Out Worksheet
 ├─ Deposits (all held deposits) ── (jumps into Lease Detail deposit section)
 ├─ Reminders
 ├─ Tax Export
 └─ Settings
Paywall (sheet — stubbed in v1, never shown)
First-launch setup (one-time flow)
```

---

## 3. Screen-by-screen breakdown

### 3.1 First-launch setup (one-time)

Shown only when the store contains no `Property`.

- **Step 1 — Welcome:** one screen stating the pitch ("Your rent ledger, on your phone, nowhere else") and the privacy stance (all data stays on this device).
- **Step 2 — First property & unit:** minimal form — property nickname + address, first unit label, monthly rent, rent due day. Creating this also creates the unit's first `Lease` shell (rent amount + due day; tenant/dates can be filled in later).
- Records `firstLaunchDate` (the trial anchor — see §5) if not already set.
- Notification permission is **not** requested here; it is requested contextually the first time the user enables a reminder (§3.9).

Skippable except for the first property/unit (the app needs at least one unit to be useful; user can add the rest later from More → Properties & Units).

### 3.2 Home (dashboard)

The launch tab. Answers "where do I stand this month?"

- **Rent this month** — one card per unit (max 3): unit label, tenant first name, amount due, amount received, derived status chip (`Paid`, `Due`, `Partial`, `Late`, `Partial · Late`). Tapping a card goes to that unit's **Month Detail** in the Rent tab. Each card has a **Record payment** quick action (subject to gating for units 2–3, §5).
- **Attention** section — only appears when non-empty: overdue rent (past due day + grace), lease renewals inside their reminder lead window, rent-raise anniversaries inside their lead window, open maintenance items older than 14 days. Each row deep-links to the relevant screen.
- **Month switcher** in the nav bar (default: current month) to glance at prior months.
- Empty state (no units): prompt to add a property/unit → pushes into More → Properties & Units flow.

### 3.3 Rent tab — Rent Ledger

- **Unit switcher** at top (segmented control up to 3 units; single unit → no switcher).
- Below: reverse-chronological list of **month rows** for the selected unit's leases: `MMM yyyy · amount due · amount received · status chip`. Months are materialized lazily from the active lease's date range (a `RentPeriod` row is created on first view or first payment of that month).
- Sticky summary header for the selected year: collected / due / outstanding.
- Tapping a month row → **Month Detail**.
- Lease-boundary rows are visually separated (e.g. section header per lease: "Lease — Jane Doe, Mar 2025 – Feb 2026") so history across turnovers stays legible.

**Month Detail**
- Shows amount due (editable — prorated months, agreed discounts), due date, grace days (from lease), derived status, running balance.
- List of payments: date, amount, note. Swipe to delete; tap to edit.
- **Record Payment** button → sheet: amount (pre-filled with remaining balance), date received (default today), optional note. Multiple payments per month are supported; status is always derived, never set by hand.
- Optional per-month note (e.g. "waived $50 for mower repair").

**Gating:** recording/editing payments for the **free unit** (the first-created unit) is free forever. For units 2–3 it is a Pro action after trial (§5).

### 3.4 Expenses tab

- List of expenses, newest first, grouped by month with monthly totals. Each row: category icon, vendor (or category name), unit badge (or "Shared" for property-level), amount, receipt-photo indicator.
- Filter bar: year, unit (incl. "Shared"), category.
- **Add Expense** (`+`) → sheet:
  - Fields: date (default today), amount, category (picker over the fixed category list, see `DATA_MODEL.md`), property, unit (optional — leave empty for a property-level/shared expense), vendor (optional), note (optional).
  - **Receipt photo:** a "Scan receipt" button that opens the camera (`UIImagePickerController`/`PhotosPicker` camera source). One photo per expense; retake replaces. **This button is the Pro gate point** — after trial without Pro it renders in locked style (§5.3); the rest of the expense form stays free.
- **Expense Detail:** all fields plus full-screen receipt viewer (pinch-zoom). Edit and delete. Existing receipt photos remain viewable regardless of entitlement, forever.

### 3.5 Maintenance tab

- List of maintenance records, newest first, filterable by unit and status (`Open` / `Completed`).
- **Add Record** (`+`) → sheet: unit, title ("Water heater leaking"), description, vendor name + phone (optional), cost (optional), date reported (default today), date completed (optional — setting it marks the record Completed), photos (0–n, camera or library).
- A **"Also log as expense"** toggle in the form: when on and cost > 0, saving creates a linked `Expense` (category `repairs` by default, editable afterwards) so the cost flows into tax export without double entry. The link is navigable both ways; maintenance costs alone do **not** appear in tax export (only Expenses do), which prevents double counting.
- **Maintenance Detail:** all fields, photo grid with full-screen viewer, link chip to the associated expense if any.
- Maintenance photos are **not** Pro-gated (only *receipt* photos are, per the monetization spec).

### 3.6 More → Properties & Units

- List of properties; each property row expands to its units. Global footer notes the v1 cap: **3 units total** across all properties (enforced at add time regardless of entitlement).
- **Property Detail:** nickname, address, notes; list of its units; add unit.
- **Unit Detail:** label, beds/baths/sq ft, notes; current lease summary card (→ Lease Detail); per-unit shortcuts to its rent ledger, expenses, maintenance.
- Adding **unit #2 or #3** is a Pro action after trial (§5). Existing units are never hidden or read-locked.
- Deleting a property/unit requires typed confirmation and warns that its ledger/expense/maintenance history goes with it.

### 3.7 More → Tenants & Leases

- List of leases grouped by unit: active lease pinned on top, prior leases beneath ("History"). Turnover is handled by **ending** a lease (set end/move-out date) and **starting a new one** — old leases, their rent history, and their deposit records are kept forever.
- **Add/Edit Lease** (sheet): unit, tenant (pick existing or create: name, phone, email, notes), start date, end date (optional = month-to-month), monthly rent, rent due day (1–28 or last day), grace days, deposit amount + date received + where held, last rent increase date, reminder toggles (§3.9).
- **Lease Detail:**
  - Terms section (all fields above).
  - **Rent** section: link to this lease's slice of the ledger.
  - **Deposit** section: amount held, date received, where held; if the lease is ended → **Move-Out Worksheet** button and refund summary.
  - **Rent raise** section: last increase date, months since, next reminder date.

**Move-Out Worksheet** (push from an ended lease)
- Header: deposit held.
- Deduction line items: label, category (`cleaning`, `damage`, `unpaid rent`, `other`), amount, note. Add/edit/delete.
- Footer math, always visible: deposit − total deductions = **refund due**. Fields to record refund actually issued (date, amount).
- Share button → renders the worksheet as a simple PDF (itemized statement to hand the tenant). This share is **not** Pro-gated (it's part of the deposit tracker, not tax export).

### 3.8 More → Deposits

Flat list of every deposit currently held (active leases): unit, tenant, amount, date received, where held; total held across all units in the header. Rows push into the owning Lease Detail. Ended-lease deposits with an unfinished worksheet (no refund recorded) surface here too, flagged "settle".

### 3.9 More → Reminders

- Master list of everything schedulable, grouped by lease: **lease renewal** (fires N days before lease end; N configurable per lease: 30/60/90, default 60) and **rent raise** (fires N days before the anniversary of `lastRentIncreaseDate`, or of lease start if never raised; default lead 30 days, anniversary cadence 12 months).
- Toggles live here and on Lease Detail (same underlying state).
- First time any toggle is switched on → request `UNUserNotificationCenter` authorization. If denied, rows show an inline "Notifications are off for DoorLedger" warning with a button to the system Settings app.
- All notifications are **local**; scheduled IDs are persisted on the lease so they can be cancelled/rescheduled when dates change.
- Notifications are **not** Pro-gated.

### 3.10 More → Tax Export

- Pickers: **tax year** (default: last complete year) and **scope** (all units / single unit).
- Preview pane: per-unit totals — gross rent collected (sum of payments dated in the year), expenses by category, net; plus a "Shared (property-level)" expense section; grand totals.
- **Export** button → generates into a temp directory and presents a share sheet with three files:
  - `DoorLedger-<year>-income.csv` — one row per rent payment: `date, property, unit, tenant, period, amount, note`
  - `DoorLedger-<year>-expenses.csv` — one row per expense: `date, property, unit_or_shared, category, vendor, amount, note, has_receipt`
  - `DoorLedger-<year>-summary.pdf` — the preview rendered per unit + totals page. Receipt images are **not** embedded in v1.
- CSV: UTF-8, RFC 4180 quoting, ISO-8601 dates, plain decimal amounts (no currency symbol).
- **The entire screen's Export action is a Pro gate point** after trial (§5.3). The preview remains viewable (viewing is always free).

### 3.11 More → Settings

- **Plan** card: current entitlement state — "Trial · ends <date>" / "Pro" / "Free" — and (post-v1) the upgrade button. In v1 this reads from the entitlement service and, since the stub is always unlocked, shows "All features unlocked".
- Currency (defaults to device locale; display-only formatting, no conversion).
- Owner/business name (optional; used on PDF headers).
- Privacy note ("Your data never leaves this device"), version, acknowledgements.
- **Danger zone:** erase all data (typed confirmation).

### 3.12 Paywall (sheet — stub in v1)

A single reusable sheet, `PaywallSheet`, presented whenever a locked Pro action is attempted. Contents (final copy post-v1): what Pro includes (receipt photos, tax export, units 2–3), what stays free forever (viewing everything, rent logging for unit 1), price, purchase/restore buttons. **In v1 this sheet exists in code but is unreachable**, because the entitlement stub always reports unlocked.

---

## 4. Where the free/Pro boundary sits in the UI

Rule of thumb: **reads are never gated; only these three write-side features are.** When gated, a control stays visible but renders in "locked" style — label + small `lock.fill` badge, tinted secondary — and tapping presents `PaywallSheet` instead of performing the action. Nothing is hidden, greyed into invisibility, or removed.

| Feature | Gate point in UI | Free-forever behavior |
|---|---|---|
| **Receipt photos** | "Scan receipt" button in Add/Edit Expense | Expense logging itself stays free; existing photos always viewable |
| **Tax export (CSV/PDF)** | "Export" button on Tax Export screen | Preview/totals remain viewable |
| **Units 2–3** | (a) "Add unit" beyond the first unit, (b) "Record payment" / edit-payment on non-free units, (c) new expenses/maintenance records assigned to non-free units | All existing data for units 2–3 stays fully viewable; unit 1 (first-created unit, stable) is fully functional free |

Never gated: viewing any screen or record, rent logging for the free unit, expense/maintenance logging (minus receipt photo) for the free unit or property-level, deposits & move-out worksheet + its PDF, reminders/notifications, settings.

> **Assumption flagged for review:** the brief lists "units 2–3" as Pro without detailing which *actions* that covers. This spec interprets it as *all new data entry targeted at units 2–3* (rows b and c above), while unit-1 and property-level entry stays free. Say the word if you want it narrower (e.g. only rent logging gated).

---

## 5. Entitlement layer (structure only in v1)

### 5.1 Model

- **Trial:** 3 calendar months from `firstLaunchDate` (stored on first launch in `UserDefaults` and mirrored into the `AppSettings` SwiftData singleton; earliest of the two wins on read, so reinstall-with-backup keeps the original anchor).
- **After trial:** keep-core-free / gate-the-extras, per §4. Existing data is never locked or deleted.

### 5.2 Code shape

One protocol, injected via SwiftUI `Environment`; feature code never touches StoreKit or dates directly:

```swift
enum ProFeature { case receiptPhotos, taxExport, additionalUnits }

protocol EntitlementService: Observable {
    var isPro: Bool { get }        // purchased (always false until StoreKit lands)
    var isInTrial: Bool { get }    // now < firstLaunchDate + 3 months
    func isUnlocked(_ feature: ProFeature) -> Bool
    // v-next semantics: isPro || isInTrial
}
```

- **v1 implementation:** `StubEntitlementService` — `isUnlocked` returns `true` unconditionally, `isPro`/`isInTrial` still compute honestly (so the Settings card and trial date are real). No feature is actually restricted in v1.
- **Gate UI helper:** a single view modifier `.proGated(_ feature: ProFeature)` that wraps any control: unlocked → passthrough; locked → locked style + intercepts tap to present `PaywallSheet`. All gate points in §4 use this one modifier.
- **Later:** flipping on real gating = replacing the stub with a `StoreKitEntitlementService` (StoreKit 2) at the injection site. Zero feature-code changes by design.

### 5.3 Free-unit identity

The free unit is the unit with the earliest `createdAt` (ties broken by ID). Deleting it promotes the next-earliest. This is computed, not stored, so it can't drift.

---

## 6. Non-functional notes

- **Persistence:** SwiftData; images stored with `@Attribute(.externalStorage)`. Rationale in `DATA_MODEL.md` §1.
- **Money:** `Decimal` end-to-end; formatted per the currency code in Settings.
- **Dates:** rent periods are (year, month) pairs, not timestamps — immune to timezone drift.
- **Backups:** data lives in the default app container, so it rides along with the user's own iCloud/local device backup. This is not cloud *sync* and involves no app network code.
- **Accessibility:** Dynamic Type throughout; status chips carry text, never color alone.
- **No analytics, no crash reporting, no SDKs that phone home.**

## 7. v1 acceptance checklist

- [ ] Create property + up to 3 units; details editable
- [ ] Full rent ledger per unit: months, multiple payments, derived Paid/Partial/Late, running history across leases
- [ ] Expenses with category + camera receipt photo; filter; monthly totals
- [ ] Lease renewal & rent-raise local notifications, configurable lead time
- [ ] Deposit tracker: held deposits list + move-out deduction worksheet + refund math + shareable PDF statement
- [ ] Maintenance log: issue, vendor, cost, dates, photos, optional linked expense
- [ ] Tax export: one tap → income CSV + expense CSV + PDF summary, by unit and year
- [ ] Entitlement layer present (`EntitlementService`, `.proGated`, `PaywallSheet`, trial dates computed) with stub always-unlocked; every gate point from §4 wired through it
- [ ] Zero network calls (verifiable: no URLSession usage outside of nothing)
