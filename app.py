from __future__ import annotations

from datetime import date, timedelta
from html import escape
from io import BytesIO

import pandas as pd
import streamlit as st
from streamlit_calendar import calendar

from scheduler import DAY_KEYS, DAY_LABELS, Employee, Shift, audit_schedule, build_week, generate_schedule
from storage import authenticate, create_leave_request, create_store, create_swap_request, init_db, list_leave_requests, list_stores, list_swap_requests, load_employees, load_latest_schedule, review_leave_request, review_swap_request, save_employees, save_schedule


st.set_page_config(page_title="Shiftwise 智慧排班", page_icon="✦", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Noto+Sans+TC:wght@400;500;700;900&display=swap');
    :root { --ink:#172033; --muted:#667085; --panel:#ffffff; --panel-2:#f8fafc; --line:#e4e7ec; --blue:#2563eb; --violet:#7c3aed; }
    html, body, [class*="css"] { font-family: 'DM Sans', 'Noto Sans TC', sans-serif; }
    .stApp { background: #f4f7fb; color: var(--ink); }
    [data-testid="stHeader"] { background: rgba(244,247,251,.94); position: relative; z-index: 1001; }
    [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid var(--line); }
    [data-testid="stSidebar"] > div:first-child { padding: 1.5rem 1.15rem; }
    [data-testid="stSidebar"] [data-testid="stExpander"] { background: #f8fafc; border: 1px solid var(--line); border-radius: 12px; margin-bottom: .7rem; box-shadow: 0 4px 16px rgba(16,24,40,.04); }
    h1, h2, h3 { letter-spacing: -.025em; color: var(--ink); }
    h1 { font-size: 2.55rem !important; font-weight: 800 !important; line-height: 1.05 !important; }
    .eyebrow { color: #60a5fa; text-transform: uppercase; letter-spacing: .18em; font-size: .68rem; font-weight: 700; }
    .subtitle { color: var(--muted); margin-top: -.55rem; margin-bottom: 1.7rem; font-size: .98rem; }
    .section-title { color: var(--ink); font-size: 1.08rem; font-weight: 700; margin: 1.35rem 0 .7rem; }
    .section-meta { color: var(--muted); font-size: .82rem; margin-top: -.35rem; }
    .kpi-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .85rem; margin: .8rem 0 1.6rem; }
    .kpi-card { background: linear-gradient(145deg, #ffffff, #f8fafc); border: 1px solid var(--line); border-radius: 12px; padding: 1rem 1.15rem; min-height: 112px; box-shadow: 0 8px 24px rgba(16,24,40,.06); }
    .kpi-label { color: var(--muted); font-size: .75rem; letter-spacing: .02em; }
    .kpi-value { color: var(--ink); font-size: 1.9rem; font-weight: 700; margin: .35rem 0 .2rem; }
    .kpi-detail { color: #667085; font-size: .74rem; }
    .kpi-blue .kpi-value { color: #60a5fa; } .kpi-violet .kpi-value { color: #c084fc; } .kpi-orange .kpi-value { color: #fb923c; }
    .panel-card { background: rgba(255,255,255,.86); border: 1px solid var(--line); border-radius: 12px; padding: 1rem 1.1rem; box-shadow: 0 8px 24px rgba(16,24,40,.05); }
    .employee-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: .75rem; margin-top: 1rem; }
    .employee-card { background: #ffffff; border: 1px solid var(--line); border-radius: 12px; padding: .9rem; box-shadow: 0 6px 20px rgba(16,24,40,.05); }
    .employee-name { color: var(--ink); font-weight: 700; font-size: .95rem; margin-bottom: .55rem; }
    .badge { display: inline-block; border-radius: 999px; padding: .22rem .52rem; margin: .13rem .18rem .13rem 0; font-size: .7rem; font-weight: 600; }
    .badge-early { background: #1e3a8a33; color: #60a5fa; } .badge-mid { background: #7c2d1233; color: #fb923c; } .badge-late { background: #581c8733; color: #c084fc; }
    .badge-neutral { background: #eef2f6; color: #475467; }
    .schedule-table { width: 100%; border-collapse: separate; border-spacing: 0; overflow: hidden; border: 1px solid var(--line); border-radius: 10px; background: #ffffff; font-size: .8rem; box-shadow: 0 6px 20px rgba(16,24,40,.05); }
    .schedule-table th { background: #f8fafc; color: var(--muted); font-weight: 600; text-align: left; padding: .7rem .8rem; border-bottom: 1px solid var(--line); }
    .schedule-table td { padding: .68rem .8rem; border-bottom: 1px solid #eef2f6; color: #475467; }
    .schedule-table tr:last-child td { border-bottom: 0; } .schedule-table .person { color: var(--ink); font-weight: 600; }
    .shift-badge { border-radius: 999px; padding: .23rem .55rem; font-size: .7rem; font-weight: 600; }
    .shift-early { background: #1e3a8a33; color: #60a5fa; } .shift-mid { background: #7c2d1233; color: #fb923c; } .shift-late { background: #581c8733; color: #c084fc; }
    .empty-state { border: 1px dashed #cfd6df; border-radius: 12px; padding: 2.4rem; text-align: center; color: var(--muted); background: rgba(255,255,255,.72); }
    [data-baseweb="tab-list"] { gap: .35rem; border-bottom: 1px solid var(--line); }
    [data-baseweb="tab"] { border-radius: 999px; padding: .42rem .9rem; color: var(--muted); border: 1px solid transparent; }
    [data-baseweb="tab"][aria-selected="true"] { color: var(--ink); background: #ffffff; border-color: #cfd6df; box-shadow: 0 4px 12px rgba(16,24,40,.06); }
    [data-baseweb="tab-highlight"] { display: none; }
    .stButton > button, .stDownloadButton > button { border-radius: 8px; border: 1px solid #d0d5dd; background: #ffffff; color: #344054; font-weight: 600; transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease; }
    .stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-1px); border-color: #84adf7; box-shadow: 0 7px 20px rgba(37,99,235,.12); color: #172033; }
    .stButton > button[kind="primary"] { background: linear-gradient(135deg, #2563eb, #3b82f6); color: #fff; border: 0; box-shadow: 0 7px 20px rgba(37,99,235,.22); }
    .stButton > button[kind="primary"]:hover { background: linear-gradient(135deg, #1d4ed8, #2563eb); color: #fff; }
    .employee-avatar { width: 34px; height: 34px; display: inline-flex; align-items: center; justify-content: center; border-radius: 10px; background: linear-gradient(135deg, #2563eb, #7c3aed); color: #fff; font-weight: 800; margin-right: .55rem; vertical-align: middle; }
    .employee-card-head { display: flex; align-items: center; justify-content: space-between; gap: .75rem; }
    .employee-card-meta { margin-top: .65rem; display: flex; flex-wrap: wrap; gap: .3rem; color: var(--muted); font-size: .72rem; }
    .day-pill { background: #f2f4f7; border: 1px solid #e4e7ec; border-radius: 999px; padding: .18rem .45rem; color: #475467; }
    .shift-setting { background: #ffffff; border: 1px solid #e4e7ec; border-radius: 10px; padding: .75rem; margin: .5rem 0; }
    .calendar-shell { background: #ffffff; border: 1px solid #dfe3e8; border-radius: 14px; padding: .65rem; box-shadow: 0 8px 28px rgba(16,24,40,.08); }
    .calendar-note { color: #667085; font-size: .76rem; margin: .5rem 0 .8rem; }
    .incident-card { background: #fff7ed; border: 1px solid #fed7aa; border-radius: 10px; padding: .65rem .75rem; margin: .45rem 0; color: #9a3412; font-size: .78rem; }
    .peak-hint { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: .55rem .65rem; color: #1d4ed8; font-size: .74rem; margin: .45rem 0 .7rem; }
    .app-topbar { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin: .35rem 0 1.25rem; }
    .brand-lockup { display: flex; align-items: center; gap: .65rem; }
    .brand-mark { width: 36px; height: 36px; display: grid; place-items: center; border-radius: 11px; background: linear-gradient(135deg, #2563eb, #7c3aed); color: white; font-weight: 900; box-shadow: 0 7px 18px rgba(37,99,235,.2); }
    .brand-name { color: #172033; font-weight: 800; letter-spacing: -.02em; }
    .brand-caption { color: #98a2b3; font-size: .7rem; margin-top: .1rem; }
    .status-pill { display: inline-flex; align-items: center; gap: .35rem; border: 1px solid #bbf7d0; background: #f0fdf4; color: #15803d; border-radius: 999px; padding: .35rem .65rem; font-size: .72rem; font-weight: 700; }
    .status-dot { width: 6px; height: 6px; border-radius: 50%; background: #22c55e; }
    .load-panel { background: #ffffff; border: 1px solid var(--line); border-radius: 12px; padding: 1rem 1.1rem; box-shadow: 0 8px 24px rgba(16,24,40,.05); }
    .load-title { display: flex; justify-content: space-between; color: #172033; font-weight: 700; font-size: .88rem; margin-bottom: .85rem; }
    .load-title span { color: #98a2b3; font-size: .72rem; font-weight: 500; }
    .load-chart { display: grid; grid-template-columns: repeat(7, 1fr); gap: .55rem; align-items: end; height: 112px; }
    .load-day { display: flex; flex-direction: column; align-items: center; justify-content: end; gap: .4rem; height: 100%; }
    .load-bar-track { width: 100%; max-width: 34px; height: 82px; background: #f2f4f7; border-radius: 7px; display: flex; align-items: end; overflow: hidden; }
    .load-bar { width: 100%; min-height: 4px; background: linear-gradient(180deg, #60a5fa, #2563eb); border-radius: 7px; }
    .load-day label { color: #98a2b3; font-size: .68rem; }
    .load-day strong { color: #475467; font-size: .68rem; }
    .alert-panel { background: #fffbeb; border: 1px solid #fde68a; border-radius: 12px; padding: 1rem 1.1rem; color: #92400e; min-height: 100%; }
    .alert-panel strong { display: block; color: #78350f; margin-bottom: .35rem; }
    .alert-panel span { color: #a16207; font-size: .78rem; line-height: 1.5; }
    .login-shell { max-width: 430px; margin: 8vh auto 0; }
    .login-card { background: #ffffff; border: 1px solid var(--line); border-radius: 16px; padding: 2rem; box-shadow: 0 18px 50px rgba(16,24,40,.1); }
    .health-panel { background: #ffffff; border: 1px solid var(--line); border-radius: 12px; padding: 1rem 1.1rem; box-shadow: 0 8px 24px rgba(16,24,40,.05); margin-top: 1rem; }
    .health-title { color: #172033; font-weight: 700; font-size: .88rem; margin-bottom: .75rem; }
    .health-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: .55rem; }
    .health-item { border: 1px solid #e4e7ec; border-radius: 9px; padding: .6rem .65rem; background: #f8fafc; }
    .health-item strong { display: block; color: #172033; font-size: .82rem; }
    .health-item span { color: #667085; font-size: .7rem; }
    .health-ok { border-color: #bbf7d0; background: #f0fdf4; } .health-ok strong { color: #15803d; }
    .health-warn { border-color: #fde68a; background: #fffbeb; } .health-warn strong { color: #a16207; }
    @media (max-width: 700px) { .health-grid { grid-template-columns: repeat(2, 1fr); } }
    .stTextInput input, .stNumberInput input, [data-baseweb="select"] > div { background: #ffffff !important; color: #172033 !important; border-color: #d0d5dd !important; }
    label, [data-testid="stWidgetLabel"] p { color: #475467 !important; }
        @media (max-width: 700px) {
            .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            h1 { font-size: 2rem !important; }
            [data-testid="stSidebar"] { width: min(86vw, 340px) !important; z-index: 1002 !important; }
            [data-testid="stSidebar"] > div:first-child { padding: 1rem .85rem 2rem; }
            [data-testid="stSidebarCollapseButton"], [data-testid="stSidebar"] button[aria-label*="Close"], [data-testid="stSidebar"] button[aria-label*="關閉"] { display: flex !important; visibility: visible !important; opacity: 1 !important; position: relative; z-index: 1004; }
            [data-testid="stSidebar"] [data-testid="stExpander"] { margin-bottom: .55rem; }
            [data-testid="stSidebar"] .stTextInput input, [data-testid="stSidebar"] .stNumberInput input { min-height: 2.6rem; }
            .employee-card-meta { font-size: .68rem; }
            .schedule-table { display: block; overflow-x: auto; white-space: nowrap; }
            .app-topbar { align-items: flex-start; }
            .status-pill { font-size: .65rem; }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def defaults() -> None:
    init_db()
    if "store_id" not in st.session_state:
        st.session_state.store_id = list_stores()[0]["id"]
    if "shifts" not in st.session_state:
        st.session_state.shifts = [
            {"班別": "早班", "開始": "07:00", "結束": "15:00", "工時": 8.0},
            {"班別": "中班", "開始": "11:00", "結束": "19:00", "工時": 8.0},
            {"班別": "晚班", "開始": "15:00", "結束": "23:00", "工時": 8.0},
        ]
    if "employees" not in st.session_state:
        stored_employees = load_employees(st.session_state.store_id)
        st.session_state.employees = stored_employees if not stored_employees.empty else pd.DataFrame(
            [
                {"姓名": "林怡君", "可上班日": "一,二,三,四,五", "可上班班別": "早班,中班", "期望休假": "六,日"},
                {"姓名": "陳柏翰", "可上班日": "一,二,三,四,五,六", "可上班班別": "中班,晚班", "期望休假": "三"},
                {"姓名": "王郁婷", "可上班日": "二,三,四,五,六,日", "可上班班別": "早班,晚班", "期望休假": "一"},
                {"姓名": "張家豪", "可上班日": "一,三,四,五,六,日", "可上班班別": "早班,中班,晚班", "期望休假": "二"},
            ]
        )
        save_employees(st.session_state.store_id, st.session_state.employees)
    if "schedule" not in st.session_state:
        st.session_state.schedule, st.session_state.gaps = load_latest_schedule(st.session_state.store_id, (date.today() - timedelta(days=date.today().weekday())).isoformat())
    if "pending_schedule" not in st.session_state:
        st.session_state.pending_schedule = pd.DataFrame()
    if "employee_edit_index" not in st.session_state:
        st.session_state.employee_edit_index = None
    if "absences" not in st.session_state:
        st.session_state.absences = []
    if "peak_demand" not in st.session_state:
        st.session_state.peak_demand = {}


def render_login() -> bool:
    if st.session_state.get("user"):
        return True
    st.markdown('<div class="login-shell"><div class="login-card">', unsafe_allow_html=True)
    st.markdown('<div class="brand-lockup"><div class="brand-mark">S</div><div><div class="brand-name">Shiftwise</div><div class="brand-caption">Service operations control center</div></div></div>', unsafe_allow_html=True)
    st.markdown("### 登入排班控制台")
    st.caption("請使用門市帳號登入以查看與管理班表。")
    with st.form("login_form"):
        username = st.text_input("帳號", placeholder="輸入帳號")
        password = st.text_input("密碼", type="password", placeholder="輸入密碼")
        submitted = st.form_submit_button("登入", type="primary", width="stretch")
    if submitted:
        user = authenticate(username, password)
        if user:
            st.session_state.user = user
            st.session_state.store_id = user["store_id"]
            st.rerun()
        st.error("帳號或密碼不正確。")
    st.markdown('</div></div>', unsafe_allow_html=True)
    return False


def approved_leave_absences(store_id: int) -> list[dict[str, str]]:
    approved: list[dict[str, str]] = []
    for request in list_leave_requests(store_id):
        if request["status"] != "approved":
            continue
        current = date.fromisoformat(request["start_date"])
        end = date.fromisoformat(request["end_date"])
        while current <= end:
            approved.append({"date": current.isoformat(), "employee": request["employee_name"], "reason": f"請假核准：{request['reason']}"})
            current += timedelta(days=1)
    return approved


def simulated_employees() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"姓名": "模擬・周怡安", "可上班日": "一,二,三,四,五", "可上班班別": "早班,中班", "期望休假": "六,日"},
            {"姓名": "模擬・許承恩", "可上班日": "一,二,三,四,六", "可上班班別": "中班,晚班", "期望休假": "五"},
            {"姓名": "模擬・黃詠晴", "可上班日": "二,三,四,五,六,日", "可上班班別": "早班,晚班", "期望休假": "一"},
            {"姓名": "模擬・高宇辰", "可上班日": "一,三,四,五,六,日", "可上班班別": "早班,中班,晚班", "期望休假": "二"},
            {"姓名": "模擬・林品妤", "可上班日": "一,二,五,六,日", "可上班班別": "早班,晚班", "期望休假": "三,四"},
            {"姓名": "模擬・吳柏勳", "可上班日": "一,二,三,四,五,六", "可上班班別": "中班,晚班", "期望休假": "日"},
            {"姓名": "模擬・蔡佳玲", "可上班日": "二,三,四,五,六", "可上班班別": "早班,中班", "期望休假": "一,日"},
            {"姓名": "模擬・鄭凱文", "可上班日": "一,三,五,六,日", "可上班班別": "晚班", "期望休假": "二,四"},
        ]
    )


def switch_store(store_id: int) -> None:
    st.session_state.store_id = store_id
    st.session_state.employees = load_employees(store_id)
    st.session_state.schedule, st.session_state.gaps = load_latest_schedule(store_id, (date.today() - timedelta(days=date.today().weekday())).isoformat())
    st.session_state.pending_schedule = pd.DataFrame()
    st.session_state.absences = []
    st.session_state.peak_demand = {}


def render_store_switcher(user: dict[str, object]) -> None:
    stores = list_stores()
    current_store = next((store for store in stores if store["id"] == st.session_state.store_id), stores[0])
    if user["role"] in {"admin", "manager"}:
        with st.sidebar.expander("分店工作區", expanded=True, icon=":material/store:"):
            store_names = [store["name"] for store in stores]
            selected_name = st.selectbox("目前分店", store_names, index=store_names.index(current_store["name"]), key="active_store_name")
            selected_store = next(store for store in stores if store["name"] == selected_name)
            if selected_store["id"] != st.session_state.store_id:
                switch_store(selected_store["id"])
                user["store_id"] = selected_store["id"]
                st.rerun()
            new_store_name = st.text_input("新增分店", placeholder="例如：信義門市", key="new_store_name")
            if st.button("新增分店", key="create_store", width="stretch") and new_store_name.strip():
                try:
                    new_store_id = create_store(new_store_name)
                except ValueError:
                    st.error("分店名稱不可為空。")
                except Exception:
                    st.error("分店名稱已存在，請換一個名稱。")
                else:
                    switch_store(new_store_id)
                    user["store_id"] = new_store_id
                    st.rerun()
    else:
        st.sidebar.caption(f"目前分店：{current_store['name']}")


def render_leave_workflow(user: dict[str, object]) -> None:
    requests = list_leave_requests(int(user["store_id"]))
    employees = [str(name) for name in st.session_state.employees["姓名"].fillna("") if str(name).strip()]
    st.markdown('<div class="section-title">請假與審核中心</div>', unsafe_allow_html=True)
    if user["role"] == "staff":
        with st.form("leave_request_form", border=True):
            st.caption("提交後由店長或管理者審核，核准後會自動避開排班。")
            if not employees:
                st.warning("目前沒有可申請的員工資料。")
                return
            employee_name = employees[0]
            st.text_input("申請員工", value=employee_name, disabled=True)
            start_date = st.date_input("開始日期", value=date.today())
            end_date = st.date_input("結束日期", value=date.today())
            reason = st.text_input("請假原因", placeholder="例如：家庭因素、身體不適")
            if st.form_submit_button("送出請假申請", type="primary", width="stretch"):
                if end_date < start_date:
                    st.error("結束日期不能早於開始日期。")
                elif not reason.strip():
                    st.error("請填寫請假原因。")
                else:
                    create_leave_request(int(user["store_id"]), str(user["username"]), employee_name, start_date.isoformat(), end_date.isoformat(), reason.strip())
                    st.success("請假申請已送出，等待主管審核。")
                    st.rerun()
    visible = requests if user["role"] in {"admin", "manager"} else [item for item in requests if item["requester"] == user["username"]]
    if not visible:
        st.caption("目前沒有請假申請紀錄。")
        return
    for request in visible:
        status_label = {"pending": "待審核", "approved": "已核准", "rejected": "已拒絕"}.get(request["status"], request["status"])
        st.markdown(f"**{escape(request['employee_name'])}** · {escape(request['start_date'])} 至 {escape(request['end_date'])} · {status_label}  \\n原因：{escape(request['reason'])}")
        if user["role"] in {"admin", "manager"} and request["status"] == "pending":
            approve_col, reject_col = st.columns(2)
            if approve_col.button("核准", key=f"approve_leave_{request['id']}", type="primary", width="stretch"):
                review_leave_request(request["id"], str(user["username"]), "approved")
                st.rerun()
            if reject_col.button("拒絕", key=f"reject_leave_{request['id']}", width="stretch"):
                review_leave_request(request["id"], str(user["username"]), "rejected")
                st.rerun()

    st.markdown('<div class="section-title">換班申請</div>', unsafe_allow_html=True)
    swap_requests = list_swap_requests(int(user["store_id"]))
    if user["role"] == "staff" and employees:
        with st.form("swap_request_form", border=True):
            from_employee = employees[0]
            st.text_input("原員工", value=from_employee, disabled=True)
            to_options = [employee for employee in employees if employee != from_employee]
            to_employee = st.selectbox("希望換班員工", to_options or employees)
            shift_date = st.date_input("班次日期", value=date.today(), key="swap_date")
            shift_name = st.text_input("班別", value="早班", key="swap_shift")
            swap_reason = st.text_input("換班原因", placeholder="例如：家庭行程", key="swap_reason")
            if st.form_submit_button("送出換班申請", width="stretch"):
                if not swap_reason.strip():
                    st.error("請填寫換班原因。")
                else:
                    create_swap_request(int(user["store_id"]), str(user["username"]), from_employee, to_employee, shift_date.isoformat(), shift_name, swap_reason.strip())
                    st.success("換班申請已送出。")
                    st.rerun()
    visible_swaps = swap_requests if user["role"] in {"admin", "manager"} else [item for item in swap_requests if item["requester"] == user["username"]]
    for request in visible_swaps:
        status_label = {"pending": "待審核", "approved": "已核准", "rejected": "已拒絕"}.get(request["status"], request["status"])
        st.markdown(f"**{escape(request['shift_date'])} {escape(request['shift_name'])}** · {escape(request['from_employee'])} → {escape(request['to_employee'])} · {status_label}  \\n原因：{escape(request['reason'])}")
        if user["role"] in {"admin", "manager"} and request["status"] == "pending":
            approve_col, reject_col = st.columns(2)
            if approve_col.button("核准換班", key=f"approve_swap_{request['id']}", type="primary", width="stretch"):
                review_swap_request(request["id"], str(user["username"]), "approved")
                st.rerun()
            if reject_col.button("拒絕換班", key=f"reject_swap_{request['id']}", width="stretch"):
                review_swap_request(request["id"], str(user["username"]), "rejected")
                st.rerun()


def token_set(value: object, mapping: dict[str, str] | None = None) -> set[str]:
    values = {item.strip() for item in str(value).replace("，", ",").split(",") if item.strip()}
    return {mapping.get(item, item) if mapping else item for item in values}


def export_excel(schedule: pd.DataFrame, gaps: list[dict[str, str]]) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        schedule.to_excel(writer, index=False, sheet_name="排班表")
        pd.DataFrame(gaps).to_excel(writer, index=False, sheet_name="未滿足需求")
    return output.getvalue()


def shift_badge(shift: object) -> str:
    shift_name = escape(str(shift))
    shift_class = {"早班": "shift-early", "中班": "shift-mid", "晚班": "shift-late"}.get(str(shift), "badge-neutral")
    return f'<span class="shift-badge {shift_class}">{shift_name}</span>'


def render_kpi_banner(employee_count: int, schedule: pd.DataFrame, gaps: list[dict[str, str]], max_hours: float, week_dates: list[date], peak_slots: int) -> None:
    total_slots = len(schedule) + len(gaps)
    coverage = len(schedule) / total_slots if total_slots else 0
    compliance_alerts = 0
    if not schedule.empty:
        over_limit = schedule.groupby("employee")["hours"].sum() > max_hours
        compliance_alerts = int(over_limit.sum())
    compliance_label = "需關注" if compliance_alerts else "全部合規"
    compliance_detail = f"{compliance_alerts} 位員工超過上限" if compliance_alerts else "目前沒有超時警示"
    st.markdown(
        f"""
        <div class="kpi-grid">
          <div class="kpi-card kpi-blue"><div class="kpi-label">當前在職員工</div><div class="kpi-value">{employee_count}</div><div class="kpi-detail">已加入本週排班名單</div></div>
          <div class="kpi-card kpi-violet"><div class="kpi-label">本週排班覆蓋率</div><div class="kpi-value">{coverage:.0%}</div><div class="kpi-detail">{len(schedule)} / {total_slots or 0} 個需求槽位</div></div>
          <div class="kpi-card kpi-blue"><div class="kpi-label">尖峰加派需求</div><div class="kpi-value">{peak_slots}</div><div class="kpi-detail">本週額外人力槽位</div></div>
          <div class="kpi-card kpi-orange"><div class="kpi-label">工時合規警示</div><div class="kpi-value">{compliance_label}</div><div class="kpi-detail">{compliance_detail}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard_overview(schedule: pd.DataFrame, gaps: list[dict[str, str]], week_dates: list[date], peak_demand: dict[str, dict[str, int]], absences: list[dict[str, str]]) -> None:
    demand_by_date = {current.isoformat(): 0 for current in week_dates}
    for day_key, shifts in peak_demand.items():
        demand_by_date[day_key] = sum(shifts.values())
    assigned_by_date = schedule.groupby("date").size().to_dict() if not schedule.empty else {}
    max_load = max([max(assigned_by_date.get(day, 0), demand_by_date.get(day, 0)) for day in demand_by_date] or [1])
    bars = []
    for current in week_dates:
        key = current.isoformat()
        assigned = int(assigned_by_date.get(key, 0))
        peak = int(demand_by_date.get(key, 0))
        height = max(assigned, peak) / max_load * 100 if max_load else 0
        bars.append(f'<div class="load-day"><strong>{assigned}</strong><div class="load-bar-track"><div class="load-bar" style="height:{max(height, 4):.0f}%"></div></div><label>{DAY_LABELS[DAY_KEYS[current.weekday()]]}</label></div>')
    if gaps:
        alert_text = f"目前有 {len(gaps)} 個需求槽位尚未補足，建議調高可用工時或加入備援員工。"
    elif absences:
        alert_text = f"已避開 {len(absences)} 筆臨時請假，請確認備援人力是否符合現場經驗需求。"
    else:
        alert_text = "目前沒有未滿足需求或臨時事件，班表狀態良好。"
    st.markdown(
        f'<div class="load-panel"><div class="load-title">本週人力負載 <span>已配置班次／尖峰加派</span></div><div class="load-chart">{"".join(bars)}</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="alert-panel"><strong>營運提醒</strong><span>{escape(alert_text)}</span></div>', unsafe_allow_html=True)


def render_health_panel(schedule: pd.DataFrame, gaps: list[dict[str, str]], max_hours: float, absences: list[dict[str, str]], violations: list[dict[str, str]]) -> None:
    overtime_count = 0
    if not schedule.empty:
        overtime_count = int((schedule.groupby("employee")["hours"].sum() > max_hours).sum())
    absence_conflicts = 0
    if not schedule.empty and absences:
        absent_pairs = {(item["date"], item["employee"]) for item in absences}
        absence_conflicts = sum((row["date"], row["employee"]) in absent_pairs for _, row in schedule.iterrows())
    checks = [
        ("需求覆蓋", "正常" if not gaps else f"{len(gaps)} 個缺口", not gaps),
        ("工時限制", "正常" if not overtime_count else f"{overtime_count} 人超時", not overtime_count),
        ("請假衝突", "無衝突" if not absence_conflicts else f"{absence_conflicts} 筆衝突", not absence_conflicts),
        ("休息間隔", "正常" if not violations else f"{len(violations)} 項警示", not violations),
        ("班表狀態", "已產生" if not schedule.empty else "待產生", not schedule.empty),
    ]
    items = "".join(f'<div class="health-item {"health-ok" if ok else "health-warn"}"><strong>{escape(label)} · {escape(status)}</strong><span>{"可直接執行" if ok else "建議立即處理"}</span></div>' for label, status, ok in checks)
    st.markdown(f'<div class="health-panel"><div class="health-title">排班健康檢查</div><div class="health-grid">{items}</div></div>', unsafe_allow_html=True)


def render_employee_cards(employees: pd.DataFrame, search: str = "", shift_filter: str = "全部班別", can_manage: bool = True) -> None:
    updated_employees = employees.copy()
    badge_class = {"早班": "badge-early", "中班": "badge-mid", "晚班": "badge-late"}
    visible_employees = employees.fillna("")
    if search.strip():
        visible_employees = visible_employees[visible_employees["姓名"].astype(str).str.contains(search.strip(), case=False, na=False)]
    if shift_filter != "全部班別":
        visible_employees = visible_employees[visible_employees["可上班班別"].astype(str).str.contains(shift_filter, regex=False, na=False)]
    if visible_employees.empty:
        st.markdown('<div class="empty-state">找不到符合條件的團隊成員。</div>', unsafe_allow_html=True)
    for index, row in visible_employees.iterrows():
        name = escape(str(row.get("姓名", "未命名員工")))
        shifts = [item.strip() for item in str(row.get("可上班班別", "")).replace("，", ",").split(",") if item.strip()]
        badges = "".join(f'<span class="badge {badge_class.get(item, "badge-neutral")}">{escape(item)}</span>' for item in shifts)
        days = [item.strip() for item in str(row.get("可上班日", "")).replace("，", ",").split(",") if item.strip()]
        day_badges = "".join(f'<span class="day-pill">{escape(item)}</span>' for item in days) or '<span class="day-pill">未設定可上班日</span>'
        days_off = escape(str(row.get("期望休假", "未設定")))
        initials = escape(str(row.get("姓名", "?"))[:1] or "?")
        card_col, action_col = st.columns([5, 1], vertical_alignment="center")
        with card_col:
            st.markdown(
                f'<div class="employee-card"><div class="employee-card-head"><div><span class="employee-avatar">{initials}</span><span class="employee-name">{name}</span></div></div><div>{badges or "<span class=\"badge badge-neutral\">尚未設定班別</span>"}</div><div class="employee-card-meta"><span>可上班</span>{day_badges}<span>偏好休假：{days_off}</span></div></div>',
                unsafe_allow_html=True,
            )
        if can_manage:
            with action_col:
                if st.button("編輯", key=f"edit_employee_{index}", width="stretch"):
                    st.session_state.employee_edit_index = int(index)
                if st.button("刪除", key=f"delete_employee_{index}", width="stretch"):
                    st.session_state.employees = employees.drop(index).reset_index(drop=True)
                    st.session_state.employee_edit_index = None
                    st.session_state.pending_schedule = pd.DataFrame()
                    st.session_state.schedule = pd.DataFrame()
                    st.session_state.gaps = []
                    st.rerun()

        if can_manage and st.session_state.get("employee_edit_index") == index:
            with st.form(f"employee_form_{index}", border=True):
                st.markdown(f"**編輯 {name}**")
                edit_name = st.text_input("姓名", value=str(row.get("姓名", "")), key=f"employee_name_{index}")
                edit_days = st.text_input("可上班日", value=str(row.get("可上班日", "")), key=f"employee_days_{index}")
                edit_shifts = st.text_input("可上班班別", value=str(row.get("可上班班別", "")), key=f"employee_shifts_{index}")
                edit_days_off = st.text_input("期望休假", value=str(row.get("期望休假", "")), key=f"employee_days_off_{index}")
                save_col, cancel_col = st.columns(2)
                if save_col.form_submit_button("儲存", type="primary", width="stretch"):
                    updated_employees.loc[index, ["姓名", "可上班日", "可上班班別", "期望休假"]] = [edit_name, edit_days, edit_shifts, edit_days_off]
                    st.session_state.employees = updated_employees
                    st.session_state.employee_edit_index = None
                    st.session_state.pending_schedule = pd.DataFrame()
                    st.session_state.schedule = pd.DataFrame()
                    st.session_state.gaps = []
                    st.rerun()
                if cancel_col.form_submit_button("取消", width="stretch"):
                    st.session_state.employee_edit_index = None
                    st.rerun()

    if can_manage:
        with st.container(border=True):
            st.markdown("**新增團隊成員**")
            add_col, add_action, demo_action = st.columns([4, 1, 2], vertical_alignment="bottom")
            add_name = add_col.text_input("姓名", placeholder="例如：趙怡安", key="new_employee_name", label_visibility="collapsed")
            if add_action.button("新增", key="add_employee", type="primary", width="stretch") and add_name.strip():
                st.session_state.employees = pd.concat([employees, pd.DataFrame([{"姓名": add_name.strip(), "可上班日": "一,二,三,四,五", "可上班班別": "早班", "期望休假": "六,日"}])], ignore_index=True)
                st.session_state.pending_schedule = pd.DataFrame()
                st.session_state.schedule = pd.DataFrame()
                st.session_state.gaps = []
                st.rerun()
            if demo_action.button("載入模擬團隊", key="add_demo_employees", width="stretch"):
                existing_names = set(employees["姓名"].astype(str))
                demo_rows = simulated_employees()
                demo_rows = demo_rows[~demo_rows["姓名"].isin(existing_names)]
                if demo_rows.empty:
                    st.info("模擬團隊已經載入目前分店。")
                else:
                    st.session_state.employees = pd.concat([employees, demo_rows], ignore_index=True)
                    st.session_state.pending_schedule = pd.DataFrame()
                    st.session_state.schedule = pd.DataFrame()
                    st.session_state.gaps = []
                    st.rerun()
        save_employees(st.session_state.store_id, st.session_state.employees)


def render_schedule_table(schedule: pd.DataFrame) -> None:
    rows = []
    for _, row in schedule.iterrows():
        rows.append(
            f"<tr><td>{escape(str(row['day']))}<br><span class='kpi-detail'>{escape(str(row['date']))}</span></td>"
            f"<td class='person'>{escape(str(row['employee']))}</td><td>{shift_badge(row['shift'])}</td>"
            f"<td>{escape(str(row['time']))}</td><td>{float(row['hours']):.1f} 小時</td></tr>"
        )
    st.markdown(
        '<table class="schedule-table"><thead><tr><th>日期</th><th>員工</th><th>班別</th><th>時段</th><th>工時</th></tr></thead><tbody>'
        + "".join(rows)
        + "</tbody></table>",
        unsafe_allow_html=True,
    )


def schedule_to_calendar_events(schedule: pd.DataFrame) -> list[dict[str, object]]:
    """Convert the internal schedule table to FullCalendar events."""
    shift_colors = {
        "早班": ("#3b82f6", "#2563eb"),
        "中班": ("#f97316", "#ea580c"),
        "晚班": ("#8b5cf6", "#7c3aed"),
    }
    events: list[dict[str, object]] = []
    for index, row in schedule.iterrows():
        start_time, end_time = str(row["time"]).split(" - ", maxsplit=1)
        background_color, border_color = shift_colors.get(str(row["shift"]), ("#22b8a6", "#0f766e"))
        events.append(
            {
                "id": f"shift-{index}",
                "title": f"{row['employee']} - {row['shift']}",
                "start": f"{row['date']}T{start_time}:00",
                "end": f"{row['date']}T{end_time}:00",
                "backgroundColor": background_color,
                "borderColor": border_color,
                "textColor": "#ffffff",
            }
        )
    return events


def extract_updated_events(state: object) -> list[dict[str, object]]:
    """Read event payloads returned by streamlit-calendar across component versions."""
    if not isinstance(state, dict):
        return []
    candidates: list[object] = []
    for key in ("events", "eventChange", "eventDrop", "eventResize", "eventsSet"):
        if key in state:
            candidates.append(state[key])

    updated: list[dict[str, object]] = []

    def collect(value: object) -> None:
        if isinstance(value, list):
            for item in value:
                collect(item)
        elif isinstance(value, dict):
            if value.get("start") and value.get("end"):
                updated.append(value)
            elif isinstance(value.get("event"), dict):
                collect(value["event"])

    for candidate in candidates:
        collect(candidate)
    return updated


def apply_calendar_updates(schedule: pd.DataFrame, updated_events: list[dict[str, object]]) -> pd.DataFrame:
    """Apply FullCalendar drag/resize results to a copy of the schedule table."""
    updated_schedule = schedule.copy()
    for event in updated_events:
        event_id = str(event.get("id", ""))
        if not event_id.startswith("shift-"):
            continue
        try:
            row_index = int(event_id.removeprefix("shift-"))
            start = pd.to_datetime(event["start"])
            end = pd.to_datetime(event["end"])
        except (TypeError, ValueError, KeyError):
            continue
        if row_index not in updated_schedule.index:
            continue
        updated_schedule.at[row_index, "date"] = start.strftime("%Y-%m-%d")
        updated_schedule.at[row_index, "time"] = f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"
        updated_schedule.at[row_index, "hours"] = round((end - start).total_seconds() / 3600, 2)
    return updated_schedule


def render_calendar(schedule: pd.DataFrame, editable: bool = True) -> pd.DataFrame | None:
    events = schedule_to_calendar_events(schedule)
    calendar_options = {
        "editable": editable,
        "selectable": editable,
        "initialView": "timeGridWeek",
        "initialDate": str(schedule["date"].min()),
        "locale": "zh-tw",
        "allDaySlot": False,
        "slotMinTime": "06:00:00",
        "slotMaxTime": "24:00:00",
        "slotDuration": "00:30:00",
        "height": 700,
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "timeGridWeek,dayGridMonth"},
    }
    custom_css = """
    .fc { --fc-border-color: #e4e7ec; --fc-page-bg-color: #ffffff; --fc-neutral-bg-color: #f8fafc; --fc-list-event-hover-bg-color: #f2f4f7; --fc-today-bg-color: rgba(37, 99, 235, .07); color: #172033; font-family: 'DM Sans', 'Noto Sans TC', sans-serif; }
    .fc .fc-scrollgrid, .fc-theme-standard td, .fc-theme-standard th { border-color: #e4e7ec; }
    .fc .fc-button-primary { background: #ffffff; border-color: #d0d5dd; color: #475467; box-shadow: 0 1px 2px rgba(16,24,40,.05); }
    .fc .fc-button-primary:hover, .fc .fc-button-primary.fc-button-active { background: #2563eb; border-color: #2563eb; color: #ffffff; }
    .fc .fc-col-header-cell-cushion, .fc .fc-timegrid-axis-cushion, .fc .fc-daygrid-day-number { color: #667085; }
    .fc .fc-timegrid-slot-label { color: #98a2b3; }
    .fc-event { cursor: grab; border-radius: 5px; padding: 2px 4px; box-shadow: 0 2px 8px rgba(16,24,40,.15); }
    .fc-event:active { cursor: grabbing; }
    """
    with st.container(border=True):
        st.markdown('<div class="calendar-note">拖曳班次可調整日期與時間，儲存後會同步至匯出班表。</div>', unsafe_allow_html=True)
        state = calendar(events=events, options=calendar_options, custom_css=custom_css, key="shift-calendar")
    updated_events = extract_updated_events(state)
    if updated_events:
        updated_schedule = apply_calendar_updates(schedule, updated_events)
        if updated_schedule.equals(schedule):
            return None
        st.markdown("#### 已更新的班次時間")
        updated_rows = []
        for _, row in updated_schedule.iterrows():
            updated_rows.append(
                {
                    "班次": f"{row['employee']} - {row['shift']}",
                    "開始": f"{row['date']} {row['time'].split(' - ')[0]}",
                    "結束": f"{row['date']} {row['time'].split(' - ')[1]}",
                }
            )
        updated_html = "".join(f"<tr><td>{escape(str(row['班次']))}</td><td>{escape(str(row['開始']))}</td><td>{escape(str(row['結束']))}</td></tr>" for row in updated_rows)
        st.markdown(f'<table class="schedule-table"><thead><tr><th>班次</th><th>開始</th><th>結束</th></tr></thead><tbody>{updated_html}</tbody></table>', unsafe_allow_html=True)
        st.caption("拖曳結果已暫存，請按下「儲存拖曳結果」後更新班表與匯出內容。")
        return updated_schedule
    return None


def render_sidebar(can_manage: bool = True) -> tuple[list[Shift], dict[str, dict[str, int]], float, int, date, list[dict[str, str]]]:
    st.sidebar.markdown('<div class="eyebrow">SHIFTWISE / CONTROL</div>', unsafe_allow_html=True)
    st.sidebar.title("排班設定")
    if st.sidebar.button("登出", key="logout", width="stretch"):
        st.session_state.pop("user", None)
        st.rerun()
    with st.sidebar.container(border=True):
        st.markdown("**本週規則**")
        start_date = st.date_input("排班週起始日", value=date.today() - timedelta(days=date.today().weekday()), disabled=not can_manage)
        max_hours = st.number_input("每週最高工時", min_value=1.0, max_value=168.0, value=40.0, step=1.0, disabled=not can_manage)
        max_consecutive = st.number_input("最多連續上班天數", min_value=1, max_value=7, value=6, step=1, disabled=not can_manage)
    with st.sidebar.expander("班別定義", expanded=True, icon=":material/schedule:"):
        for index, shift in enumerate(st.session_state.shifts):
            with st.container():
                st.markdown(f'<div class="shift-setting"><strong>{escape(str(shift.get("班別", "班別")))}</strong></div>', unsafe_allow_html=True)
                name_col, start_col, end_col, hours_col = st.columns([1.3, 1, 1, .75])
                shift["班別"] = name_col.text_input("名稱", value=str(shift.get("班別", "")), key=f"shift_name_{index}", label_visibility="collapsed", disabled=not can_manage)
                shift["開始"] = start_col.text_input("開始", value=str(shift.get("開始", "09:00")), key=f"shift_start_{index}", label_visibility="collapsed", disabled=not can_manage)
                shift["結束"] = end_col.text_input("結束", value=str(shift.get("結束", "17:00")), key=f"shift_end_{index}", label_visibility="collapsed", disabled=not can_manage)
                shift["工時"] = hours_col.number_input("工時", min_value=0.5, max_value=24.0, value=float(shift.get("工時", 8)), step=0.5, key=f"shift_hours_{index}", label_visibility="collapsed", disabled=not can_manage)
                if can_manage and st.button("移除班別", key=f"delete_shift_{index}", width="stretch"):
                    st.session_state.shifts.pop(index)
                    st.rerun()
        if can_manage and st.button("＋ 新增班別", key="add_shift", width="stretch"):
            st.session_state.shifts.append({"班別": "新班別", "開始": "09:00", "結束": "17:00", "工時": 8.0})
            st.rerun()
    shifts = []
    for row in st.session_state.shifts:
        if str(row.get("班別", "")).strip():
            shifts.append(Shift(str(row["班別"]), str(row.get("開始", "09:00")), str(row.get("結束", "17:00")), float(row.get("工時", 8))))
    demand: dict[str, dict[str, int]] = {}
    peak_demand: dict[str, dict[str, int]] = {}
    with st.sidebar.expander("每日需求人數", expanded=False, icon=":material/groups:"):
        st.markdown('<div class="peak-hint">尖峰加派會疊加到基本需求，適合處理午餐、晚餐或活動時段的人力波峰。</div>', unsafe_allow_html=True)
        for current_date in build_week(start_date):
            key = current_date.isoformat()
            with st.expander(f"{DAY_LABELS[DAY_KEYS[current_date.weekday()]]} · {current_date.strftime('%m/%d')}"):
                demand[key] = {}
                peak_demand[key] = {}
                for shift in shifts:
                    base = int(st.number_input(f"{shift.name} 基本需求", min_value=0, max_value=50, value=1, key=f"need_{key}_{shift.name}", disabled=not can_manage))
                    peak_extra = int(st.number_input(f"{shift.name} 尖峰加派", min_value=0, max_value=20, value=0, key=f"peak_{key}_{shift.name}", disabled=not can_manage))
                    demand[key][shift.name] = base + peak_extra
                    peak_demand[key][shift.name] = peak_extra
    st.session_state.peak_demand = peak_demand

    with st.sidebar.expander("臨時請假／突發狀況", expanded=False, icon=":material/notification_important:"):
        employee_names = [str(name) for name in st.session_state.employees["姓名"].fillna("") if str(name).strip()]
        if employee_names:
            absence_date = st.date_input("請假日期", value=start_date, key="absence_date", disabled=not can_manage)
            absence_employee = st.selectbox("請假員工", employee_names, key="absence_employee", disabled=not can_manage)
            absence_reason = st.text_input("原因（選填）", placeholder="例如：臨時病假", key="absence_reason", disabled=not can_manage)
            if can_manage and st.button("加入臨時請假", key="add_absence", width="stretch"):
                record = {"date": absence_date.isoformat(), "employee": absence_employee, "reason": absence_reason.strip() or "臨時請假"}
                if not any(item["date"] == record["date"] and item["employee"] == record["employee"] for item in st.session_state.absences):
                    st.session_state.absences.append(record)
                    st.session_state.pending_schedule = pd.DataFrame()
                    st.session_state.schedule = pd.DataFrame()
                    st.session_state.gaps = []
                    st.rerun()
            for index, absence in enumerate(st.session_state.absences):
                st.markdown(f'<div class="incident-card"><strong>{escape(absence["date"])} · {escape(absence["employee"])}</strong><br>{escape(absence["reason"])}</div>', unsafe_allow_html=True)
                if can_manage and st.button("移除", key=f"remove_absence_{index}", width="stretch"):
                    st.session_state.absences.pop(index)
                    st.session_state.pending_schedule = pd.DataFrame()
                    st.session_state.schedule = pd.DataFrame()
                    st.session_state.gaps = []
                    st.rerun()
        else:
            st.caption("請先新增員工，才能建立臨時請假紀錄。")
    return shifts, demand, max_hours, int(max_consecutive), start_date, st.session_state.absences


def main() -> None:
    defaults()
    if not render_login():
        return
    current_user = st.session_state.user
    can_manage = current_user["role"] in {"admin", "manager"}
    render_store_switcher(current_user)
    shifts, demand, max_hours, max_consecutive, start_date, absences = render_sidebar(can_manage)
    absences = absences + approved_leave_absences(int(current_user["store_id"]))
    week_dates = build_week(start_date)

    period_label = f"{week_dates[0].strftime('%m/%d')} - {week_dates[-1].strftime('%m/%d')}"
    st.markdown(f'<div class="app-topbar"><div class="brand-lockup"><div class="brand-mark">S</div><div><div class="brand-name">Shiftwise</div><div class="brand-caption">Service operations control center</div></div></div><div><span class="status-pill"><span class="status-dot"></span>系統運作正常</span><div class="brand-caption" style="text-align:right;margin-top:.35rem">{escape(current_user["username"])} · {escape(current_user["role"])} · 本週 {period_label}</div></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">SERVICE OPERATIONS / WEEKLY PLANNER</div>', unsafe_allow_html=True)
    st.title("智慧自動排班")
    st.markdown('<div class="subtitle">把人力需求、員工偏好與營運規則，整理成一張可直接執行的班表。</div>', unsafe_allow_html=True)
    kpi_slot = st.empty()
    tabs = st.tabs(["總覽", "團隊成員", "自動排班", "匯出班表"])

    with tabs[0]:
        st.markdown('<div class="section-title">營運總覽</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-meta">掌握本週人力配置、尖峰負載與需要主管介入的事件。</div>', unsafe_allow_html=True)
        overview_left, overview_right = st.columns([2.1, 1], gap="medium")
        with overview_left:
            render_dashboard_overview(st.session_state.schedule, st.session_state.gaps, week_dates, st.session_state.peak_demand, absences)
        with overview_right:
            next_action = "先產生本週班表" if st.session_state.schedule.empty else "檢查尖峰與缺口"
            st.markdown(f'<div class="panel-card"><div class="section-title" style="margin-top:0">下一步建議</div><div class="kpi-detail">{next_action}</div><div style="margin-top:.75rem;color:#475467;font-size:.82rem;line-height:1.6">從左側設定需求與突發狀況，再到「自動排班」執行並檢查結果。</div></div>', unsafe_allow_html=True)
        current_schedule = st.session_state.pending_schedule if not st.session_state.pending_schedule.empty else st.session_state.schedule
        render_health_panel(current_schedule, st.session_state.gaps, max_hours, absences, audit_schedule(current_schedule, max_hours))
        render_leave_workflow(current_user)

    with tabs[1]:
        st.markdown('<div class="section-title">團隊成員</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-meta">編輯人員資料後，下面的卡片會即時更新可排班班別與休假偏好。</div>', unsafe_allow_html=True)
        employee_search, employee_shift_filter = st.columns([2, 1])
        search_value = employee_search.text_input("搜尋員工", placeholder="輸入姓名", key="employee_search")
        shift_value = employee_shift_filter.selectbox("班別篩選", ["全部班別"] + [shift.name for shift in shifts], key="employee_shift_filter")
        render_employee_cards(st.session_state.employees, search_value, shift_value, can_manage)

    with tabs[2]:
        top_left, top_right = st.columns([3, 1])
        with top_left:
            st.markdown('<div class="section-title">本週排班週曆</div>', unsafe_allow_html=True)
            peak_slots = sum(sum(day.values()) for day in st.session_state.peak_demand.values())
            incident_text = f"目前有 {len(absences)} 筆臨時請假" if absences else "目前沒有臨時請假"
            st.caption(f"尖峰加派 {peak_slots} 個需求槽位 · {incident_text} · 演算法會自動找備援人力。")
        with top_right:
            run_schedule = st.button("✦  一鍵自動排班", type="primary", width="stretch", disabled=not can_manage)
        if run_schedule:
            employees = []
            day_mapping = {label: key for key, label in {"Mon": "一", "Tue": "二", "Wed": "三", "Thu": "四", "Fri": "五", "Sat": "六", "Sun": "日"}.items()}
            valid_shift_names = {shift.name for shift in shifts}
            for _, row in st.session_state.employees.fillna("").iterrows():
                name = str(row.get("姓名", "")).strip()
                available_shifts = token_set(row.get("可上班班別", "")) & valid_shift_names
                if name and available_shifts:
                    employees.append(Employee(name, token_set(row.get("可上班日", ""), day_mapping), available_shifts, token_set(row.get("期望休假", ""), day_mapping)))
            absence_map: dict[str, set[str]] = {}
            for absence in absences:
                absence_map.setdefault(absence["date"], set()).add(absence["employee"])
            st.session_state.schedule, st.session_state.gaps = generate_schedule(
                employees,
                shifts,
                week_dates,
                demand,
                max_hours,
                max_consecutive,
                absence_map,
            )
            save_schedule(st.session_state.store_id, week_dates[0].isoformat(), st.session_state.schedule, st.session_state.gaps)
            st.session_state.pending_schedule = pd.DataFrame()
        schedule = st.session_state.pending_schedule if not st.session_state.pending_schedule.empty else st.session_state.schedule
        if schedule.empty:
            st.markdown('<div class="empty-state">尚未產生班表<br><small>完成左側設定後，按下右上角的自動排班</small></div>', unsafe_allow_html=True)
        else:
            filter_employee, filter_shift = st.columns(2)
            employee_options = ["全部員工"] + sorted(schedule["employee"].dropna().unique().tolist())
            shift_options = ["全部班別"] + sorted(schedule["shift"].dropna().unique().tolist())
            selected_employee = filter_employee.selectbox("檢視員工", employee_options, key="schedule_employee_filter")
            selected_shift = filter_shift.selectbox("檢視班別", shift_options, key="schedule_shift_filter")
            calendar_schedule = render_calendar(schedule, editable=can_manage)
            if calendar_schedule is not None and not calendar_schedule.equals(schedule):
                st.session_state.pending_schedule = calendar_schedule
                schedule = calendar_schedule
            if can_manage and not st.session_state.pending_schedule.empty:
                if st.button("儲存拖曳結果", type="primary", key="save-calendar-changes"):
                    st.session_state.schedule = st.session_state.pending_schedule.copy()
                    st.session_state.pending_schedule = pd.DataFrame()
                    save_schedule(st.session_state.store_id, week_dates[0].isoformat(), st.session_state.schedule, st.session_state.gaps)
                    schedule = st.session_state.schedule
                    st.success("拖曳後的班表時間已儲存，匯出內容也已同步更新。")
            visible_schedule = schedule
            if selected_employee != "全部員工":
                visible_schedule = visible_schedule[visible_schedule["employee"] == selected_employee]
            if selected_shift != "全部班別":
                visible_schedule = visible_schedule[visible_schedule["shift"] == selected_shift]
            st.caption(f"目前顯示 {len(visible_schedule)} / {len(schedule)} 個班次；日曆仍保留完整班表，方便拖曳調整。")
            if visible_schedule.empty:
                st.markdown('<div class="empty-state">目前篩選條件沒有班次。</div>', unsafe_allow_html=True)
            else:
                render_schedule_table(visible_schedule)
            if st.session_state.gaps:
                with st.expander("查看未滿足需求", icon=":material/warning:"):
                    gap_rows = "".join(f"<tr><td>{escape(str(item['day']))} {escape(str(item['date']))}</td><td>{escape(str(item['shift']))}</td><td>{escape(str(item['reason']))}</td></tr>" for item in st.session_state.gaps)
                    st.markdown(f'<table class="schedule-table"><thead><tr><th>日期</th><th>班別</th><th>原因</th></tr></thead><tbody>{gap_rows}</tbody></table>', unsafe_allow_html=True)

    kpi_schedule = st.session_state.pending_schedule if not st.session_state.pending_schedule.empty else st.session_state.schedule
    with kpi_slot.container():
        peak_slots = sum(sum(day.values()) for day in st.session_state.peak_demand.values())
        render_kpi_banner(len(st.session_state.employees), kpi_schedule, st.session_state.gaps, max_hours, week_dates, peak_slots)
        if not st.session_state.pending_schedule.empty:
            st.caption("有尚未儲存的拖曳變更，請回到「自動排班」分頁確認並儲存。")

    with tabs[3]:
        st.markdown('<div class="section-title">下載與分享</div>', unsafe_allow_html=True)
        if st.session_state.schedule.empty:
            st.markdown('<div class="empty-state">請先在「自動排班」分頁產生班表。</div>', unsafe_allow_html=True)
        else:
            st.write("排班結果已準備完成，可下載給現場主管或匯入既有流程。")
            csv_data = st.session_state.schedule.to_csv(index=False).encode("utf-8-sig")
            col1, col2 = st.columns(2)
            col1.download_button("下載 CSV", csv_data, "shiftwise_schedule.csv", "text/csv", width="stretch")
            col2.download_button("下載 Excel", export_excel(st.session_state.schedule, st.session_state.gaps), "shiftwise_schedule.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")


if __name__ == "__main__":
    main()
