/**
 * Shared CSS selectors for SemPKM E2E tests.
 *
 * Prefer data-testid selectors when available. Falls back to semantic
 * selectors (role, label, structural CSS) for elements not yet annotated.
 *
 * Update these as data-testid attributes are added to templates.
 */

export const SEL = {
  // Auth pages
  auth: {
    setupForm: '#setupForm',
    setupTokenInput: '#setup-token',
    setupEmailInput: '#setup-email',
    setupSubmit: '#setupForm button[type="submit"]',
    setupMessage: '#setup-message',
    loginForm: '#loginForm',
    loginEmailInput: '#login-email',
    loginSubmit: '#loginForm button[type="submit"]',
    loginMessage: '#login-message',
  },

  // Workspace layout
  workspace: {
    container: '[data-testid="workspace"]',
    sidebar: '[data-testid="sidebar"]',
    editorArea: '[data-testid="editor-area"]',
    propertiesPanel: '[data-testid="properties-panel"]',
    tabBar: '[data-testid="tab-bar"]',
  },

  // Navigation tree
  nav: {
    tree: '[data-testid="nav-tree"]',
    section: '[data-testid="nav-section"]',
    item: '[data-testid="nav-item"]',
    sidebarToggle: '.sidebar-toggle',  // No data-testid; uses CSS class
  },

  // Explorer mode switching
  explorer: {
    modeSelect: '#explorer-mode-select',
    treeBody: '#explorer-tree-body',
    placeholder: '[data-testid="explorer-placeholder"]',
    mountOption: 'option[value^="mount:"]',
    mountFolderNode: '[data-testid="mount-folder"]',
    mountObjectLeaf: '[data-testid="mount-object"]',
  },

  // Type picker
  typePicker: {
    overlay: '[data-testid="type-picker"]',
    typeOption: '[data-testid="type-option"]',
  },

  // Object editor
  editor: {
    form: '[data-testid="object-form"]',
    titleInput: 'input[name*="title"], input[name*="name"], input[name*="label"]',
    saveButton: '[data-testid="save-button"]',
  },

  // Views
  views: {
    table: '[data-testid="table-view"]',
    tableRow: '[data-testid="table-row"]',
    cards: '.card-grid',  // No data-testid on card grid container; use CSS class
    card: '[data-testid="card-item"]',
    graph: '[data-testid="graph-view"]',
  },

  // Admin
  admin: {
    modelList: '[data-testid="model-list"]',
    webhookList: '[data-testid="webhook-list"]',
  },

  // Lint panel
  lint: {
    panel: '[data-testid="lint-panel"]',
    violation: '[data-testid="lint-violation"]',
  },

  // Settings
  settings: {
    page: '[data-testid="settings-page"]',
    themeBtn: '.theme-btn',  // Theme buttons in sidebar popover (light/system/dark)
  },

  // Favorites
  favorites: {
    section: '#section-favorites',
    sectionBody: '#favorites-tree-body',
    item: '[data-testid="favorites-item"]',
    starBtn: '.star-btn',
    hint: '#favorites-tree-body .tree-empty',
  },

  // Command palette
  commandPalette: {
    overlay: 'ninja-keys',
    input: 'ninja-keys input',
  },
} as const;
