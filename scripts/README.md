# Scripts

Utility scripts for managing a SemPKM instance.

## Available Scripts

### `reset-instance.sh`

Resets the SemPKM instance to a clean first-run state. Wipes the auth database (users, sessions, invitations), the setup token, and the secret key. After restarting, the API enters setup mode and displays a new setup token in the terminal logs.

```bash
./scripts/reset-instance.sh
docker compose logs api   # see the new setup token
```

**What it deletes:**
- `/app/data/sempkm.db` — SQLite auth database
- `/app/data/.setup-token` — persisted setup token
- `/app/data/.secret-key` — auto-generated secret key

**What it preserves:**
- RDF4J triplestore data (knowledge graph is untouched)
- Installed models
- Docker volumes other than auth data
