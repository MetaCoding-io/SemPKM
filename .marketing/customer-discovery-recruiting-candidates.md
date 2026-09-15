# SemPKM Customer Discovery — Recruiting Candidates

## Purpose

This is a working list of **publicly identifiable forum/community participants** who recently described problems relevant to the SemPKM customer-discovery hypotheses.

The list is intended for respectful, one-to-one research outreach. It contains only public handles and links to public posts/comments. **Do not enrich this list with private email addresses, employer data, real names, or other off-platform personal information unless the person has explicitly published a preferred research/contact channel.**

The goal is not to persuade these people to use SemPKM. The first-wave goal is to interview people who can show us how structured PKM systems evolve in real use.

## Outreach priority legend

- **P1 prospect** — unusually close to the current beachhead; contact first.
- **P2 prospect** — useful customer interview, but narrower or less clearly structured.
- **Expert/builder** — valuable domain interview, but do not count as ordinary customer evidence.
- **Counter-signal** — deliberately simplified or rejected complexity; valuable falsification interview.

A candidate may appear under several complaint categories. Contact the person once; the tags are there to explain why they are interesting.

---

## Recommended first outreach wave

If we want five interviews, start by contacting roughly 10–12 of these people.

| Priority | Public handle | Community | Why this person is unusually useful | Complaint tags | Public source |
|---|---|---|---|---|---|
| P1 prospect | `ChuckHaas` | Obsidian Forum | Explicitly wants strong object types because changing a Book type should propagate to existing Book notes. This is almost the SemPKM beachhead stated directly. | schema drift, types, model evolution | https://forum.obsidian.md/t/strong-object-typing/117966 |
| P1 prospect | `wondwrstruck` | r/ObsidianMD | Likes building/tinkering, left Notion for ownership, is now fighting Anytype's structure, wants cross-space links and local Markdown. Strong structure + ownership + flexibility tension. | rigidity, migration, portability, willingness to tinker | https://www.reddit.com/r/ObsidianMD/comments/1v0bcbk/migrating_from_anytype_to_obsidian_and_seeking/ |
| P1 prospect | `OkTomatillo5699` | r/PKMS | Academic managing research/projects/teaching/admin/personal tracking; has tried Obsidian, Capacities and Tana; needs both free capture and structured querying/relationships and says the system must remain maintainable long-term. | capture friction, querying, relationships, plugin maintenance, complexity | https://www.reddit.com/r/PKMS/comments/1qybh8m/obsidiancapacitiestanaloking_for_an_unicorn/ |
| P1 prospect | `Fuzzy_Run5971` | r/ObsidianMD | Has ~100 structured reading notes and wants bulk changes to properties/values; explicitly compares the pain with easier database edits in Notion. | schema drift, migration | https://www.reddit.com/r/ObsidianMD/comments/1ts04jm/editing_properties/ |
| P1 prospect | `mi-nombre-es-el-jefe` | r/capacitiesapp | Imported an Obsidian work vault into Capacities and is frustrated that querying Person objects does not behave like tag querying; does not want duplicate Person-object + Person-tag semantics. | querying, relationship semantics, object-vs-tag, migration | https://www.reddit.com/r/capacitiesapp/comments/1uxjpul/object_vs_tag_queries/ |
| P1 prospect | `A_King_1980` | r/ObsidianMD | Uses Book/Movie/Person templates and wants template/property changes applied to previously created instances. | schema drift, model evolution | https://www.reddit.com/r/ObsidianMD/comments/1vwcill/updating_templates/ |
| P1 prospect | `No_Pumpkin4381` | r/ObsidianMD | Describes plugin overlap, abandonment and incompatible assumptions, then writes/generates custom plugins when the ecosystem cannot provide a coherent solution. | plugin maintenance, willingness to tinker, complexity | https://www.reddit.com/r/ObsidianMD/comments/1upqpbq/we_dont_need_20_halfmaintained_plugins_for_the/ |
| P1 prospect | `MRoselius` | r/capacitiesapp | Manages a team of sysadmins and asks whether M365 products should be tags or Product objects. Excellent type-vs-tag/domain-model interview. | object-vs-tag, relationship semantics, conceptual friction | https://www.reddit.com/r/capacitiesapp/comments/1qj7xxv/tags_vs_objects_new_user_question/ |
| P1 prospect | `FlatFiveFreddie` | r/ObsidianMD | Uses thought templates, File Nav and Bases, but mobile capture latency causes thoughts to disappear; wants capture now/process later. | capture friction, progressive formalization | https://www.reddit.com/r/ObsidianMD/comments/1vnjopo/quick_capture/ |
| P1 prospect | `ChackanKun` | r/ObsidianMD | Choosing between Notion and Obsidian; values local Markdown and future-proofing but worries about long-term complexity and plugin dependence. | portability, plugin maintenance, complexity | https://www.reddit.com/r/ObsidianMD/comments/1wbkuff/deciding_between_obsidian_and_notion_some_help/ |
| Counter-signal | `Kronostatic` | r/ObsidianMD | Removed Dataview/non-Markdown plugins and says they “stopped programming my vault and shifted to using and writing my notes.” Ideal falsification interview. | simplification response, plugin maintenance, portability | https://www.reddit.com/r/ObsidianMD/comments/1vztk2y/what_did_you_remove_from_your_obsidian_setup_that/ |
| Expert/builder | `quiet__reader` | r/ObsidianMD | Metadata Menu/Fileclass author independently converged on a schema + typed/validated-property input layer with Bases for query/display. Extremely valuable adjacent-architecture interview, but not an ordinary customer. | schema, plugin architecture, typed notes, querying | https://www.reddit.com/r/ObsidianMD/comments/1v1ydjn/as_the_author_of_metadata_menu_i_rebuilt_it_from/ |

