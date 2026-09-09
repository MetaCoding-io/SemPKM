# Review: "A Semantic Agent Platform for SemPKM" (Agents Epic)

> **Status:** Design review  
> **Date:** 2026-09-09  
> **Reviewed document:** EPIC "A Semantic Agent Platform for SemPKM" (design proposal, working title SemPKM Agents / Semantic Agent Runtime)  
> **Reviewer role:** senior software architect / product designer (AI background)  
> **Method:** the proposal was read against the current codebase (`backend/app`, `src/sdk`, `models/`, `.gsd/design/`) rather than in the abstract. Where the review says "today the platform does X", that was verified in code and the file is named.

---

## 1. Overall assessment

The proposal is intellectually coherent and unusually well-grounded in prior art. Its central thesis (LLM for fluency, RDF for state, behavior trees for control, typed commands for authority, durable execution for persistence, protocols for social agency) is the right decomposition, and the insistence on command-only mutation, versioned definitions, and inspectable uncertainty is exactly what most "LLM agent" designs lack.

It has three classes of weakness that should be fixed before this becomes an implementation plan:

1. **The substrate is overstated.** Section 2.2 and Section 12 assume platform capabilities (event subscriptions, idempotent commands, server-side capability grants, an approval gate in the copilot, a structured LLM interface, an executable WorkflowSpec) that do not exist today or exist in a much weaker form. Several of these are prerequisites for Phase 2, not incidental integration work.
2. **Core runtime semantics are undefined where they matter most.** The document defines the vocabulary of behavior trees but not the execution model that reconciles "reactive re-tick from root" with "durable cursor and resume". It also has no data-flow model between nodes, no representation decision for statement-level epistemic metadata, and no answer for how LLM nodes coexist with deterministic replay.
3. **The scope is a multi-year program labelled as an epic.** Eight phases, six workspace panels, roughly 34 node types, twelve speech acts, twelve governance concepts and a VSM mapping, all under a document that also asserts "start with a closed feedback loop". The requirements list (Section 16) is not phase-tagged, so nothing in the document tells a reader which AGT requirements the first epic actually commits to.

The recommendation is to keep the architecture, split the delivery into three epics, decide roughly half of the open questions now, and add a short "platform prerequisites" phase that is honest about what has to change in `backend/app` before any behavior can run.

---

## 2. Claims about the current substrate that do not hold

These are the most consequential findings because they change the delivery plan.

### 2.1 There is no event subscription mechanism, and the existing one is not durable

Section 12.4 says the app "needs a stable event subscription mechanism" and lists nine trigger sources as if they were a configuration matter. Today:

- The only post-commit fan-out is `WebhookService.dispatch()` (`backend/app/services/webhooks.py`). It is explicitly fire-and-forget: one HTTP POST per config, 5-second timeout, no retry, no persistence, no delivery record. Failures are logged and dropped.
- The command-to-event map in `backend/app/commands/router.py` emits only two event types, `object.changed` and `edge.changed`. There is no `object.deleted` command or event, yet Section 12.4 lists "object created/updated/deleted" as a trigger.
- Outbound webhook targets pass through the SSRF guard, which rejects private and loopback addresses. A resident app cannot subscribe to itself through webhooks.
- LDN inbox notifications (`backend/app/federation/inbox.py`) are stored as named graphs and never consumed by anything.
- The app scheduler (`backend/app/apps/scheduler.py`) is push-based over a Unix socket with a 30-second minimum interval. It records task runs in SQLite (`app_task_runs`), which is a good precedent, but it is not an event queue.

**Consequence:** "at-least-once wake-up delivery with duplicate detection" (Section 7.6, AGT-15) requires a new platform component: a durable event outbox with a per-consumer cursor, written in the same transaction as `EventStore.commit()`, plus a delivery loop to app subprocesses. This is Phase 0/1 platform work and should be named as such, with its own acceptance criteria. Without it the vertical slice's "task-created event" has nothing to fire it.

### 2.2 Commands have no idempotency key

