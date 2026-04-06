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
    modeSelect: '#explorer-mode-select', // deprecated — dropdown removed, use configBtn
    configBtn: '#explorer-config-btn',
    configPanel: '#explorer-config-panel',
    configType: '#explorer-config-type',
    configGroup: '#explorer-config-group',
    configSort: '#explorer-config-sort',
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
    iconToggle: '#graph-icon-toggle',
    isometricWrapper: '.graph-isometric-wrapper',
    kanbanBoard: '.kanban-board',
    kanbanColumn: '.kanban-column',
    kanbanCard: '.kanban-card',
    calendar: '[data-testid="calendar-view"]',
    map: '[data-testid="map-view"]',
    timeline: '[data-testid="timeline-view"]',
    timelineBar: '.bar-wrapper',
    timelineArrow: '.arrow',
    scopeSelect: '.view-scope-select',
    saveViewBtn: '.save-view-btn',
    typeFilterDropdown: '.type-filter-select',
    savedViewsTree: '#saved-views-tree',
    savedViewEntry: '.view-leaf[data-view-id]',
    calendarEvent: '.fc-event',
    quadrantBoard: '.quadrant-board',
    quadrantCell: '.quadrant-cell',
    bmcBoard: '.bmc-board',
    bmcSection: '.bmc-section',
    okrBoard: '.okr-board',
    okrObjectiveCard: '.okr-objective-card',
    dmBoard: '.dm-board',
    dmRow: '.dm-row',
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

  // Ontology viewer
  ontology: {
    ontologyPage: '[data-testid="ontology-page"]',
    tboxTree: '[data-testid="tbox-tree"]',
    tboxNode: '[data-testid="tbox-node"]',
    aboxBrowser: '[data-testid="abox-browser"]',
    aboxTypeRow: '[data-testid="abox-type-row"]',
    rboxLegend: '[data-testid="rbox-legend"]',
    tabTbox: '[data-testid="ontology-tab-tbox"]',
    tabAbox: '[data-testid="ontology-tab-abox"]',
    tabRbox: '[data-testid="ontology-tab-rbox"]',
  },
  // Tag hierarchy & autocomplete
  tagHierarchy: {
    folder: '[data-testid="tag-folder"]',
    object: '[data-testid="tag-object"]',
    treeChildren: '.tree-children',
    countBadge: '.tree-count-badge',
    treeLabel: '.tree-label',
    autocompleteField: '.tag-autocomplete-field',
    autocompleteInput: '.tag-autocomplete-field input[type="text"]',
    suggestionsDropdown: '.suggestions-dropdown',
    suggestionItem: '.suggestion-item',
  },

  // Operations log
  opsLog: {
    table: '[data-testid="ops-log-table"]',
    row: '.ops-log-row',
    typeBadge: '.ops-log-type-badge',
    filter: '#ops-log-filter',
    status: '.ops-log-status',
  },

  // Class creation
  classCreation: {
    createButton: '[data-testid="create-class-btn"]',
    form: '[data-testid="class-creation-form"]',
    nameInput: '#ccf-name',
    iconGrid: '#icon-picker-grid',
    iconCell: '.icon-picker-cell',
    parentSearch: '#ccf-parent-search',
    parentIri: '#ccf-parent-iri',
    propertyRows: '#property-rows',
    addPropertyButton: '.btn-add-property',
    submitButton: '[data-testid="ccf-submit"]',
    resultContainer: '[data-testid="ccf-result"]',
    deleteButton: '[data-testid="tbox-delete-btn"]',
  },

  // App platform (admin + workspace)
  apps: {
    // Admin pages
    adminList: '/admin/apps',
    adminDetail: '/admin/apps/test-app',
    installForm: 'form.install-form',
    installInput: '#app_path',
    installDetails: 'details.install-details',
    installPathInput: '#app_path',
    statusBadge: '.status-badge',
    appCard: '.dashboard-cards .card',
    // Workspace sidebar
    sidebarAppsSection: '#section-apps',
    appsTree: '#apps-tree',
    // Workspace panels
    workspaceAppMain: '#test-app-main',
    rightPaneSection: '#test-app-right-pane',
    commandDialog: '#test-app-command-dialog',
  },

  // GitHub Sync E2E
  githubSync: {
    patInput: '#github-pat',
    connectBtn: '.api-key-form button[type="submit"]',
    connectStatus: '.connection-status',
    username: '.username',
    repoCheckbox: '.repo-checkbox-item input[type="checkbox"]',
    saveReposBtn: '.repos-section button[type="submit"]',
    syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]',
    saveConfigBtn: '.sync-config-form button[type="submit"]',
    syncNowBtn: '#sync-now-btn',
    syncStats: '.sync-stats',
    statValue: '.stat-value',
  },

  // Linear Sync E2E
  linearSync: {
    apiKeyInput: '#linear-api-key',
    connectBtn: '.api-key-form button[type="submit"]',
    connectStatus: '.connection-status',
    workspaceName: '.workspace-name',
    teamCheckbox: '.team-checkbox-item input[type="checkbox"]',
    saveTeamsBtn: '.teams-section button[type="submit"]',
    syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]',
    saveConfigBtn: '.sync-config-form button[type="submit"]',
    syncNowBtn: '#sync-now-btn',
    syncStats: '.sync-stats',
    statValue: '.stat-value',
  },

  // Jira Sync E2E
  jiraSync: {
    emailInput: '#jira-email',
    tokenInput: '#jira-token',
    siteUrlInput: '#jira-site-url',
    connectBtn: '.credentials-form button[type="submit"]',
    connectStatus: '.connection-status',
    siteUrl: '.site-url',
    projectCheckbox: '.project-checkbox-item input[type="checkbox"]',
    saveProjectsBtn: '.projects-section button[type="submit"]',
    syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]',
    saveConfigBtn: '.sync-config-form button[type="submit"]',
    syncNowBtn: '#sync-now-btn',
    syncStats: '.sync-stats',
    statValue: '.stat-value',
  },

  // Monday.com Sync E2E
  mondaySync: {
    tokenInput: '#monday-token',
    connectBtn: '.credentials-form button[type="submit"]',
    connectStatus: '.connection-status',
    displayName: '.display-name',
    boardCheckbox: '.board-checkbox-item input[type="checkbox"]',
    saveBoardsBtn: '.boards-section button[type="submit"]',
    configureColumnsBtn: '.board-mapping-row a.btn',
    saveColumnMappingBtn: 'form[hx-post*="save-column-mapping"] button[type="submit"]',
    configureLabelsBtn: '.board-mapping-row a.btn:last-of-type',
    saveLabelMappingBtn: 'form[hx-post*="save-label-mapping"] button[type="submit"]',
    syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]',
    saveConfigBtn: '.sync-config-form button[type="submit"]',
    syncNowBtn: '#sync-now-btn',
    syncStats: '.sync-stats',
  },

  // Todoist Sync E2E
  todoistSync: {
    patInput: '#todoist-token',
    connectBtn: '.api-key-form button[type="submit"]',
    connectStatus: '.connection-status',
    tokenPreview: '.token-preview',
    projectCheckbox: '.project-checkbox-item input[type="checkbox"]',
    saveProjectsBtn: '.projects-section button[type="submit"]',
    syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]',
    saveConfigBtn: '.sync-config-form button[type="submit"]',
    syncNowBtn: '#sync-now-btn',
    syncStats: '.sync-stats',
    statValue: '.stat-value',
  },

  // Asana Sync E2E
  asanaSync: {
    patInput: '#asana-pat',
    connectBtn: '.api-key-form button[type="submit"]',
    connectStatus: '.connection-status',
    projectCheckbox: '.project-checkbox-item input[type="checkbox"]',
    saveProjectsBtn: '.projects-section button[type="submit"]',
    discoverFieldsBtn: '.discover-section button[type="submit"]',
    saveMappingBtn: '.field-mapping-form button[type="submit"]',
    statusSourceSection: '.status-source-radios',
    syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]',
    saveConfigBtn: '.sync-config-form button[type="submit"]',
    syncNowBtn: '#sync-now-btn',
    syncStats: '.sync-stats',
  },

  // CalDAV Calendar Sync E2E
  caldavCalendarSync: {
    serverUrlInput: '#caldav-server-url',
    usernameInput: '#caldav-username',
    passwordInput: '#caldav-password',
    credentialsSubmitBtn: '.credentials-form button[type="submit"]',
    connectStatus: '.connection-status',
    accountUsername: '.account-username',
    calendarCheckbox: '.calendar-checkbox-item input[type="checkbox"]',
    saveCalendarsBtn: '.calendars-section button[type="submit"]',
    syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]',
    saveConfigBtn: '.sync-config-form button[type="submit"]',
    syncNowBtn: '#sync-now-btn',
    syncStats: '.sync-stats',
  },

  // Google Calendar Sync E2E
  googleCalendarSync: {
    clientIdInput: '#gcal-client-id',
    clientSecretInput: '#gcal-client-secret',
    credentialsSubmitBtn: '.credentials-form button[type="submit"]',
    connectGoogleBtn: '.btn-google',
    connectStatus: '.connection-status',
    accountEmail: '.account-email',
    calendarCheckbox: '.calendar-checkbox-item input[type="checkbox"]',
    saveCalendarsBtn: '.calendars-section button[type="submit"]',
    syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]',
    saveConfigBtn: '.sync-config-form button[type="submit"]',
    syncNowBtn: '#sync-now-btn',
    syncStats: '.sync-stats',
  },

  // Outlook Calendar Sync E2E
  outlookCalendarSync: {
    clientIdInput: '#outlook-client-id',
    clientSecretInput: '#outlook-client-secret',
    credentialsSubmitBtn: '.credentials-form button[type="submit"]',
    connectMicrosoftBtn: '.btn-microsoft',
    connectStatus: '.connection-status',
    accountEmail: '.account-email',
    calendarCheckbox: '.calendar-checkbox-item input[type="checkbox"]',
    saveCalendarsBtn: '.calendars-section button[type="submit"]',
    syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]',
    saveConfigBtn: '.sync-config-form button[type="submit"]',
    syncNowBtn: '#sync-now-btn',
    syncStats: '.sync-stats',
  },

  // RSS Reader E2E
  rss: {
    readerContainer: '#rss-reader-container',
    feedSidebar: '#rss-feed-sidebar',
    articleList: '#rss-article-list',
    readingPane: '#rss-reading-pane',
    feedItem: '.rss-feed-item',
    articleItem: '.rss-article-item',
    subscribeBtn: '.rss-subscribe-btn',
    subscribeDialog: '#rss-subscribe-dialog',
    feedUrlInput: '#feed-url-input',
    emptyState: '.rss-empty-state',
    starBtn: '.rss-star-btn',
    opmlImportForm: '#rss-opml-import',
    opmlResult: '#opml-import-result',
    successMessage: '.alert-success, .success-box',
    settingsForm: '.rss-settings',
    settingsResult: '#rss-settings-result',
    sidebarIconBtn: '.rss-sidebar-actions button',
  },

  // Copilot chat
  copilot: {
    container: '#copilot-container',
    messages: '#copilot-messages',
    input: '#copilot-input',
    sendBtn: '#copilot-send-btn',
    tabBtn: 'button.panel-tab[data-panel="ai-copilot"]',
    convHeader: '#copilot-conv-header',
    convTitle: '#copilot-conv-title',
    convMenuBtn: '.copilot-conv-menu-btn',
    convDropdown: '#copilot-conv-dropdown',
    convDropdownItem: '.copilot-conv-dropdown-item',
    convNewBtn: '.copilot-conv-new-btn',
    msgAssistant: '.copilot-msg-assistant',
    msgUser: '.copilot-msg-user',
    msgError: '.copilot-msg-error',
    approvalCard: '.copilot-approval-card',
    approvalQuery: '.copilot-approval-query',
    approveBtn: '.copilot-approval-btn-approve',
    rejectBtn: '.copilot-approval-btn-reject',
    approvalSuccess: '.copilot-approval-success',
    personaSelector: '#copilot-persona-selector',
    personaBtn: '.copilot-persona-btn',
    personaName: '.copilot-persona-name',
    personaDropdown: '#copilot-persona-dropdown',
    personaItem: '.copilot-persona-item',
    personaItemActive: '.copilot-persona-item-active',
    personaItemName: '.copilot-persona-item-name',
    createCard: '.copilot-create-card',
    createLabel: '.copilot-create-label',
    createType: '.copilot-create-type',
    createProps: '.copilot-create-props',
    createSuccess: '.copilot-create-success',
    iriPill: '.copilot-iri-pill',
    typing: '#copilot-typing',
    empty: '#copilot-empty',
  },

  // Media Scheduler app
  mediaScheduler: {
    container: '#ms-container',
    sidebar: '#ms-sidebar',
    tabs: '#ms-tabs',
    tabContent: '#ms-tab-content',
    tabToday: '.ms-tab[data-tab="today"]',
    tabEpisodes: '.ms-tab[data-tab="episodes"]',
    tabRules: '.ms-tab[data-tab="rules"]',
    tabStats: '.ms-tab[data-tab="stats"]',
    sourcesList: '#ms-sources-list',
    sourceItem: '.ms-source-item',
    addFormToggle: '#ms-toggle-add-form',
    addSection: '#ms-add-section',
    addResult: '#ms-add-result',
    addForm: '.ms-add-form',
    todayView: '.ms-today-view',
    todayEmpty: '.ms-today-empty',
    todayHeader: '.ms-today-header',
    planEntry: '.ms-plan-entry',
    statusBadge: '.ms-status-badge',
    entryActions: '.ms-entry-actions',
    actionComplete: '.ms-action-complete',
    actionSkip: '.ms-action-skip',
    actionSave: '.ms-action-save',
    entryDone: '.ms-entry-done',
    rulesView: '.ms-rules-view',
    ruleCard: '.ms-rule-card',
    ruleName: '.ms-rule-name',
    ruleFormArea: '#ms-rule-form-area',
    ruleForm: '#ms-rule-form',
    rulesList: '#ms-rules-list',
    statsView: '.ms-stats-view',
    statsCard: '.ms-stats-card',
    chartHours: '#ms-chart-hours',
    chartTopSources: '#ms-chart-top-sources',
    chartWeekly: '#ms-chart-weekly',
    emptyState: '.ms-empty-state',
    success: '.ms-success',
    error: '.ms-error',
    itemsTable: '.ms-items-table',
  },

  // Dashboard blocks
  dashboard: {
    grid: '.grid-stack',
    statCard: '.dashboard-block-stat-card',
    statValue: '[data-stat-target]',
    chart: '.dashboard-block-chart',
    chartCanvas: 'canvas.chart-canvas',
    heading: '.dashboard-block-heading',
    markdown: '[data-md-block]',
    formGroup: '.dashboard-block-form-group',
    sparqlResult: '[data-sparql-table]',
    sparqlLoaded: '[data-sparql-loaded]',
    chartLoaded: '[data-chart-loaded]',
    blockError: '.dashboard-block-error',
    blockLoading: '.dashboard-block-loading',
  },
} as const;
