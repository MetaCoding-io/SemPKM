#!/bin/sh
# Backend entrypoint — ensure data subdirectories exist before handing off to CMD.
# Runs as user sempkm (uid 1000). No privilege escalation (no gosu/su-exec).
set -e

mkdir -p /app/data/apps /app/data/imports

exec "$@"
