"""OWL 2 RL inference engine for SemPKM.

Provides forward-chaining OWL 2 RL inference using the owlrl library.
Inferred triples are stored in urn:sempkm:inferred, separate from
user-created data in urn:sempkm:current. Inference is manual-trigger
only (not automatic on every write).
"""
