# RSS Feeds

**Model ID:** `rss-feeds` · **Namespace:** `urn:sempkm:model:rss-feeds:` · **Prefix:** `rss:`

The RSS Feeds model defines the two types behind the **RSS Reader** app: **FeedSubscription**
(a feed you follow) and **Article** (an entry fetched from a feed). Articles are ordinary
knowledge-graph objects, so they participate in search, tags, edges, views, and SPARQL like
anything else. The model ships no seed data — the RSS Reader app populates it as it polls.

## Types

### FeedSubscription

A subscription to an RSS or Atom feed.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | | Display name of the feed |
| Feed URL | URI | ✓ | URL of the RSS or Atom feed |
| Site URL | URI | | URL of the feed's website |
| Last Polled | dateTime | | When this feed was last polled |
| Error Count | integer | | Consecutive polling errors |
| Last Error | string | | Description of the most recent polling error |
| ETag | string | | HTTP ETag for conditional GET requests |
| Last-Modified Header | string | | HTTP Last-Modified header for conditional GET requests |

### Article

An article or entry from a feed.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | The article title |
| Link | URI | | Original URL of the article |
| Author | string | | Author of the article |
| Published | dateTime | | Publication date (`dcterms:created`) |
| Summary | string | | Article summary or excerpt |
| Feed Source | → FeedSubscription | | The subscription this article came from |
| Read | boolean | | Whether this article has been read |
| Starred | boolean | | Whether this article has been starred |
| Article ID | string | | Unique identifier from the feed (entry ID or GUID) |

## Relationships

```
Article ──feedSource──▸ FeedSubscription
```

## Views and saved queries

| View | Description |
|------|-------------|
| Articles Table / Articles Cards | All articles |
| Unread Articles | Articles with Read = false |
| Starred Articles | Articles with Starred = true |

The RSS Reader app also registers a custom renderer for `rss:Article`, so opening an article from
a view shows the reader layout instead of the generic form.

## Validation rules

None. Field constraints come from the SHACL shapes only.

## Installation

Install this model **before** the RSS Reader app: go to **Admin > Models**, pick **RSS Feeds**
from the bundled catalog (or enter `/app/models/rss-feeds`) and click **Install**. Then install
the app from **Admin > Applications** with the path `/app/apps/rss-reader`. See the user guide
chapter *RSS Reader* for the reader interface, OPML import, and polling settings.