---

# Candidates by complaint category

## 1. Schema drift / model evolution

### `ChuckHaas` — **P1 prospect**

- **When:** September 4, 2026
- **Signal:** Wants “strong object types” in Obsidian. Their example is adding a new `cost` property to the Book type after many Book notes already exist and expecting the change to propagate.
- **Why interview:** Direct test of whether explicit types + model evolution are valuable enough to motivate a switch.
- **Source:** https://forum.obsidian.md/t/strong-object-typing/117966

### `A_King_1980` — **P1 prospect**

- **When:** August 23, 2026
- **Signal:** Has Book, Movie and Person templates and asks how to remove/reorder a property and apply the change to files previously created from the Movie template.
- **Why interview:** Very clean example of “template is not a type.”
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1vwcill/updating_templates/

### `Fuzzy_Run5971` — **P1 prospect**

- **When:** May 30, 2026
- **Signal:** Has 100 reading notes with a `genre` property, needs bulk additions and typo correction across instances, and notes this was easy in Notion.
- **Why interview:** Good structured-PKM user with an actual migration/update event rather than a hypothetical complaint.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1ts04jm/editing_properties/

### `quiet__reader` — **Expert/builder**

- **When:** July 2026
- **Signal:** Rebuilt Metadata Menu as Fileclass around the principle that one plugin should own the schema/input layer: typed, validated properties per note type with guided input, while Bases owns query/display.
- **Why interview:** Strong competitive/architectural intelligence; independent convergence on part of SemPKM's thesis.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1v1ydjn/as_the_author_of_metadata_menu_i_rebuilt_it_from/

---

## 2. Plugin maintenance / fragmented infrastructure

### `No_Pumpkin4381` — **P1 prospect**

- **When:** July 7, 2026
- **Signal:** Complains that multiple plugins solve overlapping portions of the same niche with different assumptions, maintenance status, syntax and compatibility; eventually had Codex build a custom plugin.
- **Why interview:** Excellent test of “plugins add powers, Mental Models add meaning” and whether integration is genuinely valuable.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1upqpbq/we_dont_need_20_halfmaintained_plugins_for_the/

### `ChackanKun` — **P1 prospect**

