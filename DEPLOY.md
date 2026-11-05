# Putting The DB OS online (Streamlit Community Cloud)

Streamlit Community Cloud runs your app for free at a link like
`https://your-name-db-os.streamlit.app`. One catch: the MySQL on your Mac is
**not reachable from the internet**, so the online app needs a MySQL-compatible
database in the cloud too.

```
GitHub repo ──► Streamlit Cloud (runs app.py) ──► TiDB Cloud (MySQL-compatible)
```

---

## Step 1: Create a free TiDB Cloud database (sign in with Google)

[TiDB Cloud Starter](https://www.pingcap.com/tidb-cloud-pricing/) is free, needs
no credit card, and speaks MySQL.

1. Go to [tidbcloud.com](https://tidbcloud.com) → **Sign up** → **Continue with Google**.
2. Create a **Starter** cluster (a default one may already be made for you).
   Pick a region near you, e.g. Mumbai or Singapore.
3. Open the cluster → click **Connect** (top right).
4. Click **Generate Password** and **copy it somewhere safe**. It's shown only once.
5. Note the **Host** (like `gateway01.ap-south-1.prod.aws.tidbcloud.com`),
   **Port** (`4000`) and **User** (like `3xAbCdEf.root`).

No certificate file is needed: TiDB uses a normal public certificate that every
computer already has.

## Step 2: Load the tables and sample data

In Terminal, from this project folder (put in your host and user):

```bash
python3 load_db.py --host YOUR_HOST --user YOUR_USER
```

It asks for the password, loads `schema.sql` and `sample_data.sql`, and prints
the row counts (about 18 students, 7 cities and 217 weather rows).
(Newer Homebrew `mysql` command line tools can't log in to TiDB, which is why
this uses Python.)

## Step 3: Put the code on GitHub

Use GitHub Desktop: **File → Add Local Repository** → this folder →
**Publish repository**. Later changes: write a summary → **Commit to main** →
**Push origin**.

`.gitignore` keeps `.streamlit/secrets.toml` (your passwords) **off** GitHub.

## Step 4: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. **Create app** → **Deploy a public app from GitHub**.
3. Repository: `CriusBehera/db-os` · Branch: `main` · Main file: `app.py`.
4. Open **Advanced settings** → **Secrets** and paste (with your TiDB values):

   ```toml
   [mysql]
   host = "gateway01.ap-south-1.prod.aws.tidbcloud.com"
   port = 4000
   user = "3xAbCdEf.root"
   password = "your-tidb-password"
   database = "school_db"
   ssl_ca = "/etc/ssl/certs/ca-certificates.crt"

   [nuera]
   email = "your-nuera-access-key"
   platform = "w"
   url = "https://nueracoreai-pro-get-ai.criusbehera.com"
   ```

   The `[nuera]` part turns on the Nuera Core AI chatbot. Copy the key from your
   local `.streamlit/secrets.toml`.

5. Click **Deploy**. The first start takes a minute or two while it installs
   `requirements.txt`.

## Updating later

Push new commits to `main` and Streamlit Cloud redeploys on its own.
To change the database login, open your app's menu (⋮) → **Settings → Secrets**.

## If something goes wrong

| What you see | What to check |
|---|---|
| `Database error: Can't connect` | Host, port and user in Secrets (TiDB users look like `xxxx.root`) |
| `SSL` / certificate error | `ssl_ca = "/etc/ssl/certs/ca-certificates.crt"` is in Secrets |
| `Access denied` | Password: generate a new one in TiDB → Connect, and update Secrets |
| `Table ... doesn't exist` | You skipped Step 2 |
| `ModuleNotFoundError` | The package is missing from `requirements.txt` |
| Changes not showing | App menu (⋮) → **Reboot app** |

> **Other hosts.** Any MySQL host works the same way. For a host with its own
> certificate (for example Aiven), download its `ca.pem` into this folder,
> commit it, and set `ssl_ca = "ca.pem"`.
