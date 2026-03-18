# Chapter 30: Workspace Personas

A **persona** is a named workspace configuration that saves your panel layout,
sidebar arrangement, and explorer mode. Switching between personas instantly
reconfigures the workspace — no manual rearranging needed.

Use personas to create purpose-built workspaces for different activities:

- A **Research** persona with the SPARQL console open, the graph view in focus,
  and reference panels docked to the side.
- A **Writing** persona with a minimal layout — just the editor and the explorer,
  with no bottom panel.
- A **Review** persona with the Event Log and Lint Dashboard prominently placed
  for auditing recent changes.

Each persona captures a snapshot of how the workspace is arranged. You can switch
between them at any time, and your current layout is automatically saved before
the switch.

---

## Default Persona

The first time you load the SemPKM workspace, a persona named **"Default"** is
automatically created. This captures your initial workspace state — the panel
layout, sidebar positions, and explorer mode that the workspace starts with.

You do not need to do anything to create the Default persona. It exists to ensure
you always have at least one persona to fall back to, and it serves as a baseline
you can return to after experimenting with other layouts.

---

## Creating a Persona

There are two ways to create a new persona:

### Via the Sidebar

1. Click your **user avatar** (or username) in the sidebar to open the user popover.
2. In the **PERSONAS** section of the popover, click the **+** button.
3. Enter a name for the new persona (e.g., "Research", "Writing", "Daily Review").
4. The new persona is created and captures the **current** workspace state — whatever
   panels are open, however the sidebar is arranged, and whichever explorer mode
   is active.

### Via the Command Palette

1. Press **Ctrl+K** (or **Cmd+K** on macOS) to open the command palette.
2. Type **"Persona: Create New..."** and select it.
3. Enter a name for the persona.
4. The workspace state is captured into the new persona.

The newly created persona becomes the **active** persona immediately.

---

## Switching Personas

### Via the Sidebar

1. Open the user popover by clicking your user avatar in the sidebar.
2. In the **PERSONAS** section, click the name of the persona you want to switch to.
3. The workspace reconfigures to match that persona's saved layout.

### Via the Command Palette

1. Press **Ctrl+K** to open the command palette.
2. Type **"Persona: Switch To..."** and select it.
3. Choose the target persona from the list.

When you switch personas:

1. Your **current** persona's state is **automatically saved** first — you never
   lose unsaved layout changes.
2. The target persona's saved state is **restored**, reconfiguring panels, sidebar
   positions, and the explorer mode.

---

## Saving Persona State

Persona state is saved automatically in several situations:

- **When switching** to another persona (the outgoing persona is saved first).
- **When closing** the browser tab (the active persona's state is saved on unload).

You can also save manually at any time:

### Via the Sidebar

Click the **Save** button in the PERSONAS section of the user popover. This saves
the current workspace layout into the active persona.

### Via the Command Palette

Press **Ctrl+K** and type **"Persona: Save Current"**. This is equivalent to
clicking the Save button in the sidebar.

> **Tip:** Manual saves are useful after you have arranged the workspace exactly
> how you want it. While auto-save catches most layout changes, an explicit save
> ensures your preferred layout is captured before you make experimental changes.

---

## Renaming and Deleting

### Renaming

Persona renaming is currently available via the API:

```
PUT /api/personas/{id}
Content-Type: application/json

{ "name": "New Persona Name" }
```

Replace `{id}` with the persona's UUID (visible in the sidebar popover's HTML or
via `GET /api/personas`). A sidebar rename UI will be added in a future release.

### Deleting

To delete a persona, click the **delete** button (trash icon) next to the persona
name in the sidebar popover's PERSONAS section.

If you delete the **currently active** persona, SemPKM automatically activates
another available persona. If only one persona remains, it cannot be deleted.

> **Warning:** Deleting a persona is permanent. The saved layout state is removed
> and cannot be recovered.

---

## What's Saved

Each persona stores the following workspace state:

| Saved                       | Description                                                      |
|-----------------------------|------------------------------------------------------------------|
| **Panel layout**            | Which Dockview panels/tabs are open, their positions, and sizes  |
| **Sidebar panel positions** | The arrangement of sidebar panels (Explorer, Favorites, etc.)    |
| **Explorer mode**           | The active explorer grouping mode (By Type, By Tag, etc.)        |

The following are **not** saved per persona (they are global user settings):

| Not saved        | Why                                                              |
|------------------|------------------------------------------------------------------|
| Theme            | Theme preference applies across all personas                     |
| Font size        | Typography settings are user-level, not layout-level             |
| User settings    | Authentication state, API keys, and preferences are global       |

Personas are intentionally **layout-only** in this version. This keeps them fast
to switch and predictable in behavior — you always know that switching a persona
only changes what you see, not how the application behaves.

---

---

**Previous:** [Chapter 29: Mental Model Catalog](29-mental-model-catalog.md) | **Next:** [Chapter 31: API Surface](31-api-surface.md)
