SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

CREATE TABLE IF NOT EXISTS `credit_score_cache` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `student_number` varchar(30) NOT NULL,
  `score` int(11) NOT NULL DEFAULT 0,
  `tier` enum('excellent','good','fair','poor','high_risk') NOT NULL DEFAULT 'fair',
  `repayment_pts` int(11) NOT NULL DEFAULT 0,
  `burden_pts` int(11) NOT NULL DEFAULT 0,
  `vouch_pts` int(11) NOT NULL DEFAULT 0,
  `tenure_pts` int(11) NOT NULL DEFAULT 0,
  `calculated_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_student_number` (`student_number`),
  KEY `idx_score` (`score`),
  KEY `idx_tier` (`tier`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `credit_score_events` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `student_number` varchar(30) NOT NULL,
  `event_type` varchar(100) NOT NULL,
  `score_before` int(11) DEFAULT NULL,
  `score_after` int(11) DEFAULT NULL,
  `delta` int(11) DEFAULT NULL,
  `reference_id` varchar(100) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_event_type` (`event_type`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_student_number` (`student_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `users` (
  `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  `student_number` varchar(20) DEFAULT NULL,
  `full_name` varchar(120) NOT NULL,
  `university` varchar(100) DEFAULT NULL,
  `email` varchar(120) DEFAULT NULL,
  `phone_number` varchar(20) DEFAULT NULL,
  `role` enum('borrower','lender','rep','admin','agent') NOT NULL DEFAULT 'borrower',
  `password_hash` varchar(255) NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `is_verified` tinyint(1) NOT NULL DEFAULT 0,
  `failed_attempts` int(10) UNSIGNED NOT NULL DEFAULT 0,
  `last_login_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `student_number` (`student_number`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `phone_number` (`phone_number`),
  KEY `idx_users_student_number` (`student_number`),
  KEY `idx_users_email` (`email`),
  KEY `idx_users_phone_number` (`phone_number`),
  KEY `idx_users_role` (`role`),
  KEY `idx_users_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `login_otps` (
  `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` int(10) UNSIGNED NOT NULL,
  `phone_number` varchar(20) NOT NULL,
  `otp_code` varchar(6) NOT NULL,
  `expires_at` datetime NOT NULL,
  `consumed_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_login_otps_user_id` (`user_id`),
  KEY `idx_login_otps_phone_number` (`phone_number`),
  KEY `idx_login_otps_lookup` (`phone_number`, `otp_code`, `consumed_at`),
  CONSTRAINT `fk_login_otps_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `universities` (
  `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` varchar(120) NOT NULL,
  `code` varchar(30) DEFAULT NULL,
  `city` varchar(100) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_universities_name` (`name`),
  UNIQUE KEY `uk_universities_code` (`code`),
  KEY `idx_universities_is_active` (`is_active`),
  KEY `idx_universities_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `loans` (
  `id` char(36) NOT NULL,
  `reference_code` varchar(30) NOT NULL,
  `lender_id` int(11) NOT NULL,
  `borrower_id` int(11) NOT NULL,
  `amount_zmw` decimal(12,2) NOT NULL DEFAULT 0.00,
  `due_date` date NOT NULL,
  `logged_at` datetime NOT NULL DEFAULT current_timestamp(),
  `repaid_at` datetime DEFAULT NULL,
  `status` enum('pending','active','repaid','overdue','defaulted','cancelled') NOT NULL DEFAULT 'pending',
  `note` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_reference_code` (`reference_code`),
  KEY `idx_lender_id` (`lender_id`),
  KEY `idx_borrower_id` (`borrower_id`),
  KEY `idx_status` (`status`),
  KEY `idx_due_date` (`due_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `vouches` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `voucher_student_number` varchar(30) NOT NULL,
  `beneficiary_student_number` varchar(30) NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `expires_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_is_active` (`is_active`),
  KEY `idx_voucher_student_number` (`voucher_student_number`),
  KEY `idx_beneficiary_student_number` (`beneficiary_student_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
