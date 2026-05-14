SET search_path TO aeromiles, public, extensions;

CREATE OR REPLACE FUNCTION update_member_miles_on_claim_approval()
RETURNS TRIGGER AS $$
DECLARE
    v_email_member VARCHAR;
    v_maskapai VARCHAR;
    v_flight_number VARCHAR;
    v_success_message TEXT;
BEGIN
    IF NEW.status_penerimaan = 'Disetujui' AND OLD.status_penerimaan != 'Disetujui' THEN
        
        v_email_member := NEW.email_member;
        v_maskapai := NEW.maskapai;
        v_flight_number := NEW.flight_number;
        
        UPDATE MEMBER 
        SET award_miles = award_miles + 1000,
            total_miles = total_miles + 1000
        WHERE email = v_email_member;
        
        v_success_message := 'SUKSES: Total miles Member "' || v_email_member || 
                            '" telah diperbarui. Miles ditambahkan: 1000 miles dari klaim penerbangan "' || 
                            v_flight_number || '".';
        
        RAISE NOTICE '%', v_success_message;
        
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER trg_update_member_miles_on_claim_approval
AFTER UPDATE ON claim_missing_miles
FOR EACH ROW
EXECUTE FUNCTION update_member_miles_on_claim_approval();


CREATE OR REPLACE FUNCTION get_top_5_members()
RETURNS TABLE(
    rank INT,
    email VARCHAR,
    nomor_member VARCHAR,
    nama_lengkap VARCHAR,
    total_miles INT,
    award_miles INT,
    id_tier VARCHAR
) AS $$
DECLARE
    v_top_member_email VARCHAR;
    v_top_member_miles INT;
    v_success_message TEXT;
BEGIN
    
    SELECT m.email, m.total_miles INTO v_top_member_email, v_top_member_miles
    FROM MEMBER m
    ORDER BY m.total_miles DESC
    LIMIT 1;
    
    IF v_top_member_email IS NOT NULL THEN
        v_success_message := 'SUKSES: Daftar Top 5 Member berdasarkan total miles berhasil diperbarui, ' ||
                           'dengan peringkat pertama "' || v_top_member_email || '" memiliki ' ||
                           v_top_member_miles || ' miles.';
        RAISE NOTICE '%', v_success_message;
    END IF;
    
    RETURN QUERY
    SELECT 
        ROW_NUMBER() OVER (ORDER BY m.total_miles DESC)::INT as rank,
        m.email,
        m.nomor_member,
        (p.first_mid_name || ' ' || p.last_name) as nama_lengkap,
        m.total_miles,
        m.award_miles,
        m.id_tier
    FROM MEMBER m
    JOIN PENGGUNA p ON m.email = p.email
    ORDER BY m.total_miles DESC
    LIMIT 5;
    
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION display_top_5_members_report()
RETURNS TEXT AS $$
DECLARE
    v_top_member_email VARCHAR;
    v_top_member_miles INT;
    v_success_message TEXT;
BEGIN
    
    SELECT m.email, m.total_miles INTO v_top_member_email, v_top_member_miles
    FROM MEMBER m
    ORDER BY m.total_miles DESC
    LIMIT 1;
    
    v_success_message := 'SUKSES: Daftar Top 5 Member berdasarkan total miles berhasil diperbarui, ' ||
                       'dengan peringkat pertama "' || v_top_member_email || '" memiliki ' ||
                       v_top_member_miles || ' miles.';
    
    RETURN v_success_message;
    
END;
$$ LANGUAGE plpgsql;

