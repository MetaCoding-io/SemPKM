# Chapter 12: Webhooks

Webhooks let your SemPKM instance notify external services whenever something changes. When an object is updated, an edge is created, or a validation run completes, SemPKM sends an HTTP POST request to a URL you specify, carrying a JSON payload that describes the event. This enables real-time integrations with automation platforms, notification systems, and custom scripts without any polling.

## What Webhooks Do

A webhook is a one-way notification: SemPKM pushes data outward whenever a matching event occurs. The receiving system can then act on that notification however it wants -- send a Slack message, update a spreadsheet, trigger a build pipeline, or synchronize data with another tool.

SemPKM webhooks use **fire-and-forget** semantics. The system sends the HTTP POST and logs the result, but it never retries on failure and never blocks the user's action waiting for a webhook response. If the target URL is down or returns an error, SemPKM logs a warning and moves on. Your data operations are never delayed or prevented by a misbehaving webhook endpoint.

> **Note:** Webhooks are delivered with a 5-second HTTP timeout. If your receiving endpoint takes longer than 5 seconds to respond, the delivery will be recorded as a failure in the server logs.

## Event Types

SemPKM supports three webhook event types. When configuring a webhook, you select which event types it should listen for.

### object.changed

Fired when an object is created, updated, or has its body content set. This covers the `object.create`, `object.patch`, and `body.set` command operations.

**Example payload:**

```json
{
  "event_type": "object.changed",
  "event_iri": "urn:sempkm:event:a1b2c3d4-...",
  "timestamp": "2026-02-24T14:30:00Z",
  "operation": "object.patch",
  "affected_iris": ["https://example.org/data/note/meeting-notes-feb"]
}
```

Use this event type to react when someone creates a new Note, updates a Project's status, or edits a Person's contact details.

### edge.changed

Fired when a relationship edge is created or modified. This covers the `edge.create` and `edge.patch` command operations.

**Example payload:**

```json
{
  "event_type": "edge.changed",
  "event_iri": "urn:sempkm:event:e5f6g7h8-...",
  "timestamp": "2026-02-24T14:32:00Z",
  "operation": "edge.create",
  "affected_iris": [
    "https://example.org/data/person/alice",
    "https://example.org/data/project/sempkm-development"
  ]
}
```

Use this event type to react when someone links a Person to a Project, connects a Note to a Concept, or modifies a relationship property.

### validation.completed

Fired when an asynchronous SHACL validation run finishes. This occurs after any data change that triggers the validation queue.

**Example payload:**

```json
{
  "event_type": "validation.completed",
  "event_iri": "urn:sempkm:event:i9j0k1l2-...",
  "timestamp": "2026-02-24T14:30:02Z",
  "conforms": false,
  "violations": 2,
  "warnings": 1
}
```

Use this event type to monitor data quality. For example, you could send a notification whenever validation finds new violations, or track conformance rates over time.

## Configuring Webhooks

Webhook configuration is available to the **owner** only, through the Admin Portal.

### Accessing the Webhook Page

1. Click **Admin** in the left sidebar (or navigate to `/admin`).
2. On the Admin Portal landing page, click **Configure Webhooks** (or go directly to `/admin/webhooks`).

<!-- Screenshot: Admin Portal landing page showing the Mental Models and Webhooks cards -->

### Creating a Webhook

The webhook page shows a **Create Webhook** form at the top and a list of existing webhooks below.

<!-- Screenshot: Webhook configuration page with the create form and webhook list table -->

To create a new webhook:

1. **Target URL** -- Enter the full URL that should receive the POST requests. This must be an HTTP or HTTPS endpoint that accepts JSON payloads.

2. **Events** -- Check one or more event types:
   - `object.changed`
   - `edge.changed`
   - `validation.completed`

   You must select at least one event type. If you submit the form without checking any events, you will see an error: "Please select at least one event type."

3. **Filters** (optional) -- Enter comma-separated type IRIs or namespace prefixes to restrict which events trigger this webhook. For example, entering `bpkm:Person, bpkm:Note` means only events affecting Person or Note objects will fire this webhook. Leave this field empty to receive events for all types.

4. Click **Create**. The webhook appears in the list below with its target URL, subscribed events, filters, and an "Enabled" status badge.

### The Webhook List

The webhook list table shows all configured webhooks with the following columns:

| Column | Description |
|---|---|
| **Target URL** | The endpoint receiving POST requests |
| **Events** | Badges showing subscribed event types |
| **Filters** | Type/namespace filters, or "None" if unfiltered |
| **Status** | Enabled (green badge) or Disabled (red badge) |
| **Actions** | Enable/Disable toggle and Delete button |

### Enabling and Disabling Webhooks

Each webhook has a toggle button in the Actions column. Click **Disable** to pause a webhook without deleting its configuration. Disabled webhooks remain in the list but do not receive any event notifications. Click **Enable** to resume delivery.

This is useful when you need to temporarily stop notifications (for example, while a receiving service is under maintenance) without losing the webhook's URL and event configuration.

