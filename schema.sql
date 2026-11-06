-- Run once:  mysql -u root -p < schema.sql
CREATE DATABASE IF NOT EXISTS school_db;
USE school_db;

CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    login_email   VARCHAR(255) NULL UNIQUE,   -- for email and Google sign-in (kept private)
    provider      VARCHAR(20) NOT NULL DEFAULT 'password',  -- 'password' or 'google'
    password_hash VARCHAR(255) NULL,          -- empty for Google-only accounts
    failed_attempts INT NOT NULL DEFAULT 0,   -- wrong passwords in a row
    locked_until  DATETIME NULL,              -- set after too many wrong passwords
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS students (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    roll_no    VARCHAR(20)  NOT NULL UNIQUE,
    class_name VARCHAR(20)  NOT NULL,
    email      VARCHAR(100),
    marks      DECIMAL(5,2) DEFAULT 0,
    added_by   INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (added_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS cities (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    name      VARCHAR(100) NOT NULL,
    country   VARCHAR(100),
    latitude  DECIMAL(8,5) NOT NULL,
    longitude DECIMAL(8,5) NOT NULL,
    UNIQUE (name, country)
);

-- One row per city per day
CREATE TABLE IF NOT EXISTS weather (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    city_id     INT  NOT NULL,
    date        DATE NOT NULL,
    temp_max    DECIMAL(4,1),
    temp_min    DECIMAL(4,1),
    rainfall_mm DECIMAL(5,1),
    wind_kmh    DECIMAL(4,1),
    UNIQUE (city_id, date),
    FOREIGN KEY (city_id) REFERENCES cities(id) ON DELETE CASCADE
);
