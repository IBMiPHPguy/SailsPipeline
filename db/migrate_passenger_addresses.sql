ALTER TABLE passengers
    ADD COLUMN address_line_1 VARCHAR(120) NULL AFTER date_of_birth,
    ADD COLUMN address_line_2 VARCHAR(120) NULL AFTER address_line_1,
    ADD COLUMN city VARCHAR(80) NULL AFTER address_line_2,
    ADD COLUMN state_or_province VARCHAR(50) NULL AFTER city,
    ADD COLUMN postal_code VARCHAR(20) NULL AFTER state_or_province,
    ADD COLUMN country VARCHAR(80) NULL AFTER postal_code;