- **When:** September 2026
- **Signal:** Likes local Markdown but worries that useful Obsidian functionality is plugin-dependent and could disappear when plugins stop being maintained.
- **Why interview:** Tests whether file ownership offsets ecosystem fragility, and whether integrated structure is attractive.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1wbkuff/deciding_between_obsidian_and_notion_some_help/

### `Downtown-Art2865` — **P2 prospect**

- **When:** May 5, 2026
- **Signal:** Engineering/AI knowledge base with ~3,200 notes and ~14k links; rebuilt plugin setup from scratch twice after it became bloated.
- **Why interview:** Mature vault; useful for distinguishing essential infrastructure from “plugin collecting.”
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1t4eilr/my_obsidian_plugin_list_in_2026_after_deleting/

### `JKSahara` — **Counter-signal**

- **When:** September 2026 discussion
- **Signal:** Reduced 20+ community plugins to three after realizing configuration was taking more time than note-taking.
- **Why interview:** Direct countercase: when does simplifying win instead of adopting stronger infrastructure?
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1vztk2y/what_did_you_remove_from_your_obsidian_setup_that/

---

## 3. Capture friction / progressive formalization

### `FlatFiveFreddie` — **P1 prospect**

- **When:** August 13, 2026
- **Signal:** Desktop flow uses a thought shortcut/template and then surfaces items via File Nav/Bases; mobile indexing latency kills ephemeral thoughts, so they want a capture-then-process layer.
- **Why interview:** Structured enough to be relevant while explicitly needing capture to precede organization.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1vnjopo/quick_capture/

### `xRamos` — **P2 prospect**

- **When:** August 24, 2026
- **Signal:** Wants one-tap/voice quick capture into Obsidian with as little friction as possible, potentially through an inbox before later processing.
- **Why interview:** Useful for testing where structure must stay out of the capture path.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1vx7v75/whats_your_fastest_way_to_capture_ideas_into/

### `MapLow2754` — **Expert/builder / research peer**

- **When:** April 19, 2026
- **Signal:** Explicitly frames the problem as conversion from a vague thought into usable structure and is building/surveying an AI organization product.
- **Why interview:** Useful conceptual interview, but their own product work makes them a research peer rather than ordinary prospect.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1sq0gzf/do_you_organize_while_capturing_or_capture_first/

### `Visual-Elk2388` — **Expert/builder**

- **When:** April 15, 2026
- **Signal:** Loved the object-oriented model of Capacities/Anytype but preferred Obsidian, so built an Objects plugin specifically to create typed/template-backed notes inline without leaving writing flow.
- **Why interview:** Independent evidence that object semantics are desirable but capture workflow can kill them.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1smemow/obsidian_but_with_objectorientednotes/

---

## 4. Rigidity / object-model friction

### `wondwrstruck` — **P1 prospect**

- **When:** July 18, 2026
- **Signal:** Says they are “fighting Anytype's structure rather than working with it,” while still liking customization, advanced setups and local data ownership.
- **Why interview:** Near-ideal test of whether SemPKM can offer stronger semantics without recreating Anytype-style rigidity.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1v0bcbk/migrating_from_anytype_to_obsidian_and_seeking/

### `Far-Butterscotch2405` — **P2 prospect**

- **When:** July 2026
- **Signal:** Realized part of their Capacities setup confusion came from trying to use Project objects as folders.
- **Why interview:** Excellent objects-vs-locations conceptual confusion.
- **Source:** https://www.reddit.com/r/capacitiesapp/comments/1uqytu8/how_do_you_use_projects/

### `NoFix365` — **P2 prospect**

- **When:** September 2026
- **Signal:** Calls Tana the most powerful note tool they have used but still “complicated” and argues its outliner needed to be made easier to use.
- **Why interview:** Strong evidence that structure can be highly valued while usability remains a barrier.
- **Source:** https://www.reddit.com/r/TanaInc/comments/1vmccz1/i_just_have_so_many_questions/

### `OkTomatillo5699` — **P1 prospect**

