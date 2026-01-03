import streamlit as st
from agents.extractor import extract_attendance
from excel.excel_writer import write_commit_excel
from datetime import date, datetime
from dotenv import load_dotenv
import openpyxl
import io
import os

load_dotenv()

st.set_page_config(page_title="Attendance AI", layout="wide")

HOLIDAYS_2025 = [
    date(2025, 1, 26),   # Republic Day
    date(2025, 3, 8),    # Maha Shivaratri
    date(2025, 3, 10),   # Holi
    date(2025, 3, 29),   # Good Friday
    date(2025, 4, 11),   # Eid ul-Fitr (Estimated)
    date(2025, 4, 17),   # Ram Navami
    date(2025, 4, 18),   # Mahavir Jayanti
    date(2025, 5, 23),   # Buddha Purnima
    date(2025, 6, 20),   # Eid ul-Adha (Estimated)
    date(2025, 7, 17),   # Muharram
    date(2025, 8, 15),   # Independence Day
    date(2025, 8, 27),   # Janmashtami
    date(2025, 9, 16),   # Milad un-Nabi
    date(2025, 10, 2),   # Gandhi Jayanti
    date(2025, 10, 20),  # Dussehra
    date(2025, 11, 1),   # Diwali (Lakshmi Puja)
    date(2025, 11, 2),   # Diwali (Govardhan Puja)
    date(2025, 11, 3),   # Bhai Dooj
    date(2025, 12, 25),  # Christmas
]

# Header
st.title("📊 Attendance AI – COMM-IT Consolidation Tool")
st.markdown("Upload attendance PDFs and generate consolidated attendance sheet")


# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    if not os.getenv("GROQ_API_KEY"):
        st.error("⚠️ GROQ_API_KEY not found in environment")
        st.stop()
    else:
        st.success("✅ Groq API Connected")
    
    st.divider()
    
    # Date range
    st.subheader("📅 Period Selection")
    start_date = st.date_input(
        "Start Date", 
        value=date(2025, 9, 26),
        help="Usually 26th of previous month"
    )
    end_date = st.date_input(
        "End Date", 
        value=date(2025, 10, 25),
        help="Usually 25th of current month"
    )
    
    st.info(f"📊 Period: {(end_date - start_date).days + 1} days")

    st.divider()
    st.subheader("🏛️ Holidays Configuration")
    
    # Show holidays in the period
    holidays_in_period = [h for h in HOLIDAYS_2025 if start_date <= h <= end_date]
    if holidays_in_period:
        st.write("**Holidays in this period:**")
        for holiday in holidays_in_period:
            st.write(f"- {holiday.strftime('%d-%b-%Y (%A)')}")
    else:
        st.write("No holidays in this period")

# Main area
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📄 Upload Files")
    template_file = st.file_uploader(
        "Upload COMM-IT Template Excel", 
        type=["xlsx"],
        help="Upload the blank COMM-IT template"
    )
    
    pdfs = st.file_uploader(
        "Upload Attendance PDFs", 
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload all employee attendance sheets"
    )
    
    if pdfs:
        st.success(f"✅ {len(pdfs)} PDF(s) uploaded")

with col2:
    st.subheader("ℹ️ Instructions")
    st.markdown("""
    1. **Upload template**: COMM-IT Excel format
    2. **Upload PDFs**: Employee attendance sheets
    3. **Set dates**: Select period (26th to 25th)
    4. **Generate**: Click to process all files
    5. **Download**: Get consolidated Excel
    
    **Supported formats:**
    - SABIC grid timesheets
    - Date-based timesheets
    """)

# Processing
st.divider()

if st.button("🚀 Generate Consolidated Sheet", type="primary", use_container_width=True):
    if not template_file:
        st.error("❌ Please upload COMM-IT template")
        st.stop()
    
    if not pdfs:
        st.error("❌ Please upload at least one PDF")
        st.stop()
    
    # Load template
    with st.spinner("Loading template..."):
        template_bytes = template_file.read()
        wb = openpyxl.load_workbook(io.BytesIO(template_bytes))
        st.success("✅ Template loaded")
    
    # Process each PDF
    st.subheader("📋 Processing Attendance Sheets")
    
    progress_bar = st.progress(0)
    status_container = st.container()
    
    results = []
    
    for idx, pdf in enumerate(pdfs):
        with status_container:
            with st.expander(f"📄 Processing: {pdf.name}", expanded=True):
                try:
                    # Extract data
                    st.info(f"🔍 Extracting data from {pdf.name}...")
                    result = extract_attendance(pdf.read())
                    
                    if not result or not result.get("records"):
                        st.warning(f"⚠️ No attendance records found in {pdf.name}")
                        continue
                    
                    # Display extracted info
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Employee", result.get("employee_name", "UNKNOWN"))
                    with col_b:
                        st.metric("Records", len(result.get("records", [])))
                    with col_c:
                        work_hours = sum(
                              r.get("hours", 0) for r in result.get("records", []) 
                              if r.get("status", "").upper() == "WORK"
                        )
                        st.metric("Present Work Hours", f"{work_hours:.1f}h")
                    
                    # Show debug info
                    with st.expander("🔍 Debug: View Extracted Data"):
                        st.json(result)
                    
                    # Write to Excel
                    wb, total_hours = write_commit_excel(wb, result, start_date, end_date, holidays=HOLIDAYS_2025)
                    st.success(f"✅ Added: {result.get('employee_name')}")
                    
                    results.append(result)
                    
                except Exception as e:
                    st.error(f"❌ Error processing {pdf.name}: {str(e)}")
                    st.exception(e)
        
        # Update progress
        progress_bar.progress((idx + 1) / len(pdfs))
    
    # Save final workbook
    if results:
        st.divider()
        st.subheader("💾 Download Results")
        
        out = io.BytesIO()
        wb.save(out)
        out.seek(0)
        
        col_download, col_summary = st.columns([1, 1])
        
        with col_download:
            st.download_button(
                label="⬇️ Download Consolidated Excel",
                data=out.getvalue(),
                file_name=f"COMM_IT_Attendance_{start_date}_{end_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
        
        with col_summary:
            st.success(f"✅ Successfully processed {len(results)} employees")
            st.info(f"📅 Period: {start_date} to {end_date}")
    else:
        st.error("❌ No records were successfully processed")

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; font-size: 12px;'>
    Attendance AI v1.0 | Powered by Groq LLama 3.3 70B
</div>
""", unsafe_allow_html=True)