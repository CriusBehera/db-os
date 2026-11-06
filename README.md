# 💠 The DB OS

One sign-in (username, email or **Google**), two apps, built with **Streamlit + MySQL**:

- **🎓 Student Board**: student records, marks, grades, class statistics and charts.
- **🌦️ Weather Station**: real daily weather for any city (from Open-Meteo), stored in MySQL.

Each app has its own **SQL playground** with example queries you can edit and run.

**✨ Nuera Core AI** (ai.criusbehera.com) is a built-in chatbot. Ask questions in plain English,
like "Analyse the student marks" or "Which city had the most rain?". It writes up to 3 read-only SQL
queries, runs them on your database, and explains the answer, showing the SQL, the table and a chart.

Made by **Crius Behera** · Sponsored by **Nuera Core AI**, **Crius Software Solutions**

---

## Run it on your computer

1. Install and start MySQL:
   ```
   brew install mysql
   brew services start mysql
   ```
2. Create the tables, and optionally load the example data:
   ```
   mysql -u root -p < schema.sql
   mysql -u root -p school_db < sample_data.sql
   ```
3. Copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml` and fill in your MySQL login
   and your Nuera Core AI access key.
4. Install the packages and start the app:
   ```
   pip install -r requirements.txt
   streamlit run app.py
   ```
   It opens at http://localhost:8501. Create an account, then sign in.

**To put it online, follow [DEPLOY.md](DEPLOY.md).**

## Security

- **Strong passwords only**: at least 8 characters, with an uppercase letter, a lowercase letter,
  a number and a symbol. No spaces, not containing your username, and no common words like
  "password" or "123456". A live checklist and strength bar show what's missing.
- **Three ways to sign in**, one account: username + password, email + password, or Google
  (linked by the verified email). Sign-in emails are private, never shown in the SQL playgrounds or to the AI.
- **Email verification** through Firebase: a link is emailed at signup and sign-in is blocked until it's clicked (Google sign-ins skip it).
- **Required two-step sign-in**: a 6-digit authenticator-app code (Microsoft Authenticator recommended) after the password and verified email, plus one-time backup codes.
- **Account lockout**: 5 wrong passwords in a row lock the account for 5 minutes.
- **Auto sign-out** after 30 minutes with no activity.
- Passwords are stored only as salted **PBKDF2-SHA256** hashes, and the hash never stays in the session.
- Every query uses `%s` parameters, which protects against SQL injection.
- The SQL playgrounds and the AI run **read-only**: one statement at a time, write keywords
  (INSERT, UPDATE, DELETE, DROP, INTO, …) are blocked, and the `password_hash` column is never returned.

## Files

| File | What it does |
|------|--------------|
| `app.py` | The DB OS shell: sign-in check, home screen, sidebar, app switching |
| `firebase.py` | Emails the verification link and checks it (Firebase Auth REST API) |
| `auth.py` | Sign in, create account, change password, password rules |
| `student_board.py` | Student Board pages |
| `weather_station.py` | Weather Station pages |
| `ai.py` | Nuera Core AI chatbot: question → SQL → answer |
| `migrate_auth.sql` | Adds email + Google columns to an existing `users` table |
| `load_db.py` | Loads the tables into a cloud database (for example TiDB) |
| `ui.py` | Shared styles, banners, credits and the SQL playground |
| `db.py` | All MySQL queries, password hashing and login lockout |
| `weather.py` | Fetches weather from the free Open-Meteo API (no key needed) |
| `sql_examples.py` | The example queries for both playgrounds |
| `schema.sql` | Creates the `users`, `students`, `cities` and `weather` tables |
| `sample_data.sql` | Example students, cities and weather |
| `.streamlit/config.toml` | Theme (colours, fonts, corners) |
| `.streamlit/secrets.toml` | Your MySQL login (never uploaded) |

## SQL topics covered

WHERE, ORDER BY, LIMIT, LIKE, IS NULL, GROUP BY, HAVING, CASE, subqueries, correlated subqueries,
INNER and LEFT JOIN, date functions, BETWEEN, window functions (RANK, LAG), CTEs (WITH), and DESCRIBE.
Weather is saved with `INSERT ... ON DUPLICATE KEY UPDATE`, so fetching again updates days
that are already stored instead of duplicating them.
