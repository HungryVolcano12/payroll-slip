import streamlit as st
import re
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# --- 1. ALIAS, MONTHS & STARK "DATABASE" ---
EMPLOYEE_VARIATIONS = {
    "Kak Sello": ["kak sello", "ka sello", "kak selo", "ka selo", "sello", "selo"],
    "Kak Far": ["kak far", "ka far", "far"],
    "Kak Dessy": ["kak dessy", "ka dessy", "kak desy", "ka desy", "dessy", "desy"],
    "Kak Tur": ["kak tur", "ka tur", "tur"],
    "Kak Nad": ["kak nad", "ka nad", "nad", "kak nadya", "ka nadya", "nadya"],
    "Tcr Sherly": ["tcr sherly", "teacher sherly", "sherly", "sherley", "tdr sherly", "tcr. sherly"],
    "Kak Diana": ["kak diana", "ka diana", "diana"]
}

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
}

# Auto-fill profiles. Edit these to match your actual base contracts.
EMPLOYEE_PROFILES = {
    "Kak Sello": {"salary": 3000000, "transport": 300000, "konsumsi": 450000},
    "Kak Far": {"salary": 3500000, "transport": 300000, "konsumsi": 450000},
    "Kak Dessy": {"salary": 3200000, "transport": 300000, "konsumsi": 450000},
    "Kak Tur": {"salary": 3200000, "transport": 300000, "konsumsi": 450000},
    "Kak Nad": {"salary": 3500000, "transport": 300000, "konsumsi": 450000},
    "Tcr Sherly": {"salary": 4000000, "transport": 300000, "konsumsi": 450000},
    "Kak Diana": {"salary": 2500000, "transport": 200000, "konsumsi": 300000}
}

# --- 2. PARSING FUNCTION ---
def parse_chat_file(file_content, employee_name, selected_month):
    variations = EMPLOYEE_VARIATIONS.get(employee_name, [employee_name.lower()])
    name_pattern = re.compile(r'\b(?:' + '|'.join(re.escape(var) for var in variations) + r')\b', re.IGNORECASE)
    
    time_pattern = re.compile(r'\b([01]?\d|2[0-3])[:.]([0-5]\d)\b')
    # Fixed to Indonesian WhatsApp standard format
    date_pattern = re.compile(r'^\[?(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})')
    
    attendance_tracker = {}
    all_dates = set()
    current_month = None
    current_date_str = None
    is_in_section = False 
    
    if isinstance(file_content, bytes):
        text = file_content.decode('utf-8', errors='ignore')
    else:
        text = str(file_content)
        
    text = text.replace('\ufeff', '')
    lines = text.split('\n')
    
    for line in lines:
        match_date = date_pattern.search(line)
        if match_date:
            day, month, year = match_date.groups()
            current_month = int(month)
            current_date_str = f"{day}/{month}/{year}"
            is_in_section = False
            
        if re.search(r'-{2,}\s*IN\s*-{2,}', line, re.IGNORECASE):
            is_in_section = True
            if current_date_str:
                if selected_month == "All Months" or current_month == MONTHS.get(selected_month):
                    all_dates.add(current_date_str)
            continue
        if re.search(r'-{2,}\s*OUT\s*-{2,}', line, re.IGNORECASE):
            is_in_section = False
            continue
            
        if is_in_section:
            name_match = name_pattern.search(line)
            if name_match:
                if selected_month != "All Months" and current_month != MONTHS.get(selected_month):
                    continue
                
                if current_date_str not in attendance_tracker:
                    attendance_tracker[current_date_str] = False 
                    
                best_time = None
                for t_match in time_pattern.finditer(line):
                    if t_match.start() >= name_match.end():
                        dist = t_match.start() - name_match.end()
                        if dist <= 20: 
                            best_time = t_match
                            break
                            
                if not best_time:
                    best_time = time_pattern.search(line)
                    
                if best_time and current_date_str:
                    hour = int(best_time.group(1))
                    minute = int(best_time.group(2))
                    
                    if 4 <= hour <= 11:
                        if hour > 7 or (hour == 7 and minute > 0):
                            attendance_tracker[current_date_str] = True 
                            
    total_present = len(attendance_tracker)
    days_late = sum(1 for late_status in attendance_tracker.values() if late_status)
    days_absent = len(all_dates) - total_present
    
    return total_present, days_late, days_absent

