"""Example SQL queries for the two SQL playgrounds, from basic to advanced.

"app" says which app shows the example: "students" or "weather".
"""

EXAMPLES = [
    {
        "app": "students",
        "title": "SELECT with WHERE — students who scored above 80",
        "explain": "`WHERE` keeps only the rows that match a condition.",
        "sql": """SELECT name, class_name, marks
FROM students
WHERE marks > 80;""",
    },
    {
        "app": "students",
        "title": "ORDER BY + LIMIT — top 5 students",
        "explain": "`ORDER BY ... DESC` sorts from highest to lowest, `LIMIT` keeps the first rows.",
        "sql": """SELECT name, class_name, marks
FROM students
ORDER BY marks DESC
LIMIT 5;""",
    },
    {
        "app": "students",
        "title": "LIKE and IS NULL — searching text and missing values",
        "explain": "`LIKE '%a%'` matches any name containing \"a\"; `IS NULL` finds students with no email.",
        "sql": """SELECT name, email
FROM students
WHERE name LIKE '%a%' AND email IS NULL;""",
    },
    {
        "app": "students",
        "title": "GROUP BY — average, highest and lowest marks per class",
        "explain": "`GROUP BY` puts rows into groups; `COUNT`, `AVG`, `MAX`, `MIN` summarise each group.",
        "sql": """SELECT class_name,
       COUNT(*)             AS students,
       ROUND(AVG(marks), 1) AS average,
       MAX(marks)           AS highest,
       MIN(marks)           AS lowest
FROM students
GROUP BY class_name;""",
    },
    {
        "app": "students",
        "title": "HAVING — classes whose average is above 75",
        "explain": "`HAVING` filters groups *after* `GROUP BY` (WHERE filters rows *before*).",
        "sql": """SELECT class_name, ROUND(AVG(marks), 1) AS average
FROM students
GROUP BY class_name
HAVING AVG(marks) > 75;""",
    },
    {
        "app": "students",
        "title": "CASE — give each student a grade",
        "explain": "`CASE` works like if / else inside a query.",
        "sql": """SELECT name, marks,
       CASE
         WHEN marks >= 90 THEN 'A+'
         WHEN marks >= 80 THEN 'A'
         WHEN marks >= 70 THEN 'B'
         WHEN marks >= 50 THEN 'C'
         ELSE 'Fail'
       END AS grade
FROM students
ORDER BY marks DESC;""",
    },
    {
        "app": "students",
        "title": "Subquery — students above the school average",
        "explain": "The inner query works out the average first, the outer query compares to it.",
        "sql": """SELECT name, marks
FROM students
WHERE marks > (SELECT AVG(marks) FROM students)
ORDER BY marks DESC;""",
    },
    {
        "app": "weather",
        "title": "INNER JOIN — weather with the city name",
        "explain": "`JOIN` links two tables using a shared column (`weather.city_id` = `cities.id`).",
        "sql": """SELECT c.name AS city, w.date, w.temp_max, w.temp_min, w.rainfall_mm
FROM weather w
JOIN cities c ON c.id = w.city_id
ORDER BY w.date DESC, c.name
LIMIT 20;""",
    },
    {
        "app": "weather",
        "title": "JOIN + GROUP BY — weather summary for each city",
        "explain": "Combines a join with aggregates to compare cities.",
        "sql": """SELECT c.name AS city,
       ROUND(AVG(w.temp_max), 1) AS avg_high,
       ROUND(AVG(w.temp_min), 1) AS avg_low,
       SUM(w.rainfall_mm)        AS total_rain_mm,
       MAX(w.wind_kmh)           AS strongest_wind
FROM cities c
JOIN weather w ON w.city_id = c.id
GROUP BY c.name
ORDER BY avg_high DESC;""",
    },
    {
        "app": "weather",
        "title": "COUNT with a condition — rainy days per city",
        "explain": "`SUM(condition)` counts the rows where the condition is true (true = 1).",
        "sql": """SELECT c.name AS city,
       COUNT(*)                   AS days,
       SUM(w.rainfall_mm > 0)     AS rainy_days,
       SUM(w.rainfall_mm >= 10)   AS heavy_rain_days
FROM cities c
JOIN weather w ON w.city_id = c.id
GROUP BY c.name
ORDER BY rainy_days DESC;""",
    },
    {
        "app": "weather",
        "title": "Correlated subquery — hottest day in each city",
        "explain": "The inner query runs once per row, finding that city's own maximum.",
        "sql": """SELECT c.name AS city, w.date, w.temp_max
FROM weather w
JOIN cities c ON c.id = w.city_id
WHERE w.temp_max = (SELECT MAX(w2.temp_max)
                    FROM weather w2
                    WHERE w2.city_id = w.city_id)
ORDER BY w.temp_max DESC;""",
    },
    {
        "app": "weather",
        "title": "Date functions — weekly average temperature",
        "explain": "`YEARWEEK()` turns a date into a week number so we can group by week.",
        "sql": """SELECT c.name AS city,
       MIN(w.date)               AS week_starting,
       ROUND(AVG(w.temp_max), 1) AS avg_high,
       SUM(w.rainfall_mm)        AS rain_mm
FROM weather w
JOIN cities c ON c.id = w.city_id
WHERE c.name = 'Bhubaneswar'
GROUP BY c.name, YEARWEEK(w.date)
ORDER BY week_starting;""",
    },
    {
        "app": "weather",
        "title": "BETWEEN — weather in the last 7 days",
        "explain": "`BETWEEN` picks a range; `CURDATE() - INTERVAL 7 DAY` means one week ago.",
        "sql": """SELECT c.name AS city, w.date, w.temp_max, w.rainfall_mm
FROM weather w
JOIN cities c ON c.id = w.city_id
WHERE w.date BETWEEN CURDATE() - INTERVAL 7 DAY AND CURDATE()
ORDER BY c.name, w.date;""",
    },
    {
        "app": "students",
        "title": "LEFT JOIN — which user added how many students",
        "explain": "`LEFT JOIN` keeps every user, even ones who added no students (count = 0).",
        "sql": """SELECT u.username, COUNT(s.id) AS students_added
FROM users u
LEFT JOIN students s ON s.added_by = u.id
GROUP BY u.username;""",
    },
    {
        "app": "students",
        "title": "Window function RANK() — rank students inside their class",
        "explain": "`RANK() OVER (PARTITION BY ...)` ranks within each class without merging rows.",
        "sql": """SELECT class_name, name, marks,
       RANK() OVER (PARTITION BY class_name ORDER BY marks DESC) AS class_rank
FROM students
ORDER BY class_name, class_rank;""",
    },
    {
        "app": "weather",
        "title": "Window function LAG() — temperature change from the day before",
        "explain": "`LAG()` reads the previous row's value, so we can see day-to-day change.",
        "sql": """SELECT date, temp_max,
       temp_max - LAG(temp_max) OVER (ORDER BY date) AS change_from_yesterday
FROM weather
WHERE city_id = (SELECT id FROM cities WHERE name = 'Delhi')
ORDER BY date;""",
    },
    {
        "app": "weather",
        "title": "CTE (WITH) — cities hotter than the overall average",
        "explain": "`WITH` gives a sub-result a name so the main query is easier to read.",
        "sql": """WITH city_avg AS (
    SELECT city_id, AVG(temp_max) AS avg_high
    FROM weather
    GROUP BY city_id
)
SELECT c.name AS city, ROUND(ca.avg_high, 1) AS avg_high
FROM city_avg ca
JOIN cities c ON c.id = ca.city_id
WHERE ca.avg_high > (SELECT AVG(avg_high) FROM city_avg)
ORDER BY avg_high DESC;""",
    },
    {
        "app": "weather",
        "title": "DESCRIBE — look at the weather table itself",
        "explain": "`DESCRIBE` lists a table's columns and their types. Try `SHOW TABLES;` too.",
        "sql": "DESCRIBE weather;",
    },
    {
        "app": "students",
        "title": "DESCRIBE — look at the students table itself",
        "explain": "`DESCRIBE` lists a table's columns and their types. Try `SHOW TABLES;` too.",
        "sql": "DESCRIBE students;",
    },
]
