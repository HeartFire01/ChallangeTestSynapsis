-- People Counting System Database Schema
-- MySQL/MariaDB

CREATE DATABASE IF NOT EXISTS people_counting CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE people_counting;

-- Table: polygon_areas
CREATE TABLE IF NOT EXISTS polygon_areas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    coordinates JSON NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_active (is_active),
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: counting_summary
CREATE TABLE IF NOT EXISTS counting_summary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    polygon_area_id INT,
    total_entered INT DEFAULT 0,
    total_exited INT DEFAULT 0,
    current_count INT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (polygon_area_id) REFERENCES polygon_areas(id) ON DELETE CASCADE,
    INDEX idx_polygon (polygon_area_id),
    INDEX idx_updated (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: detection_events
CREATE TABLE IF NOT EXISTS detection_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    polygon_area_id INT,
    track_id INT NOT NULL,
    event_type ENUM('entered', 'exited') NOT NULL,
    centroid_x INT,
    centroid_y INT,
    confidence FLOAT,
    frame_number INT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (polygon_area_id) REFERENCES polygon_areas(id) ON DELETE CASCADE,
    INDEX idx_polygon (polygon_area_id),
    INDEX idx_track (track_id),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;