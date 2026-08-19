-- Danwood House Search System - MySQL Database Schema
-- Created: 2026-08-18
-- Total Houses: 200+

-- Create Database
CREATE DATABASE IF NOT EXISTS danwood_houses;
USE danwood_houses;

-- Categories Table
CREATE TABLE categories (
  id INT PRIMARY KEY AUTO_INCREMENT,
  key_name VARCHAR(50) UNIQUE NOT NULL,
  name VARCHAR(100) NOT NULL,
  description TEXT,
  icon VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO categories (key_name, name, description) VALUES
('bungalows', 'Bungalows', 'Ebenerdige Häuser mit Komfort und Barrierefreiheit'),
('eineinhalbgeschossige', 'Eineinhalbgeschoßige Häuser', 'Kompakte Häuser mit optimiertem Platzangebot'),
('zweigeschossige', 'Zweigeschossige Häuser', 'Großzügige Häuser mit zwei Vollgeschossen'),
('doppel-reihen', 'Doppel- & Reihenhäuser', 'Effiziente Wohnlösungen für Stadt und Land'),
('zweifamilienhauser', 'Zweifamilienhäuser', 'Zwei getrennte Wohneinheiten unter einem Dach'),
('mehrfamilienhauser', 'Mehrfamilienhäuser', 'Moderne Lösungen für mehrere Generationen'),
('minihauser', 'Mini-Häuser', 'Flexible Rückzugsorte in Modulbauweise');

-- Houses Table
CREATE TABLE houses (
  id INT PRIMARY KEY AUTO_INCREMENT,
  slug VARCHAR(100) UNIQUE NOT NULL,
  name VARCHAR(150) NOT NULL,
  category_id INT NOT NULL,
  series VARCHAR(100),
  square_meters INT,
  rooms INT,
  description TEXT,
  full_description LONGTEXT,
  danwood_url VARCHAR(500),
  energy_class VARCHAR(20),
  construction_type VARCHAR(100),
  heating_type VARCHAR(100),
  roof_type VARCHAR(100),
  is_featured BOOLEAN DEFAULT FALSE,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (category_id) REFERENCES categories(id),
  INDEX idx_category (category_id),
  INDEX idx_series (series),
  INDEX idx_square_meters (square_meters),
  INDEX idx_rooms (rooms)
);

-- House Features Table
CREATE TABLE house_features (
  id INT PRIMARY KEY AUTO_INCREMENT,
  house_id INT NOT NULL,
  feature_name VARCHAR(150),
  feature_order INT,
  FOREIGN KEY (house_id) REFERENCES houses(id) ON DELETE CASCADE,
  INDEX idx_house (house_id)
);

-- Images Table
CREATE TABLE images (
  id INT PRIMARY KEY AUTO_INCREMENT,
  house_id INT NOT NULL,
  image_type ENUM('main', 'gallery', 'floorplan', '360_view') DEFAULT 'gallery',
  filename VARCHAR(255),
  original_url VARCHAR(500),
  image_path VARCHAR(300),
  file_size INT,
  width INT,
  height INT,
  alt_text VARCHAR(255),
  is_primary BOOLEAN DEFAULT FALSE,
  image_order INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (house_id) REFERENCES houses(id) ON DELETE CASCADE,
  INDEX idx_house (house_id),
  INDEX idx_type (image_type)
);

-- Specifications Table
CREATE TABLE specifications (
  id INT PRIMARY KEY AUTO_INCREMENT,
  house_id INT NOT NULL,
  spec_key VARCHAR(100),
  spec_value VARCHAR(255),
  FOREIGN KEY (house_id) REFERENCES houses(id) ON DELETE CASCADE,
  INDEX idx_house (house_id)
);

-- User Favorites Table
CREATE TABLE favorites (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id VARCHAR(100),
  house_id INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (house_id) REFERENCES houses(id) ON DELETE CASCADE,
  UNIQUE KEY unique_favorite (user_id, house_id),
  INDEX idx_user (user_id)
);

-- Search History Table
CREATE TABLE search_history (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id VARCHAR(100),
  search_term VARCHAR(255),
  filters JSON,
  results_count INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_user (user_id),
  INDEX idx_created (created_at)
);

-- House Comparisons Table
CREATE TABLE comparisons (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id VARCHAR(100),
  house1_id INT NOT NULL,
  house2_id INT NOT NULL,
  house3_id INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (house1_id) REFERENCES houses(id) ON DELETE CASCADE,
  FOREIGN KEY (house2_id) REFERENCES houses(id) ON DELETE CASCADE,
  FOREIGN KEY (house3_id) REFERENCES houses(id) ON DELETE CASCADE,
  INDEX idx_user (user_id)
);

-- Contact Inquiries Table
CREATE TABLE inquiries (
  id INT PRIMARY KEY AUTO_INCREMENT,
  house_id INT,
  name VARCHAR(150) NOT NULL,
  email VARCHAR(150) NOT NULL,
  phone VARCHAR(20),
  message TEXT,
  inquiry_type ENUM('contact', 'brochure', 'appointment') DEFAULT 'contact',
  status ENUM('new', 'responded', 'archived') DEFAULT 'new',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (house_id) REFERENCES houses(id) ON DELETE SET NULL,
  INDEX idx_house (house_id),
  INDEX idx_status (status)
);

-- Create Views for Easy Querying

-- House Summary View
CREATE VIEW house_summary AS
SELECT 
  h.id,
  h.slug,
  h.name,
  h.series,
  c.name as category,
  h.square_meters,
  h.rooms,
  h.description,
  h.danwood_url,
  COUNT(DISTINCT img.id) as image_count,
  MAX(CASE WHEN img.is_primary THEN img.image_path END) as main_image,
  COUNT(DISTINCT f.id) as favorite_count
FROM houses h
LEFT JOIN categories c ON h.category_id = c.id
LEFT JOIN images img ON h.id = img.house_id
LEFT JOIN favorites f ON h.id = f.house_id
WHERE h.is_active = TRUE
GROUP BY h.id;

-- House Details View
CREATE VIEW house_details AS
SELECT 
  h.id,
  h.slug,
  h.name,
  h.series,
  c.name as category,
  h.square_meters,
  h.rooms,
  h.description,
  h.full_description,
  h.danwood_url,
  h.energy_class,
  h.construction_type,
  h.heating_type,
  GROUP_CONCAT(DISTINCT hf.feature_name SEPARATOR ', ') as features,
  GROUP_CONCAT(DISTINCT CONCAT(s.spec_key, ':', s.spec_value) SEPARATOR '; ') as specifications
FROM houses h
LEFT JOIN categories c ON h.category_id = c.id
LEFT JOIN house_features hf ON h.id = hf.house_id
LEFT JOIN specifications s ON h.id = s.house_id
WHERE h.is_active = TRUE
GROUP BY h.id;

-- Sample Data Insert (First 3 houses as examples)
INSERT INTO houses (slug, name, category_id, series, square_meters, rooms, description, danwood_url, energy_class, construction_type, heating_type, roof_type) VALUES
('perfect-106', 'Perfect 106', 1, 'Perfect', 106, 3, 'Das Projekt Perfect 106 von Danwood für alle, die Komfort und höchste Qualität schätzen.', 'https://www.danwood.de/projekte/bungalows/perfect-106', 'KfW 55', 'Holzbau', 'Wärmepumpe', 'Satteldach'),
('perfect-112', 'Perfect 112', 1, 'Perfect', 112, 3, 'Das Projekt Perfect 112 von Danwood für alle, die Komfort und höchste Qualität schätzen.', 'https://www.danwood.de/projekte/bungalows/perfect-112', 'KfW 55', 'Holzbau', 'Wärmepumpe', 'Satteldach'),
('perfect-170', 'Perfect 170', 1, 'Perfect', 170, 4, 'Das Projekt Perfect 170 von Danwood für alle, die Komfort und höchste Qualität schätzen.', 'https://www.danwood.de/projekte/bungalows/perfect-170', 'KfW 55', 'Holzbau', 'Wärmepumpe', 'Satteldach'),
('park-180w', 'Park 180W', 3, 'Park', 180, 5, 'Das Projekt Park 180W von Danwood für alle, die Komfort und höchste Qualität schätzen.', 'https://www.danwood.de/projekte/zweigeschossige-hauser/park-180w', 'KfW 55', 'Holzbau', 'Wärmepumpe', 'Satteldach'),
('point-133-1', 'Point 133.1', 2, 'Point', 133, 4, 'Das Projekt Point 133.1 von Danwood für alle, die Komfort und höchste Qualität schätzen.', 'https://www.danwood.de/projekte/eineinhalbgeschossige-hauser/point-133-1', 'KfW 55', 'Holzbau', 'Wärmepumpe', 'Satteldach');

-- Insert sample features for first house
INSERT INTO house_features (house_id, feature_name, feature_order) VALUES
(1, 'Barrierefreier Zugang', 1),
(1, 'Moderne Architektur', 2),
(1, 'Holzbau', 3);

-- Create Indexes for Performance
CREATE INDEX idx_houses_search ON houses (name, series);
CREATE INDEX idx_houses_filter ON houses (square_meters, rooms, category_id);
CREATE INDEX idx_images_house ON images (house_id, image_type);

-- Example Queries

-- Find all bungalows with 3-4 rooms and 100-150 sqm
-- SELECT * FROM house_summary 
-- WHERE category = 'Bungalows' 
-- AND rooms BETWEEN 3 AND 4 
-- AND square_meters BETWEEN 100 AND 150;

-- Get house with all details and images
-- SELECT h.*, GROUP_CONCAT(img.image_path) as images
-- FROM house_details h
-- LEFT JOIN images img ON h.id = img.house_id
-- WHERE h.slug = 'perfect-106';

-- Search across name and series
-- SELECT * FROM house_summary
-- WHERE name LIKE '%Perfect%' OR series LIKE '%Perfect%';
