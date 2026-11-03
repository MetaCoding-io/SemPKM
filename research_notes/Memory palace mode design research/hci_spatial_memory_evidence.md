# HCI and cognitive-science evidence on spatial environments and the method of loci in software for personal information

Scope note: this brief covers controlled studies of virtual/VR memory palaces, classic spatial-UI information-retrieval research, the cognitive-psychology moderators of method-of-loci (MoL) effectiveness, gamification and desktop-metaphor evidence, and failure modes, ending with design implications for a 2D top-down, user-built, avatar-walked "memory palace mode" in a PKM app. Current as of November 2026. Where I could only reach an abstract or a secondary summary, I say so.

---

## Key Question 1: What do controlled studies of virtual memory palaces show (Krokos et al.; Legge et al. 2012; Fassbender & Heiden; Huttner & Robra-Bissantz; 2020–2026 follow-ups)? Effect sizes, conditions, 2D desktop vs VR.

### Takeaway
A software memory palace reliably beats "no strategy" for serial recall of word/face lists (typically +10–28 percentage points, d ≈ 0.4–0.9), and a briefly-explored virtual environment works as well as a personally familiar real one. Head-tracked VR adds a further but modest increment over a mouse-driven 3D desktop (Krokos: +8.8 points, p = 0.0017, n = 40); evidence beyond short lab lists is thin, several VR studies are small or uncontrolled, and at least one well-controlled 2023 study found VR worse than text for passive learning.

### Cited Findings