# --- 3. PDF GENERATOR ---
def generate_pdf(employee_name, selected_month, 
                 basic_salary, transport, konsumsi, edu_support, family_support, pic_student, thr, 
                 honor_kepanitiaan, uang_lembur, bonus_murid, reimbursement,
                 penalty_days, late_deduction, delay_jobdesc, denda_lapker, potongan_izin, bpjs,
                 total_earnings, total_deductions, take_home_pay):
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=50, bottomMargin=50)
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('MainTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=22, alignment=1, spaceAfter=20, textColor=colors.HexColor("#2C3E50"))
    elements.append(Paragraph("OFFICIAL PAYSLIP", title_style))
    
    period_str = selected_month if selected_month != "All Months" else "Overall"
    emp_info_data = [
        ["Name", f": {employee_name}", "Period", f": {period_str}"],
        ["Department", ": Akademik", "Role", ": Teacher / Staff"]
    ]
    emp_info_table = Table(emp_info_data, colWidths=[80, 180, 60, 140])
    emp_info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'), 
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'), 
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(emp_info_table)
    elements.append(Spacer(1, 15))
    
    table_data = []
    
    # EARNINGS
    earnings_idx = len(table_data)
    table_data.append(["PENERIMAAN (EARNINGS)", ""])
    table_data.append(["Gaji Pokok (Basic Salary)", f"Rp {basic_salary:,.0f}"])
    table_data.append(["Transport", f"Rp {transport:,.0f}"])
    table_data.append(["Konsumsi", f"Rp {konsumsi:,.0f}"])
    
    if edu_support > 0: table_data.append(["Education Supporting", f"Rp {edu_support:,.0f}"])
    if family_support > 0: table_data.append(["Family Supporting", f"Rp {family_support:,.0f}"])
    if pic_student > 0: table_data.append(["PIC Student", f"Rp {pic_student:,.0f}"])
    if thr > 0: table_data.append(["THR (Tunjangan Hari Raya)", f"Rp {thr:,.0f}"])
    if honor_kepanitiaan > 0: table_data.append(["Honor Kepanitiaan (Event)", f"Rp {honor_kepanitiaan:,.0f}"])
    if uang_lembur > 0: table_data.append(["Uang Lembur (Overtime)", f"Rp {uang_lembur:,.0f}"])
    if bonus_murid > 0: table_data.append(["Bonus Murid Baru", f"Rp {bonus_murid:,.0f}"])
    if reimbursement > 0: table_data.append(["Reimbursement (Dana Kas)", f"Rp {reimbursement:,.0f}"])
    
    tot_earning_idx = len(table_data)
    table_data.append(["TOTAL EARNINGS", f"Rp {total_earnings:,.0f}"])
    table_data.append(["", ""]) 
    
    # DEDUCTIONS
    deductions_idx = len(table_data)
    table_data.append(["POTONGAN (DEDUCTIONS)", ""])
    table_data.append([f"Late / Absent Fine ({penalty_days} days)", f"- Rp {late_deduction:,.0f}"])
    
    if delay_jobdesc > 0: table_data.append(["Get a fine, delay jobdesc", f"- Rp {delay_jobdesc:,.0f}"])
    if denda_lapker > 0: table_data.append(["Denda LAPKER", f"- Rp {denda_lapker:,.0f}"])
    if potongan_izin > 0: table_data.append(["Potongan Izin (Unpaid Leave)", f"- Rp {potongan_izin:,.0f}"])
    table_data.append(["BPJS", f"- Rp {bpjs:,.0f}"])
    
    tot_deduction_idx = len(table_data)
    table_data.append(["TOTAL DEDUCTIONS", f"- Rp {total_deductions:,.0f}"])
    table_data.append(["", ""]) 
    
    # NET PAY
    net_pay_idx = len(table_data)
    table_data.append(["TAKE HOME PAY", f"Rp {take_home_pay:,.0f}"])
    
    payslip_table = Table(table_data, colWidths=[318, 150])
    style = TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#2C3E50")),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        
        ('BACKGROUND', (0, earnings_idx), (1, earnings_idx), colors.HexColor("#34495E")),
        ('TEXTCOLOR', (0, earnings_idx), (1, earnings_idx), colors.whitesmoke),
        ('FONTNAME', (0, earnings_idx), (1, earnings_idx), 'Helvetica-Bold'),
        
        ('BACKGROUND', (0, deductions_idx), (1, deductions_idx), colors.HexColor("#E74C3C")),
        ('TEXTCOLOR', (0, deductions_idx), (1, deductions_idx), colors.whitesmoke),
        ('FONTNAME', (0, deductions_idx), (1, deductions_idx), 'Helvetica-Bold'),
        
        ('BACKGROUND', (0, tot_earning_idx), (1, tot_earning_idx), colors.HexColor("#ECF0F1")),
        ('FONTNAME', (0, tot_earning_idx), (1, tot_earning_idx), 'Helvetica-Bold'),
        
        ('BACKGROUND', (0, tot_deduction_idx), (1, tot_deduction_idx), colors.HexColor("#FDEDEC")),
        ('FONTNAME', (0, tot_deduction_idx), (1, tot_deduction_idx), 'Helvetica-Bold'),
        
        ('BACKGROUND', (0, net_pay_idx), (1, net_pay_idx), colors.HexColor("#27AE60")),
        ('TEXTCOLOR', (0, net_pay_idx), (1, net_pay_idx), colors.whitesmoke),
        ('FONTNAME', (0, net_pay_idx), (1, net_pay_idx), 'Helvetica-Bold'),
        ('FONTSIZE', (0, net_pay_idx), (1, net_pay_idx), 14),
    ])
    
    style.add('LINEABOVE', (0, tot_earning_idx+1), (1, tot_earning_idx+1), 0, colors.white)
    style.add('LINEBELOW', (0, tot_earning_idx+1), (1, tot_earning_idx+1), 0, colors.white)
    style.add('LINEABOVE', (0, tot_deduction_idx+1), (1, tot_deduction_idx+1), 0, colors.white)
    style.add('LINEBELOW', (0, tot_deduction_idx+1), (1, tot_deduction_idx+1), 0, colors.white)

    payslip_table.setStyle(style)
    elements.append(payslip_table)
    
    elements.append(Spacer(1, 30))
    sig_data = [["Dibuat Oleh,", "Diterima Oleh,"], ["\n\n\n", "\n\n\n"], ["( Bagian Keuangan )", f"( {employee_name} )"]]
    sig_table = Table(sig_data, colWidths=[234, 234])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold')
    ]))
    elements.append(sig_table)
    
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