- **When:** February 2026
- **Signal:** Tried Obsidian/Capacities/Tana extensively; wants free natural writing first, then retrieval/structure later, while also needing rich research objects and relationships.
- **Why interview:** Particularly useful for testing progressive formalization.
- **Source:** https://www.reddit.com/r/PKMS/comments/1qybh8m/obsidiancapacitiestanaloking_for_an_unicorn/

---

## 5. Relationship semantics / object-vs-tag confusion

### `mi-nombre-es-el-jefe` — **P1 prospect**

- **When:** July 2026
- **Signal:** Imported an Obsidian work vault into Capacities. Wants queries over blocks that mention a Person object, but tags provide the behavior and objects do not; explicitly rejects maintaining both `@Person1` and `#Person1`.
- **Why interview:** Great test of identity, reference, backlinks, querying and semantic duplication.
- **Source:** https://www.reddit.com/r/capacitiesapp/comments/1uxjpul/object_vs_tag_queries/

### `MRoselius` — **P1 prospect**

- **When:** January 2026
- **Signal:** Manages M365 product knowledge and asks whether OneDrive/SharePoint/Teams should remain tags or become Product objects, and what the semantic benefit would be.
- **Why interview:** Extremely clean type/tag/object modeling question grounded in a real work domain.
- **Source:** https://www.reddit.com/r/capacitiesapp/comments/1qj7xxv/tags_vs_objects_new_user_question/

### `laforge_warpcore` — **P2 prospect**

- **When:** August 2026 comment
- **Signal:** Has a Project object with summary/dates/context plus related Conversation objects and queries for related meetings; explicitly wishes tagged blocks could participate better in those relationships.
- **Why interview:** Mature object-based workflow with concrete cross-object relation needs.
- **Source:** https://www.reddit.com/r/capacitiesapp/comments/1uqytu8/how_do_you_use_projects/

---

## 6. Migration / system transfer

### `samurai--cat` — **P2 prospect**

- **When:** May 18, 2026
- **Signal:** Moving a two-year university/study workflow from Notion to Obsidian; export/import breaks expected structure and media placement.
- **Why interview:** Useful document/system migration story, though less clearly schema-heavy than the P1 group.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1tgmwcw/switching_from_notion_to_obsidian_need_tips/

### `wondwrstruck` — **P1 prospect**

- **When:** July 18, 2026
- **Signal:** Has moved from Notion to Anytype and is considering another move to Obsidian because Anytype's current structure no longer fits.
- **Why interview:** Multiple migrations reveal exactly what people discover only after living with a system.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1v0bcbk/migrating_from_anytype_to_obsidian_and_seeking/

### `bitbonsai` — **Expert/builder**

- **When:** October 5, 2025
- **Signal:** Tried to migrate a 1.8GB/1700+ file Notion workspace; existing tools broke/mangled links, so built a migration tool. Notes that Notion databases cannot be recreated from its export format.
- **Why interview:** Not as recent as the rest, but unusually deep migration expertise and direct knowledge of what “documents survive, system does not” means technically.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1nyw5c4/i_migrated_18gb_from_notion_to_obsidian_existing/

---

## 7. Portability / file ownership / system ownership

### `Pleasant-Minute-1793` — **P2 prospect**

- **When:** May 13, 2026
- **Signal:** Says Notion export preserves text while losing structures, design, views, associations and setups; was considering Notion as an organizational source of truth and lost confidence.
- **Why interview:** Excellent “document portability vs system portability” interview.
- **Source:** https://www.reddit.com/r/Notion/comments/1tcacbh/notions_importexport_is_an_absolute_disaster/

### `ChackanKun` — **P1 prospect**

- **When:** September 2026
- **Signal:** Specifically values local Markdown because it feels future-proof, while worrying about plugin-dependent behavior.
- **Why interview:** Direct opportunity to test whether the SemPKM VFS plus open semantic model actually satisfies a file-native user's trust model.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1wbkuff/deciding_between_obsidian_and_notion_some_help/

### `wondwrstruck` — **P1 prospect**

