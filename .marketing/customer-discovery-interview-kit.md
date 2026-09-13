# SemPKM Customer Discovery Interview Kit

## Purpose

This kit is for validating the current SemPKM beachhead hypothesis with real users before turning the positioning work into final marketing copy.

The current beachhead hypothesis is:

> **Structured-PKM System Builders — especially schema-strained Obsidian users whose work genuinely requires types, properties, queries, and meaningful relationships.**

The core qualification question is:

> **If your current PKM became too complicated, would removing most of its structure solve the problem?**

If yes, SemPKM is probably not for them.

If no — because the structure is necessary to the work — they are a strong candidate for discovery.

The purpose of these interviews is **not** to persuade people to use SemPKM. It is to discover whether the problem, segment, and positioning hypotheses are real enough to deserve focused marketing and product work.

---

# 1. What We Are Trying to Validate

We currently believe that a valuable group of PKM users has built an implicit data model using combinations of:

- note types or object types;
- YAML/properties/frontmatter;
- templates;
- Bases, Dataview, or other queries;
- plugins such as Templater, Metadata Menu, Linter, QuickAdd, Meta Bind, etc.;
- scripts, regex, or one-off migrations;
- conventions for relationships;
- dashboards and specialized views.

We want to learn whether these users experience recurring pain from:

- schema drift and model evolution;
- keeping similar objects consistent;
- maintaining plugin/tooling stacks;
- representing meaningful relationships;
- querying across the model;
- preserving richer structure during migration/export;
- deciding how much structure to impose during capture;
- needing to simplify versus needing stronger infrastructure.

We also want to test whether SemPKM's current positioning ideas resonate:

- **Your PKM already has a schema. Make it explicit.**
- **You've designed a data model. Why are you maintaining it with YAML and scripts?**
- **Mental Models turn a PKM methodology into an installable system.**
- **Don't just link your notes. Say how they relate.**
- **A knowledge graph when you need meaning. Markdown files when you want files.**

Do not lead with these messages. They are tested near the end of the interview, after the participant has described their actual behavior.

---

# 2. First-Wave Recruiting Goal

Start with **five interviews**.

Do not wait until twenty people have agreed before beginning. Run five, compare what was learned, adjust the screener and interview questions, then recruit the next wave.

A useful initial mix:

- 3–4 structured Obsidian users;
- 1–2 people who moved between Obsidian and Tana, Capacities, Anytype, Notion, Logseq, or another structured PKM;
- ideally at least one person who deliberately simplified an elaborate setup, as counter-evidence.

After the first five, expand toward **8–12 interviews total** if the problem still looks promising.

---

# 3. Who to Recruit

## Strong candidates

Look for people who can say yes to several of these:

- I have different meaningful kinds of notes/objects: Paper, Person, Project, Meeting, Book, Client, Server, Claim, Source, Experiment, etc.
- Different kinds of notes have different expected properties.
- I use Properties/frontmatter heavily.
- I use Bases, Dataview, queries, dashboards, or database-like views.
- I use templates for different note types.
- I rely on multiple plugins to make the structure work.
- I have written, copied, or AI-generated scripts/regex to manipulate my vault.
- I have changed my metadata structure after many notes already existed.
- I care about the meaning of relationships, not merely whether two notes link.
- I have considered moving to or from Tana, Capacities, Anytype, Notion, Logseq, or another structured system.
- I care strongly about Markdown/files/local ownership/portability.

## Especially strong candidates

Prioritize people who describe the structure as necessary to their real work:

- academic or literature research;
- technical knowledge management;
- project/program management;
- CRM or relationship management;
- infrastructure/asset inventories;
- historical/archive work;
- worldbuilding;
- genealogy;
- collections/cataloging;
- scientific/experimental records;
- legal or policy research;
- any domain with multiple entity types and meaningful relationships.

## Useful counter-candidates

Also interview some people who once had elaborate systems but intentionally simplified them.

They help answer:

> Is SemPKM solving a real need, or productizing an overengineering habit that users eventually abandon?

---

# 4. Lightweight Screener

Do not make people fill out a long survey. Five questions are enough.

1. **Which PKM/note tools do you currently use most?**
2. **Do you use different note/object types with different properties or templates?**
3. **Which of these do you use regularly?** Properties/frontmatter, templates, Bases/Dataview/queries, metadata plugins, automation/plugins, scripts/regex, other.
4. **Have you ever had to reorganize or migrate metadata across existing notes?**
5. **Would simplifying away most of your structure make your system better, or would it prevent you from doing something important? Why?**

The fifth question is the most important.