### Deleting a Webhook

Click the **Delete** button next to a webhook and confirm the deletion prompt. This permanently removes the webhook configuration from the triplestore. The action cannot be undone.

## How Webhook Storage Works

Unlike user accounts and sessions (which are stored in the SQL database), webhook configurations are stored as **RDF triples** in a dedicated named graph (`urn:sempkm:webhooks`) in the triplestore. Each webhook is represented as:

```turtle
<urn:sempkm:webhook:a1b2c3d4> a sempkm:Webhook ;
    sempkm:targetUrl "https://example.com/webhook" ;
    sempkm:event "object.changed" ;
    sempkm:event "edge.changed" ;
    sempkm:filter "bpkm:Person" ;
    sempkm:enabled "true"^^xsd:boolean .
```

This means webhook configurations are queryable via SPARQL, follow the same RDF data model as the rest of your knowledge, and are backed up along with your triplestore data.

## Testing Webhook Delivery

SemPKM does not include a built-in "test" button for webhooks, but you can verify delivery by following these steps:

1. **Set up a request catcher.** Use a free service like [webhook.site](https://webhook.site) or [RequestBin](https://requestbin.com) to get a temporary URL that captures and displays incoming HTTP requests.

2. **Create a webhook** pointing to the catcher URL, subscribing to `object.changed`.

3. **Make a change** in SemPKM -- for example, create a new Note or edit an existing Project's title.

4. **Check the catcher.** You should see an incoming POST request with a JSON body containing the `event_type`, `event_iri`, `timestamp`, and other payload fields.

5. **Check the server logs.** Successful deliveries are logged at debug level:

```
Webhook a1b2c3d4 dispatched to https://webhook.site/...: status 200
```

Failed deliveries are logged as warnings:

```
Webhook dispatch failed for a1b2c3d4 -> https://example.com/down
```

> **Tip:** If you are running SemPKM locally with Docker Compose, webhook URLs that point to `localhost` on the host machine will not work from inside the container. Use your machine's local IP address (e.g., `http://192.168.1.100:8080/hook`) or the special Docker hostname `host.docker.internal` if your platform supports it.

## Integration Ideas

### n8n

[n8n](https://n8n.io) is an open-source workflow automation platform you can self-host alongside SemPKM.

1. In n8n, create a new workflow and add a **Webhook** trigger node.
2. Set the HTTP method to POST and copy the generated webhook URL.
3. In SemPKM, create a webhook pointing to the n8n URL, subscribing to the event types you need.
4. In n8n, add downstream nodes to process the payload -- for example, an **IF** node to check the event type, a **Slack** node to send notifications, or an **HTTP Request** node to call another API.

**Example workflow:** Notify a Slack channel whenever a new Person is added to SemPKM. Subscribe to `object.changed`, filter for `bpkm:Person`, and route the payload through n8n to the Slack API.

### Zapier

If you prefer a hosted automation platform:

1. Create a Zap with a **Webhooks by Zapier** trigger (Catch Hook).
2. Copy the generated URL.
3. Create a SemPKM webhook pointing to the Zapier URL.
4. Add Zapier actions to do whatever you need -- send emails, update Google Sheets, create Trello cards, and so on.

### Custom Scripts

For simple integrations, you can write a small HTTP server that receives webhook payloads. Here is a minimal Python example using Flask:

```python
from flask import Flask, request

app = Flask(__name__)

@app.route("/hook", methods=["POST"])
def handle_webhook():
    data = request.json
    print(f"Event: {data['event_type']}")
    print(f"Affected: {data.get('affected_iris', [])}")
    # Do something useful here
    return "OK", 200

if __name__ == "__main__":
    app.run(port=9000)
```

Point your SemPKM webhook to `http://<your-server>:9000/hook` and you have a working integration.

## Payload Reference

All webhook payloads share a common field:

| Field | Type | Description |
|---|---|---|
| `event_type` | string | One of `object.changed`, `edge.changed`, `validation.completed` |

Additional fields depend on the event type:

**object.changed / edge.changed:**

| Field | Type | Description |
|---|---|---|
| `event_iri` | string | The unique IRI of the event in the Event Log |
| `timestamp` | string | ISO 8601 timestamp of when the event occurred |
| `operation` | string | The specific operation (e.g., `object.create`, `edge.patch`) |
| `affected_iris` | array | IRIs of the objects or edges affected |

**validation.completed:**

| Field | Type | Description |
|---|---|---|
| `event_iri` | string | The IRI of the triggering event |
| `timestamp` | string | ISO 8601 timestamp |
| `conforms` | boolean | Whether the data passes all SHACL constraints |
| `violations` | integer | Number of SHACL violation-severity results |
| `warnings` | integer | Number of SHACL warning-severity results |

## What is Next

Now that you know how to push data outward with webhooks, the next chapter covers how to customize your SemPKM experience through the Settings system.

[Settings](13-settings.md)