AGT-12 and AGT-15 require idempotent effects. `POST /api/commands` and `EventStore.commit()` (`backend/app/events/store.py`) have no idempotency key, no request deduplication, and no way to look up "was this key already committed". The proposal places deduplication in the agent app (Section 12.4: "consumers deduplicate by event and run identifiers"). That is insufficient: a crash between "command committed" and "checkpoint written" produces a duplicate write on resume no matter how careful the consumer is.

**Fix:** add an optional `idempotency_key` to the command envelope, store it as event metadata, and have the router return the existing event for a repeated key. This is a small, contained platform change and belongs in Phase 0's "durable-run state-machine contract", because that contract is meaningless without it.

### 2.3 Capability authority is enforced in the client, not the server

Section 13.1 asserts "groundings are unavailable unless granted" and "model output cannot manufacture or widen a grant". Today the per-app command allowlist (`permissions.commands` in the manifest) is enforced inside the SDK's `CommandClient` (`src/sdk/sempkm_app_sdk/clients/commands.py`), which is code running in the app's own subprocess. The app token minted in `AppManager.start()` carries an empty permissions map. The server checks role and API-token scope (`commands:execute`), not which command types a given app may issue.

This is acceptable for first-party sync apps. It is not acceptable as the foundation of "typed authority checks" for an agent whose plans can be LLM-generated. **The grant check has to move server-side** (per-principal allowlist evaluated in the command router, with the agent IRI as principal) before AGT-12, AGT-31 and AGT-32 can be claimed. Note also that `/api/commands` is rate-limited to 20 requests per minute for all callers; a working agent will hit that within its first hour, so service principals need a separate limiter class.

### 2.4 There is no delegated-actor provenance

`EventStore.commit()` records `sempkm:performedBy` (a user IRI) and `sempkm:performedByRole`. There is no way to say "agent X acting on behalf of owner Y". The proposal's entire audit story (Section 14.1, "explain why it acted") depends on that distinction being in the event metadata.

The repository already has an accepted PROV-O alignment design (`.gsd/design/PROV-O-ALIGNMENT.md`) that the proposal never cites. `prov:Agent`, `prov:actedOnBehalfOf`, `prov:wasAssociatedWith`, `prov:used`, `prov:wasDerivedFrom` and `prov:wasRevisionOf` cover a large part of Sections 6.1, 6.2 and 6.5. The epistemic vocabulary should be built as a PROV-O extension, not a parallel `sempkm:` vocabulary that the PROV-O design will later want to migrate. The ops log (`urn:sempkm:ops-log`, already `prov:Activity`-based) is the natural home for admin-visible agent activity.

### 2.5 The copilot has no approval gate and no structured LLM interface

Section 2.2 lists "an LLM integration with SPARQL validation, correction, and approval". The copilot (`backend/app/copilot/service.py`, `backend/app/api/ai.py`) generates read-only SPARQL, validates syntax and predicates, retries on error, and executes. There is no human approval step, and there is no write path. LLM calls are raw `httpx` posts to an OpenAI-compatible `/v1/chat/completions` endpoint with prompt-in, text-out; there is no JSON-schema-constrained output, no tool-calling abstraction, no recording of prompt and response, and no token accounting.

The proposal assumes all of these ("LLM invocations as traceable, replaceable reasoning steps", "typed output", "budgets", "trace redaction"). An `LLMActivity` abstraction (provider adapter, schema-constrained output, recorded and redacted request/response, cost meter) is a prerequisite for `LLMInterpret` and `LLMProposePlan` and does not appear in any phase. The test stack already ships a mock LLM (`docker-compose.test.yml`), which should be the determinism mechanism for runtime tests.

### 2.6 WorkflowSpec is a UI wizard, not an execution model

