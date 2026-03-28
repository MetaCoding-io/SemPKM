# Personal Finance Mental Model: Research Cycle Plan

**Date:** 2026-03-28
**Status:** Active Research
**Goal:** Design a robust `personal-finance` mental model for SemPKM that supports diverse user perspectives on their financial life, including rich visualizations and animated flow views.

---

## Table of Contents

1. [Research Phases](#research-phases)
2. [Phase 1: User Stories & Personas](#phase-1-user-stories--personas)
3. [Phase 2: Visualization & Flow Research](#phase-2-visualization--flow-research)
4. [Phase 3: Ontology Design](#phase-3-ontology-design)
5. [Phase 4: SHACL Shapes & Views](#phase-4-shacl-shapes--views)
6. [Phase 5: Seed Data & Demo](#phase-5-seed-data--demo)
7. [Open Questions](#open-questions)

---

## Research Phases

```
Phase 1: User Stories & Personas           ◄── WE ARE HERE
    │   Who uses this? What do they need to see?
    │   What financial "lenses" do people use?
    │
Phase 2: Visualization & Flow Research
    │   How should money flows be visualized?
    │   What existing tools/patterns inspire us?
    │   What can SemPKM's view system support?
    │
Phase 3: Ontology Design
    │   Classes, properties, taxonomies
    │   REA/EREN/READY patterns applied
    │   GIST grounding, schema.org alignment
    │
Phase 4: SHACL Shapes & Views
    │   Auto-generated forms for each class
    │   ViewSpecs: tables, cards, graphs, dashboards
    │   Flow/Sankey views (new view type?)
    │
Phase 5: Seed Data & VC Demo
        Realistic demo scenario with rich data
        Compelling visualizations for pitch
```

Each phase produces a deliverable that feeds the next. We iterate within phases as needed.

---

## Phase 1: User Stories & Personas

### 1.1 Personas

We need to design for **multiple financial perspectives**, not just one. Different users look at their money differently:

#### Persona A: "The Budgeter" (Sarah, 28, UX Designer)
- **Primary concern:** Where does my money go each month?
- **Mental model:** Categories and envelopes. Money comes in, gets allocated to buckets, gets spent.
- **Key views:** Monthly budget vs. actual, spending by category pie/bar chart, trend lines over months
- **Tools she's leaving:** Mint, YNAB, spreadsheets
- **Pain point:** Disconnected from her goals and life plans. Budget feels like a chore, not a strategy.

#### Persona B: "The Net Worth Tracker" (Marcus, 35, Software Engineer)
- **Primary concern:** Am I building wealth? What's my trajectory?
- **Mental model:** Balance sheet. Assets vs. liabilities. Net worth over time.
- **Key views:** Net worth chart over time, asset allocation pie, account balances dashboard
- **Tools he's leaving:** Personal Capital, spreadsheets
- **Pain point:** Can see the numbers but can't connect them to life goals or decisions.

#### Persona C: "The Goal Planner" (Priya, 42, Product Manager)
- **Primary concern:** Am I on track for my goals? (house, kids' college, retirement)
- **Mental model:** Goal-based. Each dollar serves a purpose tied to a life outcome.
- **Key views:** Goal progress bars, projected timelines, "what-if" scenarios
- **Tools she's leaving:** Financial advisor spreadsheets, Notion
- **Pain point:** Goals live in one place, accounts live in another, no unified view.

#### Persona D: "The Cash Flow Analyst" (James, 50, Small Business Owner)
- **Primary concern:** What's my cash position? Where does money flow between accounts?
- **Mental model:** Flow network. Money as streams moving between pools.
- **Key views:** Sankey diagrams of money flow, cash flow waterfall, forecast vs. actual
- **Tools he's leaving:** QuickBooks (personal side), multiple bank apps
- **Pain point:** Business and personal finances intertwine. Needs to see the full flow.

#### Persona E: "The Debt Warrior" (Alex, 30, Teacher)
- **Primary concern:** When will I be debt-free? What's the optimal payoff strategy?
- **Mental model:** Liability-focused. Snowball vs. avalanche. Progress bars.
- **Key views:** Debt payoff timeline, interest cost visualization, payment schedule
- **Tools they're leaving:** Undebt.it, spreadsheets
- **Pain point:** Can't see how debt payoff connects to the rest of financial life.

### 1.2 User Stories

Stories are grouped by the **financial lens** they represent. Each story should be satisfiable by the ontology + views we build.

#### Lens 1: Transaction Tracking (backward-looking / REA Events)

| ID | Story | Persona | Priority |
|----|-------|---------|----------|
| T1 | As a user, I can record an expense with amount, date, category, payee, account, and payment method | All | P0 |
| T2 | As a user, I can record income with amount, date, source, and destination account | All | P0 |
| T3 | As a user, I can record a transfer between my own accounts | All | P0 |
| T4 | As a user, I can see all transactions in a filterable/sortable table view | All | P0 |
| T5 | As a user, I can categorize transactions and bulk-edit categories | A, D | P1 |
| T6 | As a user, I can set up recurring transactions (subscriptions, salary, rent) that auto-populate | All | P1 |
| T7 | As a user, I can split a single transaction across multiple categories | A | P2 |
| T8 | As a user, I can tag transactions with freeform tags beyond categories | All | P2 |

#### Lens 2: Budget Planning (READY Commitment-Fulfillment)

| ID | Story | Persona | Priority |
|----|-------|---------|----------|
| B1 | As a budgeter, I can create a monthly budget with category allocations | A | P0 |
| B2 | As a budgeter, I can see budget vs. actual spending per category in a bar chart | A | P0 |
| B3 | As a budgeter, I can see how much is remaining in each category mid-month | A | P0 |
| B4 | As a budgeter, I can roll over unspent amounts to the next month | A | P1 |
| B5 | As a budgeter, I can see spending trends by category over 3/6/12 months | A, B | P1 |
| B6 | As a budgeter, I can set category-level alerts when spending exceeds a threshold | A | P2 |
| B7 | As a budgeter, I can compare budget periods side by side | A | P2 |

#### Lens 3: Accounts & Net Worth (REA Resources / Balance Sheet)

| ID | Story | Persona | Priority |
|----|-------|---------|----------|
| N1 | As a user, I can add financial accounts (checking, savings, credit card, investment, loan) | All | P0 |
| N2 | As a user, I can see all account balances in a dashboard view | B, D | P0 |
| N3 | As a user, I can see my total net worth (assets - liabilities) | B | P0 |
| N4 | As a user, I can see net worth plotted over time (monthly snapshots) | B | P0 |
| N5 | As a user, I can see asset allocation breakdown (cash, stocks, bonds, real estate) | B | P1 |
| N6 | As a user, I can track individual investment holdings with current value | B | P2 |
| N7 | As a user, I can see account-level transaction history | All | P1 |

#### Lens 4: Financial Goals (READY Commitments + Fulfillment)

| ID | Story | Persona | Priority |
|----|-------|---------|----------|
| G1 | As a goal-setter, I can create a financial goal with target amount and target date | C | P0 |
| G2 | As a goal-setter, I can link a savings account or budget category to a goal | C | P0 |
| G3 | As a goal-setter, I can see progress toward each goal as a progress bar | C | P0 |
| G4 | As a goal-setter, I can see projected completion date based on current pace | C | P1 |
| G5 | As a goal-setter, I can see all goals in a single dashboard with status indicators | C | P1 |
| G6 | As a goal-setter, I can mark goals as achieved, paused, or abandoned | C | P1 |
| G7 | As a goal-setter, I can link goals to life pillars (PPV integration) | C | P2 |

#### Lens 5: Debt Management (READY State Machine)

| ID | Story | Persona | Priority |
|----|-------|---------|----------|
| D1 | As a debt manager, I can track each debt with balance, interest rate, minimum payment | E | P0 |
| D2 | As a debt manager, I can see total debt and a payoff timeline | E | P0 |
| D3 | As a debt manager, I can see how much of each payment goes to interest vs. principal | E | P1 |
| D4 | As a debt manager, I can compare snowball vs. avalanche payoff strategies | E | P2 |
| D5 | As a debt manager, I can see total interest cost over the life of each debt | E | P1 |

#### Lens 6: Cash Flow & Money Movement (EREN Event Networks / Sankey)

| ID | Story | Persona | Priority |
|----|-------|---------|----------|
| F1 | As a flow analyst, I can see a Sankey diagram of money flow: income sources -> accounts -> expense categories | D | P1 |
| F2 | As a flow analyst, I can see a monthly cash flow waterfall (income - expenses = net) | D | P0 |
| F3 | As a flow analyst, I can see money movement between accounts as an animated flow | D | P2 |
| F4 | As a flow analyst, I can filter flows by time period, category, or account | D | P1 |
| F5 | As a flow analyst, I can see recurring vs. one-time flows distinguished visually | D | P2 |

#### Lens 7: Connections & Life Context (SemPKM's Unique Value)

| ID | Story | Persona | Priority |
|----|-------|---------|----------|
| L1 | As a user, I can see my financial accounts, goals, and budgets in the knowledge graph alongside my projects, notes, and life pillars | All | P1 |
| L2 | As a user, I can link a financial goal to a project (e.g., "Kitchen Renovation" project linked to "Home Improvement" savings goal) | C | P1 |
| L3 | As a user, I can see how a spending category relates to a life pillar (e.g., "Health" pillar -> "Healthcare" spending) | A, C | P2 |
| L4 | As a user, I can annotate a financial account or goal with notes and context | All | P2 |
| L5 | As a user, I can see financial objects in the graph view connected to the rest of my knowledge | All | P1 |

### 1.3 Visualization Inventory

Based on the user stories, we need these visualization types:

| Visualization | Stories | Existing in SemPKM? | Notes |
|--------------|---------|---------------------|-------|
| **Filterable table** | T4, N7, B7 | Yes (ViewSpec table) | Core view type, already works |
| **Bar chart** (budget vs. actual) | B2, B5 | No | Need chart ViewSpec or dashboard widget |
| **Progress bar** | G3, D2 | No | Simple CSS, could be a card variant |
| **Line chart** (net worth over time) | N4, B5 | No | Time-series chart needed |
| **Pie/donut chart** (allocation) | N5, B2 | No | Category breakdown |
| **Dashboard** (multi-widget) | N2, G5 | Planned (see dashboard research) | Depends on dashboard builder feature |
| **Sankey diagram** (money flow) | F1, F3 | No | Major new viz -- needs research |
| **Waterfall chart** (cash flow) | F2 | No | Income -> expenses -> net |
| **Knowledge graph** | L1, L5 | Yes (ViewSpec graph) | Already works, just needs financial nodes |
| **Card grid** | G5, D2 | Yes (ViewSpec cards) | Works for goal/debt summary cards |
| **Timeline** | D2, G4 | No | Projected payoff/achievement dates |
| **Animated flow** | F3, F5 | No | Advanced -- particles moving along paths |

---

## Phase 2: Visualization & Flow Research

### 2.1 Research Questions

- What Sankey diagram libraries work well with RDF/SPARQL data?
  - D3-sankey, Google Charts Sankey, ECharts, Plotly
  - Can we generate Sankey data from SPARQL aggregation queries?
- What personal finance apps have the best flow visualizations?
  - Sankey: SankeyMATIC, Fluxo, r/personalfinance Sankey posts
  - Flow animation: MoneyStream (concept), banking app animations
- How do we fit new chart types into SemPKM's ViewSpec system?
  - New `viewType: "chart"` with chart subtype?
  - Or dashboard widgets that embed charts?
- What's the minimal viable animation for "money flow"?
  - CSS particle animation along SVG paths?
  - Or static Sankey is sufficient for v1?

### 2.2 Competitive Analysis (TODO)

| Tool | Flow Viz | Budget Viz | Goal Viz | Net Worth | Graph/Network |
|------|----------|-----------|----------|-----------|---------------|
| YNAB | No | Excellent (envelope) | Basic | No | No |
| Mint | No | Good (category) | Basic | Basic | No |
| Personal Capital | No | No | Basic | Excellent | No |
| Monarch Money | No | Good | Good | Good | No |
| Copilot Money | No | Good | Good | Good | No |
| SankeyMATIC | Excellent (Sankey) | No | No | No | No |
| SemPKM (target) | Yes (Sankey + animated) | Yes (READY) | Yes (READY) | Yes (snapshots) | Yes (RDF graph) |

**SemPKM's differentiator:** No existing tool combines financial visualization with a knowledge graph. We can show finances *in context* of life goals, projects, and relationships.

### 2.3 Sankey / Flow Diagram Deep Dive (TODO)

Research needed:
- [ ] Survey D3-sankey, ECharts Sankey, Plotly Sankey for HTMX integration
- [ ] Study r/personalfinance Sankey diagram conventions
- [ ] Prototype: SPARQL query -> Sankey data structure
- [ ] Determine if animated flow is feasible with CSS/SVG particles

### 2.4 Chart Integration Architecture (TODO)

Research needed:
- [ ] How to add chart ViewSpec types to existing view system
- [ ] Server-side (SPARQL -> chart data JSON) vs. client-side (fetch + render)
- [ ] Library choice: lightweight (Chart.js) vs. powerful (D3/ECharts)

---

## Phase 3: Ontology Design

### 3.1 Inputs

- Phase 1 user stories (what classes and properties are needed)
- Phase 2 visualization requirements (what aggregation queries must be possible)
- Ontology landscape research (existing `personal-finance-ontologies.md`)
- REA/EREN/READY patterns

### 3.2 Deliverables

- [ ] `models/personal-finance/ontology/personal-finance.jsonld` -- OWL classes & properties
- [ ] Expense/income category SKOS taxonomy
- [ ] Alignment mappings to schema.org, GIST, Wikidata
- [ ] Design decision document (why each class exists, which stories it serves)

### 3.3 Design Constraints

1. Must work with SemPKM's existing SHACL shape -> auto-generated form pipeline
2. Must produce data queryable by SPARQL for ViewSpecs
3. Must be explorable in the graph view (nodes + edges)
4. Must not require changes to the core platform (ontology-only extension)
5. Classes should map to REA/EREN/READY concepts documented in research

---

## Phase 4: SHACL Shapes & Views

### 4.1 Deliverables

- [ ] `models/personal-finance/shapes/personal-finance.jsonld` -- form shapes for each class
- [ ] `models/personal-finance/views/personal-finance.jsonld` -- ViewSpecs
- [ ] Manifest with icons (Lucide icon set, finance-themed)

### 4.2 View Design (TODO after Phase 2)

| View | Type | Purpose | Data Source |
|------|------|---------|-------------|
| All Transactions | table | Sortable/filterable transaction list | SPARQL on pf:Transaction |
| Monthly Budget | card grid + bars | Budget vs. actual per category | SPARQL aggregation |
| Account Balances | card grid | Dashboard of all accounts | SPARQL on pf:FinancialAccount |
| Net Worth History | line chart | Net worth over time | SPARQL on pf:NetWorthSnapshot |
| Goal Tracker | card grid + progress | All goals with progress | SPARQL on pf:FinancialGoal |
| Money Flow | Sankey | Income -> accounts -> expenses | SPARQL aggregation |
| Debt Overview | table + timeline | All debts with payoff info | SPARQL on pf:LoanAccount |
| Financial Graph | graph | Everything connected | SPARQL CONSTRUCT |

---

## Phase 5: Seed Data & VC Demo

### 5.1 Demo Scenario

Create a realistic but fictional persona with:
- 2 income sources (salary + freelance)
- 6 accounts (checking, savings, credit card, investment, 401k, mortgage)
- 12 months of transaction history (~200-300 transactions)
- 3 active goals (emergency fund, house down payment, retirement)
- 2 debts (student loan, mortgage)
- Monthly budget with 8-10 categories
- Monthly net worth snapshots showing growth
- Connections to PPV pillars (if PPV model is also installed)

### 5.2 Demo Walkthrough (for VCs)

1. **"Here's my financial dashboard"** -- Account balances, net worth, goal progress
2. **"Where does my money go?"** -- Sankey diagram from income through accounts to categories
3. **"Am I on track?"** -- Budget vs. actual with trend lines
4. **"Watch the money flow"** -- Animated flow visualization (wow factor)
5. **"But here's what no other tool does"** -- Switch to graph view, show finances connected to life goals, projects, and knowledge
6. **"My emergency fund goal is linked to my 'Financial Security' life pillar, which also connects to my insurance research notes"** -- This is the PKM differentiator

---

## Open Questions

### Product Questions
- [ ] Should this model standalone or require PPV as a companion?
- [ ] Do we need import from CSV/bank exports for the demo?
- [ ] How much automation vs. manual entry? (V1 = manual, future = import)
- [ ] Should categories be flat or hierarchical? (SKOS supports both)

### Technical Questions
- [ ] Can SPARQL aggregation queries power Sankey diagrams efficiently?
- [ ] What chart library integrates best with our HTMX/vanilla JS stack?
- [ ] Do we need a new ViewSpec type for charts, or do dashboards handle this?
- [ ] How do we model time-series data (net worth snapshots) efficiently in RDF?

### Design Questions
- [ ] How many classes is too many for a mental model? (PPV has ~10 types)
- [ ] Should pf:Transaction be a single class with a type property, or separate Income/Expense/Transfer subclasses?
- [ ] Is the READY commitment layer too abstract for users? Should Budget just be a simple object?
- [ ] How do we handle multi-currency?

### Research Questions (for iteration)
- [ ] What do real YNAB/Mint/Monarch users complain about most?
- [ ] What's the simplest Sankey that still tells a useful story?
- [ ] Can we prototype a flow animation cheaply with CSS?