Do not reject someone just because they answer differently than expected. Counter-examples are useful. The goal is to avoid spending the entire sample on casual note-taking users.

---

# 5. Interview Format

Target **30–40 minutes**.

Ask permission to take notes. If recording, explicitly ask permission before recording.

Whenever possible, ask the participant to **show their actual system** rather than describe it abstractly.

A screen-share walkthrough of a real vault is more useful than ten hypothetical opinions.

Recommended flow:

- 0–5 min: context and current system;
- 5–15 min: walkthrough of structure;
- 15–25 min: recent pain/history;
- 25–30 min: tradeoffs and alternatives;
- 30–40 min: SemPKM concept/message reaction, only after problem discovery.

---

# 6. Opening Script

Keep the opening neutral.

> Thanks for talking with me. I'm researching how people build structured personal knowledge systems — especially systems that go beyond ordinary notes into things like different note types, properties, queries, relationships, templates, and automation.
>
> I'm building something in this area, but I'm not trying to sell it to you during the interview. I'm much more interested in how your current system actually works, what has become painful, and what you've tried.
>
> There aren't right answers here. If your current setup works great, or if you've concluded that all this structure is a mistake, that's useful too.

Then begin with their system, not SemPKM.

---

# 7. Core Interview Questions

## A. Understand the system

### 1. Tell me how your PKM system is organized today.

Follow-ups:

- What kinds of things do you keep in it?
- Do you think of some notes as different kinds/types of things?
- What are the most important types?
- Why do those need to be different?

### 2. Could you show me one or two examples?

Ask them to show a real Paper, Person, Project, Book, Meeting, etc.

Look for:

- properties;
- templates;
- tags;
- folders;
- queries;
- relationships;
- plugin-generated interfaces;
- naming conventions;
- things the user has to remember manually.

### 3. How do you make sure notes of the same kind stay consistent?

Follow-ups:

- Is that enforced or just a convention?
- What happens if you forget a property?
- Do you have required fields?
- Which plugins or scripts help?

---

## B. Find real historical pain

### 4. Tell me about the last time you changed the structure of your system.

This is one of the highest-value questions.

Follow-ups:

- What triggered the change?
- How many existing notes did it affect?
- What did you have to change?
- How did you make the change?
- Did you use a plugin, regex, script, VS Code, AI, or manual edits?
- How long did it take?
- What did you decide wasn't worth fixing?
- Has this happened more than once?

### 5. Tell me about the last time your setup broke or became annoying to maintain.

Follow-ups:

- Was a plugin involved?
- Did two plugins disagree about metadata?
- Did an update break something?
- Did you have to learn or maintain code?
- What would stop working if one important plugin disappeared?

### 6. What's something you wish you could ask of your knowledge base but can't easily ask today?

This probes querying and relationship semantics without suggesting either.

Follow-ups:

- What would the query need to understand?
- Is the missing information already present but difficult to query?
- Would you need to change how you model your notes to answer it?

### 7. When two notes link, does the kind of relationship matter?

If yes:

- Give me an example.
- How do you encode that today?
- Do you ever need to query that relationship?

Do not introduce terms like RDF or typed edges.

---

## C. Test the simplification counter-hypothesis

### 8. When your system gets complicated, why not simplify it?

Do not soften this question. We want the real answer.

Possible strong-beachhead answer:

> Because I actually need Papers, Authors, Claims, Sources, etc. to behave differently.

Possible counter-answer:

> That's exactly what I eventually did; most of the structure wasn't adding value.

Both are valuable findings.

### 9. How much of the complexity feels essential versus self-inflicted?

Follow-ups:

- Which parts would you happily remove?
- Which parts would you refuse to lose?
- What capability would disappear if you simplified?

---

## D. Test ownership and switching

### 10. What keeps you on your current tool?

Do not assume the answer is files.

Probe only after they answer:

- plugins/ecosystem;
- Markdown;
- local files;
- mobile experience;
- speed;
- familiarity;
- integrations;
- community;
- specific workflows.

### 11. Have you tried or seriously considered another PKM tool?

Follow-ups:

- Which one?
- Why?
- What looked better?
- Why didn't you switch, or why did you switch back?
- What would you need preserved in a migration?

### 12. If you left your current tool tomorrow, what would you be most afraid of losing?

Listen for the difference between:

- documents;
- metadata;
- relationships;
- queries;
- views;
- workflow behavior;
- plugins;
- file access.

---

# 8. Solution and Message Testing

Do this only after the discovery portion.

## Step 1: Explain SemPKM minimally

Use a short neutral description:

