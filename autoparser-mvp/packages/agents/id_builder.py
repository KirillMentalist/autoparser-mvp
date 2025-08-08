from sqlalchemy import text

def build_intlid(e1: dict, e4: dict, db_session) -> str:
    prefix = f"{e1['msr_geocde']}_{e1['msr_prglvl']}_{e4['msr_segmnt']}_{e4['msr_typeid']}"
    # Query existing max seq for this prefix
    sql = text("SELECT msr_intlid FROM measures WHERE msr_intlid LIKE :pref || '\\_%' ORDER BY msr_intlid DESC LIMIT 1")
    row = db_session.execute(sql, {"pref": prefix}).fetchone()
    if row and row[0]:
        try:
            last = int(row[0].split('_')[-1])
        except Exception:
            last = 0
    else:
        last = 0
    return f"{prefix}_{last + 1:03d}"
