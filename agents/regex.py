import re
from datetime import datetime

def regex_extract(text: str):
    """
    Fallback regex-based extraction for SABIC timesheets
    Handles grid-based formats with day columns
    """
    
    records = []
    employee_name = None
    employee_code = None
    po_number = None
    
    # Extract employee name
    name_patterns = [
        r"Employee Name\s*[:\-]\s*(.+?)(?:\n|$)",
        r"EMPLOYEE NAME\s*[:\-]\s*(.+?)(?:\n|$)",
        r"Name\s*[:\-]\s*(.+?)(?:\n|$)"
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            employee_name = match.group(1).strip()
            break
    
    # Extract employee code/ID
    id_patterns = [
        r"ID\s*#\s*[:\-]?\s*(\w+)",
        r"Employee Code\s*[:\-]?\s*(\w+)",
        r"ID\s*[:\-]?\s*(\w+)"
    ]
    for pattern in id_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            employee_code = match.group(1).strip()
            break
    
    # Extract PO number
    po_match = re.search(r"PO\s*#?\s*[:\-]?\s*(\d+)", text, re.I)
    if po_match:
        po_number = po_match.group(1)
    
    # Find "Regular" or "Reg.HR" row with numbers
    regular_pattern = r"(?:Regular|Reg\.HR)\s+([\d\sLHOFEAL]+)"
    regular_match = re.search(regular_pattern, text, re.I)
    
    if regular_match:
        values = regular_match.group(1).split()
        
        for day, val in enumerate(values, start=1):
            val = val.strip()
            
            if val.isdigit():
                records.append({
                    "day": day,
                    "hours": int(val),
                    "status": "WORK"
                })
            elif val.upper() in ["L", "AL", "SL"]:
                records.append({
                    "day": day,
                    "hours": 0,
                    "status": "LEAVE"
                })
            elif val.upper() in ["H", "EH"]:
                records.append({
                    "day": day,
                    "hours": 0,
                    "status": "HOLIDAY"
                })
            elif val.upper() == "OFF":
                records.append({
                    "day": day,
                    "hours": 0,
                    "status": "OFF"
                })
    
    # Check for overtime row
    ot_pattern = r"(?:Overtime|OT)\s+([\d\s]+)"
    ot_match = re.search(ot_pattern, text, re.I)
    
    if ot_match:
        ot_values = ot_match.group(1).split()
        
        for day, val in enumerate(ot_values, start=1):
            if val.strip().isdigit():
                ot_hours = int(val.strip())
                
                # Add to existing record or create new
                existing = next((r for r in records if r["day"] == day), None)
                if existing:
                    existing["hours"] += ot_hours
                else:
                    records.append({
                        "day": day,
                        "hours": ot_hours,
                        "status": "WORK"
                    })
    
    return {
        "employee_name": employee_name or "UNKNOWN",
        "employee_code": employee_code or "",
        "po_number": po_number or "",
        "attendance_type": "GRID",
        "records": records
    }