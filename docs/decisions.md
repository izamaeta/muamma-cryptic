# Design decisions

## Docker Compose for local and production

The app and PostgreSQL run in containers so the local setup matches the
server. The web container runs gunicorn as a non-root user. PostgreSQL is
pinned to 17, stores data in a named volume, and its port is bound to
localhost only.

The host port for PostgreSQL is 15432 to avoid clashing with a local
PostgreSQL install on the default port.