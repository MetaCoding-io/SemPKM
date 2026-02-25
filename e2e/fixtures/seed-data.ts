/**
 * Constants for the Basic PKM seed data that auto-installs on first run.
 *
 * These IRIs and titles match the objects in models/basic-pkm/seed/basic-pkm.jsonld.
 * Tests can reference these to assert against known seed objects without hardcoding
 * strings in every test file.
 */

export const SEED = {
  projects: {
    sempkm: {
      iri: 'urn:sempkm:model:basic-pkm:seed-project-sempkm',
      title: 'SemPKM Development',
      status: 'active',
      priority: 'high',
    },
    garden: {
      iri: 'urn:sempkm:model:basic-pkm:seed-project-garden',
      title: 'Knowledge Garden',
      status: 'active',
      priority: 'medium',
    },
  },

  people: {
    alice: {
      iri: 'urn:sempkm:model:basic-pkm:seed-person-alice',
      name: 'Alice Chen',
      jobTitle: 'Lead Developer',
    },
    bob: {
      iri: 'urn:sempkm:model:basic-pkm:seed-person-bob',
      name: 'Bob Martinez',
      jobTitle: 'Product Designer',
    },
    carol: {
      iri: 'urn:sempkm:model:basic-pkm:seed-person-carol',
      name: 'Carol Singh',
      jobTitle: 'Domain Expert',
    },
  },

  notes: {
    architecture: {
      iri: 'urn:sempkm:model:basic-pkm:seed-note-architecture',
      title: 'Architecture Decision: Event Sourcing',
    },
    kickoff: {
      iri: 'urn:sempkm:model:basic-pkm:seed-note-kickoff',
      title: 'Meeting: Project Kickoff',
    },
    graphViz: {
      iri: 'urn:sempkm:model:basic-pkm:seed-note-graph-viz',
      title: 'Idea: Graph Visualization',
    },
  },

  concepts: {
    km: {
      iri: 'urn:sempkm:model:basic-pkm:seed-concept-knowledge-management',
      label: 'Knowledge Management',
    },
    semanticWeb: {
      iri: 'urn:sempkm:model:basic-pkm:seed-concept-semantic-web',
      label: 'Semantic Web',
    },
    eventSourcing: {
      iri: 'urn:sempkm:model:basic-pkm:seed-concept-event-sourcing',
      label: 'Event Sourcing',
    },
  },

  /** Total counts for assertions */
  counts: {
    projects: 2,
    people: 3,
    notes: 3,
    concepts: 3,
    total: 11,
  },
} as const;

/** Basic PKM type IRIs */
export const TYPES = {
  Note: 'urn:sempkm:model:basic-pkm:Note',
  Concept: 'urn:sempkm:model:basic-pkm:Concept',
  Project: 'urn:sempkm:model:basic-pkm:Project',
  Person: 'urn:sempkm:model:basic-pkm:Person',
} as const;
