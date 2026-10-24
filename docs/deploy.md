# Going live

This document builds a server from nothing, opens the site, updates it and
restores from a backup when that is needed. The steps are meant to be read
in order.

No real password, key or token is written down anywhere: every secret that
gets generated goes straight into `.env.production` on the server, and that
file is not in git (`.gitignore`). The same holds for the certificate: the
origin certificate and its private key live in `certs/` on the server,
which is not in git either.

## Where a request goes

```
Player  →  Cloudflare  →  Caddy  →  gunicorn (muamma)
                            │          │
                            │          ├── PostgreSQL
                            │          └── Redis (rate limits)
                            └── /static/* (direct, cached a year)
```

The only thing open to the outside is Caddy's port 443, and only to the
Cloudflare ranges. PostgreSQL and Redis stay inside the compose network and
publish no ports at all.

Caddy does not obtain a certificate of its own: it reads the Cloudflare
Origin CA certificate from disk. The hop to the origin is encrypted too,
but that certificate is validated by Cloudflare, never by a browser.

## 1. S3 bucket

One bucket is enough for the backups:

1. Create a new bucket (same region as the server, for example
   `eu-north-1`).
2. Leave **Block all public access** on.
3. **Default encryption**: SSE-S3 (or KMS if you prefer).
4. **Versioning** is worth turning on: a backup deleted by accident comes
   back.
5. Note the bucket name; it becomes `BACKUP_BUCKET` in `.env.production`.

Backups are stored as `s3://<bucket>/muamma/muamma-<timestamp>.sql.gz`.

## 2. IAM role

The server writes to S3 as itself. No key goes into the environment: a key
that does not exist cannot leak.

