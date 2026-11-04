# Putting The DB OS online (Streamlit Community Cloud)

Streamlit Community Cloud runs your app for free at a link like
`https://your-name-db-os.streamlit.app`. One catch: the MySQL on your Mac is
**not reachable from the internet**, so the online app needs a MySQL database in
the cloud too.

```
Your GitHub repo ──► Streamlit Cloud (runs app.py) ──► Cloud MySQL (Aiven)
```

---

## Step 1 — Create a free cloud MySQL database

[Aiven](https://aiven.io) has a free MySQL plan (check the plan page, free tiers change).

1. Sign up at aiven.io → **Create service** → **MySQL** → choose the **Free** plan.
2. When it's running, open the service **Overview** and note:
   **Host**, **Port**, **User** (`avnadmin`) and **Password**.
3. Download the **CA certificate** and save it in this project folder as `ca.pem`.
   (It's a public certificate, so it is safe to put on GitHub.)

## Step 2 — Load the tables and sample data into it

From this project folder (replace the values with yours):

```bash
mysql -h YOUR_HOST -P YOUR_PORT -u avnadmin -p --ssl-ca=ca.pem < schema.sql
```

```bash
mysql -h YOUR_HOST -P YOUR_PORT -u avnadmin -p --ssl-ca=ca.pem school_db < sample_data.sql
```

## Step 3 — Put the code on GitHub

1. Create an empty repository on [github.com/new](https://github.com/new), e.g. `db-os`.
2. In this folder:

```bash
git init && git add . && git commit -m "The DB OS"
```

```bash
git branch -M main && git remote add origin https://github.com/YOUR_NAME/db-os.git && git push -u origin main
```

`.gitignore` keeps `.streamlit/secrets.toml` (your passwords) **off** GitHub.
Check with `git status` before pushing: `secrets.toml` must not be listed.

## Step 4 — Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. **Create app** → **Deploy a public app from GitHub**.
3. Repository: `YOUR_NAME/db-os` · Branch: `main` · Main file: `app.py`.
4. Open **Advanced settings** → **Secrets** and paste (with your Aiven values):

   ```toml
   [mysql]
   host = "your-service.aivencloud.com"
   port = 12345
   user = "avnadmin"
   password = "your-aiven-password"
   database = "school_db"
   ssl_ca = "ca.pem"
   ```

5. Click **Deploy**. The first start takes a minute or two while it installs
   `requirements.txt`.

## Step 5 — Updating later

Push new commits to `main` and Streamlit Cloud redeploys on its own.
To change passwords or the database, edit **Settings → Secrets** in your app's menu.

## If something goes wrong

| What you see | What to check |
|---|---|
| `Database error: Can't connect` | Host/port in Secrets; Aiven service is running |
| `SSL` / certificate error | `ca.pem` is committed and `ssl_ca = "ca.pem"` is in Secrets |
| `Table ... doesn't exist` | You skipped Step 2 |
| `ModuleNotFoundError` | The package is missing from `requirements.txt` |
| Changes not showing | App menu (⋮) → **Reboot app** |

> Other MySQL hosts work the same way. If yours uses a normal public certificate
> (for example TiDB Cloud), set `ssl_ca = "/etc/ssl/certs/ca-certificates.crt"`
> instead of uploading a `ca.pem`.
