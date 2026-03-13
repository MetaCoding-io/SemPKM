/**
 * Comments E2E Tests
 *
 * Tests threaded object comments (CMT-01) and comment panel with
 * author attribution and timestamps (CMT-02):
 * - Empty state → post first comment → verify author + timestamp
 * - Reply to comment → threaded indentation verified
 * - Soft-delete parent → "[deleted]" body, replies preserved
 *
 * NOTE: Limited to ≤5 tests to stay within the auth rate limit
 * (5 magic-link calls per minute).
 */
import { test, expect } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';
import { openObjectTab } from '../../helpers/dockview';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';
import { execSync } from 'child_process';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';
const REPO_ROOT = execSync('git rev-parse --show-toplevel', { encoding: 'utf-8' }).trim();

/**
 * Wait for the comments section to be loaded in the right pane.
 * The loadRightPaneSection() fetch populates #comments-content
 * with the comments_section.html partial.
 */
async function waitForCommentsLoaded(page: import('@playwright/test').Page) {
  await page.waitForSelector('#comments-content .comments-section', { timeout: 15000 });
}

/**
 * Post a comment via the comment form in the right pane.
 * Waits for the htmx-triggered refresh cycle to complete.
 */
async function postComment(page: import('@playwright/test').Page, body: string) {
  const form = page.locator('#comments-content .comment-form');
  await form.locator('textarea[name="body"]').fill(body);
  await form.locator('button.comment-submit-btn').click();
  // After post, the HX-Trigger "commentsRefreshed" fires, which
  // triggers an hx-get on #comments-content to reload. Wait for the
  // new content to settle.
  await waitForIdle(page);
  // The commentsRefreshed trigger causes a full re-fetch of the comments
  // section — wait for the refreshed section to appear
  await page.waitForSelector('#comments-content .comments-section', { timeout: 10000 });
}

/**
 * Clean up leftover comments on an object by hard-deleting all comment
 * triples directly on the triplestore via the Docker-internal SPARQL
 * Update endpoint. This removes comments entirely (including soft-deleted
 * ones) so tests start with a truly clean slate.
 */
function cleanupComments(objectIri: string) {
  // Send SPARQL UPDATE directly to triplestore inside Docker network.
  // Deletes all triples for comments on this object (including soft-deleted).
  const sparql = `PREFIX sempkm: <urn:sempkm:> PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> DELETE { GRAPH <urn:sempkm:current> { ?c ?p ?o . } } WHERE { GRAPH <urn:sempkm:current> { ?c rdf:type sempkm:Comment ; sempkm:commentOn <${objectIri}> . ?c ?p ?o . } }`;

  // Write SPARQL to a temp file to avoid shell escaping issues
  const fs = require('fs');
  const tmpFile = '/tmp/sempkm-cleanup.sparql';
  fs.writeFileSync(tmpFile, sparql);

  // Copy into container and execute
  execSync(
    `docker compose -f docker-compose.test.yml cp ${tmpFile} triplestore:/tmp/cleanup.sparql`,
    { cwd: REPO_ROOT, encoding: 'utf-8', timeout: 10000 },
  );
  execSync(
    `docker compose -f docker-compose.test.yml exec -T triplestore curl -sf -X POST ` +
    `'http://localhost:8080/rdf4j-server/repositories/sempkm_test/statements' ` +
    `-H 'Content-Type: application/sparql-update' ` +
    `--data-binary @/tmp/cleanup.sparql`,
    { cwd: REPO_ROOT, encoding: 'utf-8', timeout: 10000 },
  );

  // Verify cleanup worked
  const verify = execSync(
    `docker compose -f docker-compose.test.yml exec -T triplestore curl -sf ` +
    `'http://localhost:8080/rdf4j-server/repositories/sempkm_test' ` +
    `-H 'Accept: application/sparql-results+json' ` +
    `--data-urlencode 'query=PREFIX sempkm: <urn:sempkm:> PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> SELECT (COUNT(?c) as ?cnt) WHERE { GRAPH <urn:sempkm:current> { ?c rdf:type sempkm:Comment ; sempkm:commentOn <${objectIri}> } }'`,
    { cwd: REPO_ROOT, encoding: 'utf-8', timeout: 10000 },
  );
  const count = JSON.parse(verify)?.results?.bindings?.[0]?.cnt?.value;
  if (count !== '0') {
    throw new Error(`Comment cleanup failed: ${count} comments remain for ${objectIri}`);
  }
}