1. Create a new IAM **role**, trusted service: EC2.
2. Attach this inline policy (replace `BUCKET` with your own):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::BUCKET/muamma/*"
    },
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::BUCKET",
      "Condition": { "StringLike": { "s3:prefix": "muamma/*" } }
    }
  ]
}
```

3. Attach the role to the server (EC2 → Actions → Security → Modify IAM
   role).

## 3. Server

- Type: **t4g.small** (ARM, Graviton). Every image runs on arm64.
- Operating system: Ubuntu 24.04 LTS **arm64**.
- Disk: 20 GB gp3 is enough; the database is small and the backups are in
  S3.

Two settings matter while the instance is being created:

- **IMDSv2: required**, **hop limit: 2**. The backup runner works inside a
  container, so it needs the second hop to read credentials from the
  instance metadata. To change it afterwards:

  ```bash
  aws ec2 modify-instance-metadata-options \
      --instance-id i-XXXXXXXX \
      --http-tokens required \
      --http-put-response-hop-limit 2
  ```

- **Security group**: only **443**, and only to the Cloudflare ranges
  (https://www.cloudflare.com/ips/). Port 80 is not needed at all: there is
  no ACME validation and Cloudflare always connects to the origin over
  HTTPS. The origin is therefore unreachable directly and everyone has to
  come through Cloudflare. Open 22 to your own address only; use SSM
  Session Manager if you can and leave 22 closed.

## 4. Docker

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=arm64 signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" |
    sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
```

Log out and back in once after the last command; that is when the group
membership takes effect.

## 5. Repository and settings

```bash
git clone https://github.com/izamaeta/muamma-cryptic.git
cd muamma-cryptic
cp .env.production.example .env.production
chmod 600 .env.production
```

What to fill in inside `.env.production`:

| Setting | What to write |
| --- | --- |
| `SECRET_KEY` | Output of `openssl rand -hex 32`. Changing it resets every player's progress. |
| `SITE_URL` | Like `https://muamma.app`, without a trailing slash |
| `SITE_DOMAIN` | The same domain, without the scheme (`muamma.app`) |
| `CONTACT_EMAIL` | The contact address shown on the site |
| `POSTGRES_PASSWORD` | Output of `openssl rand -base64 24` |
| `AWS_REGION` | The server's region |
| `BACKUP_BUCKET` | The bucket from step 1 |

`SESSION_COOKIE_SECURE=1`, `HSTS_ENABLED=1` and `TRUSTED_PROXY_HOPS=2` are
already right in the example; leave them alone.

## 6. Cloudflare

The certificate comes from Cloudflare, so this step happens before the
first start: Caddy will not come up without the files in place.

**The origin certificate first.** SSL/TLS → Origin Server → **Create
Certificate**:

- Let Cloudflare generate the private key (the default), type **RSA
  (2048)**.
- Hostnames: `muamma.app` and `*.muamma.app`.
- Validity: 15 years. Note the expiry date somewhere; this certificate does
  not renew itself.

The page that opens has two blocks of text, and **the private key is never
shown again**. Write both into these files on the server:

```bash
mkdir -p certs && chmod 700 certs
nano certs/origin.pem          # the Origin Certificate block
nano certs/origin.key          # the Private Key block
chmod 600 certs/origin.key
```

`certs/` is in both `.gitignore` and `.dockerignore`: the private key goes
neither into git nor into an image. Caddy sees the directory read-only.

To replace the certificate later — when it expires or if the key leaks —
write the new files in the same place, then restart Caddy. The files are
read at startup only, and an update pulled with `git pull` does not touch
Caddy:

```bash
docker compose -f compose.prod.yaml --env-file .env.production restart caddy
```

**Then DNS and the SSL settings:**

1. Add an **A record** for the domain pointing at the server's public IP,
   **Proxied** (orange cloud). There is no need for the grey cloud: there
   is no ACME validation, and the security group only admits requests that
   come from Cloudflare anyway.
2. SSL/TLS → Overview → **Full (strict)**. This is the mode that validates
   the origin certificate; "Flexible" or "Full" would leave the hop to the
   origin unverified.
3. SSL/TLS → Edge Certificates → **Always Use HTTPS** on.
4. Caching → do **not** add a rule that caches HTML: the day's puzzle and
   the player's state have to come from the server on every request.
   `/static/*` already arrives with a one year cache and Cloudflare keeps
   it by itself.

Static addresses end in `?v=<hash>`: the address changes when the file
does, which is what makes the long cache safe and why no cache purge is
needed after a deploy.

## 7. First start

```bash
docker compose -f compose.prod.yaml --env-file .env.production up -d --build
docker compose -f compose.prod.yaml --env-file .env.production ps
```

Migrations run by themselves while the web container starts; there is no
separate step. To check:

```bash
docker compose -f compose.prod.yaml --env-file .env.production logs web | head -30
```

Check that Caddy read the certificate too; the container stops here if the
files are missing or broken:

```bash
docker compose -f compose.prod.yaml --env-file .env.production logs caddy | tail -20
```

Create the admin account (it asks for the password, which does not appear
on the command line):

```bash
docker compose -f compose.prod.yaml --env-file .env.production \
    exec web flask create-admin you@example.com
```

A last check, now over the domain:

```bash
curl -I https://muamma.app
```

## 8. Updating

```bash
cd muamma-cryptic
git pull
docker compose -f compose.prod.yaml --env-file .env.production up -d --build
```

The new web container applies the migrations as it starts. Caddy keeps
talking to the old container until the health check passes, so there is a
short gap but no dropped request.

A look afterwards:

```bash
docker compose -f compose.prod.yaml --env-file .env.production ps
docker compose -f compose.prod.yaml --env-file .env.production logs -n 50 web
curl -I https://muamma.app
```

If old images fill the disk:

```bash
docker image prune -f
```

## 9. Backups

Every day at `BACKUP_AT` (03:15 by default, in the server's timezone) the
`backup` service:

1. takes a full dump with `pg_dump` and compresses it with `gzip`,
2. uploads it to `s3://<bucket>/muamma/muamma-<timestamp>.sql.gz`,
3. deletes backups older than 30 days (`BACKUP_KEEP_DAYS`).

After setup, take one backup by hand to see that it works:

```bash
docker compose -f compose.prod.yaml --env-file .env.production \
    run --rm --entrypoint sh backup /usr/local/bin/backup.sh
```

To see the list:

```bash
./scripts/restore.sh --list
```

To confirm it runs daily, `docker compose ... logs backup`.

## 10. Restoring from a backup

```bash
./scripts/restore.sh --list                 # which backups exist
./scripts/restore.sh                        # restore the newest
./scripts/restore.sh muamma/muamma-20261001T001500Z.sql.gz
```

The script, in order: asks for confirmation, stops `web`, streams the dump
from S3 straight into `psql`, starts `web` again. The dump was taken with
`--clean --if-exists`, so it writes over the existing tables; `psql` stops
at the first error so you are not left with a half-finished restore.

When the restore is done, open a daily puzzle and check that it plays.

## 11. Moving puzzles

Puzzles can be prepared on a local machine and carried to the server.

Locally:

```bash
flask export-puzzles muamma.puzzles.json
```

**The export holds every answer and explanation, so it must never be
committed.** `*.puzzles.json` and `exports/` are in `.gitignore` for that
reason; keep exports under one of those names and delete them when you are
done.

On the server (copy the file over with `scp` first):

```bash
docker compose -f compose.prod.yaml --env-file .env.production \
    cp muamma.puzzles.json web:/tmp/muamma.puzzles.json
docker compose -f compose.prod.yaml --env-file .env.production \
    exec web flask import-puzzles /tmp/muamma.puzzles.json \
    --start 2026-11-01 --dry-run
```

`--dry-run` prints what would happen and saves nothing. If the output looks
right, run the same command without `--dry-run`.

Dailies land on the **free** days from the given date on, in order; a day
that is taken is skipped. Practice puzzles are added without a date. A clue
and answer that were imported before are not added again — the output says
"skipped". If the answer is one of the worked examples on the guide page, a
warning appears; it does not block the import, the decision is yours.

## 12. Things to check now and then

```bash
df -h                     # disk
docker compose -f compose.prod.yaml --env-file .env.production ps
docker compose -f compose.prod.yaml --env-file .env.production logs -n 100 web
```

Logs are rotated by Docker (10 MB per file, three files), so they cannot
fill the disk.

To update the server's packages, `sudo apt-get update && sudo apt-get
upgrade`; if a kernel update needs a reboot, the containers come back by
themselves thanks to `restart: unless-stopped`.
