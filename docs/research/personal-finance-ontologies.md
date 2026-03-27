# Personal Finance Ontologies: RDF & Linked Data Landscape

**Date:** 2026-03-27
**Purpose:** Background research for building a SemPKM personal finance mental model
**Context:** VC demo targeting personal finance / life planning use cases

---

## Executive Summary

There is **no widely-adopted, dedicated RDF/OWL ontology for personal finance**. The semantic web finance space is dominated by institutional ontologies (FIBO, FRO, XBRL). This represents both a gap and an opportunity: SemPKM can build a lightweight personal finance mental model by selectively reusing primitives from schema.org, FIBO foundations, and the OntoFINE money/exchange ontologies, layered on top of our existing GIST upper ontology.

The recommended approach is a **new SemPKM mental model** (`personal-finance`) that:
1. Reuses GIST's `FinancialAgreement`, monetary aspects, and temporal primitives
2. Aligns with schema.org financial types for interoperability
3. Draws conceptual structure from OntoFINE's money and economic exchange models
4. Defines its own classes for budgets, goals, and categories -- the gap no existing ontology fills

---

## 1. FIBO -- Financial Industry Business Ontology

**The dominant finance ontology, but institutional-focused.**

| Attribute | Detail |
|-----------|--------|
| **Full name** | Financial Industry Business Ontology |
| **Maintainer** | EDM Council (merged with OMG in Oct 2025) |
| **Namespace** | `https://spec.edmcouncil.org/fibo/ontology/` |
| **License** | MIT License |
| **Format** | OWL (Turtle, RDF/XML, JSON-LD) |
| **Status** | Active -- 2025/Q4 Production release, 2,436 classes; 3,173 normative entities as of Jan 2026 |
| **GitHub** | [edmcouncil/fibo](https://github.com/edmcouncil/fibo) |
| **Spec** | [spec.edmcouncil.org/fibo](https://spec.edmcouncil.org/fibo/) |

### Modules

| Module | Abbreviation | Personal Finance Relevance |
|--------|-------------|---------------------------|
| Foundations (FND) | `fibo-fnd` | **High** -- Agreements, Accounting, Quantities, Dates |
| Finance Business & Commerce (FBC) | `fibo-fbc` | **Medium** -- Debt, interest terms, financial instruments |
| Business Entities (BE) | `fibo-be` | Low -- Corporate entities, ownership structures |
| Securities (SEC) | `fibo-sec` | **Medium** -- Stocks, bonds, funds (investment tracking) |
| Loans (LOAN) | `fibo-loan` | **High** -- Mortgage, consumer loans, credit |
| Indices & Indicators (IND) | `fibo-ind` | Low -- Market benchmarks, economic indicators |
| Derivatives (DER) | `fibo-der` | Low -- Options, futures, swaps |

### Key Classes for Personal Finance Reuse

From FIBO Foundations:
- `fibo-fnd-acc-cur:MonetaryAmount` -- currency-denominated amounts
- `fibo-fnd-agr-ctr:Contract` -- any financial agreement
- `fibo-fnd-acc-cur:Currency` -- currency codes
- `fibo-fnd-dt-fd:DatePeriod` -- temporal ranges for budgets/goals

From FIBO Loans:
- `fibo-loan-ln-ln:Loan` -- loan/debt modeling
- `fibo-loan-ln-ln:LoanPayment` -- payment schedules

### Assessment

FIBO is **too heavy** for a personal finance PKM tool (2,400+ classes, deep corporate focus). However, its **Foundations module** provides well-defined monetary and agreement primitives worth aligning with. We should not import FIBO directly but can reference its design patterns.

---

## 2. Schema.org Financial Types

**Lightweight, widely adopted, excellent for interoperability.**

| Attribute | Detail |
|-----------|--------|
| **Namespace** | `https://schema.org/` |
| **License** | CC BY-SA 3.0 |
| **Format** | RDFa, JSON-LD, Microdata |
| **Status** | Active, continuously updated |
| **Docs** | [schema.org/docs/financial.html](https://schema.org/docs/financial.html) |

### Type Hierarchy

```
schema:Service
  schema:FinancialProduct
    schema:BankAccount
      schema:DepositAccount
    schema:PaymentCard
      schema:CreditCard
    schema:LoanOrCredit
      schema:MortgageLoan
    schema:InvestmentOrDeposit
      schema:BrokerageAccount
      schema:DepositAccount
      schema:InvestmentFund
    schema:PaymentService
    schema:CurrencyConversionService
```

### Key Types & Properties

| Type/Property | Relevance to Personal Finance |
|---------------|-------------------------------|
| `schema:BankAccount` | Checking/savings account modeling |
| `schema:DepositAccount` | Savings with interest |
| `schema:LoanOrCredit` | Debt tracking (mortgages, car loans, student loans) |
| `schema:CreditCard` | Credit card accounts |
| `schema:InvestmentOrDeposit` | Investment account modeling |
| `schema:InvestmentFund` | Mutual funds, ETFs, index funds |
| `schema:BrokerageAccount` | Stock trading accounts |
| `schema:MonetaryAmount` | Any monetary value with currency |
| `schema:ExchangeRateSpecification` | Multi-currency support |
| `schema:RepaymentSpecification` | Loan payment schedules |
| `schema:interestRate` | APR/interest modeling |
| `schema:amount` | Monetary amounts |
| `schema:currency` | Currency codes (ISO 4217) |

### Assessment

Schema.org is the **best alignment target** for a personal finance model. Its types are lightweight, widely understood, and map cleanly to personal finance concepts. The main gap: no budget, expense category, financial goal, or income/expense tracking concepts.

---

## 3. OntoFINE -- Ontology Network in Finance and Economics

**Academic, well-grounded, covers foundational financial concepts.**

| Attribute | Detail |
|-----------|--------|
| **Full name** | Ontology Network in Finance and Economics |
| **Maintainer** | Glenda Amaral (Central Bank of Brazil / Univ. of Twente) |
| **Foundation** | Unified Foundational Ontology (UFO) |
| **Format** | OntoUML + OWL implementations |
| **Status** | Active -- PhD Award (CAiSE 2024), Springer book 2024 |
| **Website** | [ontofine.wordpress.com](https://ontofine.wordpress.com/) |

### Component Ontologies

| Ontology | Full Name | OWL URI | Personal Finance Relevance |
|----------|-----------|---------|---------------------------|
| **ROME** | Reference Ontology of Money | `http://purl.org/krdb-core/money-ontology` | **High** -- Money, currency, virtual currencies |
| **COEX** | Core Ontology of Economic Exchanges | `http://purl.org/krdb-core/economic-exchanges-ontology` | **High** -- Buying, selling, transactions |
| **COVER** | Common Ontology of Value and Risk | `http://purl.org/krdb-core/value-and-risk-ontology` | **Medium** -- Risk assessment, value modeling |
| **ROT** | Reference Ontology of Trust | `http://purl.org/krdb-core/trust-ontology` | Low -- Trust relationships |
| **ROTwR** | Ref. Ontology of Trustworthiness Req. | `http://purl.org/krdb-core/trustworthiness-requirements-ontology` | Low -- Requirements |

### Assessment

OntoFINE's **ROME** (money) and **COEX** (economic exchanges) are conceptually excellent for personal finance foundations. They formalize what money *is*, how exchanges work, and how value flows -- exactly the conceptual grounding a personal finance model needs. The OWL implementations are available via persistent URIs. Worth studying for design patterns even if we don't import directly.

---

## 4. Payments Ontology

**Linked data vocabulary for spend/payment data.**

| Attribute | Detail |
|-----------|--------|
| **Maintainer** | Epimorphics / Local e-Government Standards Body (LeGSB) |
| **Based on** | W3C RDF Data Cube Vocabulary |
| **Format** | RDF |
| **Status** | Stable but low activity |
| **Guide** | [epimorphics.com/guide-to-the-payments-ontology](https://www.epimorphics.com/guide-to-the-payments-ontology/) |

### Key Concepts

- Treats spend data as a **data cube** (expenditures as observations)
- Payments = groups of expenditures (slices across the cube)
- Extensible via other vocabularies (W3C Organization Ontology, etc.)
- Originally for government transparency, but general-purpose

### Assessment

Interesting for **expense tracking** patterns -- representing expenditures as structured observations with dimensions (date, category, payee, amount). The data cube approach could inform how we model transaction history and budget tracking.

---

## 5. GoodRelations

**E-commerce ontology, integrated into schema.org.**

| Attribute | Detail |
|-----------|--------|
| **Namespace** | `http://purl.org/goodrelations/v1#` |
| **Maintainer** | Martin Hepp |
| **Status** | Mature -- largely superseded by schema.org integration (since 2012) |
| **OWL** | [heppnetz.de/ontologies/goodrelations/v1.owl](http://www.heppnetz.de/ontologies/goodrelations/v1.owl) |

### Relevance

- Detailed **pricing model**: `gr:hasCurrencyValue`, `gr:hasCurrency`, min/max ranges, VAT
- Product/service offering structure
- Mostly relevant through its schema.org integration rather than direct use

### Assessment

**Low direct relevance** for personal finance. GoodRelations is about describing commercial offers, not tracking personal spending. Its pricing primitives are already in schema.org.

---

## 6. XBRL and RDF Representations

**Financial reporting standard, primarily corporate.**

| Attribute | Detail |
|-----------|--------|
| **Full name** | eXtensible Business Reporting Language |
| **Format** | XML (primary), RDF conversions exist |
| **Status** | Active industry standard |
| **RDF work** | FinRegOnt XBRL ontology ([finregont.com/xbrl](https://finregont.com/xbrl/)) |

### Assessment

**Low relevance** for personal finance PKM. XBRL is designed for regulatory financial reporting (SEC filings, IFRS). The RDF conversions (FinRegOnt, MUSING project) target corporate financial statements. However, the *concept* of financial statement structure (assets, liabilities, income, expenses, equity) from XBRL taxonomies informs personal finance modeling.

---

## 7. Wikidata / DBpedia Financial Entities

**Knowledge base entries, useful for linking and reference data.**

| Entity | Wikidata ID | Description |
|--------|-------------|-------------|
| Personal finance | Q253613 | Financial management by individuals/families |
| Financial planning | Q2120150 | Planning to achieve financial goals |
| Personal Financial Management | Q11777362 | Management of personal finances |
| Investor (property) | P1951 | Links entities to their investors |

### Assessment

Useful as **reference links** (owl:sameAs) to ground our personal finance concepts in the broader linked data cloud, but Wikidata doesn't provide the structural ontology we need.

---

## 8. GIST Upper Ontology (Already in SemPKM)

**Our existing foundation -- already has financial primitives.**

| Relevant Class/Aspect | Description |
|----------------------|-------------|
| `gist:FinancialAgreement` | Agreement with a balance |
| `gistd:_Aspect_financial_balance` | Financial balance measurement |
| `gistd:_Aspect_monetary_value` | Monetary value measurement |
| `gist:Magnitude` | Measured quantities |
| `gist:UnitOfMeasure` | Units including currency |
| `gist:Event` / `gist:TemporalRelation` | Temporal modeling |
| `gist:Agreement` | Base class for contracts |
| `gist:Organization` | Financial institutions |
| `gist:Category` | Classification system |
| `gist:Goal` | Goals and objectives |

### Assessment

GIST provides a **strong foundation** for a personal finance model. Its `FinancialAgreement`, monetary aspects, and `Goal` class are directly usable. A personal finance mental model would naturally layer domain-specific concepts on top of GIST, consistent with how all other SemPKM models work.

---

## 9. REA (Resources, Events, Agents) Pattern

**Foundational accounting theory with high conceptual relevance.**

| Attribute | Detail |
|-----------|--------|
| **Origin** | William McCarthy, Michigan State University (1982) |
| **Status** | Foundational theory, widely cited in academia and ISO 15944-4 |
| **RDF version** | No single canonical RDF serialization exists |

### Core Model

REA models all economic activity as three primitives:
- **Resources** -- things of economic value (money, goods, services)
- **Events** -- economic transactions that affect resources (payment, purchase, sale)
- **Agents** -- participants in economic events (you, your employer, a merchant)

Every economic event involves a Resource flowing from one Agent to another. Double-entry accounting emerges naturally: every exchange has a give-event and a take-event.

### Assessment

**High theoretical relevance.** REA maps cleanly to personal finance: your money (Resource) moves via transactions (Events) between you and counterparties (Agents). No canonical RDF download exists, but the pattern is straightforward to implement in OWL and aligns well with GIST's `Event` and `Organization` classes.

### 9a. EREN -- Entity-Relationship Event Network (Batra's REA Extension)

**Extends REA with richer event semantics grounded in cognitive linguistics.**

| Attribute | Detail |
|-----------|--------|
| **Full name** | Entity-Relationship Event Network |
| **Author** | Dinesh Batra, Florida International University |
| **Key paper** | "An Event-Oriented Data Modeling Technique Based on the Cognitive Semantics Theory" -- *Journal of Database Management (JDM)*, Vol. 23, No. 4, 2012, pp. 52-74 |
| **Follow-up** | Batra & Wishart, "Novice Designer Performance Comparison Between the Entity Relationship Event Network and the Event-Based Logical Relational Design Techniques" -- *JDM*, Vol. 25, No. 3, 2014, pp. 1-27 |
| **Also see** | Batra, *Conceptual Data Modeling Patterns* (book, ResearchGate) |

#### Why EREN Extends REA

REA was designed for **accounting transactions** -- but most real-world business events are not pure accounting transactions. Batra observed that the REA formulation of Resource + Event + Agent is **incomplete** for modeling the full range of events a person or business encounters. EREN addresses this by introducing more discriminating entity types derived from Jackendoff's Conceptual Semantics theory (1985).

#### The EREN Template

Where REA gives you three entity categories per event, EREN provides a richer **event template** drawing on Jackendoff's thematic roles:

| Jackendoff Thematic Role | EREN Entity Type | Personal Finance Example |
|--------------------------|-----------------|-------------------------|
| **Thing** (what is affected) | Resource | Money, investment shares, property |
| **Event** (what happens) | Event | Purchase, payment, transfer, deposit |
| **Agent** (who acts) | Agent | You, your employer, a merchant, a bank |
| **Place** (where) | Location | Bank branch, online platform, ATM |
| **Path** (trajectory of change) | Flow/Transfer | From checking to savings, from employer to you |
| **Manner** (how) | Detail/Method | Wire transfer, cash, direct deposit, recurring |

The EREN technique is **top-down and template-driven**: you identify events, sketch a network of how events relate to each other, then apply the EREN template to each event to derive its full data model. This contrasts with bottom-up approaches and makes it particularly useful for **design** (not just description) of new data models.

#### The Event Network Concept

Beyond enriching individual events, EREN models **networks of events** -- how events connect, trigger, and depend on each other. For personal finance, this captures real patterns:

```
Salary Deposit ──triggers──> Budget Allocation
Budget Allocation ──enables──> Bill Payment
                  ──enables──> Savings Transfer
                  ──enables──> Investment Purchase
Investment Purchase ──may trigger──> Dividend Income
Loan Payment ──reduces──> Loan Balance
              ──is part of──> Debt Payoff Plan
```

This network view is a natural fit for SemPKM's knowledge graph approach -- financial events don't exist in isolation, they form meaningful chains that users want to see and reason about.

#### READY Model (Dynamic Behavior Extension)

| Attribute | Detail |
|-----------|--------|
| **Full name** | READY (REA + DYnamic behavior) |
| **Authors** | Dinesh Batra & Thant Sin, Florida International University |
| **Published** | "The READY model: Patterns of dynamic behavior in REA-based accounting applications" -- *Information Systems Management*, Vol. 25, No. 3, 2008, pp. 200-210 |
| **Notation** | UML sequence diagrams applied to REA objects |

##### The Problem READY Solves

REA is a **static data model** -- it defines entities (Resources, Events, Agents) and their relationships, but says nothing about the **temporal ordering** of events, the **state transitions** of objects, or the **dynamic workflows** that connect events into business processes. An event in REA is both a data entity *and* an implied scenario of activities, but REA provides no formal way to express that scenario.

Existing solutions like the OOREA model had sparse coverage of accounting scenarios and used ad-hoc notation. READY addresses this by applying the well-established UML sequence diagram convention to REA patterns, creating reusable **analysis patterns** for dynamic behavior.

##### How READY Works

READY adds a behavioral layer on top of REA's structural layer:

1. **Generic READY Model**: An abstract sequence diagram template showing how Resource, Event, and Agent objects interact over time during a transaction scenario
2. **Scenario-Specific Patterns**: Concrete instantiations of the generic model for common accounting workflows
3. **Event-to-Event Sequencing**: Shows which events trigger, precede, or follow other events

##### Scenario Patterns in READY

The paper provides sequence diagram patterns for key accounting scenarios:

| Scenario Pattern | Objects Involved | Dynamic Flow |
|-----------------|------------------|--------------|
| **Revenue/Sales Order** | Customer, Sales Order, Invoice, Cash Receipt | Commitment (order) -> Fulfillment (ship/invoice) -> Collection (payment) |
| **Invoice** | Vendor, Invoice, Payment, Receivable | Invoice issued -> Receivable increases -> Payment received -> Receivable decreases |
| **Fixed Assets** | Asset, Acquisition, Depreciation, Disposal | Acquire -> Periodic depreciation events -> Eventual disposal |
| **Payroll** | Employee, Time Record, Paycheck, Deductions | Time recorded -> Pay calculated -> Deductions applied -> Payment issued |

##### The Commitment-to-Fulfillment Pattern

A key insight from READY (building on Geerts & McCarthy 2002's REA extensions) is the **commitment-fulfillment lifecycle**:

```
Commitment (promise of future event)
    │
    ├── State: Planned / Promised
    │
    ▼
Fulfillment (actual event occurs)
    │
    ├── State: Partially Fulfilled / Fully Fulfilled
    │
    ▼
Settlement (economic exchange complete)
    │
    └── State: Settled / Closed
```

This maps directly to personal finance workflows:

| REA/READY Concept | Personal Finance Equivalent |
|------------------|---------------------------|
| **Commitment** | Budget allocation, subscription signup, loan agreement, savings goal pledge |
| **Event** | Actual transaction (purchase, payment, deposit, withdrawal) |
| **Fulfillment** | Budget spend against allocation, loan payment against schedule, savings deposit toward goal |
| **Duality** | Every expense has a dual: money outflow + value received. Every income has a dual: service provided + money inflow |
| **State transition** | Goal: Planned -> In Progress -> Achieved. Debt: Active -> Paying Down -> Paid Off. Budget period: Open -> Tracking -> Closed |

##### Relevance to Personal Finance in SemPKM

The READY model's dynamic patterns are **highly relevant** for personal finance because personal finance is inherently temporal and state-driven:

**1. Budget Lifecycle (Commitment -> Fulfillment)**
```
Budget Period Opens (monthly)
    │
    ├── Category commitments set (Housing: $1500, Food: $600, Transport: $300)
    │
    ├── Transactions fulfill commitments throughout the month
    │   ├── Rent payment: $1500 -> Housing FULFILLED
    │   ├── Grocery runs: $420 -> Food PARTIALLY FULFILLED
    │   └── Gas + transit: $280 -> Transport PARTIALLY FULFILLED
    │
    └── Period closes -> Variance analysis (planned vs actual)
```

**2. Debt Payoff (State Machine)**
```
Loan Created (commitment to repay)
    │
    ├── State: Active (balance = principal)
    │
    ├── Monthly payment events (READY sequence)
    │   ├── Interest portion calculated
    │   ├── Principal portion applied
    │   └── Balance reduced
    │
    ├── State: Paying Down (balance decreasing)
    │
    └── Final payment -> State: Paid Off
```

**3. Savings Goal (Commitment-Fulfillment with Progress)**
```
Goal Set: "Emergency Fund $10,000 by Dec 2026"
    │
    ├── State: Planned (current: $0, target: $10,000)
    │
    ├── Recurring deposit events
    │   ├── Each deposit is a fulfillment event
    │   └── Progress: $0 -> $2,500 -> $5,000 -> $7,500 -> $10,000
    │
    ├── State: In Progress (partially fulfilled)
    │
    └── Target reached -> State: Achieved
```

**4. Payroll / Income Cycle (Revenue Pattern)**
```
Employment Agreement (commitment to pay for services)
    │
    ├── Work Period (time-based resource provision)
    │
    ├── Paycheck Event (fulfillment)
    │   ├── Gross pay (resource inflow)
    │   ├── Tax withholding (resource outflow to government agent)
    │   ├── Benefits deduction (resource outflow to insurance agent)
    │   └── Net deposit to checking account
    │
    └── Triggers: budget allocation cycle restarts
```

##### OntoREA: The OWL Formalization

The REA/READY patterns have been formalized into OWL by Fischer-Pauzenberger & Schwaiger (TU Wien) as the **OntoREA** model:

| Attribute | Detail |
|-----------|--------|
| **Full name** | OntoREA Accounting and Finance Model |
| **Authors** | Christian Fischer-Pauzenberger, Walter S. A. Schwaiger (TU Wien) |
| **Published** | CSIMQ 2017; ER 2017 (Springer LNCS vol. 10650) |
| **Foundation** | OntoUML (Guizzardi) applied to REA |
| **Key innovation** | Distinguishes backward-looking (accounting: recording past events) from forward-looking (finance: commitments about the future) |
| **Extensions** | Includes uncertainty modeling for commitments, derivative instrument hedge portfolios |

OntoREA's backward/forward distinction is particularly useful for personal finance:
- **Backward-looking** = transaction history, spending records, account statements
- **Forward-looking** = budgets, financial goals, loan schedules, expected income

##### Sources

- [READY Model (ResearchGate)](https://www.researchgate.net/publication/220630345_The_READY_model_Patterns_of_dynamic_behavior_in_REA-based_accounting_applications)
- [READY Model (Taylor & Francis)](https://www.tandfonline.com/doi/full/10.1080/10580530802151103)
- [Generic READY Model Diagram (ResearchGate)](https://www.researchgate.net/figure/The-generic-READY-model_fig3_220630345)
- [OntoREA Model (Springer)](https://link.springer.com/chapter/10.1007/978-3-319-69904-2_38)
- [OntoREA Model (ResearchGate)](https://www.researchgate.net/publication/318824704_The_OntoREA_Accounting_Model_Ontology-based_Modeling_of_the_Accounting_Domain)
- [REA State Machine (Hunka & Zacek 2015)](https://www.researchgate.net/publication/277942361_A_new_view_of_REA_state_machine)
- [REA Ontological Foundations (Geerts & McCarthy 2000)](https://static1.squarespace.com/static/5feb9bf81c227637fcd6262b/t/5fecea680493bd2827baf2c9/1609362052890/The+Ontological+Foundations+of+REA+Enterprise+Information+Systems_2000.pdf)
- [Formal REA at Operational Level (MPRA)](https://mpra.ub.uni-muenchen.de/34766/1/MPRA_paper_34766.pdf)

#### Combined Assessment: REA + EREN + READY for SemPKM

**High relevance for our mental model design.** Together, these three layers provide a complete conceptual framework:

| Layer | What it gives us | SemPKM application |
|-------|-----------------|-------------------|
| **REA** (McCarthy 1982) | Static structure: Resource-Event-Agent | Core entity types for the ontology |
| **EREN** (Batra 2012) | Enriched event template: thematic roles from cognitive semantics | Richer transaction properties (who, what, where, how, from, to) |
| **READY** (Batra & Sin 2008) | Dynamic behavior: sequence patterns, state transitions, commitment-fulfillment | Budget lifecycle, goal progress, debt amortization, income cycles |
| **OntoREA** (Fischer-Pauzenberger 2017) | OWL formalization + backward/forward distinction | Accounting (history) vs. Finance (planning) views in the same model |

Key design implications:

1. **Template-driven design** (EREN) aligns with how SemPKM mental models work -- we define a template (ontology + shapes) that users instantiate
2. **Thematic roles** (EREN) map to the properties we need on transactions (who, what, where, how, from-where, to-where)
3. **Event networks** (EREN) map naturally to RDF graph structure -- events linked to resources, agents, locations, and to each other
4. **Commitment-Fulfillment** (READY) is the conceptual backbone for budgets (commitment = allocation, fulfillment = actual spend) and goals (commitment = target, fulfillment = progress)
5. **State machines** (READY) model the lifecycle of debts, goals, budget periods, and recurring obligations
6. **Backward/Forward** (OntoREA) cleanly separates transaction history from financial planning -- both essential for a PKM tool
7. **Cognitive grounding** (EREN/Jackendoff) means the model mirrors how people actually think about their financial events -- critical for a personal tool

The EREN template should inform `pf:Transaction` class properties. The READY commitment-fulfillment pattern should inform `pf:Budget`, `pf:FinancialGoal`, and `pf:LoanAccount` lifecycle modeling.

#### Sources

- [EREN Paper (IGI Global)](https://www.igi-global.com/article/event-oriented-data-modeling-technique/76666)
- [EREN vs ELRD Comparison (IGI Global)](https://www.igi-global.com/gateway/article/118086)
- [Conceptual Data Modeling Patterns (ResearchGate)](https://www.researchgate.net/publication/276002049_Conceptual_Data_Modeling_Patterns)
- [REA Wikipedia](https://en.wikipedia.org/wiki/Resources,_Events,_Agents)
- [Understanding REA (XBRL blog)](http://xbrl.squarespace.com/journal/2016/9/27/understanding-the-resource-event-agent-rea-conceptual-model.html)

---

## 10. Open Banking Ontology (OBO)

**Academic ontology for bank statement semantics.**

| Attribute | Detail |
|-----------|--------|
| **Published** | 2023, Applied Sciences journal (MDPI) |
| **Format** | OWL 2 |
| **Size** | 14 classes, 10 object properties, 35 data properties, ~250 axioms |
| **Context** | PSD2 open banking, bank statement & invoice management |
| **Status** | Academic prototype |

### Assessment

**Medium relevance.** Directly models bank statements and transactions, which is the core data flow for personal finance. However, it is an academic prototype rather than an adopted standard. Useful as a reference for transaction modeling patterns.

---

## Gap Analysis: What's Missing for Personal Finance

No existing ontology covers these personal finance concepts that users need:

| Concept | Existing Coverage | Gap |
|---------|------------------|-----|
| **Budget** (planned spending) | None | Full gap -- no ontology models budgets |
| **Expense categories** (housing, food, transport...) | None as RDF | Need taxonomy |
| **Income sources** (salary, freelance, investment returns) | None specific | Need classes |
| **Financial goals** (emergency fund, house down payment) | GIST `Goal` partial | Need finance-specific subclass |
| **Net worth tracking** | XBRL balance sheet concept | Need personal version |
| **Recurring transactions** | None | Need recurrence pattern |
| **Debt payoff planning** | FIBO Loans partial | Need simplified personal version |
| **Savings buckets** | None | Full gap |
| **Tax categories** | XBRL partial | Need personal tax concepts |
| **Insurance policies** | schema.org has some | Need to specialize |
| **Account aggregation** | schema.org `BankAccount` | Need to extend |

---

## Recommended Architecture for SemPKM Personal Finance Model

### Design Principles

1. **Lightweight over comprehensive** -- model what users actually track, not institutional complexity
2. **GIST-grounded** -- use GIST upper ontology as foundation (consistent with all SemPKM models)
3. **Schema.org-aligned** -- map to schema.org types where possible for interoperability
4. **REA/EREN-structured** -- use Resource-Event-Agent pattern as conceptual backbone, enriched with EREN thematic roles (location, method, path) for richer event modeling
5. **READY-dynamic** -- model commitment-fulfillment lifecycles for budgets, goals, and debts using state transitions
6. **Category-driven** -- expense/income categories are the core user mental model
7. **Goal-oriented** -- financial planning = goal tracking with monetary targets
8. **Backward/Forward** -- separate transaction history (accounting) from future plans (finance), per OntoREA

### Proposed Core Classes

```
Personal Finance Model (urn:sempkm:model:personal-finance:)

─── REA LAYER: Resources ───

  pf:FinancialAccount        (aligns with schema:BankAccount)  [Resource]
    pf:CheckingAccount
    pf:SavingsAccount
    pf:CreditCardAccount
    pf:InvestmentAccount
    pf:LoanAccount
    pf:RetirementAccount
  pf:Asset                   (grounded in gist:Magnitude)      [Resource]
  pf:Liability               (grounded in gist:Magnitude)      [Resource]

─── REA LAYER: Events (backward-looking: what happened) ───

  pf:Transaction             (subclass of gist:Event)          [Event]
    pf:Income
    pf:Expense
    pf:Transfer
  pf:RecurringTransaction    (pattern for recurring items)

─── REA LAYER: Agents ───

  pf:FinancialAgent          (subclass of gist:Organization or gist:Person)  [Agent]
    (employer, bank, merchant, government, self)

─── READY LAYER: Commitments (forward-looking: what's planned) ───

  pf:Commitment              (promise of future economic activity)
    pf:Budget                (commitment to spend within limits)
      pf:BudgetCategory      (per-category allocation)
      pf:BudgetPeriod        (monthly, weekly, annual)
    pf:FinancialGoal         (extends gist:Goal)
      pf:SavingsGoal         (commitment to accumulate)
      pf:DebtPayoffGoal      (commitment to reduce liability)
      pf:InvestmentGoal      (commitment to grow assets)
    pf:Subscription          (recurring commitment: Netflix, gym, insurance)
    pf:LoanAgreement         (commitment to repay over time)

─── READY LAYER: Fulfillment (linking commitments to events) ───

  pf:Fulfillment             (tracks commitment -> event progress)
    pf:hasBudgetAllocation   -- BudgetCategory -> MonetaryAmount (planned)
    pf:hasBudgetActual       -- BudgetCategory -> MonetaryAmount (actual)
    pf:hasGoalProgress       -- FinancialGoal -> MonetaryAmount (current)
    pf:hasGoalTarget         -- FinancialGoal -> MonetaryAmount (target)
    pf:fulfills              -- Transaction -> Commitment (this spend fulfills that budget/goal)
    pf:hasVariance           -- BudgetCategory -> MonetaryAmount (actual - planned)

─── READY LAYER: State (lifecycle tracking) ───

  pf:LifecycleState          (enumerated states for stateful objects)
    For Goals:    Planned | InProgress | Achieved | Abandoned
    For Debts:    Active | PayingDown | PaidOff | Defaulted
    For Budgets:  Open | Tracking | Closed | OverBudget
    For Accounts: Active | Dormant | Closed

─── SNAPSHOTS (point-in-time aggregations) ───

  pf:NetWorthSnapshot        (point-in-time: total assets - total liabilities)
  pf:MonthlyStatement        (period summary: income, expenses, savings rate)

─── CATEGORIES (SKOS taxonomy) ───

  pf:ExpenseCategory         (Housing, Food, Transport, Healthcare, ...)
  pf:IncomeCategory          (Salary, Freelance, Investment, Rental, ...)
  pf:AssetCategory           (Cash, Stocks, Bonds, Real Estate, ...)
  pf:LiabilityCategory       (Mortgage, Student Loan, Credit Card, ...)
```

### Key Properties

```
Core (REA):
pf:hasAccount           -- Person -> FinancialAccount          (Agent -> Resource)
pf:hasBalance           -- FinancialAccount -> MonetaryAmount
pf:transactionAmount    -- Transaction -> MonetaryAmount        (Event -> Resource)
pf:transactionDate      -- Transaction -> xsd:date              (Event -> Time)
pf:category             -- Transaction -> ExpenseCategory       (Event -> Classification)
pf:payee                -- Expense -> Organization/Person       (Event -> Agent)
pf:payer                -- Income -> Organization/Person        (Event -> Agent)

EREN-enriched (thematic roles):
pf:fromAccount          -- Transaction -> FinancialAccount      (Path: source)
pf:toAccount            -- Transaction -> FinancialAccount      (Path: destination)
pf:transactionMethod    -- Transaction -> PaymentMethod         (Manner: how)
pf:transactionLocation  -- Transaction -> Place                 (Place: where)
pf:triggeredBy          -- Transaction -> Transaction           (Event network: causation)
pf:partOfPlan           -- Transaction -> FinancialGoal         (Event network: goal linkage)

Planning & Goals:
pf:targetAmount         -- FinancialGoal -> MonetaryAmount
pf:currentAmount        -- FinancialGoal -> MonetaryAmount
pf:targetDate           -- FinancialGoal -> xsd:date
pf:budgetAmount         -- BudgetCategory -> MonetaryAmount
pf:actualAmount         -- BudgetCategory -> MonetaryAmount
pf:interestRate         -- LoanAccount -> xsd:decimal (aligns with schema:interestRate)
```

### Alignment Mappings

```turtle
pf:FinancialAccount  owl:equivalentClass  schema:BankAccount .
pf:Transaction       rdfs:subClassOf      gist:Event .
pf:FinancialGoal     rdfs:subClassOf      gist:Goal .
pf:transactionAmount rdfs:subPropertyOf   schema:amount .
pf:CheckingAccount   skos:closeMatch      wikidata:Q3480829 .
pf:personalFinance   skos:exactMatch      wikidata:Q253613 .
```

---

## Sources

### Primary Ontologies
- [FIBO Specification](https://spec.edmcouncil.org/fibo/) | [GitHub](https://github.com/edmcouncil/fibo)
- [Schema.org Financial Types](https://schema.org/docs/financial.html)
- [OntoFINE](https://ontofine.wordpress.com/) | [Springer Book](https://link.springer.com/book/10.1007/978-3-031-71082-7)
- [Payments Ontology Guide](https://www.epimorphics.com/guide-to-the-payments-ontology/)
- [GoodRelations](https://www.w3.org/wiki/GoodRelations) | [OWL Spec](http://www.heppnetz.de/ontologies/goodrelations/v1.owl)
- [FinRegOnt XBRL Ontology](https://finregont.com/xbrl/)

### OntoFINE OWL Implementations
- ROME (Money): `http://purl.org/krdb-core/money-ontology`
- COEX (Economic Exchanges): `http://purl.org/krdb-core/economic-exchanges-ontology`
- COVER (Value & Risk): `http://purl.org/krdb-core/value-and-risk-ontology`

### Reference
- [W3C Common Vocabularies](https://www.w3.org/wiki/TaskForces/CommunityProjects/LinkingOpenData/CommonVocabularies)
- [Wikidata: Personal Finance (Q253613)](https://www.wikidata.org/wiki/Q253613)
- [Wikidata: Financial Planning (Q2120150)](https://www.wikidata.org/wiki/Q2120150)
- [FIBO EDM Council](https://edmcouncil.org/financial-industry-business-ontology/)
- [FIB-DM](https://fib-dm.com/finance-ontology-transform-data-model/)
