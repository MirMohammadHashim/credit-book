-- Reference schema for Credit Book (MySQL 8.x).
-- Run once against the `creditbook` database, for example from the EC2 server:
--   mysql -h <rds-endpoint> -u admin -p creditbook < database/schema.sql

CREATE DATABASE IF NOT EXISTS creditbook;
USE creditbook;

CREATE TABLE IF NOT EXISTS users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  email         VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,          -- bcrypt hash, never the password
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customers (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT NOT NULL,
  name       VARCHAR(100) NOT NULL,
  phone      VARCHAR(20),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS entries (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  customer_id INT NOT NULL,
  amount      DECIMAL(10,2) NOT NULL,           -- money is never FLOAT
  type        ENUM('credit', 'payment') NOT NULL,
  note        VARCHAR(255),
  entry_date  DATE NOT NULL,
  FOREIGN KEY (customer_id) REFERENCES customers(id)
);
