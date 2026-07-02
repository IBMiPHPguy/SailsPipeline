ALTER TABLE agencies
    ADD COLUMN business_address_line_1 VARCHAR(120) NULL AFTER is_active,
    ADD COLUMN business_address_line_2 VARCHAR(120) NULL AFTER business_address_line_1,
    ADD COLUMN business_city VARCHAR(80) NULL AFTER business_address_line_2,
    ADD COLUMN business_state_or_province VARCHAR(50) NULL AFTER business_city,
    ADD COLUMN business_postal_code VARCHAR(20) NULL AFTER business_state_or_province,
    ADD COLUMN business_country VARCHAR(80) NULL AFTER business_postal_code;

CREATE INDEX idx_agencies_business_state ON agencies (business_state_or_province);
