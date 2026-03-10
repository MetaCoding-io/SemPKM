/**
 * Keyboard Navigation E2E Tests (CANV-03)
 *
 * Verifies arrow keys, Tab cycling, Delete, Enter, Escape, and Ctrl+S on canvas.
 */
import { test, expect } from '../../fixtures/auth';

test.describe('Spatial Canvas: Keyboard Navigation', () => {
  test.todo('arrow keys move selected node by one grid step (24px)');
  test.todo('shift+arrow moves selected node by 5 grid steps (120px)');
  test.todo('tab cycles focus through nodes in spatial order');
  test.todo('shift+tab cycles focus backward');
  test.todo('escape deselects the current node');
  test.todo('delete removes selected node without confirmation');
  test.todo('enter toggles neighbor expansion on selected node');
  test.todo('ctrl+s saves the current canvas session');
  test.todo('keyboard events do not fire during text input');
});