Open question 1 asks whether `BehaviorSpec` and `WorkflowSpec` should "share a base execution vocabulary". `WorkflowSpec` (`backend/app/workflow/models.py`) is a SQLAlchemy row holding a JSON list of steps of type `form`, `view` or `dashboard`. It is a guided click-through, stored in SQLite, with no conditions, no state and no execution. There is no execution vocabulary to share. The question can be closed now: keep them separate, and resolve the naming collision in the UI ("Workflows" versus "Behaviors") so users do not expect one to run like the other. The non-goal "replacing SemPKM's existing WorkflowSpec" is moot for the same reason.

### 2.7 The platform is single-node

The validation queue is an in-process `asyncio.Queue`, the scheduler is an in-process tick loop, and app subprocesses talk over local Unix sockets. Open question 5 (leases across multiple SemPKM instances) can be answered now: the epic targets one runtime per instance, and leases exist only to survive restarts, not to coordinate replicas. Spending Phase 0 design on cross-instance coordination is wasted.

### 2.8 Smaller mismatches

- Section 12.5 proposes RDF for definitions and SQLite for operational state without mentioning the existing per-app operational graph `urn:sempkm:app:{appId}:state`, which is direct-CRUD and not event-sourced (`.gsd/design/APP-PLATFORM-DESIGN.md`, Section 4). The storage decision should be stated in terms of the three tiers that already exist: event-sourced current graph, app state graph, SQLite.
- The vertical slice needs a concrete type. `bpkm:Task` has `bpkm:priority` constrained to `low | medium | high | critical` and `bpkm:dueDate` (`models/basic-pkm`). PPV's `ActionItem` has its own priority. Pick one and say so; "task" is not a platform concept.
- Section 4.14 lists LDN as a transport; the LDN inbox today accepts only ActivityStreams `Offer | Announce | Update | Note` from a signature-verified WebID. Section 9 never says whether FIPA-style acts map onto AS2 types or replace them.
- Jaeger/OTLP is already in the dev stack. The trace model in Section 7.1 should be OpenTelemetry spans with NodeRun identifiers as attributes, not a bespoke trace format that will later need an exporter.
- The event log already supports compensation (`EventQueryService.build_compensation()` and undo). For SemPKM-internal effects, "compensation" should mean "undo the event", which removes the need for per-action compensation definitions for every command grounding. Only external groundings need bespoke compensation. Section 6.6 and open question 7 become much smaller.

---

## 3. Undefined or inconsistent runtime semantics

### 3.1 Reactive re-tick versus durable resume

Section 4.3 describes behavior trees as "repeatedly evaluated from the root". Section 7.6 describes a "durable cursor" and "replay without re-performing effects". These are two different execution models with different failure behaviour:

- AJAN and classic BTs re-tick from the root every cycle; a `running` child is re-entered, and conditions above it are re-evaluated (that is what makes them reactive).
- Temporal-style durable workflows resume at the saved cursor and do not re-evaluate anything above it.

The `suspended` status (Section 7.1) makes the tension concrete: on wake, does the runtime re-enter at the suspended node or restart from the root and rely on memoised results to skip completed siblings? The document must choose. **Recommended:** resume at the cursor, but re-evaluate every `Guard`, `Condition` and `BudgetGuard` ancestor on the path from root to cursor before continuing (a "reactive sequence with memory"). That gives reactivity where it matters (guards) without re-running actions. This belongs in Phase 0's state-machine contract with test cases.

### 3.2 No data-flow model between nodes

`SparqlSelect`, `ConstructPayload`, `LLMInterpret` and `SemPKMCommand` clearly pass data to one another, but the document never says how. AJAN uses the agent's knowledge graph as an implicit blackboard. Options are: named bindings in a per-run working-memory graph, a typed blackboard keyed by IRI, or explicit input/output ports on nodes. Whatever is chosen has to be checkpointed, redacted, and visible in the inspector (Section 11.4 promises "what evidence it read"). Define it before Phase 1, because the SHACL shapes for node properties depend on it.

### 3.3 Non-deterministic nodes versus deterministic replay

