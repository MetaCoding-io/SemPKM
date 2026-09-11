<!-- GENERATED FILE. Do not edit. Source: models/crm/README.md. Regenerate with: python3 scripts/sync-model-docs.py -->
> **Bundled model documentation.** This page mirrors the `README.md` shipped inside the `crm` Mental Model archive. The same text is available in the app under **Admin > Models > Personal CRM > Documentation** and at `/api/models/crm/docs`. To change it, edit `models/crm/README.md` and run `scripts/sync-model-docs.py`.

# Personal CRM

**Model ID:** `crm` · **Namespace:** `urn:sempkm:model:crm:` · **Prefix:** `crm:`

The Personal CRM model helps you manage professional and personal relationships. Track
**Contacts**, the **Companies** they work at, every **Interaction** you have with them, and
business **Deals** moving through a pipeline. SHACL-AF rules warn you about contacts you have
not spoken to and follow-ups that slipped.

## Types

### Contact

A person in your network.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| First Name | string | ✓ | Given name |
| Last Name | string | ✓ | Family name |
| Email | string | | Primary email address |
| Phone | string | | Phone number |
| Role | string | | Job title or role at their company |
| Works At | → Company | | Company where this contact works |
| Relationship | enum | | `colleague`, `client`, `friend`, `mentor`, `vendor`, `other` |
| Knows | → Contact | | Other contacts this person knows (mutual) |
| Follow-up Date | date | | Date by which to follow up |
| Follow-up Done | boolean | | Whether the follow-up is completed |
| Tags | string[] | | Free-form labels |
| Notes | string | | Free-form notes about this contact |

### Company

An organization your contacts work at.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Company Name | string | ✓ | Display name |
| Industry | string | | Industry sector (e.g., Technology, Healthcare) |
| Website | string | | Company website URL |
| Company Size | enum | | `solo`, `small`, `medium`, `large`, `enterprise` |
| Employees | → Contact | | Contacts who work here (inverse of Works At) |
| Notes | string | | Free-form notes |

### Interaction

A recorded touchpoint with one or more contacts.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Type | enum | ✓ | `meeting`, `call`, `email`, `coffee`, `conference`, `other` |
| Date | date | ✓ | When the interaction took place |
| Summary | string | | Brief summary of what was discussed |
| With Contact | → Contact | ✓ | Contact(s) involved (at least one required) |
| Follow-up Date | date | | When to follow up |
| Follow-up Done | boolean | | Whether the follow-up is completed |

### Deal

A business opportunity tracked through a pipeline.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Deal Name | string | ✓ | Name or title of the deal |
| Stage | enum | ✓ | `lead`, `qualified`, `proposal`, `negotiation`, `won`, `lost` |
| Value | decimal | | Monetary value |
| Currency | enum | | `USD`, `EUR`, `GBP` (default: `USD`) |
| Contact | → Contact | | Primary contact for this deal |
| Company | → Company | | Company associated with this deal |
| Notes | string | | Deal-specific context |

## The pipeline

Deal stages form a linear pipeline reflecting opportunity progression:

```
lead → qualified → proposal → negotiation → won / lost
```

Use the **Open Deals** saved query to see all deals not yet at `won` or `lost`. Filter the Deals
Table view by stage, or open the Deals Cards view and group by stage, to build a pipeline board.

## Relationships

```
Contact ──worksAt──▸ Company (inverse: hasEmployee)
Contact ──knows──▸ Contact (symmetric)
Interaction ──withContact──▸ Contact
Deal ──dealContact──▸ Contact
Deal ──dealCompany──▸ Company
```

## Views and saved queries

Table, Cards, and Graph views exist for Contacts; Table and Graph for Companies and
Interactions; Table and Cards for Deals. Saved queries:

| Query | Description |
|-------|-------------|
| Stale Contacts | Contacts with no recent interactions |
| Upcoming Follow-ups | Interactions or contacts with future follow-up dates |
| Open Deals | Deals not at `won` or `lost` stage |
| Network Map / CRM Network | Graph views of contacts and their connections |

## Inference and validation rules

| Rule | Kind | Effect |
|------|------|--------|
| Derive lastContactedDate | Inference | Sets a contact's last-contacted date from their most recent interaction |
| No interactions | Warning | "Contact has had no interactions recorded. Consider reaching out." |
| Overdue follow-up | Warning | "Follow-up is overdue and not marked done." |

## Installation

Go to **Admin > Models**, pick **Personal CRM** from the bundled catalog (or enter the path
`/app/models/crm`) and click **Install**. The four CRM types appear in the Explorer sidebar, and
the seed data adds a handful of contacts, companies, interactions, and deals — including a stale
contact so you can see the warning rule fire.

## Recommended dashboards

Use a **sidebar-main** layout:

- **Sidebar:** embed the Contacts Table view as a view-embed block for a scrollable contact list.
- **Main:** embed the Interactions Table, filtered by the selected contact using cross-view context.

For a pipeline overview, create a second dashboard with a **top-bottom** layout: Open Deals on
top, Stale Contacts on the bottom.

---

**Back:** [Chapter 39: Mental Model Catalog](39-mental-model-catalog.md)
