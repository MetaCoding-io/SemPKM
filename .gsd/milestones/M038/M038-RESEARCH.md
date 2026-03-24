# M038: Personal Media Scheduler App — Research

Research complete. Key findings:
- App SDK provides clean framework: decorator routes, task handlers, lazy-init clients
- RSS reader is the primary reuse target for podcast polling (feedparser, dedup, conditional GET)
- OAuth pattern proven across Google Calendar, Linear — Spotify follows same shape
- M037 context system fully operational (SSE, rules engine, geofences, notifications)
- No new Python dependencies needed — raw HTTP for YouTube and Spotify (consistent with all sync apps)
- Risk ordering: Spotify OAuth (HIGH) > Context polling latency (MEDIUM) > YouTube quota (LOW)
- Natural slice boundaries: model → podcast → YouTube → Spotify → rules → plan → UI → integration