AGT-63 says replay must not re-execute external effects, and Section 19 says "replay produces the same decisions". That is only possible if every non-deterministic step (LLM call, SPARQL query against a live graph, HTTP call, clock read) is recorded as an activity result and replayed from the record. The document should adopt the Temporal distinction explicitly: tree logic is deterministic given recorded activity results; `LLMInterpret`, `InvokeMCP`, `InvokeHTTPAction`, `SparqlSelect` and `SetTimer` are activities. Today's list mixes both kinds under "action nodes".

### 3.4 Parallel is listed as initial and also as unresolved

`Parallel` appears under "initial control nodes" (Section 7.2), while open question 4 asks what the minimum safe parallel semantics are. Parallel branches with durable suspension and cancellation propagation are the hardest part of any BT runtime. Remove `Parallel` from the initial set, state that v1 trees are sequential, and treat parallelism as a separate design.

### 3.5 CONSTRUCT to command is an unspecified compiler

Section 3.4 allows SPARQL to "construct candidate payloads", and `ConstructPayload` feeds `SemPKMCommand`. The command API takes typed parameters (`type`, `properties`, `source`, `target`), not triples. Something must map a constructed graph to a list of `object.create` / `object.patch` / `edge.create` commands, validate it against the target SHACL shape, and mint IRIs under the agent's prefix. That component is not named anywhere and is where most of the "typed authority" actually lives.

### 3.6 Statement-level epistemic metadata has no representation decision

Section 6.2 wants ten epistemic categories with source, evidence, confidence, scope, expiry, contradiction links and supersession per item. RDF has no statement-level metadata without a choice among RDF-star (supported by RDF4J), named graphs per status, or reification. The choice affects every SPARQL condition node and every view. **Recommended:** one named graph per agent per epistemic status (for example `urn:sempkm:agent:{id}:hypotheses`), PROV-O for provenance, and no reification. Separately, agent-generated hypotheses must never land in `urn:sempkm:current` or they will appear in user views and search; `scope_to_current_graph()` needs an explicit rule for agent graphs.

### 3.7 Definitions and blank nodes

"Semantic diff" (Sections 6.5 and 11.2) is only tractable if BehaviorSpec graphs contain no blank nodes. Mandate skolemised node IRIs (`{spec}/node/{ulid}`) as a SHACL constraint, and mint versions as distinct IRIs linked by `prov:wasRevisionOf`. Also decide open question 3 now: compile to an internal representation at deploy time and pin runs to the IR hash, so that an ontology edit cannot silently change a running tree.

### 3.8 Inconsistencies in the text

- AGT-10 requires `Retry` and `Timeout` nodes; Phase 2 deliverables omit them.
- Section 7.1 defines five node statuses; Section 11.4 defines eleven UI states with no mapping.
- `promise` is listed as a communicative act (Section 4.8) and as a commitment object (Section 6.8); open question 11 leaves it open. Decide: `propose` and `accept` are the acts, `Commitment` is derived. Drop the `promise` act.
- Section 8.1 says the deliberator "emits an explicit rationale". If the deliberator is rule-based (as it should be in v1), rationale means "which rules fired with which bindings". Say so, or readers will assume an LLM in the loop.
- Phase 6 leaves the first transport open between LDN and XMPP. XMPP requires an XMPP server in the Compose stack, JID provisioning, and a client library; LDN exists and is signature-verified. Decide LDN.
- Naming drifts between "SemPKM Agents", "Semantic Agent Runtime", "Agent Studio", "resident semantic-agent app" and `apps/semantic-agent/`. Pick one product name and one app id.
- Acceptance criterion 1 ("no action beyond an auditable evaluation") means every task creation produces a run record. Without a retention or sampling policy that is unbounded growth in either RDF or SQLite; Section 14 has no retention design.

---

## 4. Missing features

Listed roughly by how early they are needed.