> I'm working on SemPKM, which treats things like Papers, People, Projects, Claims, etc. as typed objects with explicit properties and relationships. Those definitions can be packaged into reusable Mental Models that also include things like validation and views. Underneath it's based on open semantic-web standards, and it can also expose objects as Markdown files/directories through a virtual filesystem.

Then stop talking.

Ask:

> What's your immediate reaction?

Then:

> What sounds useful?
>
> What sounds unnecessary or concerning?
>
> What would stop you from trying it?

Do not defend SemPKM immediately when they criticize it.

## Step 2: Test message territories individually

Show one at a time. Ask the participant to rate each informally as:

- immediately describes my problem;
- somewhat relevant;
- clever but not really my problem;
- confusing;
- actively off-putting.

### A. Schema

> **Your PKM already has a schema. Make it explicit.**

### B. Maintenance

> **You've designed a data model. Why are you maintaining it with YAML and scripts?**

### C. Mental Models

> **Mental Models turn a PKM methodology into an installable system.**

### D. Relationships

> **Don't just link your notes. Say how they relate.**

### E. Files

> **A knowledge graph when you need meaning. Markdown files when you want files.**

Ask after each:

> What do you think this means?

That question is more useful than asking whether they like the copy.

## Step 3: Test behavior, not praise

Finish with something concrete:

> Would you be interested in trying this with a copy/import of part of your real system?

Possible strong signals:

- volunteers to test;
- offers sample vault/data;
- asks detailed migration questions;
- asks whether SemPKM can express a real part of their model;
- schedules a follow-up;
- asks for access without prompting.

Weak signal:

> "This is cool."

---

# 9. Questions NOT to Ask

Avoid questions that practically manufacture a positive answer.

## Don't ask

> Would automatic schema enforcement be useful?

Ask instead:

> How do you keep these notes consistent today?

## Don't ask

> Would you like typed relationships?

Ask instead:

> Does it ever matter *how* two notes are related?

## Don't ask

> Do you worry about lock-in?

Ask instead:

> If you left tomorrow, what would you be afraid of losing?

## Don't ask

> Would reusable Mental Models save you time?

Ask instead:

> When you started this system, how did you decide on its structure?

## Don't ask

> Would you pay for this?

Not yet. First establish that the problem is real and that they will spend time trying the solution.

---

# 10. Interview Notes Template

Create one record per participant.

```markdown
# Interview: <participant-code>

Date:
Tool(s):
Use case/domain:
Experience level:
Recording consent: yes/no

## Current system

Primary note/object types:

Important properties:

Queries/views used:

Critical plugins/tools:

Scripts/automation:

## Strongest observed pains

1.
2.
3.

## Most recent schema/model change

What changed:

Why:

Number of affected notes/objects:

How they migrated it:

Cost/frustration:

## Relationships

Do relationship semantics matter?

Example:

Current workaround:

## Simplification test

Would removing structure solve the problem?

Why/why not?

## Ownership / portability

What would they fear losing?

How important are direct files?

## Alternatives tried

Tool:
Reason tried:
Why stayed/left:

## Language worth preserving

Exact phrases the participant used:

- "..."
- "..."

## Positioning reactions

Schema message:
Maintenance message:
Mental Models message:
Relationships message:
Files/VFS message:

## Behavioral signal

Would try SemPKM with real data: yes/no/maybe
Offered follow-up: yes/no
Offered sample vault/data: yes/no
Asked for access: yes/no

## Biggest surprise


## Evidence against our hypothesis


## Interviewer interpretation


```

Prefer participant codes over public names in research notes unless there is a reason to retain identity and the participant expects it.

---

# 11. Simple Prospect Score

Do not turn qualitative interviews into fake precision. This score only helps compare participants after several interviews.

Give 0, 1, or 2 points for each dimension.

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Distinct object/note types | none | informal | explicit/important |
| Different schemas per type | no | some | central to system |
| Querying/views | minimal | regular | essential |
| Relationship semantics | generic links enough | sometimes matters | explicitly modeled/needed |
| Schema evolution pain | none | occasional | repeated/costly |
| Tool/plugin maintenance | minimal | moderate | significant |
| Simplification response | wants less structure | mixed | structure cannot be removed |
| Ownership/portability | low concern | moderate | major switching constraint |
| Willingness to tinker | dislikes all tinkering | some | actively builds system |
| Behavioral interest in SemPKM | none | curiosity | willing to test with real data |

A high score is not "a better person." It means closer fit to the current beachhead hypothesis.

---

# 12. What Would Count as Validation?

Do not expect unanimous agreement.

After 5 interviews, pause and compare notes.

