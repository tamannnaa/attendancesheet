from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import json
import re

load_dotenv()

def normalize_records(records):
    """Normalize records to ensure all days 1-31 are present with proper values"""
    fixed = {}

    for r in records:
        day = int(r.get("day", 0))
        hours = float(r.get("hours", 0))
        status = r.get("status", "ABSENT")

        if 1 <= day <= 31:
            fixed[day] = {
                "day": day,
                "hours": max(0, hours),
                "status": status.upper().strip()
            }

    # Fill missing days with ABSENT status
    for d in range(1, 32):
        if d not in fixed:
            fixed[d] = {"day": d, "hours": 0, "status": "ABSENT"}

    return list(sorted(fixed.values(), key=lambda x: x["day"]))


def groq_attendance_extraction(text: str):
    """Extract attendance from PDF text using Groq LLM - Generic for any format"""
    
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0
    )

    prompt = ChatPromptTemplate.from_template("""
You are an EXPERT Attendance Data Extractor. Your ONLY job is to extract EXACT attendance data from ANY company's timesheet.

**CRITICAL: EXTRACT EXACTLY WHAT YOU SEE. NO ASSUMPTIONS. NO AVERAGES.**

===== STEP 1: FIND EMPLOYEE INFORMATION =====
- Look for "Employee Name", "EMPLOYEE NAME", "Name:", "Emp Name", "Employee:"
- Extract the EXACT name shown
- Look for "ID #", "Employee Code", "Emp Code", "ID:", "Code:", "Employee ID", "ID Number"
- Extract the EXACT code/ID shown

===== STEP 2: FIND THE TIME GRID =====
- Look for a table/grid with:
  * Column headers: Day numbers (1, 2, 3, ... 31) OR Day names (Mon, Tue, Wed, etc.)
  * Row labels: "Regular", "Reg.HR", "Normal", "Hours", "Daily", "Overtime", "OT", "Leaves", "Leave", "Absent", "Holiday", "Off", "Offline"
  * Cell values: Numbers (8, 16, 5.5, 10, etc.) OR Letters (B, L, H, EH, AL, SL, OFF)

===== STEP 3: EXTRACT HOURS FOR EVERY SINGLE DAY (1-31) =====

**MAPPING RULES - FOLLOW EXACTLY:**

A. **IF YOU SEE "B" (this represents 8 hours):**
   - This is WORK for 8 hours
   - Status: "WORK"
   - Hours: 8

B. **IF YOU SEE A NUMBER (8, 16, 5.5, 10, 24, etc.):**
   - This is WORK hours for that day
   - Status: "WORK"
   - Hours: The exact number shown

C. **IF YOU SEE "L" or "AL" or "SL" or "Leave" or "Annual Leave" or "Sick Leave":**
   - This is a LEAVE day
   - Status: "LEAVE"
   - Hours: 0 (NEVER calculate or estimate hours for leaves)

D. **IF YOU SEE "H" or "EH" or "Holiday" or "Extra Holiday" or "LH":**
   - This is a HOLIDAY
   - Status: "HOLIDAY"
   - Hours: 0 (unless work hours are shown separately for that holiday)

E. **IF YOU SEE "OFF" or "Off Day" or "Weekend":**
   - Status: "OFF"
   - Hours: 0

F. **IF CELL IS BLANK OR EMPTY:**
   - Do NOT try to determine if it's a weekend or holiday (you don't have calendar context)
   - Simply mark as: "ABSENT"
   - Hours: 0
   - The Excel writer will later determine if it should be OFF or ABSENT based on the actual calendar

G. **IF YOU SEE MULTIPLE VALUES IN ONE DAY (e.g., "8" in Regular row AND "2" in Overtime row, OR "B" in Regular row AND "8" in Overtime row):**
   - Add them together: 8 + 2 = 10 hours (or B=8 + 8 OT = 16 hours)
   - Status: "WORK"
   - Hours: Sum of all values

H. **IF A ROW IS FOR "OVERTIME" or "OT":**
   - Add these hours to the main day total
   - Example: Day 5 has "8" in Regular and "2" in OT = 10 hours total
   - Example: Day 5 has "B" in Regular and "8" in OT = 16 hours total

**SPECIAL CASES:**
- If a day has BOTH a leave marker (L) AND hours: The leave marker takes priority, hours = 0
- If a day has BOTH a holiday marker (H) AND work hours: It's work on a holiday, count the hours as WORK
- If multiple rows apply to same day: Add all numeric hours together
- "B" always means 8 hours of work

===== IMPORTANT =====
- USE ONLY THESE STATUSES: WORK, LEAVE, HOLIDAY, OFF, ABSENT
- HOURS MUST BE 0 for LEAVE, HOLIDAY, OFF, ABSENT
- HOURS CAN BE ANY NUMBER (8, 16, 5.5, 10, 24, etc.) for WORK
- "B" = 8 hours = WORK
                                              
7. **NEVER** invent or estimate hours - extract ONLY what is shown
8. **NEVER** skip days - ensure days 1 through 31 are ALL present
                                              
9. **Shortfall- Currently the minimum working days in a month is considered as 22 days and minium hours will be 22*8= 176 hours. If the extracted days are less then 22 then check if the total working hours are less than 176 hours. If yes then calculate the shortfall hours as (176 - total working hours). If the extracted days are more than 22 days or total working hours are more than 176 then no need to calculate shortfall hours.**

10. ** Remember that ABSENT means no work done on a working day (WEEKDAY). If the day is weekend or holiday then mark it as OFF or HOLIDAY respectively and do not count it as ABSENT.**                      

===== STEP 4: CREATE COMPLETE RECORDS FOR ALL 31 DAYS =====

For EVERY day 1 through 31:
- If you found data: Use the extracted value
- If you found NO data: Mark as ABSENT with 0 hours
- NEVER skip days
- NEVER leave gaps

===== STEP 5: VERIFY YOUR EXTRACTION =====
- Count total WORK hours from all days
- Compare with "Total Hours" shown in timesheet (if available)
- If numbers match, extraction is correct
- If numbers don't match, RE-CHECK your extraction

===== OUTPUT FORMAT (CRITICAL) =====
Return ONLY a JSON object. NO markdown. NO code blocks. NO explanations. NO extra text.

{{
  "employee_name": "Exact name as shown on timesheet",
  "employee_code": "Exact code/ID as shown",
  "records": [
    {{"day": 1, "hours": 8, "status": "WORK"}},
    {{"day": 2, "hours": 0, "status": "LEAVE"}},
    {{"day": 3, "hours": 0, "status": "ABSENT"}},
    {{"day": 4, "hours": 8, "status": "WORK"}},
    {{"day": 5, "hours": 16, "status": "WORK"}},
    {{"day": 6, "hours": 0, "status": "OFF"}},
    {{"day": 7, "hours": 0, "status": "HOLIDAY"}},
    {{"day": 8, "hours": 0, "status": "ABSENT"}},
    ...continue for all 31 days...
    {{"day": 31, "hours": 8, "status": "WORK"}}
  ]
}}

===== REAL EXAMPLES FROM TIMESHEETS =====

Example 1 - Simple Grid with "B":
Input: "Regular row: B B L L B B B B..."
Extract:
  Day 1: 8h WORK (B=8)
  Day 2: 8h WORK (B=8)
  Day 3: 0h LEAVE
  Day 4: 0h LEAVE
  Day 5: 8h WORK (B=8)
  Day 6: 8h WORK (B=8)
  Day 7: 8h WORK (B=8)
  Day 8: 8h WORK (B=8)

Example 2 - With Overtime and B notation:
Input: 
  "Regular: B B B B B"
  "Overtime: blank blank 8 blank 8"
Extract:
  Day 1: 8h WORK (B=8)
  Day 2: 8h WORK (B=8)
  Day 3: 16h WORK (B=8 + 8 OT)
  Day 4: 8h WORK (B=8)
  Day 5: 16h WORK (B=8 + 8 OT)

Example 3 - Mixed Status with B:
Input: "Regular: B B H blank L B B blank..."
Extract:
  Day 1: 8h WORK (B=8)
  Day 2: 8h WORK (B=8)
  Day 3: 0h HOLIDAY
  Day 4: 0h ABSENT (blank cell)
  Day 5: 0h LEAVE
  Day 6: 8h WORK (B=8)
  Day 7: 8h WORK (B=8)
  Day 8: 0h ABSENT (blank cell)

Example 4 - Total Verification with B:
Input shows "Total Hours: 160"
Your extraction shows: 20 days with "B" × 8h = 160h ✓
This means extraction is CORRECT

===== FINAL INSTRUCTIONS =====
1. Extract EXACTLY what you see - NO estimation
2. Include ALL 31 days - NEVER skip
3. Use ONLY these statuses: WORK, LEAVE, HOLIDAY, OFF, ABSENT
4. Hours must be 0 for LEAVE, HOLIDAY, OFF, ABSENT
5. Hours can be any number (8, 16, 5.5, 10, 24, etc.) for WORK
6. "B" = 8 hours of work - ALWAYS
7. Return ONLY JSON
8. NO markdown code blocks
9. NO explanation text
10. Verify total hours match timesheet total

**TEXT TO EXTRACT FROM:**
{text}

**START EXTRACTION NOW:**
""")

    response = llm.invoke(prompt.format_messages(text=text))
    content = response.content.strip()
    
    # Remove markdown code blocks
    content = re.sub(r'^```json\s*', '', content, flags=re.IGNORECASE)
    content = re.sub(r'^```\s*', '', content)
    content = re.sub(r'\s*```$', '', content)
    content = content.strip()
    
    if content.startswith('`'):
        content = content.strip('`').strip()

    try:
        data = json.loads(content)
        
        if data.get("records"):
            data["records"] = normalize_records(data["records"])

        return data
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"LLM returned: {content[:500]}")
        return None