1. **Approval and clarification UX.** Human approval is the central gate of the vertical slice, yet nothing describes where approvals appear (an inbox panel, the object tab, email via the existing `EmailService`, mobile), how they expire, whether they can be batched, or how "approve and stop asking for this class" works. Graduated autonomy is mentioned only as a risk mitigation (Section 20) and has no requirement. It should be an AGT requirement in Phase 2 with an autonomy level per action class: `observe`, `propose`, `act-reversible`, `act`.
2. **Kill switch and shadow mode.** A global "pause all agents" control, and a per-behavior "shadow deploy" mode in which a new version runs against live events but only records what it would have done. Shadow mode is the single most effective de-risking tool for LLM-influenced behaviors and is cheaper than the full simulation harness in Section 14.3.
3. **Server-side grants and principals.** See 2.3 and 2.4. The agent needs to be a principal in the auth layer, with a token type distinct from user API tokens and from app tokens.
4. **Durable event outbox.** See 2.1.
5. **LLM activity abstraction.** See 2.5. Includes structured output, recording, redaction, cost metering and budgets (there is no token meter anywhere today).
6. **Multi-user semantics.** Instances have owners, members and teams. Is an agent per user, per team, or per instance? Can a member see the owner's agent runs? Can a member's task creation trigger the owner's agent? The proposal is written for a single owner.
7. **Run migration and handler versioning.** Section 7.6 says "migration or safe completion of runs across platform upgrades" and nothing more. Because apps can contribute node handlers (Section 7.5), a suspended run may wake to find its handler gone. Define: runs pinned to a handler version; if unavailable, the run enters `blocked` with an impasse rather than failing.
8. **Retention and garbage collection** for runs, node traces, working memory and dead letters. Event-store growth is already a known concern; agent traces multiply it.
9. **Threat model.** `docs/security-model.md` exists. Section 13 should extend it with concrete cases: exfiltration through `SendMessage` after reading a shared graph, capability description injection through imported MCP schemas, LDN messages that carry instructions, and grant escalation through an LLM-authored plan. Each needs a named control, not a principle.
10. **Time.** Durable timers need a clock source, timezone (the context service already tracks user time), and a recurrence model for recurring goals. Recurrence is mentioned only under future extensions.
11. **Non-functional requirements.** No targets for tick latency, events per second, RDF4J write amplification from traces, or LLM cost ceilings. Add a small NFR table.
12. **Documentation.** New user-facing surfaces require a guide chapter; the chapter registry lives in three places (`docs/guide/README.md`, `docs/guide/index.html`, `GUIDE_SECTIONS`). Trivial, but it is not in any phase.

---

## 5. Scope and delivery plan

### 5.1 Split into three epics

The current document is one epic with eight phases. Principle 3.11 (thin vertical slice) contradicts Section 15.1, which puts the agent Mental Model, a runtime, supervision, triggers, waits, approvals, traces, live visualisation, the Studio, and extension points all in scope.

Suggested split:

- **Epic A: Durable governed automation.** Platform prerequisites (event outbox, idempotency keys, agent principal with server-side grants, LLM activity abstraction), the `agents` Mental Model core (Agent, BehaviorSpec, BehaviorRun, NodeRun, Impasse, UncertaintySignal, Approval), the sequential runtime, the vertical slice, run inspection. This is current Phases 0 to 3 plus the prerequisites. It has a real user-visible outcome.
- **Epic B: Authoring and deliberation.** Studio editor, LLM-assisted drafts, Goal and Intention lifecycle, method selector, impasses. Current Phases 4 and 5.
- **Epic C: Social agency and governance.** Messages, protocols, commitments, LDN transport, capability import, VSM channels, audit behaviors. Current Phases 6 to 8.

Tag every AGT requirement with the epic that owns it. As written, the requirements list implies all of Section 16 is in scope for the first delivery.

### 5.2 Justify the architecture against the simple alternative

The proposal never compares itself to the obvious cheaper design: durable "automations" of the form event, condition, optional LLM step, approval, command, implemented as an app on the existing platform without BT, BDI or HTN vocabulary. Section 20 warns against "behavior-tree overreach" but does not show a scenario the simple design cannot handle. Add one paragraph with a concrete scenario (for example, a multi-step research task with fallback and clarification that spans days) and explain what the BT plus intention layer buys there. The same section should relate the design to the SHACL rules the platform already runs (`sh:SPARQLRule` in model bundles), which are a declarative reactive layer today and are never mentioned.

