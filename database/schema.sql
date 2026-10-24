-- Customer Follow-up CRM Database Schema
-- Target: MySQL 5.7+ / 8.0+ / MariaDB (XAMPP)

CREATE DATABASE IF NOT EXISTS `customer_followup_crm` 
DEFAULT CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE `customer_followup_crm`;

-- 1. Admins Table
CREATE TABLE IF NOT EXISTS `admins` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `email` VARCHAR(255) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `full_name` VARCHAR(150) DEFAULT 'Administrator',
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_admin_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Import Files Table
CREATE TABLE IF NOT EXISTS `import_files` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `original_filename` VARCHAR(255) NOT NULL,
    `stored_filename` VARCHAR(255) NOT NULL,
    `storage_path` VARCHAR(500) NOT NULL,
    `uploaded_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `data_period_start` DATE NULL,
    `data_period_end` DATE NULL,
    `import_month` INT NOT NULL,
    `import_year` INT NOT NULL,
    `worksheet_name` VARCHAR(100) NULL,
    `total_rows` INT DEFAULT 0,
    `imported_rows` INT DEFAULT 0,
    `updated_rows` INT DEFAULT 0,
    `duplicate_rows` INT DEFAULT 0,
    `rejected_rows` INT DEFAULT 0,
    `import_status` VARCHAR(50) DEFAULT 'Completed', -- Completed, Partial, Failed, In Progress
    `error_report_path` VARCHAR(500) NULL,
    `created_by` INT NULL,
    INDEX `idx_import_year_month` (`import_year`, `import_month`),
    INDEX `idx_import_uploaded_at` (`uploaded_at`),
    CONSTRAINT `fk_import_files_admin` FOREIGN KEY (`created_by`) REFERENCES `admins` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Customers Table
CREATE TABLE IF NOT EXISTS `customers` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `customer_code` VARCHAR(100) NULL UNIQUE,
    `name` VARCHAR(200) NOT NULL,
    `normalized_mobile` VARCHAR(30) NULL,
    `mobile` VARCHAR(50) NULL,
    `alternate_phone` VARCHAR(50) NULL,
    `normalized_email` VARCHAR(255) NULL,
    `email` VARCHAR(255) NULL,
    `company` VARCHAR(200) NULL,
    `address` TEXT NULL,
    `city` VARCHAR(100) NULL,
    `state` VARCHAR(100) NULL,
    `country` VARCHAR(100) DEFAULT 'India',
    `category` VARCHAR(100) DEFAULT 'General',
    `source` VARCHAR(100) DEFAULT 'Excel Import',
    `status` VARCHAR(50) DEFAULT 'New', -- New, Contacted, Follow-up Scheduled, Interested, Converted, Not Interested
    `custom_fields` JSON NULL,
    `last_contacted_at` DATETIME NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `archived_at` DATETIME NULL,
    INDEX `idx_cust_normalized_mobile` (`normalized_mobile`),
    INDEX `idx_cust_normalized_email` (`normalized_email`),
    INDEX `idx_cust_city` (`city`),
    INDEX `idx_cust_status` (`status`),
    INDEX `idx_cust_last_contacted` (`last_contacted_at`),
    INDEX `idx_cust_archived` (`archived_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Import File Records Table (Traceability for each row in an import)
CREATE TABLE IF NOT EXISTS `import_file_records` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `import_file_id` INT NOT NULL,
    `customer_id` INT NULL,
    `source_row_number` INT NOT NULL,
    `row_status` VARCHAR(50) NOT NULL, -- Imported, Updated, Duplicate_Skipped, Rejected
    `row_hash` VARCHAR(64) NULL,
    `error_message` TEXT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_ifr_import_file` (`import_file_id`),
    INDEX `idx_ifr_customer` (`customer_id`),
    CONSTRAINT `fk_ifr_file` FOREIGN KEY (`import_file_id`) REFERENCES `import_files` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_ifr_customer` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Follow-ups Table
CREATE TABLE IF NOT EXISTS `followups` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `customer_id` INT NOT NULL,
    `scheduled_at` DATETIME NOT NULL,
    `status` VARCHAR(50) DEFAULT 'Pending', -- Pending, Completed, Rescheduled, Cancelled
    `priority` VARCHAR(30) DEFAULT 'Medium', -- Low, Medium, High, Urgent
    `notes` TEXT NULL,
    `completed_at` DATETIME NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `created_by` INT NULL,
    INDEX `idx_followup_status_scheduled` (`status`, `scheduled_at`),
    INDEX `idx_followup_customer` (`customer_id`),
    CONSTRAINT `fk_followup_customer` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_followup_admin` FOREIGN KEY (`created_by`) REFERENCES `admins` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Follow-up Audit Table
CREATE TABLE IF NOT EXISTS `followup_audit` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `followup_id` INT NOT NULL,
    `previous_scheduled_at` DATETIME NULL,
    `new_scheduled_at` DATETIME NULL,
    `previous_status` VARCHAR(50) NULL,
    `new_status` VARCHAR(50) NOT NULL,
    `reason` TEXT NULL,
    `changed_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `changed_by` INT NULL,
    INDEX `idx_fa_followup_id` (`followup_id`),
    CONSTRAINT `fk_fa_followup` FOREIGN KEY (`followup_id`) REFERENCES `followups` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_fa_admin` FOREIGN KEY (`changed_by`) REFERENCES `admins` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Call History Table
CREATE TABLE IF NOT EXISTS `call_history` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `customer_id` INT NOT NULL,
    `followup_id` INT NULL,
    `call_datetime` DATETIME NOT NULL,
    `outcome` VARCHAR(100) NOT NULL, -- Interested, Not Interested, No Answer, Busy, Call Back Required, Converted, Wrong Number, Other
    `notes` TEXT NULL,
    `next_action` VARCHAR(255) NULL,
    `created_by` INT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_call_customer` (`customer_id`),
    INDEX `idx_call_datetime` (`call_datetime`),
    INDEX `idx_call_outcome` (`outcome`),
    CONSTRAINT `fk_call_customer` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_call_followup` FOREIGN KEY (`followup_id`) REFERENCES `followups` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_call_admin` FOREIGN KEY (`created_by`) REFERENCES `admins` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. System Settings Table
CREATE TABLE IF NOT EXISTS `system_settings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `setting_key` VARCHAR(100) NOT NULL UNIQUE,
    `setting_value` TEXT NOT NULL,
    `description` VARCHAR(255) NULL,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_setting_key` (`setting_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

