-- Migration 001: Add/verify foreign key constraints for BAOS tables.

DO $$
BEGIN
  IF to_regclass('baos.port_call') IS NOT NULL
     AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_baos_port_call_port') THEN
    ALTER TABLE baos.port_call
      ADD CONSTRAINT fk_baos_port_call_port
      FOREIGN KEY (port_id) REFERENCES baos.port(port_id)
      ON DELETE RESTRICT ON UPDATE CASCADE;
  END IF;

  IF to_regclass('baos.port_call') IS NOT NULL
     AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_baos_port_call_berth') THEN
    ALTER TABLE baos.port_call
      ADD CONSTRAINT fk_baos_port_call_berth
      FOREIGN KEY (berth_id) REFERENCES baos.berth(berth_id)
      ON DELETE SET NULL ON UPDATE CASCADE;
  END IF;

  IF to_regclass('baos.berth') IS NOT NULL
     AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_baos_berth_port') THEN
    ALTER TABLE baos.berth
      ADD CONSTRAINT fk_baos_berth_port
      FOREIGN KEY (port_id) REFERENCES baos.port(port_id)
      ON DELETE RESTRICT ON UPDATE CASCADE;
  END IF;

  IF to_regclass('baos.berth_capability') IS NOT NULL
     AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_baos_berth_capability_berth') THEN
    ALTER TABLE baos.berth_capability
      ADD CONSTRAINT fk_baos_berth_capability_berth
      FOREIGN KEY (berth_id) REFERENCES baos.berth(berth_id)
      ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
END $$;
