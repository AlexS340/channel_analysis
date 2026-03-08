"""
Subscription Analytics — Streamlit Web App
Запуск: streamlit run app.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import timedelta
from pathlib import Path
from typing import Optional

# Auto-detect data file: look for any .xlsx/.csv in ../data/ relative to this script
_APP_DIR  = Path(__file__).parent
_APP_DIR  = Path(__file__).parent
_DATA_DIR = _APP_DIR.parent / "data"


@st.cache_data(ttl=300)  # перечитывать папку не чаще раз в 5 минут
def _load_data_dir() -> Optional[pd.DataFrame]:
    """
    Загружает все .xlsx / .xls / .csv из папки ../data/,
    конкатенирует и убирает полные дубликаты строк.
    Возвращает DataFrame или None если папки/файлов нет.
    """
    if not _DATA_DIR.exists():
        return None
    frames = []
    for ext in ("*.xlsx", "*.xls", "*.csv"):
        for path in sorted(_DATA_DIR.glob(ext)):
            try:
                if path.suffix in (".xlsx", ".xls"):
                    frames.append(pd.read_excel(path))
                else:
                    frames.append(pd.read_csv(path, sep=None, engine="python"))
            except Exception as e:
                st.warning(f"⚠️ Не удалось загрузить `{path.name}`: {e}")
    if not frames:
        return None
    combined = pd.concat(frames, ignore_index=True)
    before = len(combined)
    combined = combined.drop_duplicates()
    after  = len(combined)
    if before != after:
        st.sidebar.caption(f"🗑 Удалено {before - after} дублей при объединении файлов")
    return combined

# ══════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Subscription Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════
# DARK THEME CSS
# ══════════════════════════════════════════════════════════════
st.markdown("""<style>
html, .stApp, .main, .block-container { background: #0D0F14 !important; }
section[data-testid="stSidebar"] > div { background: #161A23 !important; }
.stTabs [data-baseweb="tab-list"] { background: #161A23; border-radius: 8px; gap: 4px; }
.stTabs [data-baseweb="tab"] { color: #6B7280 !important; border-radius: 6px; }
.stTabs [aria-selected="true"] { background: #1E2330 !important; color: #F0F2F8 !important; }
div[data-testid="stMetricValue"] { color: #C084FC; font-size: 1.6rem !important; }
div[data-testid="stMetricLabel"] { color: #6B7280 !important; }
div[data-testid="stMetricDelta"] { font-size: 0.8rem !important; }
div[data-testid="stMetric"] { background: #1E2330; border-radius: 10px; padding: 12px 16px; }
.stButton > button {
    background: #1E2330; color: #C084FC; border: 1px solid #C084FC;
    border-radius: 8px; padding: 8px 20px; font-weight: 600;
}
.stButton > button:hover { background: #C084FC22; }
hr { border-color: #232738 !important; }
label, .stSelectbox label, .stMultiSelect label { color: #6B7280 !important; }
</style>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════
BG, CARD, GRID = "#0D0F14", "#1E2330", "#232738"
C1, C2, C3, C4 = "#C084FC", "#38BDF8", "#FB7185", "#34D399"
MUTED, TEXT = "#6B7280", "#F0F2F8"

ALL_CHANNELS   = ["liissa.club", "liissa.health", "Listen.community"]
CH_COLOR       = {ALL_CHANNELS[0]: C1, ALL_CHANNELS[1]: C4, ALL_CHANNELS[2]: C2}
GAP_DAYS       = 45
ANNUAL_RATE    = 0.20


def hex_rgba(hex_color: str, alpha: float = 0.12) -> str:
    """Convert #RRGGBB to rgba(r,g,b,alpha) for Plotly compatibility."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _lay(fig, title="", height=380):
    """Apply dark layout to any Plotly figure."""
    fig.update_layout(
        title=dict(text=title, font=dict(color=TEXT, size=13), x=0),
        paper_bgcolor=BG, plot_bgcolor=CARD, height=height,
        font=dict(color=TEXT, size=11),
        legend=dict(bgcolor=CARD, bordercolor=GRID, borderwidth=1),
        margin=dict(l=10, r=10, t=46, b=10),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=GRID, zerolinecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, linecolor=GRID, zerolinecolor=GRID)
    return fig


# ══════════════════════════════════════════════════════════════
# DEMO DATA
# ══════════════════════════════════════════════════════════════
@st.cache_data
def make_demo() -> pd.DataFrame:
    from datetime import datetime
    rng = np.random.default_rng(42)
    ch_cfg = {
        "liissa.club":      {"prices": [499, 699, 999, 1299], "disc": [249, 349], "n": 200},
        "liissa.health":    {"prices": [799, 999],            "disc": [399, 499], "n": 100},
        "Listen.community": {"prices": [299, 499],            "disc": [149, 199], "n": 70},
    }
    start, end = datetime(2024, 8, 1), datetime(2025, 3, 31)
    rows = []

    def add_user(uname, ch, first_date, base_price, first_price, months):
        for m in range(months):
            d = first_date + timedelta(days=m * 30 + int(rng.integers(-3, 4)))
            if d > end: break
            amt  = first_price if m == 0 else base_price
            if m > 0 and rng.random() < 0.06:
                amt = int(rng.choice(ch_cfg[ch]["disc"]))
            is_last = (m == months - 1)
            rows.append({
                "Date": d.strftime("%Y-%m-%d"),
                "Time": f"{rng.integers(0,23):02d}:{rng.integers(0,59):02d}:00",
                "Currency": "RUB", "Amount": amt,
                "Your Amount": round(amt * 0.905, 2), "From": uname,
                "Type of transaction": "Init payment" if m == 0 else "Recurrent payment",
                "Channel": ch, "Subscription": ch, "Period": "monthly",
                "Follower Status": "disabled" if is_last and rng.random() < 0.45 else "enabled",
                "Subscription Status": "inactive" if is_last and rng.random() < 0.45 else "active",
            })

    for ch, cfg in ch_cfg.items():
        for uid in range(cfg["n"]):
            uname = f"@{ch[:4]}_{uid:03d}"
            off   = int(rng.integers(0, 7))
            fd    = start + timedelta(days=off * 30 + int(rng.integers(0, 28)))
            disc  = rng.random() < 0.25
            bp    = int(rng.choice(cfg["prices"]))
            fp    = int(rng.choice(cfg["disc"])) if disc else bp
            mo    = 1
            churn = 0.25 if disc else 0.18
            for _ in range(11):
                if rng.random() < churn: break
                mo += 1
            add_user(uname, ch, fd, bp, fp, mo)

    # multi-channel subscribers
    for uid in range(25):
        uname = f"@multi_{uid:03d}"
        for ch in rng.choice(ALL_CHANNELS, size=int(rng.integers(2, 4)), replace=False):
            cfg = ch_cfg[ch]
            fd  = start + timedelta(days=int(rng.integers(0, 180)))
            bp  = int(rng.choice(cfg["prices"]))
            add_user(uname, ch, fd, bp, bp, int(rng.integers(2, 7)))

    df = pd.DataFrame(rows)
    df = df.sort_values("Date").reset_index(drop=True)
    return df


# ══════════════════════════════════════════════════════════════
# PREPARE
# ══════════════════════════════════════════════════════════════
@st.cache_data
def prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["Amount", "Your Amount"]:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace(",", ".").astype(float)
    df["Datetime"] = pd.to_datetime(
        df["Date"].astype(str) + " " + df["Time"].astype(str), errors="coerce"
    )
    df = df.dropna(subset=["Datetime"]).copy()
    df["Month"]    = df["Datetime"].dt.to_period("M")
    df["Is_Init"]  = df["Type of transaction"].str.lower().str.contains("init")
    df["Is_Recur"] = df["Type of transaction"].str.lower().str.contains("recurrent")

    # Normalize channel name — if column missing, fill from Subscription
    if "Channel" not in df.columns:
        if "Subscription" in df.columns:
            df["Channel"] = df["Subscription"]
        else:
            df["Channel"] = ALL_CHANNELS[0]

    # Map any value not in ALL_CHANNELS to closest match (case-insensitive)
    ch_lower = {c.lower(): c for c in ALL_CHANNELS}
    def _norm_ch(v):
        v_str = str(v).strip()
        if v_str in ALL_CHANNELS:
            return v_str
        return ch_lower.get(v_str.lower(), v_str)
    df["Channel"] = df["Channel"].apply(_norm_ch)
    # fallback for optional status columns
    if "Follower Status" not in df.columns:
        df["Follower Status"] = "enabled"
    if "Subscription Status" not in df.columns:
        df["Subscription Status"] = "active"
    df["From"] = df["From"].fillna("unknown")
    # cohort per (user, channel)
    # Важно: если первый платёж пользователя в данных — Recurrent,
    # значит он подписался ДО начала данных. Помечаем как pre_existing,
    # исключаем из когортного анализа.
    first = (
        df.sort_values("Datetime")
        .groupby(["From", "Channel"])
        .first()[["Datetime", "Is_Init"]]
        .rename(columns={"Datetime": "Cohort_Dt", "Is_Init": "First_Is_Init"})
        .reset_index()
    )
    first["Cohort"] = first["Cohort_Dt"].dt.to_period("M")
    # pre_existing = первый платёж не Init (был активен до начала данных)
    first["Pre_Existing"] = ~first["First_Is_Init"]
    df = df.merge(first[["From", "Channel", "Cohort_Dt", "Cohort", "Pre_Existing"]],
                  on=["From", "Channel"], how="left")
    df["Pre_Existing"] = df["Pre_Existing"].fillna(False).astype(bool)
    df["Life_Month"] = (
        df["Month"].astype("int64") - df["Cohort"].astype("int64")
    ).clip(lower=0)
    return df


# ══════════════════════════════════════════════════════════════
# METRIC COMPUTATION
# ══════════════════════════════════════════════════════════════
def compute_ltv(df, channels):
    """
    LTV = сумма платежей пользователя, индексированная на 20% годовых
    (каждый прошлый рубль стоит больше с учётом временной стоимости денег).
    payment_pv = amount * (1.20 ^ (days_since_payment / 365))
    """
    now = df["Datetime"].max()
    out = []
    for ch in channels:
        c = df[df["Channel"] == ch].copy()
        if c.empty:
            out.append({"Channel": ch, "Ср. LTV, ₽": 0, "Медиана LTV, ₽": 0})
            continue
        c["days_ago"]  = (now - c["Datetime"]).dt.days.clip(lower=0)
        c["pv"]        = c["Your Amount"] * (1.20 ** (c["days_ago"] / 365))
        user_ltv       = c.groupby("From")["pv"].sum()
        out.append({
            "Channel":       ch,
            "Ср. LTV, ₽":   round(user_ltv.mean()),
            "Медиана LTV, ₽": round(user_ltv.median()),
        })
    return pd.DataFrame(out)


def compute_monthly_churn(df, channels):
    rows = []
    for ch in channels:
        c = df[df["Channel"] == ch]
        months = sorted(c["Month"].unique())
        for i, m in enumerate(months[:-1]):
            a = set(c[c["Month"] == m]["From"])
            b = set(c[c["Month"] == months[i+1]]["From"])
            rows.append({"Month": str(m), "Channel": ch,
                         "Churn_Rate": round(len(a - b) / len(a) * 100, 1) if a else 0,
                         "New": len(b - a), "Churned": len(a - b)})
    if not rows:
        return pd.DataFrame(columns=["Month", "Channel", "Churn_Rate", "New", "Churned"])
    return pd.DataFrame(rows)


def compute_cohort_retention(df, channel):
    # исключаем пользователей, которые были активны до начала данных
    c = df[(df["Channel"] == channel) & (~df["Pre_Existing"])]
    cg = c.groupby(["Cohort", "Life_Month"])["From"].nunique().reset_index()
    piv = cg.pivot_table(index="Cohort", columns="Life_Month", values="From")
    if 0 not in piv.columns:
        return pd.DataFrame()
    return piv.div(piv[0], axis=0) * 100


def compute_vintage_churn(df, channel, sub_id=None):
    """
    Накопленный % ушедших по месяцам жизни когорты.
    sub_id: если передан — фильтруем только по этому Subscription ID.
    """
    c = df[(df["Channel"] == channel) & (~df["Pre_Existing"])]
    if sub_id and "Subscription ID" in c.columns:
        c = c[c["Subscription ID"] == sub_id]
    rows = []
    for cohort in sorted(c["Cohort"].unique()):
        cd = c[c["Cohort"] == cohort]
        init_u = set(cd[cd["Life_Month"] == 0]["From"])
        if not init_u: continue
        survived = init_u.copy()
        for lm in range(int(cd["Life_Month"].max()) + 1):
            survived &= set(cd[cd["Life_Month"] == lm]["From"])
            rows.append({"Cohort": str(cohort), "Life_Month": lm,
                         "Pct_Churned": round((1 - len(survived) / len(init_u)) * 100, 1)})
    return pd.DataFrame(rows)


def compute_resubscribe(df, channels):
    """
    Доля отписавшихся, кто вернулся и сейчас активен.
    'Активен' = последняя запись по (From, Channel) имеет Follower Status == enabled.
    """
    now = df["Datetime"].max()
    last_status = (
        df.sort_values("Datetime")
        .groupby(["From", "Channel"])
        .last()[["Follower Status"]]
        .reset_index()
    )
    rows = []
    for ch in channels:
        c  = df[df["Channel"] == ch].sort_values("Datetime")
        ls = last_status[last_status["Channel"] == ch].set_index("From")
        total, returned = 0, 0
        for user, grp in c.groupby("From"):
            dates = grp["Datetime"].sort_values().reset_index(drop=True)
            gaps  = dates.diff().dt.days.dropna()
            if (gaps > GAP_DAYS).any():
                total += 1
                status = ls.loc[user, "Follower Status"] if user in ls.index else "disabled"
                if status == "enabled":
                    returned += 1
        rows.append({
            "Channel":             ch,
            "Отписывались":        total,
            "Вернулись и активны": returned,
            "% вернулись":         round(returned / total * 100, 1) if total else 0,
            "Актуально на":        str(now.date()),
        })
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
def render_sidebar(df):
    with st.sidebar:
        st.markdown("## ⚙️ Фильтры")
        st.divider()

        mn, mx = df["Datetime"].min().date(), df["Datetime"].max().date()
        d_from = st.date_input("С", value=mn, min_value=mn, max_value=mx)
        d_to   = st.date_input("По", value=mx, min_value=mn, max_value=mx)

        gran = st.selectbox("Гранулярность", ["Месяц", "Неделя", "День"])

        st.divider()
        channels = st.multiselect("Каналы", ALL_CHANNELS, default=ALL_CHANNELS)
        if not channels:
            channels = ALL_CHANNELS

        st.divider()
        st.caption(f"Данные: {mn} — {mx}")
    return d_from, d_to, gran, channels


# ══════════════════════════════════════════════════════════════
# ACTIVE SUBSCRIBERS — INTERVAL EXPANSION
# ══════════════════════════════════════════════════════════════
def compute_active_by_period(df: pd.DataFrame, gran: str, channels: list) -> pd.DataFrame:
    """
    Активных = уникальных From с Follower Status == 'enabled' в каждом периоде.
    """
    fmt = {"Месяц": "%Y-%m", "Неделя": "%G-W%V", "День": "%Y-%m-%d"}[gran]
    d = df[df["Channel"].isin(channels)].copy()
    d["pk"] = d["Datetime"].dt.strftime(fmt)
    result = (
        d[d["Follower Status"] == "enabled"]
        .groupby(["pk", "Channel"])["From"]
        .nunique()
        .reset_index()
        .rename(columns={"From": "Active"})
    )
    return result.sort_values("pk")


# ══════════════════════════════════════════════════════════════
# TAB 1 — ОБЗОР
# ══════════════════════════════════════════════════════════════
def tab_overview(df_f, df_all, d_from, d_to, channels, gran):

    # ── Active = уникальные From с enabled-статусом в выбранном периоде
    total = df_f[df_f["Follower Status"] == "enabled"]["From"].nunique()

    # ── payment sequence number per (user, channel) across ALL data
    df_all_ch = df_all[df_all["Channel"].isin(channels)].copy()
    df_all_ch = df_all_ch.sort_values(["From", "Channel", "Datetime"])
    df_all_ch["pay_num"] = df_all_ch.groupby(["From", "Channel"]).cumcount() + 1

    # payments that fall inside the selected period
    df_fp = df_all_ch[
        (df_all_ch["Datetime"].dt.date >= d_from) &
        (df_all_ch["Datetime"].dt.date <= d_to)
    ]

    # New = Init payment in period (first-ever payment for this user/channel)
    new_df   = df_fp[df_fp["Is_Init"] & (df_fp["pay_num"] == 1)]
    new_u    = new_df["From"].nunique()
    new_list = sorted(new_df["From"].unique().tolist())

    # 1st renewal = their 2nd payment is in this period
    r1_df    = df_fp[df_fp["pay_num"] == 2]
    first_r  = r1_df["From"].nunique()
    r1_list  = sorted(r1_df["From"].unique().tolist())

    # 2+ renewals = 3rd+ payment is in this period
    vet_df   = df_fp[df_fp["pay_num"] >= 3]
    vet      = vet_df["From"].nunique()
    vet_list = sorted(vet_df["From"].unique().tolist())

    # Not renewed = paid in previous comparable period, but NOT in current period
    period_len = max((d_to - d_from).days, 30)
    prev_from  = d_from - timedelta(days=period_len)
    df_prev = df_all_ch[
        (df_all_ch["Datetime"].dt.date >= prev_from) &
        (df_all_ch["Datetime"].dt.date < d_from)
    ]
    churned_set  = set(df_prev["From"]) - set(df_fp["From"])
    churned      = len(churned_set)
    churned_list = sorted(list(churned_set))

    rev_total = df_f["Your Amount"].sum()

    # ── KPI row
    k = st.columns(6)
    k[0].metric("👥 Активных в периоде", f"{total:,}".replace(",", " "),
                help="Уникальных From с Follower Status == enabled в выбранном периоде")
    k[1].metric("🆕 Новые подписчики", f"{new_u}",
                f"{new_u/max(total,1)*100:.0f}% от активных",
                help="Init-платёж в выбранном периоде (первая подписка)")
    k[2].metric("🔄 1-е продление", f"{first_r}",
                f"{first_r/max(total,1)*100:.0f}%",
                help="Пользователи, чей 2-й платёж пришёлся на период")
    k[3].metric("💎 2+ продлений", f"{vet}",
                f"{vet/max(total,1)*100:.0f}%",
                help="Пользователи, чей 3-й+ платёж пришёлся на период")
    k[4].metric("❌ Не продлили", f"{churned:,}".replace(",", " "),
                help="Платили в предыдущем периоде, но не платили в текущем")
    k[5].metric("💰 Выручка", f"{rev_total:,.0f} ₽".replace(",", " "))

    # ── кнопки для списков (session_state — список не исчезает при перерисовке)
    _lists = [
        ("_kpi_new",     "📋 Новые",         new_list),
        ("_kpi_r1",      "📋 1-е продление", r1_list),
        ("_kpi_vet",     "📋 2+ продлений",  vet_list),
        ("_kpi_churned", "📋 Не продлили",   churned_list),
    ]
    for key, _, _ in _lists:
        if key not in st.session_state:
            st.session_state[key] = False
    b = st.columns(4)
    for col, (key, label, _) in zip(b, _lists):
        if col.button(label):
            st.session_state[key] = not st.session_state[key]
    for key, title, lst in _lists:
        if st.session_state.get(key):
            st.text_area(title, "\n".join(lst), height=150, key=f"ta{key}")

    st.divider()

    # ── period key for time series
    fmt = {"Месяц": "%Y-%m", "Неделя": "%G-W%V", "День": "%Y-%m-%d"}[gran]
    df_f = df_f.copy()
    df_f["pk"] = df_f["Datetime"].dt.strftime(fmt)

    c1, c2 = st.columns(2)

    # Revenue per channel
    with c1:
        rev_ts = df_f.groupby(["pk", "Channel"])["Your Amount"].sum().reset_index()
        fig = go.Figure()
        for ch in channels:
            d = rev_ts[rev_ts["Channel"] == ch].sort_values("pk")
            fig.add_trace(go.Scatter(
                x=d["pk"], y=d["Your Amount"], name=ch, mode="lines+markers",
                line=dict(color=CH_COLOR.get(ch, C1), width=2),
                fill="tozeroy", fillcolor=hex_rgba(CH_COLOR.get(ch, C1), 0.12),
            ))
        _lay(fig, "💰 Чистая выручка по каналам, ₽")
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    # Avg price per channel
    with c2:
        pr_ts = df_f.groupby(["pk", "Channel"])["Amount"].mean().reset_index()
        fig2 = go.Figure()
        for ch in channels:
            d = pr_ts[pr_ts["Channel"] == ch].sort_values("pk")
            fig2.add_trace(go.Scatter(
                x=d["pk"], y=d["Amount"], name=ch, mode="lines+markers",
                line=dict(color=CH_COLOR.get(ch, C1), width=2),
            ))
        _lay(fig2, "📏 Средняя стоимость подписки по каналам, ₽")
        fig2.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig2, use_container_width=True)

    c3, c4 = st.columns(2)

    # Active subscribers over time — interval expansion
    with c3:
        act_ts = compute_active_by_period(df_f, gran, channels)
        fig3 = go.Figure()
        for ch in channels:
            d = act_ts[act_ts["Channel"] == ch].sort_values("pk")
            fig3.add_trace(go.Bar(x=d["pk"], y=d["Active"], name=ch,
                                  marker_color=CH_COLOR.get(ch, C1)))
        _lay(fig3, "👥 Активных подписчиков по периодам")
        fig3.update_layout(barmode="group", xaxis_tickangle=-45)
        st.plotly_chart(fig3, use_container_width=True)

    # Revenue share pie
    with c4:
        rev_ch = df_f.groupby("Channel")["Your Amount"].sum().reset_index()
        fig4 = go.Figure(go.Pie(
            labels=rev_ch["Channel"], values=rev_ch["Your Amount"],
            hole=0.55,
            marker=dict(colors=[CH_COLOR.get(c, C1) for c in rev_ch["Channel"]],
                        line=dict(color=BG, width=2)),
        ))
        _lay(fig4, "📊 Доля выручки по каналам")
        fig4.update_traces(textfont=dict(color=TEXT))
        st.plotly_chart(fig4, use_container_width=True)


# ══════════════════════════════════════════════════════════════
# TAB 2 — ПОДПИСЧИКИ
# ══════════════════════════════════════════════════════════════
def tab_subscribers(df_all, channels):
    # последняя запись по каждому (пользователь, канал) — для статусов
    latest = (
        df_all.sort_values("Datetime")
        .groupby(["From", "Channel"], as_index=False)
        .last()
    )

    c1, c2 = st.columns(2)

    # Metric 4: subscription periods per person
    with c1:
        sp = []
        for ch in channels:
            for _, grp in df_all[df_all["Channel"] == ch].sort_values("Datetime").groupby("From"):
                dates = grp["Datetime"].sort_values().reset_index(drop=True)
                gaps  = dates.diff().dt.days.fillna(0)
                sp.append({"Channel": ch, "Periods": int(1 + (gaps > GAP_DAYS).sum())})
        sp_df = pd.DataFrame(sp)
        fig = go.Figure()
        for ch in channels:
            d = sp_df[sp_df["Channel"] == ch]["Periods"]
            fig.add_trace(go.Histogram(x=d, name=ch, nbinsx=8,
                                       marker_color=CH_COLOR.get(ch, C1), opacity=0.75))
        _lay(fig, "🔢 Периодов подписки на человека (разы подписки)")
        fig.update_layout(barmode="overlay", xaxis_title="Периодов", yaxis_title="Чел.")
        st.plotly_chart(fig, use_container_width=True)

    # Metric 8: avg renewals per channel
    with c2:
        ar = []
        for ch in channels:
            pays = df_all[df_all["Channel"] == ch].groupby("From").size()
            ar.append({"Channel": ch, "Среднее": round(pays.mean(), 1),
                       "Медиана": round(pays.median(), 1)})
        ar_df = pd.DataFrame(ar)
        fig2 = go.Figure()
        for col, clr in [("Среднее", C1), ("Медиана", C2)]:
            fig2.add_trace(go.Bar(
                x=ar_df["Channel"], y=ar_df[col], name=col,
                marker_color=clr, text=ar_df[col], textposition="outside",
            ))
        _lay(fig2, "📅 Среднее число продлений (месяцев) по каналам")
        fig2.update_layout(barmode="group")
        st.plotly_chart(fig2, use_container_width=True)

    # Автопродление:
    # Формула: последний платёж = Recurrent payment  И  Follower Status = enabled
    # Смысл: система автоматически списала деньги последний раз И подписка ещё активна
    st.markdown("### 🔄 Доля с активным автопродлением")
    st.caption(
        "Считаются пользователи, у которых **последний платёж** — `Recurrent payment` "
        "**и** `Follower Status = enabled`. "
        "Означает: автосписание сработало последним и подписка активна прямо сейчас."
    )
    cols = st.columns(len(channels))
    for i, ch in enumerate(channels):
        ch_latest  = latest[latest["Channel"] == ch]
        active_ch  = ch_latest[ch_latest["Follower Status"] == "enabled"]
        autopay_ch = active_ch[
            active_ch["Type of transaction"].str.lower().str.contains("recurrent", na=False)
        ]
        rate = len(autopay_ch) / max(len(active_ch), 1) * 100
        cols[i].metric(ch, f"{rate:.1f}%",
                       f"{len(autopay_ch)} из {len(active_ch)} активных")


# ══════════════════════════════════════════════════════════════
# TAB 3 — LTV & RETENTION
# ══════════════════════════════════════════════════════════════
def tab_ltv_retention(df_all, channels):
    c1, c2 = st.columns(2)

    with c1:
        ltv_df = compute_ltv(df_all, channels)
        fig = go.Figure()
        for col, clr, lbl in [("Ср. LTV, ₽", C1, "Средний"), ("Медиана LTV, ₽", C2, "Медиана")]:
            fig.add_trace(go.Bar(
                x=ltv_df["Channel"], y=ltv_df[col], name=lbl,
                marker_color=clr,
                text=ltv_df[col].apply(lambda x: f"{x:,.0f} ₽".replace(",", " ")),
                textposition="outside",
            ))
        _lay(fig, f"💎 LTV по каналам (индексация {int(ANNUAL_RATE*100)}% годовых), ₽")
        fig.update_layout(barmode="group")
        st.plotly_chart(fig, use_container_width=True)
        with st.expander("Детали расчёта LTV"):
            st.dataframe(ltv_df, hide_index=True, use_container_width=True)

    with c2:
        churn_df = compute_monthly_churn(df_all, channels)
        fig2 = go.Figure()
        for ch in channels:
            d = churn_df[churn_df["Channel"] == ch]
            fig2.add_trace(go.Scatter(
                x=d["Month"], y=d["Churn_Rate"], name=ch, mode="lines+markers",
                line=dict(color=CH_COLOR.get(ch, C1), width=2),
            ))
        _lay(fig2, "📉 Churn Rate по месяцам, %")
        fig2.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # Cohort retention heatmaps
    st.markdown("### 🗓️ Когортный retention по каналам")
    ch_cols = st.columns(min(len(channels), 3))
    for i, ch in enumerate(channels):
        with ch_cols[i % 3]:
            piv = compute_cohort_retention(df_all, ch)
            if piv.empty:
                st.info(f"Нет данных: {ch}")
                continue
            piv = piv.iloc[:, :12]
            labels_x = [f"+{c}м" for c in piv.columns]
            labels_y = [str(r) for r in piv.index]
            z = piv.values
            text = [[f"{v:.0f}%" if not np.isnan(v) else "" for v in row] for row in z]
            fig_r = go.Figure(go.Heatmap(
                z=z, x=labels_x, y=labels_y,
                colorscale=[[0, CARD], [0.3, "#2D1B69"], [0.7, C1], [1, "#F0ABFC"]],
                zmin=0, zmax=100,
                text=text, texttemplate="%{text}",
                textfont=dict(size=9, color=TEXT),
            ))
            _lay(fig_r, f"Retention — {ch}", height=320)
            st.plotly_chart(fig_r, use_container_width=True)

    st.divider()

    # Vintage churn
    st.markdown("### 📊 Винтаж оттока (накопленный % ушедших по месяцам жизни)")

    # Группировка по Subscription ID (если колонка есть в данных)
    has_sub_id = "Subscription ID" in df_all.columns
    if has_sub_id:
        group_by_sub = st.toggle("🔀 Разбить по Subscription ID", value=False,
                                 help="Показать отдельный винтаж для каждого Subscription ID")
    else:
        group_by_sub = False

    for ch in channels:
        if group_by_sub and has_sub_id:
            sub_ids = sorted(df_all[df_all["Channel"] == ch]["Subscription ID"].dropna().unique())
        else:
            sub_ids = [None]

        n_cols = min(len(sub_ids), 3)
        if len(sub_ids) > 1:
            st.markdown(f"#### {ch}")
        cols = st.columns(n_cols)

        for k, sub_id in enumerate(sub_ids):
            with cols[k % n_cols]:
                vdf = compute_vintage_churn(df_all, ch, sub_id=sub_id)
                if vdf.empty:
                    st.caption(f"Нет данных: {sub_id or ch}")
                    continue
                title_suffix = f" — {sub_id}" if sub_id else f" — {ch}"
                fig_v = go.Figure()
                cohorts = sorted(vdf["Cohort"].unique())
                n = max(len(cohorts), 2)
                palette = px.colors.sample_colorscale("Viridis", n)
                for j, cohort in enumerate(cohorts):
                    d = vdf[vdf["Cohort"] == cohort]
                    fig_v.add_trace(go.Scatter(
                        x=d["Life_Month"], y=d["Pct_Churned"],
                        name=cohort, mode="lines", opacity=0.85,
                        line=dict(width=1.8, color=palette[j]),
                    ))
                _lay(fig_v, f"Винтаж оттока{title_suffix}", height=320)
                fig_v.update_xaxes(title="Месяц жизни")
                fig_v.update_yaxes(title="% ушедших (накопл.)", range=[0, 105])
                st.plotly_chart(fig_v, use_container_width=True)


# ══════════════════════════════════════════════════════════════
# TAB 4 — ОТТОК
# ══════════════════════════════════════════════════════════════
def tab_churn(df_all, channels):
    c1, c2 = st.columns(2)

    # Metric 10: re-subscribers
    with c1:
        rs = compute_resubscribe(df_all, channels)
        last_date = rs["Актуально на"].iloc[0] if len(rs) and "Актуально на" in rs.columns else ""
        st.caption(f"📅 Актуально на: **{last_date}** — статус берётся из последней записи каждого пользователя в данных")
        fig = go.Figure(go.Bar(
            x=rs["Channel"], y=rs["% вернулись"],
            marker_color=[CH_COLOR.get(c, C1) for c in rs["Channel"]],
            text=rs["% вернулись"].apply(lambda x: f"{x:.1f}%"),
            textposition="outside",
        ))
        _lay(fig, f"↩️ Вернулись на тот же канал, % (на {last_date})")
        fig.update_yaxes(range=[0, 105], title="%")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(rs, hide_index=True, use_container_width=True)

    # Monthly new vs churned bars
    with c2:
        churn_df = compute_monthly_churn(df_all, channels)
        fig2 = go.Figure()
        for ch in channels:
            d = churn_df[churn_df["Channel"] == ch]
            fig2.add_trace(go.Bar(x=d["Month"], y=d["New"], name=f"{ch} — новые",
                                  marker_color=CH_COLOR.get(ch, C1)))
            fig2.add_trace(go.Bar(x=d["Month"], y=-d["Churned"], name=f"{ch} — ушли",
                                  marker_color=CH_COLOR.get(ch, C1),
                                  marker_pattern_shape="x", opacity=0.6))
        _lay(fig2, "📊 Новые vs Ушедшие по месяцам")
        fig2.update_layout(barmode="relative", xaxis_tickangle=-45)
        fig2.add_hline(y=0, line_color=MUTED, line_width=1)
        st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════
# TAB 5 — АКЦИИ
# ══════════════════════════════════════════════════════════════
def tab_promos(df_all, channels):

    # ── Шаг 1: уникальные Init-цены по каждой подписке ───────────────────────
    init_prices_raw = (
        df_all[df_all["Is_Init"]]
        .groupby(["Channel", "Subscription"])["Amount"]
        .apply(lambda x: sorted(x.unique(), reverse=True))
        .reset_index()
        .rename(columns={"Amount": "Prices"})
    )

    # ── Шаг 2: виджет настройки акционных цен ────────────────────────────────
    with st.expander("⚙️ Настройка акционных цен", expanded=False):
        st.caption(
            "Для каждой подписки показаны все уникальные цены первого платежа. "
            "**Отметь галочкой акционные (скидочные) цены.** "
            "По умолчанию акционными считаются все цены ниже максимальной на 10%+."
        )
        if "promo_price_flags" not in st.session_state:
            st.session_state["promo_price_flags"] = {}
        for _, row in init_prices_raw.iterrows():
            ch, sub, prices = row["Channel"], row["Subscription"], row["Prices"]
            full_price = prices[0]
            st.markdown(f"**{ch} / {sub}** — максимальная цена: **{int(full_price)} ₽**")
            price_cols = st.columns(min(len(prices), 6))
            for j, price in enumerate(prices):
                key = f"promo_{ch}_{sub}_{price}"
                default_is_promo = (price < full_price * 0.90)
                if key not in st.session_state["promo_price_flags"]:
                    st.session_state["promo_price_flags"][key] = default_is_promo
                checked = price_cols[j % 6].checkbox(
                    f"{int(price)} ₽",
                    value=st.session_state["promo_price_flags"].get(key, default_is_promo),
                    key=key,
                )
                st.session_state["promo_price_flags"][key] = checked

    # ── Шаг 3: функция проверки акционной цены ───────────────────────────────
    def is_promo_price(ch, sub, price):
        key = f"promo_{ch}_{sub}_{price}"
        flags = st.session_state.get("promo_price_flags", {})
        if key in flags:
            return bool(flags[key])
        row = init_prices_raw[
            (init_prices_raw["Channel"] == ch) & (init_prices_raw["Subscription"] == sub)
        ]
        if len(row):
            full = row.iloc[0]["Prices"][0]
            return price < full * 0.90
        return False

    # ── Шаг 4: записи по пользователям ───────────────────────────────────────
    records = []
    for ch in channels:
        c = df_all[df_all["Channel"] == ch]
        if c.empty: continue
        for user, grp in c.groupby("From"):
            grp_sorted = grp.sort_values("Datetime")
            first_row  = grp_sorted.iloc[0]
            fp         = first_row["Amount"]
            sub        = first_row["Subscription"]
            first_dt   = first_row["Datetime"]

            is_promo = is_promo_price(ch, sub, fp)

            if len(grp_sorted) > 1:
                second_dt = grp_sorted.iloc[1]["Datetime"]
                converted = (second_dt - first_dt).days <= GAP_DAYS
            else:
                converted = False

            pays = len(grp_sorted)
            records.append({
                "Channel": ch, "From": user,
                "First_Amount": fp,
                "Is_Promo": is_promo,
                "Promo_Label": f"{int(fp)} ₽" if is_promo else "Полная цена",
                "Total_Pays": pays, "Converted": converted,
            })
    if not records:
        st.info("Нет данных по акциям")
        return

    pdf = pd.DataFrame(records)
    c1, c2 = st.columns(2)

    # Доп 2: subscribers per promo
    with c1:
        promo_only = pdf[pdf["Is_Promo"]]
        cnt = promo_only.groupby(["Channel", "Promo_Label"])["From"].count().reset_index()
        cnt.columns = ["Channel", "Цена входа", "Подписчиков"]
        fig = px.bar(cnt, x="Цена входа", y="Подписчиков", color="Channel",
                     color_discrete_map=CH_COLOR, barmode="group",
                     text="Подписчиков")
        fig.update_traces(textposition="outside")
        _lay(fig, "🎁 Подписчики по цене первого платежа (акции)")
        st.plotly_chart(fig, use_container_width=True)

    # Конверсия в продление (2-й платёж ≤45 дней после первого)
    with c2:
        conv = (
            pdf.groupby(["Channel", "Is_Promo"])
            .agg(Всего=("From", "count"), Продлили=("Converted", "sum"))
            .reset_index()
        )
        conv["Конверсия_%"] = (conv["Продлили"] / conv["Всего"] * 100).round(1)
        conv["Тип"] = conv["Is_Promo"].map({True: "Акция", False: "Полная цена"})
        fig2 = go.Figure()
        for тип, clr in [("Акция", C3), ("Полная цена", C4)]:
            d = conv[conv["Тип"] == тип]
            if d.empty: continue
            fig2.add_trace(go.Bar(
                x=d["Channel"], y=d["Конверсия_%"], name=тип,
                marker_color=clr,
                text=d.apply(
                    lambda r: f"{r['Конверсия_%']:.1f}%<br>({int(r['Продлили'])}/{int(r['Всего'])})",
                    axis=1
                ),
                textposition="outside",
            ))
        _lay(fig2, "📈 Конверсия в продление (2-й платёж ≤45 дней после первого)")
        fig2.update_layout(barmode="group")
        fig2.update_yaxes(range=[0, 115], title="%")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.markdown("### 📋 Детальная таблица по акциям")
    summary = (
        pdf.groupby(["Channel", "Promo_Label", "Is_Promo"])
        .agg(Подписчиков=("From", "count"),
             Конверсия=("Converted", lambda x: f"{x.mean()*100:.1f}%"),
             Ср_платежей=("Total_Pays", "mean"))
        .reset_index()
        .drop(columns="Is_Promo")
        .rename(columns={"Promo_Label": "Цена входа", "Ср_платежей": "Ср. месяцев"})
    )
    summary["Ср. месяцев"] = summary["Ср. месяцев"].round(1)
    st.dataframe(summary, hide_index=True, use_container_width=True)


# ══════════════════════════════════════════════════════════════
# CROSS-CHANNEL OVERLAP
# ══════════════════════════════════════════════════════════════
def show_overlap(df_all):
    st.markdown("### 🔗 Пересечения аудитории между каналами")
    ch_users = {ch: set(df_all[df_all["Channel"] == ch]["From"]) for ch in ALL_CHANNELS}

    # Pair overlaps
    pairs = [(i, j) for i in range(3) for j in range(i + 1, 3)]
    pcols = st.columns(len(pairs) + 1)
    for k, (i, j) in enumerate(pairs):
        a, b = ALL_CHANNELS[i], ALL_CHANNELS[j]
        common = ch_users[a] & ch_users[b]
        pcols[k].metric(
            f"{a.split('.')[0]} ∩ {b.split('.')[0]}",
            f"{len(common)} чел.",
            f"{len(common)/max(len(ch_users[a]),1)*100:.1f}% от {a.split('.')[0]}",
        )
    triple = ch_users[ALL_CHANNELS[0]] & ch_users[ALL_CHANNELS[1]] & ch_users[ALL_CHANNELS[2]]
    pcols[-1].metric("Все 3 канала", f"{len(triple)} чел.")

    # Overlap heatmap
    labels = [c.split(".")[0] for c in ALL_CHANNELS]
    mat = np.array([[len(ch_users[r] & ch_users[c]) for c in ALL_CHANNELS] for r in ALL_CHANNELS], dtype=float)
    # diagonal = size of channel
    for i in range(3): mat[i][i] = len(ch_users[ALL_CHANNELS[i]])

    fig = go.Figure(go.Heatmap(
        z=mat, x=labels, y=labels,
        colorscale=[[0, CARD], [1, C1]],
        text=[[f"{int(v)}" for v in row] for row in mat],
        texttemplate="%{text}", textfont=dict(size=16, color=TEXT),
        showscale=False,
    ))
    _lay(fig, "Матрица пересечений (кол-во уникальных подписчиков)", height=280)
    st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
def main():
    st.markdown(
        "<h1 style='color:#F0F2F8; font-weight:700; margin-bottom:0'>📊 Subscription Analytics</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(f"<p style='color:{MUTED}; margin-top:4px'>Аналитика платных каналов</p>",
                unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("## 📁 Данные")
        uploaded = st.file_uploader("Загрузить другой файл (Excel / CSV)", type=["xlsx", "csv"])

    # Автоматически читаем файл из папки data/ рядом с app.py
    import pathlib
    _DATA_DIR = pathlib.Path(__file__).parent.parent / "data"

    if uploaded:
        # Если пользователь загрузил файл вручную — используем его
        try:
            raw = pd.read_excel(uploaded) if uploaded.name.endswith((".xlsx", ".xls")) \
                  else pd.read_csv(uploaded, sep=None, engine="python")
            df_all = prepare(raw)
        except Exception as e:
            st.error(f"Ошибка загрузки файла: {e}")
            return
    else:
        # Иначе ищем файл в папке data/
        data_files = list(_DATA_DIR.glob("*.xlsx")) + list(_DATA_DIR.glob("*.xls")) + list(_DATA_DIR.glob("*.csv"))
        if data_files:
            try:
                raw = pd.concat([
                    pd.read_excel(f) if f.suffix in (".xlsx", ".xls") else pd.read_csv(f, sep=None, engine="python")
                    for f in data_files
                ], ignore_index=True)
                df_all = prepare(raw)
                with st.sidebar:
                    st.success(f"✅ Файл загружен: **{data_files[0].name}**")
                    st.caption(f"Строк: **{len(raw):,}**".replace(",", " "))
            except Exception as e:
                st.error(f"Ошибка при чтении данных: {e}")
                return
        else:
            df_all = prepare(make_demo())
            st.info("⚡ Отображаются демо-данные. Файл не найден в папке `data/`.")

    # ── Step 2: sidebar filters (now df_all always has Datetime)
    d_from, d_to, gran, channels = render_sidebar(df_all)

    # ── Step 3: apply filters
    df_f = df_all[
        (df_all["Datetime"].dt.date >= d_from) &
        (df_all["Datetime"].dt.date <= d_to) &
        df_all["Channel"].isin(channels)
    ].copy()

    if df_f.empty:
        st.warning("Нет данных для выбранных фильтров")
        return

    # ── Tabs
    t1, t2, t3, t4, t5 = st.tabs([
        "📊 Обзор", "👥 Подписчики", "📈 LTV & Retention", "📉 Отток", "🎁 Акции"
    ])
    with t1: tab_overview(df_f, df_all, d_from, d_to, channels, gran)
    with t2: tab_subscribers(df_all, channels)
    with t3: tab_ltv_retention(df_all, channels)
    with t4: tab_churn(df_all, channels)
    with t5: tab_promos(df_all, channels)

    # ── Cross-channel button
    st.divider()
    if st.button("🔗 Показать пересечения аудитории между каналами"):
        show_overlap(df_all)


if __name__ == "__main__":
    main()