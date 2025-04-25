--DB作成
CREATE DATABASE status_management_db;
--作成したDBに接続
\c status_management_db;

--立入り状態情報作成
CREATE TABLE IF NOT EXISTS  "entry_status_information" (
	id SERIAL NOT NULL,
	port VARCHAR(16) NULL,
	datetime TIMESTAMP WITH TIME ZONE NULL,
	detect BOOLEAN NULL,
	report_id UUID NULL,
	CONSTRAINT entry_status_information_pkey PRIMARY KEY (ID)
);
--レポート作成
CREATE TABLE IF NOT EXISTS "report" (
	report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	endpoint VARCHAR(256)
);
--イベント作成
CREATE TABLE IF NOT EXISTS "event_information" (
	id SERIAL NOT NULL,
	ent_stat_id INTEGER NOT NULL,
	object_id VARCHAR(64) NULL,
	object_type VARCHAR(16) NULL,
	detect BOOLEAN NULL,
	location VARCHAR(256) NULL,
	CONSTRAINT event_information_pkey PRIMARY KEY (ID)
);
--外部キー追加
ALTER TABLE "entry_status_information"
	ADD FOREIGN KEY (report_id)
	REFERENCES "report" (report_id);
	
ALTER TABLE "event_information"
	ADD FOREIGN KEY (ent_stat_id)
	REFERENCES "entry_status_information" (id);

