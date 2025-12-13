DROP VIEW IF EXISTS resource_usage_view;
DROP VIEW IF EXISTS event_resources_view;
DROP TABLE IF EXISTS event_logs;
DROP TABLE IF EXISTS constraint_rules;
DROP TABLE IF EXISTS constraints;
DROP TABLE IF EXISTS event_resources;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS resources;

CREATE TABLE resources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    resource_type VARCHAR(50),
    quantity INT DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_resource_type (resource_type),
    INDEX idx_is_active (is_active)
);

CREATE TABLE events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    status ENUM('scheduled', 'cancelled', 'completed') DEFAULT 'scheduled',
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_start_time (start_time),
    INDEX idx_end_time (end_time),
    INDEX idx_status (status),
    CONSTRAINT chk_event_time CHECK (end_time > start_time)
);

CREATE TABLE event_resources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    resource_id INT NOT NULL,
    quantity_used INT DEFAULT 1,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
    UNIQUE KEY unique_event_resource (event_id, resource_id),
    INDEX idx_event_id (event_id),
    INDEX idx_resource_id (resource_id)
);

CREATE TABLE constraints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    constraint_type ENUM('co_requirement', 'mutual_exclusion', 'capacity') NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE constraint_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    constraint_id INT NOT NULL,
    resource_id INT NOT NULL,
    rule_type ENUM('requires', 'excludes', 'max_capacity', 'min_quantity') NOT NULL,
    related_resource_id INT,
    value INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (constraint_id) REFERENCES constraints(id) ON DELETE CASCADE,
    FOREIGN KEY (resource_id) REFERENCES resources(id),
    FOREIGN KEY (related_resource_id) REFERENCES resources(id)
);

CREATE TABLE event_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT,
    action VARCHAR(50),
    details TEXT,
    performed_by VARCHAR(100),
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE SET NULL,
    INDEX idx_event_log (event_id),
    INDEX idx_action (action)
);

CREATE VIEW event_resources_view AS
SELECT 
    e.id as event_id,
    e.title,
    e.start_time,
    e.end_time,
    e.status,
    GROUP_CONCAT(CONCAT(r.name, ' (', er.quantity_used, ')') SEPARATOR ', ') as resources_summary,
    SUM(er.quantity_used) as total_items_used
FROM events e
LEFT JOIN event_resources er ON e.id = er.event_id
LEFT JOIN resources r ON er.resource_id = r.id
GROUP BY e.id, e.title, e.start_time, e.end_time, e.status;

CREATE VIEW resource_usage_view AS
SELECT 
    r.id,
    r.name,
    r.resource_type,
    r.quantity as total_inventory,
    COALESCE(SUM(er.quantity_used), 0) as currently_in_use,
    (r.quantity - COALESCE(SUM(er.quantity_used), 0)) as available_now
FROM resources r
LEFT JOIN event_resources er ON r.id = er.resource_id
LEFT JOIN events e ON er.event_id = e.id 
    AND e.status = 'scheduled'
    AND (NOW() BETWEEN e.start_time AND e.end_time OR e.start_time > NOW())
GROUP BY r.id, r.name, r.resource_type, r.quantity;

SELECT '✅ Estructura de base de datos creada y optimizada correctamente' as status;