**Krokos, Plaisant & Varshney (2019, *Virtual Reality* 23:1–15; online 2018)**
- Within-subject design, 40 participants (30 male, 10 female), two pre-built environments (ornate palace, medieval town), two sets of 21 celebrity faces, 5 min study time, recall by writing names onto numbered positions on paper. HMD (Oculus Rift, head-tracked) vs 30-inch desktop with mouse, both rendered at 100° FOV. — [Krokos et al. PDF](https://obj.umiacs.umd.edu/virtual_reality_study/10.1007-s10055-018-0346-3.pdf)
- Mean recall accuracy HMD 84.05% vs desktop 75.24% (+8.8 points); median 90.48% vs 78.57%; paired t-test with Bonferroni–Holm p = 0.0017; display condition F(1,79) = 4.6, p < 0.05. Errors: 33/840 (HMD) vs 56/840 (desktop), p = 0.0195; skips significantly fewer in HMD (p = 0.0062). — [Krokos et al. PDF](https://obj.umiacs.umd.edu/virtual_reality_study/10.1007-s10055-018-0346-3.pdf)
- No significant effect of scene (palace vs town, F(1,79) = 0.27) or face set, i.e. the specific environment did not matter. — [Krokos et al. PDF](https://obj.umiacs.umd.edu/virtual_reality_study/10.1007-s10055-018-0346-3.pdf)
- Participants did not walk: they stood at the centre of the scene surrounded by faces and rotated their view (head rotation in HMD, mouse on desktop). The authors attribute the gain to vestibular/proprioceptive input from head rotation. Confidence 9.4 vs 9.1 on a 10-point scale; HMD confidence was better calibrated with accuracy. — [Krokos et al. PDF](https://obj.umiacs.umd.edu/virtual_reality_study/10.1007-s10055-018-0346-3.pdf)
- Order effect: going desktop→HMD improved performance; HMD→desktop did not (p = 0.025 for second trials), suggesting positive transfer from immersive to non-immersive. — [Krokos et al. PDF](https://obj.umiacs.umd.edu/virtual_reality_study/10.1007-s10055-018-0346-3.pdf)
- UMD press summary: 40% of participants scored ≥10% higher in VR; only two reported discomfort in VR. — [UMIACS news](https://www.umiacs.umd.edu/about-us/news/people-recall-information-better-through-virtual-reality-says-new-umd-study)

**Legge, Madan, Ng & Caplan (2012, *Acta Psychologica* 141:380–390)**
- 142 participants; 10 lists of 11 unrelated words; three virtual environments (apartment, school, warehouse) explored for 5 min on a desktop; groups: MoL-virtual, MoL-familiar (own home etc.), uninstructed control. — [BPS Research Digest summary](https://www.bps.org.uk/research-digest/memory-palace-mnemonic-strategy-works-virtual-environments); [paper PDF](https://www.psych.ualberta.ca/~cml/papers/LeggEtal2012.pdf)
- Both MoL groups recalled 10–16% more than controls; virtual-environment MoL was statistically equivalent to familiar-environment MoL; the specific virtual layout made no difference; virtual-environment participants were more compliant with the strategy. Authors: "a highly detailed environment does not support substantially better memory for verbal serial lists" for naïve users. — [BPS Research Digest](https://www.bps.org.uk/research-digest/memory-palace-mnemonic-strategy-works-virtual-environments)

**Caplan, Legge, Cheng & Madan (2019, *Quarterly Journal of Experimental Psychology*)**
- Trained participants on three virtual environments (apartment, open field, radial-arm maze), five 11-word lists each. Performance varied significantly across environments but effects were small; navigation-related knowledge and ability were not major determinants of recall even in confirmed strategy users. Conclusion: imagined navigation is unlikely to explain MoL; MoL "may be best viewed as a variant of peg methods". — [MacEwan repository abstract](https://roam.macewan.ca/items/b98f1cfc-31cc-45b5-95f7-7ef18519a182/full)

**Fassbender & Heiden (2006, *Journal of Computational Information Systems* 2(1):457–464)**
- Desktop 3D medieval castle; users freely explored and placed icons at locations. 15 subjects; items learned in the Virtual Memory Palace had a higher remembrance rate than a word list; results indicated a long-term-memory benefit. — [H-BRS repository record](https://pub.h-brs.de/frontdoor/index/index/year/2015/docId/2172)
- As summarized in Krokos et al.'s related work, the desktop 3D castle condition showed a 25% recall advantage over word-list learning after one week. — [Krokos et al. PDF](https://obj.umiacs.umd.edu/virtual_reality_study/10.1007-s10055-018-0346-3.pdf)

**Huttner, Robra-Bissantz and colleagues (TU Braunschweig, 2015–2019)**
- AMCIS 2017 "An Immersive Memory Palace": laptop-displayed virtual palace vs HMD; the HMD group had higher accuracy and higher actual use of the method (hypotheses "partly confirmed"). — [AISeL AMCIS 2017](https://aisel.aisnet.org/amcis2017/HumanCI/Presentations/20)
- HICSS 2018 "Imaginary Versus Virtual Loci": HMD palace with items shown as image+text at fixed loci (n = 23) vs text-only where users had to imagine placing items (n = 28); 51 datasets after excluding participants with motion sickness. Strict (order-sensitive) score 0.31 vs 0.11 (Mann-Whitney p = 0.008; 2.81×); lenient score 0.79 vs 0.68 (p < 0.05). About 11% had prior MoL knowledge. — [HICSS 2018 PDF](https://pdfs.semanticscholar.org/e95e/e925865c9d999513b7a647b31c4f008ff532.pdf); [ScholarSpace record](https://scholarspace.manoa.hawaii.edu/handle/10125/49924)
- The same paper reviews a 142-student, three-group study (traditional MoL, virtual MoL, control) where both MoL groups beat control, the two MoL groups did not differ, and recall across three different virtual environments within the vMOL group did not differ. — [HICSS 2018 PDF](https://pdfs.semanticscholar.org/e95e/e925865c9d999513b7a647b31c4f008ff532.pdf)
- Earlier pilot (two groups of five students) found no superiority of a virtual palace over uninstructed learning. ECIS 2019 tested recall after "mere exposure" to a visuospatial palace to reduce the mnemonic's extra mental effort. — [ECIS 2019](https://aisel.aisnet.org/ecis2019_rp/7)
- Huttner et al. 2019 review (as summarized by Moll & Sykes) recommended ≥40 items per test list, longer training, and familiar environments. — [Moll & Sykes, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9540171/)

**Reggente, Essoe, Baek & Rissman (2020, *Journal of Cognitive Enhancement* 4:12–30)**
- Three distinct desktop virtual environments as palaces; 15 3D objects appear in sequence in front of the avatar. Experimental group (n = 30) could click to lock each object in place (explicit binding); control (n = 30) could not. Experimental group recalled ~28% more objects despite matched exposure; strong correlation between spatial memory for objects/landmarks and verbal recall. — [Springer](https://link.springer.com/article/10.1007%2Fs41465-019-00141-8); [eScholarship](https://escholarship.org/uc/item/5wp80275)

**Yang, Krokos, Varshney et al. (2021, *IEEE TVCG*, "A Virtual Reality Memory Palace Variant Aids Knowledge Retrieval from Scholarly Articles")**
- 26 recruited (25 analysed: 12 IMAGE, 13 VR). Task: read 12 scientific abstracts, then recall and recognise them. Conditions: CONTROL (no strategy), IMAGE (picture + story of a coffee shop as loci), VR (HMD coffee shop with the same loci). Mixed design, control visit then mnemonic visit several days later. — [TVCG preprint PDF](https://scispace.com/pdf/a-virtual-reality-memory-palace-variant-aids-knowledge-23c63ss5io.pdf)
- Recall accuracy rose by 0.058 [95% CI 0.021, 0.092] over control for VR, paired Cohen's d = 0.84 [0.21, 1.53]; for IMAGE the effect was d = 0.058 [−0.69, 0.62]. Recognition accuracy did not improve substantially in either. Participants spontaneously asked for personalised palaces. — [TVCG preprint PDF](https://scispace.com/pdf/a-virtual-reality-memory-palace-variant-aids-knowledge-23c63ss5io.pdf)

**Moll & Sykes (2022/2023, *Virtual Reality* 27:941–966, feasibility study)**
- 11 adults, one-group pre/post design, two sessions a week apart; 15-min own-strategy study vs 15-min VR MoL (Oculus Rift S, physical walking via KAT Loco sensors, visible hands, 3D placement chime, participant-chosen images). Palace: a 3D apartment with ~10 rooms, 15 floating "collectibles" guiding a path through every room. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9540171/)
- Lenient recall: week 1 62.6% → 82.9% (p = 0.014); week 2 63.4% → 85.7% (p = 0.024); strategy main effect F(1,40) = 9.9, p = 0.003. Strict order-sensitive scoring did NOT improve (declined 39.4 → 23.2 and 42.6 → 20.4). Participants who followed a path-preserving strategy scored better on strict order; participants who rated immersion 4–5/5 scored better; 91% said they would use it. Pilot: rooms with less visible entrances from the central space were under-used. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9540171/)

**Boller, Ouellet & Belleville (2021, *Frontiers in Psychology* 12:627242, RCT in older adults)**
- 40 analysed (VR+ 20, VR− 20), adults >50 with memory complaints; all got classroom MoL training; VR+ practised in an immersive "Virtual Shop", VR− did visuomotor tasks there. Word recall improved pre→post (F(2,37) = 12.55, p = 0.00002, ηp² = 0.25) and transfer improved, but with no condition or interaction effect: adding VR practice gave no measurable advantage over active control. Some cybersickness; VR dose was only ~10 min/session. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7994284/)

**Johnsdorf et al. (2023, *Frontiers in Psychology*, "New is not always better")**
- Learning block-arrangement rules from text vs 2D video vs 360° video in HMD; recognition, construction and next-day free recall. Text produced the best memory; no VR advantage. Authors propose salient VR stimuli draw attention from core information in passive learning. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9975255/)

**Vindenes & Wasson (2023, *Virtual Reality* 27:3239–3258, eight-week in-the-wild qualitative study)**
- 10 students, Oculus Quest + Hubs Cloud; each had seven rooms off a lobby, could furnish with images/GIFs/videos/3D objects but could not change room layouts or add raw text. No memory outcomes measured. Experiences varied widely; some used it for organising course content, others abandoned it. Barriers: setup effort, no text entry, simulator sickness, migraines, disconnection from everyday study tools. Core challenge framed as deciding what to abstract and represent visually. — [Springer](https://link.springer.com/article/10.1007/s10055-023-00868-y)
- Vindenes et al. 2018 "Mnemosyne" pilot (18 participants): users with higher spatial reasoning benefited more from the VR MoL. — [Springer chapter](https://rd.springer.com/chapter/10.1007%252F978-3-319-95270-3_16)

**Gerard, Leymarie & Latham (2021, iLRN)**
- Compared two VR environments (Palladian vs modern curved architecture) for remembering sequences of random playing cards; the abstract states spatial design affected performance but gives no numbers. — [Goldsmiths record](https://research.gold.ac.uk/id/eprint/30322)

**Essoe, Reggente, Ohno et al. (2022, *npj Science of Learning* 7:31)**
- 48 participants learned 80 words in two phonetically similar languages while navigating VR. Distinct context per language: 92% one-week retention vs 76% same-context; benefit appeared only when participants found the VR contexts subjectively "real"; fMRI showed context reinstatement at retrieval predicted recall. — [eScholarship PDF](https://escholarship.org/content/qt5tv000gq/qt5tv000gq.pdf?t=rxglfz)

**Immersion-level evidence outside MoL**
- Ragan, Sowndararajan, Kopper & Bowman (2010, *Presence* 19(6):527–543): procedure memorisation improved with higher field of regard / physical FOV when software FOV matched; even moderate immersion helped; memorisation transferred to the real world; mechanism attributed to richer spatial cues. — [VTechWorks](https://vtechworks.lib.vt.edu/items/0a137332-46bf-4ee3-9fff-5f078cd9082f/full)
- Krokos et al. summarise Mania et al. (2003): immediately after exposure, recall of object positions was most accurate in a real room, then HMD, then desktop; the ordering had changed after one week. — [Krokos et al. PDF](https://obj.umiacs.umd.edu/virtual_reality_study/10.1007-s10055-018-0346-3.pdf)

### Inferences
- The robust, replicated effect is "software palace vs no strategy" and "any explorable environment vs none", not "VR vs desktop". A 2D top-down palace has no direct controlled study; the closest analogues (Legge's mouse-driven desktop environments, Reggente's desktop environments, Yang's IMAGE condition) show that non-immersive spatial scaffolds do work when the user actively binds items to places (Reggente's +28% from a single click-to-lock interaction is the strongest single design lesson).
- Krokos's HMD advantage came from head-rotation vestibular cues in a non-locomoting setup, so it is unlikely to transfer to a 2D top-down avatar view. Expect a 2D mode to perform like a desktop palace (Legge, Fassbender), not like VR.
- Yang's IMAGE condition (static picture + story) failing while VR succeeded suggests that passive, non-navigable spatial depictions are weak; a navigable 2D map with avatar movement sits between those.
- Strict-order recall is fragile: Moll & Sykes saw lenient gains but strict-order losses unless users followed a fixed path. A 2D palace that enforces or visualises a route should help ordered recall; free roaming will not.

### Gaps
- No controlled study of a 2D top-down/RPG-style palace was found; all desktop studies used first-person 3D.
- No 2024–2026 RCT of a virtual MoL for vocabulary or for personal notes was found; recent work is feasibility or qualitative.
- Krokos's effect has not, to my knowledge, been independently replicated with the same paradigm; the Boller RCT and Johnsdorf study are the only well-controlled recent VR-vs-non-VR comparisons and both are null or negative for VR.
- Gerard et al. 2021 (architectural layout effects) full text and numbers were not retrievable.
- Peeters & Segundo-Ortin (2019, *Consciousness and Cognition*) design recommendations were only reachable via Moll & Sykes's summary (maximise immersion, distinctive landmarks, require physical movement, let users create their own imagery).

---

## Key Question 2: What did classic spatial-UI information-retrieval research find (Data Mountain, Cockburn & McKenzie, spatial hypertext/VIKI, Task Gallery, ZUIs)? Where did spatial memory help and where did 3D hurt?

### Takeaway
User-arranged spatial layouts of ~100 documents produce fast retrieval (≈4–6 s) that survives six months without practice and does not depend on thumbnails, but the third dimension itself adds nothing measurable and tends to hurt (more clutter, slower as freedom in depth increases); users nonetheless prefer 3D subjectively. Performance degrades with density in every study, and pure location-based reference degrades faster than name-based reference as item count grows.

### Cited Findings

**Robertson, Czerwinski, Larson, Robbins, Thiel & van Dantzich (1998, UIST, "Data Mountain")**
- 32 experienced IE4 users stored 100 web-page thumbnails on an inclined 3D plane by manual layout, then retrieved them from four cue types (title, summary, thumbnail, all); compared with IE4 Favorites. Data Mountain users were reliably faster (main effect of application F(2,18) = 4.84, p < .02), made reliably fewer incorrect retrievals (F(2,18) = 4.48, p < .03) and had fewer failed trials (F(2,18) = 8.3, p < .01). Users spontaneously said "it's right here", "I know where it is". — [UIST 1998 PDF](https://courses.ischool.berkeley.edu/i247/s04/resources/p153-robertson.pdf)

**Czerwinski, van Dantzich, Robertson & Hoffman (1999, INTERACT)**
- Participants returned ~6 months (pilot: 6 weeks) after creating their 100-page layouts. No significant effect of delay on retrieval time (F(1,8) < 1), incorrect retrievals (F(1,8) < 1) or failed trials (F(1,8) < 1). Removing thumbnails (blank icons) initially caused a significant drop, but within a short period users found pages equally fast without them, i.e. spatial location memory, not the picture, carried retrieval. — [INTERACT 1999 PDF](https://www.microsoft.com/en-us/research/wp-content/uploads/1999/01/interact99.pdf)

**Cockburn & McKenzie (2001, CHI, "3D or not 3D?")**
- 2D vs 3D (Data Mountain-like) systems differing only in dimensionality; 33/66/99-page densities; Computer Science students. Storing 33 pages and retrieving: 2D slightly faster but not significant (storage F(1,26) = 1.89, p = .18; retrieval means 5.98 s 2D vs 6.77 s 3D, F(1,26) = 0.29, p = .60). Density strongly significant (F(2,52) = 8.75, p < .005). ~90% (2D) and ~85% (3D) of retrievals within 10 s. Clutter rating rose 2.2 → 4.0 (2D) and 2.0 → 3.9 (3D) from sparse to dense. Users rated 3D higher overall (3.50 vs 4.25). — [CHI 2001 PDF](https://www.cs.kent.edu/~jmaletic/cs63903/papers/Cockburn01.pdf)

**Cockburn & McKenzie (2002, CHI, physical and virtual 2D/2½D/3D)**
- 69 CS students; six interfaces (physical card models and Tcl/Tk virtual equivalents) at 2D, 2½D, 3D; 33/66/99 pages. Mean retrieval across 2070 trials 4.13 s. Density significant (3.2 / 4.2 / 5.0 s sparse/medium/dense, F(2,126) = 12.8, p < .001). Dimensionality trend toward slower with more depth (3.7 / 3.8 / 4.8 s for 2D/2½D/3D, F(2,63) = 2.5, p = .09); 3D virtual had the highest mean (4.8 s). Physical 2D vs 3D differed significantly. Subjects rated 2D less cluttered (2.7) than 2½D/3D (3.4; Kruskal-Wallis p < .05). Abstract: "performance deteriorated in both the physical and virtual systems as their freedom to locate items in the third dimension increased". — [CHI 2002 PDF](https://www.csse.canterbury.ac.nz/andrew.cockburn/papers/chi02DM.pdf)
- Cockburn's project page: re-examining Tavanti & Lind (2001) with controls, spatial memory was unaffected by 3D perspective in static displays; items were memorised better when personally meaningful and visually distinctive. Cone trees were slower than a standard tree browser and degraded rapidly with branching factor, despite enthusiasm. — [Canterbury 2D vs 3D page](https://www.csse.canterbury.ac.nz/andrew.cockburn/2d3d.html)

**Jones & Dumais (1986, *ACM Transactions on Office Information Systems*)**
- Experimental tests of reference by location vs name. Location-only filing accuracy was initially comparable to name-only but "deteriorated much more rapidly with increases in the number of objects filed"; enhancements in later experiments did not significantly improve location reference, which stayed below name-only. The authors questioned the utility of the spatial metaphor over symbolic filing. — [Scilit record](https://scilit.com/publications/4c5b11cc06e84621618b9240435ffbf4)

**Robertson et al. (2000, CHI, "Task Gallery")**
- 3D window manager placing tasks on gallery walls; the abstract claims user studies show it helps task management, is enjoyable, and the 3D metaphor evokes spatial memory; tasks return to their original wall position after use so remembered positions stay valid. — [Microsoft Research page](https://www.microsoft.com/en-us/research/?p=145458)

**Spatial hypertext (Marshall & Shipman, VIKI)**
- VIKI (ECHT 1994) supports emergent structure via spatial arrangement; earlier observations found users avoided explicit linking in favour of implicit relationships expressed through proximity and visual attributes; CHI 1995 work parsed implicit structure (lists, piles, composites) from user layouts; a HT 1997 information-triage study compared paper vs two VIKI variants. — [ECHT 1994 abstract](https://people.engr.tamu.edu/shipman/abstracts/echt94-abstract.html); [CHI 1995 paper](https://chi1995.chistatic.hosting.acm.org/proceedings/papers/fms_bdy.htm)

**Zoomable UIs**
- Jul & Furnas (1998, UIST) named "desert fog": disorientation when zooming/panning leaves no informational cues; proposed "critical zones" as residues of interesting views. — [DBLP record](https://dblp.uni-trier.de/rec/conf/uist/JulF98.html)
- Rädle et al.: egocentric body movement in a ZUI gave no immediate spatial-memory benefit but a 27% advantage on recall after a 15-min distractor (n = 8, second experiment). — [FH OÖ record](https://pure.fh-ooe.at/en/publications/the-effect-of-egocentric-body-movements-on-users-navigation-perfo/)

**Spatial stability (Scarr, Cockburn, Gutwin et al.)**
- Monograph *Supporting and Exploiting Spatial Memory in User Interfaces* (Foundations and Trends in HCI, 2013): many interfaces undermine spatial memory by rearranging items; offers guidelines for designing for spatial memory. — [Now Publishers summary](https://nowpublishers.com/article/DownloadSummary/HCI-046)
- CommandMaps: fixed command positions were slower for novices but significantly faster than menus/Ribbon for experienced users. — [CommandMaps PDF](https://scispace.com/pdf/improving-command-selection-with-commandmaps-1efcj7xneh.pdf)
- CHI 2013 robustness: spatial memory performance survived translation, scaling and perspective changes but not large rotations; stable-with-scaling beat reflowing layouts. — [Gutwin publications](https://independent.academia.edu/CGutwin)
- Tak et al. (2009) window switching: spatially stable layouts significantly faster than recency-ordered; gradual changes to fit new windows did not hurt. — [UU record](https://research-portal.uu.nl/en/publications/improving-window-switching-interfaces/)
- Gutwin et al. (GI 2020): with 700 items a spatially stable layout matched paged layouts on overall time and was faster for revisitation. — [Graphics Interface 2020](https://graphicsinterface.org/?p=6040)

### Inferences
- The durable finding is that *user-arranged, stable* 2D (or 2½D) layouts give fast, long-lived location memory for ~100 items; the Data Mountain's benefit was never shown to come from its depth. A 2D top-down palace is on the right side of this evidence; adding true 3D or free depth placement is not.
- Clutter/density is the dominant performance variable in every Cockburn/Robertson study (retrieval time rises ~50% from 33 to 99 items on one surface). Rooms are a natural way to cap per-surface density.
- Jones & Dumais show pure location reference scales poorly; the modern synthesis (Scarr et al.) is that spatial memory should supplement, not replace, naming/search. A palace should be an additional retrieval path over the RDF graph, never the only one.
- Spatial hypertext shows users express relationships through proximity instead of explicit links; a palace room can therefore double as an informal "pile" that the system may later parse into typed relationships.
- Stability matters more than realism: never auto-rearrange placed objects; if a layout must grow, grow it incrementally (Tak et al.) and avoid rotation (Scarr et al.).

### Gaps
- Full text and numbers for Task Gallery user studies and the VIKI triage study were not retrieved; findings are abstract-level only.
- I found no study measuring long-term (months) retention for 2D desktop layouts beyond the Data Mountain 6-month follow-up (n = 9 returning subjects).

---

## Key Question 3: What are the key cognitive-psychology variables for memory-palace effectiveness (familiarity, self-generated vs assigned loci, distinctiveness/bizarreness, fixed route order, items per locus, interference on reuse, retention over days/weeks, active vs passive navigation)?

### Takeaway
Meta-analyses put MoL at g ≈ 0.65 (13 RCTs) to d ≈ 0.4–0.9 depending on population, with low-quality evidence and strong publication bias. The moderators with the best support are: dissimilar/distinctive loci (d = 0.91 vs −0.41 for similar loci), self-generated loci (d ≈ 0.43 over assigned, especially long-term), explicit binding of item to place, few items per locus (~2), and a fixed route for ordered recall; familiarity and navigational realism matter surprisingly little for novices; reusing the same loci for new material causes retroactive interference; effects shrink over days (d 0.94 → 0.48 at 3 days in older adults); active exploration gives a small-to-moderate advantage over passive viewing.

### Cited Findings

**Overall effect sizes and quality**
- Twomey & Kroneisen (2021, *QJEP*): 13 RCTs, g = 0.65 [0.45, 0.85], I² = 45.5%; robust to publication-bias adjustment; most studies did not report allocation concealment, high risk of bias. — [SAGE](https://journals.sagepub.com/doi/10.1177/1747021821993457)
- Ondřej (2025, *British Journal of Psychology*, systematic review and meta-analysis): 83 eligible studies, 68 in main analyses; young-adult immediate serial recall vs rehearsal d = 0.42 [0.00, 0.80] (13 experiments), abstract-level adult estimate d = 0.88 [0.47, 1.25]; very strong evidence of publication bias (BF ≈ 6.4 × 10⁶); 89.2% of young-adult experiments at high risk of bias; GRADE very low. VR implementations (Fassbender & Heiden, Legge et al., Moll & Sykes) reported as equivalent or superior to classical MoL. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12514325/)
- Dresler et al. (2017, *Neuron*): 23 world-class memory athletes vs controls; 51 naïve participants, 6 weeks of MoL training vs active (n-back) and passive controls. Training produced connectivity changes correlated with the athlete pattern; improvements described as enduring; no structural brain differences. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5439266/)

**Distinctiveness of loci and images**
- Massen & Vaterrodt-Plünnecke (2006, *Memory*): similar loci d = −0.41 (Exp. 1) vs dissimilar loci d = 0.91 (as extracted by Ondřej 2025). — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12514325/)
- Cockburn's re-analysis of Tavanti & Lind: items memorised better when personally meaningful and visually distinctive. — [Canterbury page](https://www.csse.canterbury.ac.nz/andrew.cockburn/2d3d.html)
- Liu et al. (2019, pilot with real walking, summarised by Moll & Sykes): identical rooms without transitions confused participants. — [Moll & Sykes, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9540171/)
- Bizarreness: McDaniel & Einstein argue the benefit comes from distinctiveness and appears mainly in free recall and immediate tests; sentence complexity eliminates it; Robinson-Riegler & McDaniel (1994) found it only in impoverished encoding contexts; Besken & Mulligan (2021) found a robust bizarreness effect unaffected by visuospatial distraction, implying little role for visual imagery per se. — [WUSTL: distinctiveness](https://profiles.wustl.edu/en/publications/bizarre-imagery-as-an-effective-memory-aid-the-importance-of-dist/); [WUSTL: sentence complexity](https://profiles.wustl.edu/en/publications/sentence-complexity-eliminates-the-mnemonic-advantage-of-bizarre-/); [Besken & Mulligan PDF](https://core.ac.uk/download/370791836.pdf)
- Essoe et al. (2022): distinct VR contexts per material set cut interference and raised one-week retention 76% → 92%, but only when contexts felt "real". — [eScholarship PDF](https://escholarship.org/content/qt5tv000gq/qt5tv000gq.pdf?t=rxglfz)

**Self-generated vs assigned loci; familiarity**
- Moè & De Beni (2004): subject-generated loci pathways gave a greater benefit than experimenter-supplied ones, particularly long-term. — [Padua repository](https://research.unipd.it/handle/11577/2468982)
- Moè & De Beni (2005, n = 90): advantage of oral presentation was stronger for the subject-generated loci group; Ondřej 2025 computes d ≈ 0.43 for subject- vs experimenter-generated loci overall, with written-presentation subject-generated loci performing worse (d = −1.23 vs rehearsal). — [Padua repository](https://research.unipd.it/handle/11577/2467916); [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12514325/)
- 2022 *Memory* study: participant-generated Loci, Body and Story scaffolds all beat no-scaffold control; Loci and Body were equally best. — [Taylor & Francis](https://informahealthcare.com/doi/full/10.1080/09658211.2022.2052322)
- Legge et al. 2012 and Caplan et al. 2019: a 5-min-explored virtual environment matched a lifelong-familiar one; navigation ability did not predict recall. — [BPS summary](https://www.bps.org.uk/research-digest/memory-palace-mnemonic-strategy-works-virtual-environments); [MacEwan abstract](https://roam.macewan.ca/items/b98f1cfc-31cc-45b5-95f7-7ef18519a182/full)
- Yang et al. 2021: participants asked for personalised palaces; the authors deliberately used a generic coffee shop so the loci would be "moderately familiar". — [TVCG preprint](https://scispace.com/pdf/a-virtual-reality-memory-palace-variant-aids-knowledge-23c63ss5io.pdf)

**Items per locus, route order, binding**
- Crovitz recommends about two items per locus (as reported by Ondřej 2025). — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12514325/)
- Reggente et al. 2020: a click to "lock" each object to its place yielded ~28% more recall; spatial memory for object locations predicted verbal recall. — [Springer](https://link.springer.com/article/10.1007%2Fs41465-019-00141-8)
- Moll & Sykes: path-preserving placement produced better strict-order recall; grouping items together did not. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9540171/)
- Huttner et al. 2018: fixed loci with item images gave 2.81× the order-sensitive score of free, imagined placement. — [HICSS 2018 PDF](https://pdfs.semanticscholar.org/e95e/e925865c9d999513b7a647b31c4f008ff532.pdf)

**Interference when reusing a palace**
- De Beni & Cornoldi (1988): using the same loci for three successive paired-item lists improved free recall but produced retroactive interference. — [Padua repository](https://www.research.unipd.it/handle/11577/2511862)
- Massen & Vaterrodt-Plünnecke (2006): MoL is not more susceptible to proactive interference than rehearsal (as cited by Ng, Legge & Caplan and by Bass & Oswald). — [Bass & Oswald, PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4116757/)
- Bass & Oswald (2014, *Advances in Cognitive Psychology*): proactive interference builds across lists of similar items; MoL users reduced it (~25% reduction per Ondřej's extraction) via distinctive encoding. — [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4116757/); [Ondřej 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12514325/)
- Legge et al. 2012 note that poor performance across repeated use has been hypothesised to stem from proactive-interference build-up from reusing the same environment. — [Legge PDF](https://www.psych.ualberta.ca/~cml/papers/LeggEtal2012.pdf)
- Ondřej 2025: repeated use of the same locations produced carry-over interference in older adults; Groninger and Ross & Lawrence reported more intrusion errors at longer intervals. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12514325/)

**Retention over days/weeks**
- Hill et al. (older adults, extracted by Ondřej 2025): d = 0.94 immediate, 0.84 at 1 hour, 0.48 at 3 days. Wang & Thomas: MoL outperformed rehearsal especially after retention intervals. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12514325/)
- Czerwinski et al. 1999: spatial location memory for 100 self-arranged pages was intact at 6 months. — [INTERACT 1999 PDF](https://www.microsoft.com/en-us/research/wp-content/uploads/1999/01/interact99.pdf)
- Boller et al. 2021: gains plateaued after the third session, no gain at session six; no follow-up beyond one week. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7994284/)

**Active vs passive navigation**
- Chrastil & Warren (2012, *Psychonomic Bulletin & Review* 19:1–23): the literature is "decidedly mixed" partly because "active" bundles five components (motor, proprioceptive/idiothetic, decision-making, attention, mental manipulation); overall there is an active advantage that manifests task-dependently in route and survey knowledge. — [Springer PDF](https://link.springer.com/content/pdf/10.3758/s13423-011-0182-x.pdf)
- Qin & Karimi (2023, *QJEP*): 128 effect sizes from 33 experiments; small-to-moderate advantage of active exploration over passive observation in large unfamiliar environments. — [SAGE](https://journals.sagepub.com/doi/10.1177/17470218231185121)
- Meade, Meade, Sauzeon & Fernandes (2019, *Brain Sciences* 9(3):47): 22 young, 22 older adults, cardboard-HMD routes, 30 s encoding; active encoding more accurate (F(1,40) = 23.07, p < .001, η² = 0.37); benefit larger in older adults (d = 0.61 vs 0.35 young, marginal). Prior studies in older adults sometimes found active encoding hurt when motor demands were high; the authors argue decision-making/attention, not movement, drive the benefit. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6468686)
- Counter-example: a mixed-reality virtual-house study found guided navigation produced higher spatial memory than free navigation. — [Aston University record](https://research.aston.ac.uk/en/publications/the-effect-of-guided-and-free-navigation-on-spatial-memory-in-mix/)
- Krokos et al. summarise a 1999 desktop study: active (joystick) participants recalled better only the aspects of a 3D house they directly interacted with, not room exits or positions. — [Krokos PDF](https://obj.umiacs.umd.edu/virtual_reality_study/10.1007-s10055-018-0346-3.pdf)
- Johnsdorf et al. 2023: passive VR viewing lost to text; authors recommend active involvement if VR is used. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9975255/)

### Inferences
- The variables that matter most for a software palace are controllable by the UI: make every room visually distinct (not identical tiles), give each object a deliberate "place" action, keep items per locus low, expose a route, and let the user author the layout. Familiarity and 3D realism are the variables that matter least for novices, which favours a cheap 2D build-it-yourself approach.
- Palace reuse is the biggest long-run risk for a PKM: notes are permanent, not disposable lists. The evidence suggests allocating new material to new rooms rather than overwriting loci, and making rooms distinct per topic (the Essoe result generalises this: distinct contexts per knowledge set reduce interference).
- Active navigation helps modestly, but what matters is the decision-making and attention component, not motor effort; an avatar walk that forces choices (which door, which room) is more defensible than one that just adds travel time. A low-motor-demand control scheme avoids the "cognitive load from controls" failure seen in older adults.
- Decay over days means the palace itself will not sustain recall without revisiting; spaced revisits (walking the route again) are the natural complement, though no study directly tests spaced review inside a virtual palace.

### Gaps
- No study directly crosses self-generated vs assigned loci with environment familiarity.
- No quantitative study on optimal room size, loci per room, or rooms per palace in software; "~2 items per locus" is a classic recommendation, not a VR-tested parameter.
- No study of spaced repetition implemented inside a virtual memory palace.
- No peer-reviewed meta-analysis dedicated to the bizarreness effect's size was found; the evidence is a set of boundary-condition studies.
- Massen & Vaterrodt-Plünnecke's and De Beni & Cornoldi's full texts were not accessible; findings are from secondary citations.

---

## Key Question 4: What do studies of gamified/game-like knowledge tools and of "desktop metaphor" spatial file arrangement show (users remembering file locations, piles, Malone 1983)?

### Takeaway
Gamification yields small positive effects on learning (g ≈ 0.49 cognitive, 0.36 motivational, 0.25 behavioural), with the cognitive effect surviving in rigorous studies. Desk/desktop research shows people use spatial location both for finding and for reminding, prefer informal piles to classification, and avoid elaborate filing; but spatial-only reference degrades with item count, so spatial arrangement is best as a complement to naming/search.

### Cited Findings
- Sailer & Homner (2020, *Educational Psychology Review* 32:77–112): meta-analysis of gamification of learning; cognitive outcomes g = .49 (k = 19), motivational g = .36 (k = 16), behavioural g = .25 [0.04, 0.46] (k = 9, N = 951). Cognitive effect held in the high-rigor subset; motivational/behavioural less stable. Game fiction and social interaction moderated behavioural outcomes; competition plus collaboration was most effective. Authors call it a "stopgap" given few studies per gamification type. — [Augsburg OPUS PDF](https://opus.bibliothek.uni-augsburg.de/opus4/files/109056/109056.pdf)
- Malone (1983, *ACM TOIS* 1(1):99–112): 10 office workers; two units of desk organisation, files (titled, arranged) and piles (untitled, unordered); both serve finding and reminding; people found classification hard, and messy desks created retrieval problems for their owners; recommended systems support untitled piles and automatic classification (e.g., by access date). — [Typeset PDF](https://typeset.io/pdf/how-do-people-organize-their-desks-implications-for-the-3j0xdr453p.pdf); [researchr record](https://researchr.org/publication/Malone83/bibtex)
- Voit, Andrews & Slany (PIM 2009): users like to arrange resources by location, grouping icons on the desktop, and avoid elaborate filing; location serves as a memory aid. Cited work found users place files where they serve a reminding function. — [TU Graz PDF](https://graz.elsevierpure.com/files/2964388/PIM09_-_Why_PIM_Tech_Are_Not_Widespread_-_Voit_Andrews_Slany.pdf)
- Jones & Dumais (1986): location-only reference accuracy fell much faster than name-only as objects increased; spatial enhancements did not close the gap. — [Scilit record](https://scilit.com/publications/4c5b11cc06e84621618b9240435ffbf4)
- Marshall & Shipman: hypertext users express relationships via proximity and visual attributes rather than explicit links. — [ECHT 1994 abstract](https://people.engr.tamu.edu/shipman/abstracts/echt94-abstract.html)
- Vindenes & Wasson 2023: in eight weeks of self-directed use, the palace that lacked text entry and sat apart from everyday tools was abandoned by several participants; those who persisted used it for organising and planning course content, i.e. as a PIM surface more than a recall drill. — [Springer](https://link.springer.com/article/10.1007/s10055-023-00868-y)
- Moll & Sykes: 91% of participants said they would use a VR palace for real studying; participants with higher self-rated immersion scored better. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9540171/)

### Inferences
- A game-like frame (avatar, rooms, furniture) plausibly improves motivation and engagement more than recall per se; the "game fiction" moderator in Sailer & Homner supports a coherent narrative/world over bolt-on points and badges.
- Rooms-as-piles fits Malone: let users dump items into a room without naming or typing them, and let the system infer structure (as VIKI did) rather than force classification at placement time.
- Because spatial-only reference scales badly, the palace must stay integrated with search, typed relations and dashboards; Vindenes & Wasson's abandonment data show that a palace detached from the daily workflow dies.

### Gaps
- No study specifically evaluates a gamified or game-world note-taking/knowledge tool for retention outcomes; the gamification meta-analysis covers classroom gamification generally.
- No direct empirical study of desktop-icon location memory with sample sizes and retention intervals was found beyond secondary summaries.

---

## Key Question 5: What are the known failure modes (auto-generated layouts, too many items per room, changing environments, navigation cognitive load, motion sickness)?

### Takeaway
The documented failure modes are: density/clutter (retrieval time rises steadily with items per surface), layouts that change (destroys spatial memory), identical or indistinct rooms (confusion, interference), passive consumption of a rich environment (attention pulled from content), the extra mental effort of the mnemonic itself (compliance drops, especially for older users), and cybersickness in HMD VR (mean dropout 15.6%; controller locomotion worst, physical walking best). Auto-generated layouts specifically are a gap: the closest evidence is that assigned loci underperform self-generated ones and that users ask for personalisation.

### Cited Findings
- Density: retrieval time 3.2 → 4.2 → 5.0 s for 33/66/99 items (F(2,126) = 12.8, p < .001); clutter ratings doubled from sparse to dense; cone trees degraded rapidly with branching factor. — [Cockburn & McKenzie 2002 PDF](https://www.csse.canterbury.ac.nz/andrew.cockburn/papers/chi02DM.pdf); [CHI 2001 PDF](https://www.cs.kent.edu/~jmaletic/cs63903/papers/Cockburn01.pdf); [Canterbury page](https://www.csse.canterbury.ac.nz/andrew.cockburn/2d3d.html)
- Changing layouts: interfaces that rearrange items undermine spatial memory; large rotations break it; recency-ordered layouts lose to spatially stable ones. — [Scarr et al. monograph](https://nowpublishers.com/article/DownloadSummary/HCI-046); [Tak et al. 2009](https://research-portal.uu.nl/en/publications/improving-window-switching-interfaces/)
- Indistinct rooms: identical rooms without transitions confused participants (Liu et al. 2019); similar loci gave a negative effect (d = −0.41) vs dissimilar (d = 0.91). — [Moll & Sykes, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9540171/); [Ondřej 2025, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12514325/)
- Under-used rooms: rooms with less visible entrances from the hub were visited less. — [Moll & Sykes, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9540171/)
- Passive rich environments: 360° video in HMD lost to plain text for rule learning; salient VR stimuli compete for attention. — [Johnsdorf et al. 2023, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9975255/)
- Mnemonic effort and compliance: MoL "demands significant cognitive load and attention" and "necessitates hours of training"; Verhaeghen & Marcoen (1996) found compliance problems in older participants; Huttner's ECIS 2019 work was motivated by reducing the method's extra mental effort. — [Yang et al. TVCG](https://scispace.com/pdf/a-virtual-reality-memory-palace-variant-aids-knowledge-23c63ss5io.pdf); [Moll & Sykes, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9540171/); [ECIS 2019](https://aisel.aisnet.org/ecis2019_rp/7)
- Navigation cognitive load in older adults: high motor demands during active encoding added load and impaired memory in some studies. — [Meade et al. 2019, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6468686)
- Strict-order loss: order-sensitive scores fell after VR MoL unless users followed a path; grouping items broke order. — [Moll & Sykes, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9540171/)
- Cybersickness: Saredakis et al. (2020, *Frontiers in Human Neuroscience*), 55 studies/3,016 participants: pooled SSQ 28.0; mean dropout 15.6% across 46 experiments (gaming up to 44–100% in some studies); controller-based locomotion SSQ 32.6 vs stationary 28.0 vs physical walking 17.0; exposure ≥10 min worse than <10 min. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7145389)
- Caserman et al. (2021, *Virtual Reality*): current-generation HMDs cause significantly less cybersickness but some symptoms remain as intense. — [TU Darmstadt PDF](https://tuprints.ulb.tu-darmstadt.de/23452/1/s10055-021-00513-6.pdf)
- Sickness in MoL studies specifically: Huttner et al. excluded motion-sick participants; Moll & Sykes capped lists at 30 words to limit nausea; Boller et al. lost transfer data to cybersickness; Vindenes & Wasson report simulator sickness and migraines as reasons for abandonment. — [HICSS 2018 PDF](https://pdfs.semanticscholar.org/e95e/e925865c9d999513b7a647b31c4f008ff532.pdf); [Moll & Sykes, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9540171/); [Boller et al., PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7994284/); [Vindenes & Wasson](https://link.springer.com/article/10.1007/s10055-023-00868-y)
- Workflow disconnection: no text entry and separation from daily study tools led to abandonment. — [Vindenes & Wasson](https://link.springer.com/article/10.1007/s10055-023-00868-y)
- ZUI "desert fog": zooming/panning without cues disorients. — [Jul & Furnas 1998](https://dblp.uni-trier.de/rec/conf/uist/JulF98.html)

### Inferences
- A 2D top-down mode sidesteps the single largest VR failure mode (cybersickness, ~1 in 6 dropouts) at the cost of the modest VR immersion gain; on current evidence that is a favourable trade for a daily-use PKM.
- Auto-generated layouts are risky on three counts: they remove the self-generation benefit (d ≈ 0.43), they tend to produce visually similar rooms (interference), and any regeneration changes positions (destroying spatial memory). If auto-layout is offered at all, it should be a one-time scaffold the user then edits, never re-run on an existing palace.
- Density caps per room and per locus are the cheapest, best-supported safeguard; the Cockburn data suggest keeping any single view well under ~60–100 items.

### Gaps
- No study explicitly compares auto-generated vs user-built palace layouts; the inference is indirect.
- No data on how many rooms a user can keep distinct over months, or on degradation when a palace is extended incrementally.

---

## Key Question 6: Concrete design implications for a 2D top-down, user-built, avatar-walked memory palace mode in a PKM (room size, items per room, ordering, distinctiveness, user-built vs auto layouts, 2D vs 3D vs VR, revisiting/spaced review)

### Takeaway
The evidence supports a 2D, user-authored, spatially stable palace with distinct rooms, a deliberate "place" action per object, a visible route for anything ordered, low per-room density, no auto-rearrangement, and tight integration with search and the typed graph; it does not support investing in 3D or VR for recall gains, and it flags interference (reusing rooms for new material) and workflow disconnection as the main long-term risks.

### Cited Findings (evidence base for each implication)
- 2D vs 3D vs VR: 3D added no measurable retrieval benefit and increased clutter and time (Cockburn & McKenzie 2001, 2002); VR's gain over 3D desktop was +8.8 points from head-tracking with no walking (Krokos); desktop virtual environments matched real familiar environments (Legge 2012); passive VR lost to text (Johnsdorf 2023); VR practice added nothing over active control (Boller 2021). — [CHI 2002 PDF](https://www.csse.canterbury.ac.nz/andrew.cockburn/papers/chi02DM.pdf); [Krokos PDF](https://obj.umiacs.umd.edu/virtual_reality_study/10.1007-s10055-018-0346-3.pdf); [BPS/Legge](https://www.bps.org.uk/research-digest/memory-palace-mnemonic-strategy-works-virtual-environments); [Johnsdorf PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9975255/); [Boller PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7994284/)
- User-built: self-generated loci d ≈ 0.43 over assigned, stronger long-term (Moè & De Beni); Yang's participants asked for personalisation; Vindenes's users valued personal creative associations; Peeters & Segundo-Ortin recommend self-created imagery. — [Padua](https://research.unipd.it/handle/11577/2468982); [Yang TVCG](https://scispace.com/pdf/a-virtual-reality-memory-palace-variant-aids-knowledge-23c63ss5io.pdf); [Vindenes & Wasson](https://link.springer.com/article/10.1007/s10055-023-00868-y); [Moll & Sykes PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9540171/)
- Explicit placement action: click-to-lock gave +28% recall (Reggente 2020); fixed image loci gave 2.81× order-sensitive recall vs imagined placement (Huttner 2018). — [Springer](https://link.springer.com/article/10.1007%2Fs41465-019-00141-8); [HICSS PDF](https://pdfs.semanticscholar.org/e95e/e925865c9d999513b7a647b31c4f008ff532.pdf)
- Distinct rooms: dissimilar loci d = 0.91 vs similar −0.41; identical rooms confused users; distinct contexts per material set raised one-week retention 76% → 92%. — [Ondřej PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12514325/); [Moll & Sykes PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9540171/); [Essoe PDF](https://escholarship.org/content/qt5tv000gq/qt5tv000gq.pdf?t=rxglfz)
- Items per room/locus: ~2 items per locus (Crovitz via Ondřej); retrieval time climbs 3.2 → 5.0 s from 33 to 99 items on one surface, clutter ratings double. — [Ondřej PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12514325/); [CHI 2002 PDF](https://www.csse.canterbury.ac.nz/andrew.cockburn/papers/chi02DM.pdf)
- Ordering: strict-order recall improved only with path-preserving placement; collectibles guiding a path through every room produced high compliance (Bhandari 2019 via Moll & Sykes). — [Moll & Sykes PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9540171/)
- Stability: never rearrange; incremental growth is fine; avoid rotation; stable layouts outperform recency ordering and match paging at 700 items with faster revisitation. — [Scarr et al.](https://nowpublishers.com/article/DownloadSummary/HCI-046); [Tak et al.](https://research-portal.uu.nl/en/publications/improving-window-switching-interfaces/); [Gutwin GI 2020](https://graphicsinterface.org/?p=6040)
- Room visibility/hub layout: rooms with less visible entrances from the hub were under-used. — [Moll & Sykes PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9540171/)
- Complement, don't replace, search: location-only reference degrades faster than names as items grow. — [Jones & Dumais](https://scilit.com/publications/4c5b11cc06e84621618b9240435ffbf4)
- Thumbnails/visuals are not what carries location memory long-term; the arrangement is (Czerwinski 1999), but visually distinctive, personally meaningful items are memorised better (Cockburn). — [INTERACT 1999 PDF](https://www.microsoft.com/en-us/research/wp-content/uploads/1999/01/interact99.pdf); [Canterbury page](https://www.csse.canterbury.ac.nz/andrew.cockburn/2d3d.html)
- Active navigation: small-to-moderate advantage driven by decision-making/attention rather than motor effort; high motor demands can hurt. — [Qin & Karimi](https://journals.sagepub.com/doi/10.1177/17470218231185121); [Meade et al. PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6468686); [Chrastil & Warren PDF](https://link.springer.com/content/pdf/10.3758/s13423-011-0182-x.pdf)
- Retention decay and revisits: MoL effect in older adults fell d 0.94 → 0.48 by 3 days; user-arranged spatial layouts survived 6 months when revisited; training gains plateaued after a few sessions. — [Ondřej PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12514325/); [INTERACT 1999 PDF](https://www.microsoft.com/en-us/research/wp-content/uploads/1999/01/interact99.pdf); [Boller PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7994284/)
- Workflow integration: lack of text entry and separation from everyday tools drove abandonment over eight weeks. — [Vindenes & Wasson](https://link.springer.com/article/10.1007/s10055-023-00868-y)

### Inferences (design recommendations)
- Ship 2D top-down; treat any 3D/VR as optional presentation, not as the recall mechanism. The expected benefit of a 2D palace is in the Legge/Fassbender range (+10–25 points over no strategy on list-like material) only when the user actively places and revisits items; passive viewing of a pretty map should be assumed to be worth ~nothing.
- Make placement a deliberate, confirmed act (drag onto furniture, then "pin") and show the pinned object with a user-chosen or user-edited visual; let users attach a one-line "image/association" note per placement.
- Default to small rooms with a handful of loci (furniture) each, and warn or soft-cap when a room exceeds roughly a dozen items; keep a whole palace view well under ~100 visible objects before requiring the user to enter a room.
- Force or strongly encourage visual distinctiveness between rooms (different floor/wall palettes, landmark furniture, room names), and provide clear transitions (doors/corridors) rather than adjacent identical tiles.
- Offer an explicit, editable route (numbered waypoints or a drawn path) for anything with sequence (project steps, outlines, lists); the avatar walk can follow it; show route progress on revisit.
- Never auto-rearrange placed objects. If offering auto-layout, make it a one-time starter template that the user edits; growth should append rooms, not reflow existing ones. Avoid rotating or mirroring the map.
- Prefer new rooms for new material over overwriting old loci; when a room is reused, surface the prior occupant to let the user consciously replace it (interference is the known cost).
- Design the hub so every room's door is visible from a central space; under-visible rooms will be forgotten.
- Keep search, typed relations and dashboards one click away from any placed object; the palace should write back to the RDF graph (placement as a relation, room as a container) so it is an additional retrieval path, not a silo. Support text entry inside the palace.
- Add spaced revisits: schedule "walk the route" prompts for rooms/paths not visited recently; this is the obvious counter to the day-scale decay, though it is an inference, not a tested finding.
- Keep avatar controls trivial (click-to-move or arrow keys); the benefit of active navigation is in choosing where to go, not in motor skill.
- Position the mode as a motivation/engagement and organisation feature with a plausible recall bonus, not as a proven memory multiplier; the strongest controlled effects are on ordered word lists, not on rich notes.

### Gaps
- No empirical values exist for optimal room size, loci per room, or rooms per palace in software; the numbers above are extrapolations from density studies and the classic "~2 items per locus" rule.
- No study tests spaced review inside a virtual palace, nor the palace's effect on recall of rich, non-list knowledge over weeks (Yang's abstracts study is the closest, with a days-scale interval and n = 25).
- No study compares user-built vs auto-generated palace layouts head-to-head.
- No study evaluates a memory palace integrated into a working PKM/knowledge graph; the Vindenes & Wasson eight-week study is the only longitudinal in-the-wild data and measured no memory outcomes.