- **When:** July 18, 2026
- **Signal:** Says data ownership was the main reason for leaving Notion and describes local `.md` files that outlive the app as giving “immense peace of mind.”
- **Why interview:** The right person to challenge our claim that VFS + RDF can satisfy the same psychological requirement as file-native storage.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1v0bcbk/migrating_from_anytype_to_obsidian_and_seeking/

### `evyevenly` — **P2 prospect**

- **When:** August 25, 2026
- **Signal:** Likes Notion databases but hesitates to commit to Obsidian because database-like structure is important; thread centers heavily on local ownership vs cloud dependence.
- **Why interview:** Useful boundary case between database UX and file ownership.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1vxnya8/obsidian_vs_notion/

---

## 8. Querying / views over structured knowledge

### `mi-nombre-es-el-jefe` — **P1 prospect**

- **Signal:** Wants queryable backlinks/content mentions of Person objects, not a duplicate tag system.
- **Source:** https://www.reddit.com/r/capacitiesapp/comments/1uxjpul/object_vs_tag_queries/

### `OkTomatillo5699` — **P1 prospect**

- **Signal:** Uses Dataview to retrieve free-form annotations, aggregate multiple mood observations, combine tags and numeric values, and show results as tables/calendars; could not reproduce the same natural workflow in Capacities/Tana.
- **Source:** https://www.reddit.com/r/PKMS/comments/1qybh8m/obsidiancapacitiestanaloking_for_an_unicorn/

### `ichbin-deinvater` — **P2 prospect**

- **When:** July 2026 comment
- **Signal:** Uses meeting templates with frontmatter + Bases to see meetings associated with a person, company, customer or project.
- **Why interview:** A useful “structured Obsidian that now works” positive control: what would SemPKM need to improve enough to justify switching?
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1v5kk4j/how_much_time_do_you_spend_managing_obsidian/

---

## 9. Complexity / system-maintenance tax

### `InevitableHealth2729` — **P2 prospect / research-minded user**

- **When:** July 2026
- **Signal:** Explicitly asks how much Obsidian time goes to learning/configuring plugins, organizing, maintaining, troubleshooting and workflow tweaking versus using information.
- **Why interview:** Their own concern maps directly to the maintenance-tax hypothesis.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1v5kk4j/how_much_time_do_you_spend_managing_obsidian/

### `Drafting-` — **P2 prospect**

- **When:** July 2026 comment
- **Signal:** Spends substantial time designing/implementing/testing templates and frameworks, partly because it is enjoyable but with the goal of reducing future friction.
- **Why interview:** Good “tinkering is a feature, not only pain” case.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1v5kk4j/how_much_time_do_you_spend_managing_obsidian/

### `AdministrativeFile78` — **P2 prospect / positive control**

- **When:** July 2026 comment
- **Signal:** Estimates ~500 hours tinkering since 2020 but says the resulting setup is now perfect and needs almost no management.
- **Why interview:** Tests whether up-front system building can itself be an acceptable solution and what parts are transferable/reusable.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1v5kk4j/how_much_time_do_you_spend_managing_obsidian/

### `NoFix365` — **P2 prospect**

- **When:** September 2026
- **Signal:** Loves Tana's power but calls it complicated; commenters characterize the learning curve as requiring computer-science-level understanding.
- **Why interview:** Helps separate valuable sophistication from unnecessary conceptual tax.
- **Source:** https://www.reddit.com/r/TanaInc/comments/1vmccz1/i_just_have_so_many_questions/

---

## 10. Simplification response / “maybe structure is the problem”

### `Kronostatic` — **Counter-signal**

- **When:** September 2026
- **Signal:** Replaced Dataview with sparse Bases, removed non-Markdown behavior, uninstalled Dataview and now avoids community-plugin dependence. Their phrase: stopped programming the vault and shifted to using/writing notes.
- **Why interview:** One of the most important people to interview because their solution is the opposite of ours.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1vztk2y/what_did_you_remove_from_your_obsidian_setup_that/

