-- Phase 1: denormalize agency_id on request-scoped child tables + tenant attachment paths.

-- proposed_cruises
ALTER TABLE proposed_cruises ADD COLUMN agency_id CHAR(36) NULL AFTER id;
UPDATE proposed_cruises pc JOIN travel_requests tr ON tr.id = pc.travel_request_id SET pc.agency_id = tr.agency_id WHERE pc.agency_id IS NULL;
ALTER TABLE proposed_cruises MODIFY agency_id CHAR(36) NOT NULL, ADD CONSTRAINT fk_proposed_cruises_agency FOREIGN KEY (agency_id) REFERENCES agencies(id);
CREATE INDEX idx_proposed_cruises_agency ON proposed_cruises(agency_id);

-- request_communications
ALTER TABLE request_communications ADD COLUMN agency_id CHAR(36) NULL AFTER id;
UPDATE request_communications rc JOIN travel_requests tr ON tr.id = rc.travel_request_id SET rc.agency_id = tr.agency_id WHERE rc.agency_id IS NULL;
ALTER TABLE request_communications MODIFY agency_id CHAR(36) NOT NULL, ADD CONSTRAINT fk_request_communications_agency FOREIGN KEY (agency_id) REFERENCES agencies(id);
CREATE INDEX idx_request_communications_agency ON request_communications(agency_id);

-- request_tasks
ALTER TABLE request_tasks ADD COLUMN agency_id CHAR(36) NULL AFTER id;
UPDATE request_tasks rt JOIN travel_requests tr ON tr.id = rt.travel_request_id SET rt.agency_id = tr.agency_id WHERE rt.agency_id IS NULL;
ALTER TABLE request_tasks MODIFY agency_id CHAR(36) NOT NULL, ADD CONSTRAINT fk_request_tasks_agency FOREIGN KEY (agency_id) REFERENCES agencies(id);
CREATE INDEX idx_request_tasks_agency ON request_tasks(agency_id);

-- request_notes
ALTER TABLE request_notes ADD COLUMN agency_id CHAR(36) NULL AFTER id;
UPDATE request_notes rn JOIN travel_requests tr ON tr.id = rn.travel_request_id SET rn.agency_id = tr.agency_id WHERE rn.agency_id IS NULL;
ALTER TABLE request_notes MODIFY agency_id CHAR(36) NOT NULL, ADD CONSTRAINT fk_request_notes_agency FOREIGN KEY (agency_id) REFERENCES agencies(id);
CREATE INDEX idx_request_notes_agency ON request_notes(agency_id);

-- request_workflows
ALTER TABLE request_workflows ADD COLUMN agency_id CHAR(36) NULL AFTER id;
UPDATE request_workflows rw JOIN travel_requests tr ON tr.id = rw.travel_request_id SET rw.agency_id = tr.agency_id WHERE rw.agency_id IS NULL;
ALTER TABLE request_workflows MODIFY agency_id CHAR(36) NOT NULL, ADD CONSTRAINT fk_request_workflows_agency FOREIGN KEY (agency_id) REFERENCES agencies(id);
CREATE INDEX idx_request_workflows_agency ON request_workflows(agency_id);

-- call_transcripts
ALTER TABLE call_transcripts ADD COLUMN agency_id CHAR(36) NULL AFTER id;
UPDATE call_transcripts ct JOIN travel_requests tr ON tr.id = ct.travel_request_id SET ct.agency_id = tr.agency_id WHERE ct.agency_id IS NULL;
ALTER TABLE call_transcripts MODIFY agency_id CHAR(36) NOT NULL, ADD CONSTRAINT fk_call_transcripts_agency FOREIGN KEY (agency_id) REFERENCES agencies(id);
CREATE INDEX idx_call_transcripts_agency ON call_transcripts(agency_id);

-- chat_logs
ALTER TABLE chat_logs ADD COLUMN agency_id CHAR(36) NULL AFTER id;
UPDATE chat_logs cl JOIN travel_requests tr ON tr.id = cl.travel_request_id SET cl.agency_id = tr.agency_id WHERE cl.agency_id IS NULL;
ALTER TABLE chat_logs MODIFY agency_id CHAR(36) NOT NULL, ADD CONSTRAINT fk_chat_logs_agency FOREIGN KEY (agency_id) REFERENCES agencies(id);
CREATE INDEX idx_chat_logs_agency ON chat_logs(agency_id);

-- request_research_documents
ALTER TABLE request_research_documents ADD COLUMN agency_id CHAR(36) NULL AFTER id;
UPDATE request_research_documents rd JOIN travel_requests tr ON tr.id = rd.travel_request_id SET rd.agency_id = tr.agency_id WHERE rd.agency_id IS NULL;
ALTER TABLE request_research_documents MODIFY agency_id CHAR(36) NOT NULL, ADD CONSTRAINT fk_request_research_documents_agency FOREIGN KEY (agency_id) REFERENCES agencies(id);
CREATE INDEX idx_request_research_documents_agency ON request_research_documents(agency_id);

-- quoted_insurance
ALTER TABLE quoted_insurance ADD COLUMN agency_id CHAR(36) NULL AFTER id;
UPDATE quoted_insurance qi JOIN travel_requests tr ON tr.id = qi.travel_request_id SET qi.agency_id = tr.agency_id WHERE qi.agency_id IS NULL;
ALTER TABLE quoted_insurance MODIFY agency_id CHAR(36) NOT NULL, ADD CONSTRAINT fk_quoted_insurance_agency FOREIGN KEY (agency_id) REFERENCES agencies(id);
CREATE INDEX idx_quoted_insurance_agency ON quoted_insurance(agency_id);

-- Prefix legacy attachment paths with agency_id
UPDATE call_transcripts ct
JOIN travel_requests tr ON tr.id = ct.travel_request_id
SET ct.stored_path = CONCAT(tr.agency_id, '/', ct.stored_path)
WHERE ct.stored_path LIKE 'requests/%';

UPDATE chat_logs cl
JOIN travel_requests tr ON tr.id = cl.travel_request_id
SET cl.stored_path = CONCAT(tr.agency_id, '/', cl.stored_path)
WHERE cl.stored_path LIKE 'requests/%';

UPDATE request_research_documents rd
JOIN travel_requests tr ON tr.id = rd.travel_request_id
SET rd.stored_path = CONCAT(tr.agency_id, '/', rd.stored_path)
WHERE rd.stored_path LIKE 'requests/%';
