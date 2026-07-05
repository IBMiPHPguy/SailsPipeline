CREATE TABLE IF NOT EXISTS passenger_loyalty_numbers (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    passenger_id INT NOT NULL,
    cruise_line VARCHAR(100) NOT NULL,
    loyalty_number VARCHAR(80) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_passenger_loyalty_numbers_passenger
        FOREIGN KEY (passenger_id) REFERENCES passengers(id) ON DELETE CASCADE,
    UNIQUE KEY uq_passenger_loyalty_line (passenger_id, cruise_line),
    INDEX idx_passenger_loyalty_passenger (passenger_id)
);