test.describe('Comments', () => {
  // Use a known seed object for all comment tests
  const testIri = SEED.notes.architecture.iri;
  const testLabel = SEED.notes.architecture.title;

  test('empty state, post comment, verify author and timestamp (CMT-01, CMT-02)', async ({ ownerPage }) => {
    // Clean up any leftover comments from prior runs
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);
    await cleanupComments(testIri);

    // Open the test object tab — this triggers loadRightPaneSection for comments
    await openObjectTab(ownerPage, testIri, testLabel);
    await waitForCommentsLoaded(ownerPage);

    // ── Empty state ──
    const emptyMsg = ownerPage.locator('#comments-content .comments-empty');
    await expect(emptyMsg).toBeVisible({ timeout: 5000 });
    await expect(emptyMsg).toContainText('No comments yet');

    // No count badge should be visible when empty
    const countBadge = ownerPage.locator('#comments-content .comments-count-badge');
    await expect(countBadge).not.toBeVisible();

    // ── Post first comment ──
    const commentBody = 'E2E test comment — first post';
    await postComment(ownerPage, commentBody);

    // ── Verify display ──
    // The empty state should be gone
    await expect(emptyMsg).not.toBeVisible({ timeout: 5000 });

    // The comment should appear in the list
    const commentItem = ownerPage.locator('#comments-content .comment-item').first();
    await expect(commentItem).toBeVisible({ timeout: 5000 });

    // Verify comment body text
    const bodyEl = commentItem.locator('.comment-body');
    await expect(bodyEl).toHaveText(commentBody);

    // CMT-02: Verify author display name is shown (not "Unknown")
    const authorEl = commentItem.locator('.comment-author');
    await expect(authorEl).toBeVisible();
    const authorText = await authorEl.textContent();
    expect(authorText).toBeTruthy();
    expect(authorText!.trim()).not.toBe('Unknown');

    // CMT-02: Verify timestamp is shown (relative time like "just now")
    const timeEl = commentItem.locator('.comment-time');
    await expect(timeEl).toBeVisible();
    const timeText = await timeEl.textContent();
    expect(timeText).toBeTruthy();
    // Should be "just now" since we just posted
    expect(timeText!.trim()).toBe('just now');

    // Count badge should show "1 comment"
    const badge = ownerPage.locator('#comments-content .comments-count-badge');
    await expect(badge).toBeVisible({ timeout: 5000 });
    await expect(badge).toHaveText('1 comment');
  });

  test('reply creates threaded display and second top-level comment appears (CMT-01)', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Clean up and set up: ensure one comment exists
    await cleanupComments(testIri);
    await openObjectTab(ownerPage, testIri, testLabel);
    await waitForCommentsLoaded(ownerPage);

    // Post a root comment
    await postComment(ownerPage, 'Parent comment for threading test');

    // ── Click Reply on the root comment ──
    const firstComment = ownerPage.locator('#comments-content .comment-item').first();
    const replyBtn = firstComment.locator(':scope > .comment-actions .comment-reply-btn');
    await replyBtn.click();

    // Verify inline reply form appears
    const replyForm = firstComment.locator(':scope > .comment-reply-form');
    await expect(replyForm).toBeVisible({ timeout: 5000 });

    // ── Submit a reply ──
    const replyTextarea = replyForm.locator('textarea[name="body"]');
    await replyTextarea.fill('Threaded reply — child comment');
    await replyForm.locator('button.comment-submit-btn').click();

    // Wait for refresh
    await waitForIdle(ownerPage);
    await ownerPage.waitForSelector('#comments-content .comments-section', { timeout: 10000 });

    // ── Verify threading ──
    // The parent should still be visible
    const parentComment = ownerPage.locator('#comments-content .comment-item').first();
    await expect(parentComment.locator(':scope > .comment-body')).toHaveText('Parent comment for threading test');

    // The reply should be nested inside the parent's .comment-thread-line
    const threadLine = parentComment.locator(':scope > .comment-thread-line');
    await expect(threadLine).toBeVisible({ timeout: 5000 });

    const replyItem = threadLine.locator('.comment-item').first();
    await expect(replyItem).toBeVisible();
    await expect(replyItem.locator('.comment-body')).toHaveText('Threaded reply — child comment');

    // The reply is indented (margin-left > 0)
    const marginLeft = await replyItem.evaluate(
      (el) => getComputedStyle(el).marginLeft,
    );
    expect(parseInt(marginLeft, 10)).toBeGreaterThan(0);

    // Both comments should have author names (CMT-02)
    await expect(parentComment.locator(':scope > .comment-meta .comment-author')).not.toHaveText('Unknown');
    await expect(replyItem.locator('.comment-author')).not.toHaveText('Unknown');

    // ── Post another top-level comment ──
    await postComment(ownerPage, 'Second top-level comment');

    // Now there should be 2 root-level comments (the parent+reply, and the new one)
    // Count badge should show 3 total (parent + reply + new)
    const badge = ownerPage.locator('#comments-content .comments-count-badge');
    await expect(badge).toHaveText('3 comments', { timeout: 5000 });

    // The second top-level comment should appear
    const allRootComments = ownerPage.locator(
      '#comments-content .comments-list > .comment-item',
    );
    await expect(allRootComments).toHaveCount(2, { timeout: 5000 });
  });

  test('soft-delete parent shows "[deleted]" but preserves reply thread', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Clean up and create a parent + reply
    await cleanupComments(testIri);
    await openObjectTab(ownerPage, testIri, testLabel);
    await waitForCommentsLoaded(ownerPage);

    // Post parent
    await postComment(ownerPage, 'Comment to be deleted');

    // Reply to it
    const parentComment = ownerPage.locator('#comments-content .comment-item').first();
    const replyBtn = parentComment.locator(':scope > .comment-actions .comment-reply-btn');
    await replyBtn.click();

    const replyForm = parentComment.locator(':scope > .comment-reply-form');
    await replyForm.locator('textarea[name="body"]').fill('Reply that should survive deletion');
    await replyForm.locator('button.comment-submit-btn').click();
    await waitForIdle(ownerPage);
    await ownerPage.waitForSelector('#comments-content .comments-section', { timeout: 10000 });

    // Confirm both exist
    const badge = ownerPage.locator('#comments-content .comments-count-badge');
    await expect(badge).toHaveText('2 comments', { timeout: 5000 });

    // ── Delete the parent comment ──
    // Set up dialog handler BEFORE clicking delete
    ownerPage.once('dialog', async (dialog) => {
      expect(dialog.type()).toBe('confirm');
      expect(dialog.message()).toContain('Delete this comment?');
      await dialog.accept();
    });

    // The parent comment's delete button
    const parentItem = ownerPage.locator('#comments-content .comments-list > .comment-item').first();
    const deleteBtn = parentItem.locator(':scope > .comment-actions .comment-delete-btn');
    await deleteBtn.click();

    // Wait for the refresh cycle
    await waitForIdle(ownerPage);
    await ownerPage.waitForSelector('#comments-content .comments-section', { timeout: 10000 });

    // ── Verify soft-delete result ──
    const deletedParent = ownerPage.locator('#comments-content .comments-list > .comment-item').first();

    // Body should show "[deleted]"
    const deletedBody = deletedParent.locator(':scope > .comment-body');
    await expect(deletedBody).toHaveText('[deleted]', { timeout: 5000 });

    // The deleted comment should have the .comment-deleted class
    await expect(deletedParent).toHaveClass(/comment-deleted/);

    // Author should show "Unknown" (author triple was removed)
    const deletedAuthor = deletedParent.locator(':scope > .comment-meta .comment-author');
    await expect(deletedAuthor).toHaveText('Unknown');

    // Reply button should NOT be visible on a deleted comment
    const deletedReplyBtn = deletedParent.locator(':scope > .comment-actions .comment-reply-btn');
    await expect(deletedReplyBtn).not.toBeVisible();

    // Delete button should NOT be visible on an already-deleted comment
    const deletedDeleteBtn = deletedParent.locator(':scope > .comment-actions .comment-delete-btn');
    await expect(deletedDeleteBtn).not.toBeVisible();

    // ── Reply is still intact ──
    const threadLine = deletedParent.locator(':scope > .comment-thread-line');
    await expect(threadLine).toBeVisible();

    const replyItem = threadLine.locator('.comment-item').first();
    await expect(replyItem.locator('.comment-body')).toHaveText('Reply that should survive deletion');

    // Reply author should still be present (not "Unknown")
    const replyAuthor = replyItem.locator('.comment-author');
    await expect(replyAuthor).not.toHaveText('Unknown');

    // Comment count badge still shows both comments
    await expect(badge).toHaveText('2 comments');
  });
});