### 5.3 Close the decidable open questions

Of the sixteen open questions, these can be decided now and the document is weaker for leaving them open: 1 (separate), 3 (compile to IR at deploy), 4 (no parallel in v1), 5 (single node), 7 (undo for internal effects, custom only for external groundings), 8 (LDN), 11 (commitment derived from propose plus accept), 16 (rule-based method selector first). Record them as ADR entries; the repo already keeps `.gsd/DECISIONS.md`.

---

## 6. Product and UX observations

- **Legibility principle 3.10 is right but under-designed.** The six Studio panels are inventory, not a narrative. The first-run experience should be a single "Agent" page that answers four questions: what is it waiting on, what did it do recently, what does it want to do next, what does it need from me. The behavior tree canvas is a debugging surface, not the home screen.
- **Anthropomorphism risk is real in the copy.** "Semantic Tamagotchi", "quiet companion", "health state" invite users to read intent into a rule engine. Section 20 names the risk; the UX section should state the rule: personality words in UI only where they map to inspectable state (for example "waiting on you since Tuesday" rather than "feeling ignored").
- **Approval fatigue is the product-killer.** The proposal's mitigation list is fine, but the slice as specified ("any resulting mutation requires approval") will train users to rubber-stamp. The slice should include one reversible action class that executes without approval and is undoable from the run view, so that graduated autonomy is demonstrated, not deferred.
- **Progressive disclosure (11.3) needs an owner.** "Guided, Semantic, Source" is three editors. The first epic should ship Source (read-only Turtle) and a minimal Guided form for the slice's parameters, and leave the palette editor to Epic B.

---

## 7. Things the proposal gets right and should keep

For balance, and so the fixes above are not read as a rejection:

- Command-only mutation (3.4) and the rejection of AJAN's SPARQL UPDATE nodes.
- Separate versioning of definitions and executions (3.9) and pinning in-flight runs.
- Description versus grounding versus grant (6.6), and "discovery does not confer permission" (AGT-31).
- Impasse and UncertaintySignal as first-class objects with routing owned by the system (6.4).
- The evidence hierarchy (14.2) and "learned structures do not silently become policy" (14.4).
- The insistence that the versioned artifact, not the chat response, is the behavior (11.5).
- Starting from a single vertical slice with restart-during-wait and duplicate-delivery acceptance criteria (Section 18). Those two criteria are the right ones.

---

## 8. Recommended edits, in priority order

1. Add a "Platform prerequisites" phase before Phase 1: durable event outbox with consumer cursors; command idempotency keys; agent principal with server-side command allowlist and separate rate-limit class; `prov:actedOnBehalfOf` in event metadata; LLM activity abstraction with schema-constrained output, recording and metering.
2. Rewrite Section 2.2 to describe the substrate as it is, citing the PROV-O alignment design, the app state graph, event undo, the ops log, and Jaeger.
3. Define the execution model: resume-at-cursor with guard re-evaluation, activities versus logic, working-memory data flow, no `Parallel` in v1, compiled IR pinned per run.
4. Choose the epistemic representation (named graphs per status plus PROV-O) and forbid agent hypotheses in `urn:sempkm:current`.
5. Split into three epics and tag every AGT requirement with its epic.
6. Add requirements for autonomy levels, approval UX, kill switch, shadow mode, retention, multi-user ownership, and run migration.
7. Close open questions 1, 3, 4, 5, 7, 8, 11 and 16 as ADR entries.
8. Add a threat-model subsection extending `docs/security-model.md`, and an NFR table.
9. Fix the textual inconsistencies in 3.8 and settle on one product name and one app id.
10. Add the "why not a simple automation engine" paragraph and relate the design to existing SHACL rules.