### `CatSauce66` — **Counter-signal**

- **When:** July 2026 comment
- **Signal:** Says the first year was heavily spent tinkering, then concluded they only needed ~10% of it and deleted the rest.
- **Why interview:** Ask exactly what structure survived and why the discarded structure failed to earn its cost.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1v5kk4j/how_much_time_do_you_spend_managing_obsidian/

### `JKSahara` — **Counter-signal**

- **When:** September 2026
- **Signal:** Reduced 20+ plugins to three because configuration was displacing note-taking.
- **Why interview:** Strong test of our qualification question: did simplification lose anything materially important?
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1vztk2y/what_did_you_remove_from_your_obsidian_setup_that/

---

## 11. Willingness to tinker / build a personal information system

### `Visual-Elk2388` — **Expert/builder**

- **When:** April 15, 2026
- **Signal:** Tried many PKM products, says object-oriented thinking changed everything, then built an Obsidian Objects plugin to adapt the model to their preferred workflow.
- **Why interview:** Very strong proof that some users want the semantic model enough to build missing infrastructure themselves.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1smemow/obsidian_but_with_objectorientednotes/

### `Majestic_Focus_420` — **P2 prospect**

- **When:** July 2026 comment
- **Signal:** Says vault tweaking is almost a hobby and gives compounding returns; is adding a `type` property to every frontmatter to conform to a knowledge-format specification.
- **Why interview:** High willingness to model/tinker. Ask which plumbing they enjoy versus which they would gladly delegate.
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1v5kk4j/how_much_time_do_you_spend_managing_obsidian/

### `wondwrstruck` — **P1 prospect**

- **When:** July 18, 2026
- **Signal:** Explicitly says they enjoy building and tinkering and are fine with community plugins/advanced setups.
- **Why interview:** Tests our hypothesis that the promise should be “tinker with the model, not the plumbing,” not “no configuration.”
- **Source:** https://www.reddit.com/r/ObsidianMD/comments/1v0bcbk/migrating_from_anytype_to_obsidian_and_seeking/

---

# Suggested outreach method

For Reddit participants, use a short Reddit DM/chat request rather than replying publicly with a product pitch. For Obsidian Forum participants, use the forum's private-message mechanism if their account allows it.

A good first message is specific to the post:

> Hi — I found your post about **[specific issue]** while researching how people build structured PKM systems. I'm the developer of an open-source PKM project, but I'm not looking to sell you anything; I'm trying to understand how these systems actually evolve in real use. Your example about **[one concrete detail from their post]** is exactly the kind of thing I'm studying. Would you be open to a 30–40 minute call where you walk me through how your setup works and what became difficult? Happy to share the research page with more context.

Once the research page is deployed, include:

`https://sempkm.metacoding.io/research/structured-pkm/`

Do **not** lead with a SemPKM feature list or tell the person that SemPKM solves their complaint. The interview is much more valuable if they explain their existing problem and alternatives before seeing the solution.

---

# Sampling guardrails

For the first five completed interviews, aim for:

1. **2–3 P1 structured Obsidian/system-builder prospects** (`ChuckHaas`, `Fuzzy_Run5971`, `A_King_1980`, `No_Pumpkin4381`, or comparable).
2. **1 cross-product structured user** (`wondwrstruck`, `mi-nombre-es-el-jefe`, `MRoselius`, or `OkTomatillo5699`).
3. **1 deliberate simplifier/counter-signal** (`Kronostatic`, `CatSauce66`, or `JKSahara`).

Treat builder/expert conversations such as `quiet__reader` and `Visual-Elk2388` as a separate track. They can produce exceptional product and ecosystem insight, but five interviews with plugin authors would not validate five ordinary customers.

## Status

This is a **public-source recruiting shortlist**, not a contact database. It should be updated as people are contacted so we avoid duplicate outreach. Suggested fields to add after outreach begins:

- contacted date
- channel
- response
- scheduled date
- interview completed
- notes file / interview ID

Do not store sensitive personal information in this repository.