Encouraging evidence would include several participants independently showing some of the following without being prompted:

- meaningful note/object types;
- type-specific property expectations;
- painful changes to existing metadata;
- scripts/plugins/manual work to maintain consistency;
- queries that depend on consistent structure;
- need for relationship semantics beyond generic links;
- fear of losing more than plain document text during migration;
- an explicit reason they cannot simply remove the structure;
- strong recognition of one or more positioning messages;
- willingness to test SemPKM against real data.

Very strong evidence is historical behavior:

- they already wrote code to solve the problem;
- they changed tools because of the problem;
- they abandoned a migration because it was too expensive;
- they maintain documentation for their own schema;
- they have a real example SemPKM could model immediately.

## Evidence that should make us reconsider

Take these seriously:

- most elaborate users eventually simplify and are happier;
- formal structure interferes with capture more than it helps later;
- users care far more about plugin flexibility than integrated structure;
- file-native storage is non-negotiable even with VFS;
- the perceived migration cost overwhelms the value proposition;
- "schema" and "data model" language consistently fails to resonate;
- Mental Models sound more restrictive than useful;
- users like the idea but nobody is willing to try it with real data.

---

# 13. Debrief After Every Interview

Immediately after the call, spend five minutes recording:

1. What did they say that confirmed our hypothesis?
2. What did they say that contradicted it?
3. What exact phrase did they use that was better than our marketing language?
4. What real behavior demonstrated pain?
5. What was the most painful event they described?
6. Which positioning message did they correctly interpret fastest?
7. What would stop them from adopting SemPKM?
8. Are they worth a follow-up prototype/import session?

Do this before conducting another interview whenever possible.

---

# 14. Recruitment Approach

## Do not recruit "dissatisfied users" as the primary framing

A page titled something like **"Are you frustrated with Obsidian?"** would bias the sample toward anger and invite generic complaints unrelated to SemPKM's actual beachhead.

Instead recruit for the behavior:

> **Do you use Obsidian as more than a note app?**
>
> I'm researching people who've built structured PKM systems using things like Properties, templates, Bases/Dataview, metadata plugins, relationships, or scripts. I'd like to see how your system works and learn what becomes difficult as it grows.

That finds the people we want without telling them what pain they are supposed to have.

## Recommended small landing page

A dedicated page is useful because message-board posts can point somewhere that explains the research consistently.

It does not need to be a marketing site. Keep it simple.

Suggested URL shape:

`sempkm.metacoding.io/research/structured-pkm`

Suggested page structure:

### Heading

**Do you use your PKM like a personal database or information system?**

### Short explanation

> I'm researching how advanced PKM users structure information with note types, properties, templates, queries, relationships, plugins, and scripts — and what becomes painful as those systems grow.
>
> I'm especially interested in seeing real setups rather than hearing abstract opinions.

### Who we want to talk to

- people with multiple meaningful note/object types;
- people using Properties/frontmatter heavily;
- users of Bases, Dataview, metadata plugins, templates, or scripts;
- people who have reorganized or migrated a large vault;
- people who tried object-oriented tools such as Tana, Capacities, Anytype, or Notion;
- people who deliberately simplified an elaborate PKM system.

### What the conversation involves

> 30–40 minute conversation, ideally with an optional screen-share walkthrough of your setup. This is research, not a sales demo.

### CTA

**Volunteer for a research conversation**

Link to a short form containing the five screener questions.

## Message-board recruiting

Post to communities where structured-PKM behavior already occurs, but follow each community's rules about research/recruitment posts.

Do not cross-post identical promotional copy everywhere at once.

Start with one or two communities, see who responds, and refine the wording.

Recruiting posts should emphasize:

- curiosity about their system;
- specific structured behaviors;
- willingness to learn from people who simplified as well as people who doubled down;
- that it is not a sales call;
- approximate time commitment;
- whether an incentive is offered.

A modest interview incentive can help when recruiting strangers, but it is not necessary for the first wave if community members are enthusiastic about showing their setups.

---

# 15. First-Wave Process

1. Put up the lightweight research page and screener.
2. Recruit enough people to schedule **five** interviews — not fifty signups.
3. Conduct the first two interviews.
4. Review whether the questions are producing concrete historical examples.
5. Adjust the script if necessary.
6. Complete five.
7. Compare notes against `jobs-pains-gains-positioning.md`.
8. Revise the beachhead and messaging hypotheses.
9. Recruit the next 3–7 people using what was learned.
10. Only then begin turning the winning language into serious homepage copy.

The research is successful even if the initial positioning is wrong. The goal is to discover the strongest real problem before optimizing the message around it.