# --- 4. STREAMLIT UI (AIRBNB DESIGN) ---
def main():
    st.set_page_config(page_title="TC Wika Payroll", page_icon="🏠", layout="centered")
    
    # Inject Dark Mode Theme
    st.markdown("""
        <style>
        /* Dark Font Style */
        .stApp, .stApp > header {
            font-family: 'Circular', -apple-system, BlinkMacSystemFont, Roboto, Helvetica Neue, sans-serif;
        }
        
        /* Soft, Bold Headers */
        h1, h2, h3 {
            color: #FAFAFA !important;
            font-weight: 800 !important;
            letter-spacing: -0.02em;
        }

        /* The 'Price Breakdown' Metric Cards */
        [data-testid="stMetric"] {
            background-color: #1E1E24;
            border: 1px solid #333333;
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.4);
        }
        
        /* Metric Values (Light and Readable) */
        [data-testid="stMetricValue"] {
            color: #FAFAFA !important;
            font-weight: 600;
        }

        /* Friendly, Soft File Uploader */
        [data-testid="stFileUploader"] {
            border: 1px dashed #555555;
            border-radius: 12px;
            padding: 20px;
            background-color: #1E1E24;
            transition: all 0.2s ease;
        }
        [data-testid="stFileUploader"]:hover {
            border-color: #FAFAFA;
            background-color: #2A2A35;
        }

        /* The Signature 'Reserve' Button */
        .stButton>button {
            background-color: #FF5A5F;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 14px 24px;
            font-weight: 600;
            font-size: 16px;
            width: 100%; 
            transition: box-shadow 0.2s ease, transform 0.1s ease;
        }
        
        /* Button Hover Effect */
        .stButton>button:hover {
            background-color: #E0484D;
            color: white;
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.4);
            transform: translateY(-1px);
        }

        
        /* Subtle Dividers */
        hr {
            border-top: 1px solid #333333 !important;
            margin-top: 2rem;
            margin-bottom: 2rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.title("🏠 TC Wika Payroll")
    st.markdown("<p style='font-size: 18px; color: #A0A0A0;'>Generate beautiful, accurate payslips in seconds.</p>", unsafe_allow_html=True)
    
    st.divider()
    
    # Step 1
    st.markdown("### 1. Who are we paying?")
    col_emp, col_mon = st.columns(2)
    
    with col_emp:
        employees = list(EMPLOYEE_VARIATIONS.keys())
        selected_employee = st.selectbox("Select Employee", employees)
        
    with col_mon:
        months_list = ["All Months"] + list(MONTHS.keys())
        selected_month = st.selectbox("Select Month", months_list, index=2) 
        
    st.write("") # Spacer
    
    # Step 2
    st.markdown("### 2. Upload Attendance Log")
    uploaded_file = st.file_uploader("Drop your WhatsApp Chat Export (.txt) here", type=["txt"])
    
    days_late = 0
    days_absent = 0
    total_present = 0
    
    if uploaded_file is not None:
        file_content = uploaded_file.read()
        total_present, days_late, days_absent = parse_chat_file(file_content, selected_employee, selected_month)
        
        period_text = f"in **{selected_month}**" if selected_month != "All Months" else "overall"
        st.success(f"Log scanned! **{selected_employee}** was present **{total_present}** times, late **{days_late}** times, and absent **{days_absent}** times {period_text}.")
        
    st.divider()
    
    # Step 3
    st.markdown("### 3. Price Breakdown")
    profile = EMPLOYEE_PROFILES.get(selected_employee, {"salary": 0, "transport": 0, "konsumsi": 0})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<p style='font-weight:bold; color:#2ECC71;'>Penerimaan (Earnings)</p>", unsafe_allow_html=True)
        basic_salary = st.number_input("Gaji Pokok", min_value=0, value=profile["salary"], step=100000)
        transport = st.number_input("Transport", min_value=0, value=profile["transport"], step=50000)
        konsumsi = st.number_input("Konsumsi", min_value=0, value=profile["konsumsi"], step=50000)
        
        with st.expander("Show Variable Earnings (Optional)"):
            edu_support = st.number_input("Education Supporting", min_value=0, value=0, step=50000)
            family_support = st.number_input("Family Supporting", min_value=0, value=0, step=50000)
            pic_student = st.number_input("PIC Student", min_value=0, value=0, step=50000)
            thr = st.number_input("THR", min_value=0, value=0, step=100000)
            honor_kepanitiaan = st.number_input("Honor Kepanitiaan (Event)", min_value=0, value=0, step=50000)
            uang_lembur = st.number_input("Uang Lembur", min_value=0, value=0, step=50000)
            bonus_murid = st.number_input("Bonus Murid Baru", min_value=0, value=0, step=50000)
            reimbursement = st.number_input("Reimbursement", min_value=0, value=0, step=50000)
        
    with col2:
        st.markdown("<p style='font-weight:bold; color:#FF6B6B;'>Potongan (Deductions)</p>", unsafe_allow_html=True)
        penalty_days = days_late + days_absent
        late_deduction = penalty_days * 50000
        st.metric(label="Late & Absent Fine", value=f"- Rp {late_deduction:,.0f}", delta=f"{penalty_days} penalty days", delta_color="inverse")
        
        bpjs = st.number_input("BPJS", min_value=0, value=150000, step=10000)
        
        with st.expander("Show Penalty Deductions (Optional)"):
            delay_jobdesc = st.number_input("Fine: Delay Jobdesc", min_value=0, value=0, step=25000)
            denda_lapker = st.number_input("Fine: Denda LAPKER", min_value=0, value=0, step=50000)
            potongan_izin = st.number_input("Potongan Izin (Unpaid Leave)", min_value=0, value=0, step=50000)
        
    # Math Calculations
    total_earnings = basic_salary + transport + konsumsi + edu_support + family_support + pic_student + thr + honor_kepanitiaan + uang_lembur + bonus_murid + reimbursement
    total_deductions = late_deduction + delay_jobdesc + denda_lapker + potongan_izin + bpjs
    take_home_pay = total_earnings - total_deductions
    
    st.divider()
    
    # Step 4
    st.markdown(f"<h2 style='text-align: center;'>Total: Rp {take_home_pay:,.0f}</h2>", unsafe_allow_html=True)
    st.write("")
    
    # Generate and Download
    pdf_data = generate_pdf(
        selected_employee, selected_month, basic_salary, transport, konsumsi, edu_support, family_support, pic_student, thr, 
        honor_kepanitiaan, uang_lembur, bonus_murid, reimbursement,
        penalty_days, late_deduction, delay_jobdesc, denda_lapker, potongan_izin, bpjs,
        total_earnings, total_deductions, take_home_pay
    )
    
    st.download_button(
        label="Reserve & Generate PDF",
        data=pdf_data,
        file_name=f"Payslip_{selected_employee.replace(' ', '_')}_{selected_month}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

if __name__ == "__main__":
    main()
