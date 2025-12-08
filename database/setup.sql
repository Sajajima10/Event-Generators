-- setup.sql - Script de creación de tablas para el gestor de eventos
-- Versión limpia sin datos de ejemplo

-- ============================================
-- ELIMINAR TABLAS EXISTENTES (si es necesario)
-- ============================================
DROP TABLE IF EXISTS event_logs;
DROP TABLE IF EXISTS constraint_rules;
DROP TABLE IF EXISTS constraints;
DROP TABLE IF EXISTS event_resources;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS resources;

-- ============================================
-- TABLA DE RECURSOS
-- ============================================
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

-- ============================================
-- TABLA DE EVENTOS
-- ============================================
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
    INDEX idx_created_at (created_at),
    CONSTRAINT chk_time CHECK (end_time > start_time)
);

-- ============================================
-- TABLA DE ASIGNACIÓN EVENTOS-RECURSOS
-- ============================================
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
    INDEX idx_resource_id (resource_id),
    INDEX idx_assigned_at (assigned_at)
);

-- ============================================
-- TABLA DE RESTRICCIONES
-- ============================================
CREATE TABLE constraints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    constraint_type ENUM('co_requirement', 'mutual_exclusion', 'capacity') NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_constraint_type (constraint_type),
    INDEX idx_is_active (is_active)
);

-- ============================================
-- TABLA DE REGLAS DE RESTRICCIONES
-- ============================================
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
    FOREIGN KEY (related_resource_id) REFERENCES resources(id),
    
    INDEX idx_constraint_id (constraint_id),
    INDEX idx_resource_id (resource_id),
    INDEX idx_rule_type (rule_type)
);

-- ============================================
-- TABLA DE HISTORIAL/LOGS
-- ============================================
CREATE TABLE event_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT,
    action VARCHAR(50),
    details TEXT,
    performed_by VARCHAR(100),
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE SET NULL,
    
    INDEX idx_event_id (event_id),
    INDEX idx_performed_at (performed_at),
    INDEX idx_action (action)
);

-- ============================================
-- ÍNDICES ADICIONALES PARA OPTIMIZACIÓN
-- ============================================
CREATE INDEX idx_event_resources_composite ON event_resources(event_id, resource_id);
CREATE INDEX idx_events_date_range ON events(start_time, end_time);
CREATE INDEX idx_resources_name_type ON resources(name, resource_type);

-- ============================================
-- VISTAS ÚTILES
-- ============================================
-- Vista: Eventos con sus recursos
CREATE VIEW event_resources_view AS
SELECT 
    e.id as event_id,
    e.title,
    e.start_time,
    e.end_time,
    e.status,
    GROUP_CONCAT(r.name SEPARATOR ', ') as resources,
    COUNT(er.resource_id) as total_resources
FROM events e
LEFT JOIN event_resources er ON e.id = er.event_id
LEFT JOIN resources r ON er.resource_id = r.id
GROUP BY e.id, e.title, e.start_time, e.end_time, e.status;

-- Vista: Recursos con uso actual
CREATE VIEW resource_usage_view AS
SELECT 
    r.id,
    r.name,
    r.resource_type,
    r.quantity as total_available,
    COUNT(DISTINCT er.event_id) as current_assignments,
    (r.quantity - COUNT(DISTINCT er.event_id)) as available_now
FROM resources r
LEFT JOIN event_resources er ON r.id = er.resource_id
    AND EXISTS (
        SELECT 1 FROM events e 
        WHERE e.id = er.event_id 
        AND e.status = 'scheduled'
        AND e.end_time > NOW()
    )
GROUP BY r.id, r.name, r.resource_type, r.quantity;

-- ============================================
-- MENSAJE DE CONFIRMACIÓN
-- ============================================
SELECT '✅ Base de datos del Gestor de Eventos creada exitosamente' as mensaje;