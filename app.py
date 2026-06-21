from flask import Flask, render_template_string, request, redirect, url_for, session
from databricks import sql
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = "change_this_secret_key"

TABLE_NAME = "gold.crm_campaign_recommendations"

DATABRICKS_SERVER_HOSTNAME = os.getenv("DATABRICKS_SERVER_HOSTNAME")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")


def load_data():
    query = f"""
        SELECT *
        FROM {TABLE_NAME}
    """

    with sql.connect(
        server_hostname=DATABRICKS_SERVER_HOSTNAME,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN
    ) as connection:
        df = pd.read_sql(query, connection)

    return df


def safe_money(x):
    try:
        return f"AED {float(x or 0):,.0f}"
    except Exception:
        return "AED 0"


def render_card(r):
    confidence = r.get("confidence", "")
    conf_color = {
        "High": "#0F766E",
        "Medium": "#B45309",
        "Low": "#B91C1C"
    }.get(confidence, "#374151")

    strategy_type = r.get("strategy_type", "")

    if strategy_type == "Active Offer":
        offer_title = "Active Offer"
        offer_value = r.get("active_offer", "")
        offer_bg = "#ECFDF5"
        offer_border = "#10B981"
    elif strategy_type == "Recommended New Offer":
        offer_title = "Recommended New Offer"
        offer_value = r.get("recommended_offer", "")
        offer_bg = "#FEF3C7"
        offer_border = "#F59E0B"
    else:
        offer_title = "Strategy-led Campaign"
        offer_value = r.get("recommended_strategy", "")
        offer_bg = "#F9FAFB"
        offer_border = "#9CA3AF"

    title = r.get("campaign_title") or r.get("recommended_strategy") or "Campaign Recommendation"

    return f"""
    <div class="card">
        <div class="card-top">
            <div class="brand">{r.get("brand", "")} · {r.get("category", "")}</div>
            <div class="confidence" style="color:{conf_color};">{confidence} Confidence</div>
        </div>

        <h2>{title}</h2>
        <div class="segment">{r.get("customer_segment", "")} · {int(r.get("customer_count", 0) or 0):,} customers</div>

        <p class="summary">{r.get("audience_summary", "")}</p>

        <div class="kpi-box">
            <div class="label">Recommended KPI</div>
            <b>{r.get("recommended_kpi", "")}</b>
            <p>{r.get("expected_kpi_impact", "")}</p>
        </div>

        <div class="offer-box" style="background:{offer_bg};border-left:5px solid {offer_border};">
            <div class="label">{offer_title}</div>
            <b>{offer_value}</b>
        </div>

        <div class="revenue-grid">
            <div>
                <span>Without Campaign</span>
                <b>{safe_money(r.get("revenue_without_campaign"))}</b>
            </div>
            <div>
                <span>Incremental Revenue</span>
                <b>{safe_money(r.get("incremental_revenue"))}</b>
            </div>
            <div>
                <span>After Campaign</span>
                <b>{safe_money(r.get("revenue_after_campaign"))}</b>
            </div>
        </div>

        <p><b>Strategy:</b><br>{r.get("recommended_strategy", "")}</p>
        <p><b>Historical Evidence:</b><br>{r.get("historical_evidence", "")}</p>
        <p><b>Business Rationale:</b><br>{r.get("business_rationale", "")}</p>

        <button>{r.get("cta", "Create Campaign")}</button>
    </div>
    """


LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>CRM Decisioning Login</title>
    <style>
        body {font-family: Arial; background:#F9FAFB; display:flex; justify-content:center; align-items:center; height:100vh;}
        .login {background:white; padding:32px; border-radius:18px; width:360px; box-shadow:0 8px 24px rgba(0,0,0,0.1);}
        input {width:100%; padding:12px; margin:10px 0; border:1px solid #D1D5DB; border-radius:10px;}
        button {width:100%; padding:12px; background:#8A1538; color:white; border:none; border-radius:10px; font-weight:bold;}
        .error {color:#B91C1C; margin-top:10px;}
    </style>
</head>
<body>
    <form class="login" method="post">
        <h2>CRM Campaign Decisioning Engine</h2>
        <input name="username" placeholder="Username" />
        <input name="password" type="password" placeholder="Password" />
        <button type="submit">Login</button>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
    </form>
</body>
</html>
"""


DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>CRM Campaign Decisioning Engine</title>
    <style>
        body {font-family: Arial, sans-serif; background:#F8FAFC; margin:0; color:#111827;}
        .header {background:white; padding:24px 36px; border-bottom:1px solid #E5E7EB; display:flex; justify-content:space-between;}
        .container {padding:24px 36px;}
        .filters {background:white; padding:18px; border-radius:16px; display:flex; gap:14px; flex-wrap:wrap; margin-bottom:20px;}
        select {padding:10px; border-radius:10px; border:1px solid #D1D5DB; min-width:170px;}
        .kpis {display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:24px;}
        .kpi {background:white; padding:18px; border-radius:16px; box-shadow:0 4px 12px rgba(0,0,0,0.06);}
        .kpi span {font-size:12px; color:#6B7280; text-transform:uppercase; font-weight:bold;}
        .kpi b {display:block; margin-top:8px; font-size:24px; color:#8A1538;}
        .cards {display:grid; grid-template-columns:repeat(auto-fill,minmax(430px,1fr)); gap:18px;}
        .card {background:white; border:1px solid #E5E7EB; border-radius:18px; padding:22px; box-shadow:0 6px 18px rgba(0,0,0,0.08);}
        .card-top {display:flex; justify-content:space-between; align-items:center;}
        .brand {font-size:12px; font-weight:700; color:#6B7280; text-transform:uppercase;}
        .confidence {font-size:12px; font-weight:700; background:#F3F4F6; padding:6px 10px; border-radius:20px;}
        h2 {font-size:21px; margin-bottom:6px;}
        .segment {font-size:13px; color:#6B7280; margin-bottom:12px;}
        .summary, p {font-size:13px; line-height:1.5; color:#374151;}
        .kpi-box {background:#EEF2FF; padding:12px; border-radius:12px; margin:12px 0;}
        .offer-box {padding:12px; border-radius:12px; margin:12px 0;}
        .label {font-size:11px; font-weight:700; color:#6B7280; text-transform:uppercase; margin-bottom:6px;}
        .revenue-grid {display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin:14px 0;}
        .revenue-grid div {background:#F9FAFB; padding:10px; border-radius:10px;}
        .revenue-grid span {font-size:11px; color:#6B7280;}
        .revenue-grid b {display:block; font-size:14px; margin-top:5px;}
        button {background:#8A1538; color:white; border:none; border-radius:10px; padding:12px 16px; font-weight:700; width:100%;}
        .logout {text-decoration:none; color:#8A1538; font-weight:bold;}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>CRM Campaign Decisioning Engine</h1>
            <div>Revenue summary, campaign opportunities and AI-generated recommendation cards.</div>
        </div>
        <a class="logout" href="/logout">Logout</a>
    </div>

    <div class="container">
        <form class="filters" method="get">
            <select name="brand">
                <option value="All">All Brands</option>
                {% for b in brands %}
                    <option value="{{b}}" {% if selected_brand == b %}selected{% endif %}>{{b}}</option>
                {% endfor %}
            </select>

            <select name="segment">
                <option value="All">All Segments</option>
                {% for s in segments %}
                    <option value="{{s}}" {% if selected_segment == s %}selected{% endif %}>{{s}}</option>
                {% endfor %}
            </select>

            <select name="strategy">
                <option value="All">All Strategies</option>
                {% for st in strategies %}
                    <option value="{{st}}" {% if selected_strategy == st %}selected{% endif %}>{{st}}</option>
                {% endfor %}
            </select>

            <select name="confidence">
                <option value="All">All Confidence</option>
                {% for c in confidences %}
                    <option value="{{c}}" {% if selected_confidence == c %}selected{% endif %}>{{c}}</option>
                {% endfor %}
            </select>

            <button style="width:150px;">Apply Filters</button>
        </form>

        <div class="kpis">
            <div class="kpi"><span>Total Customers</span><b>{{ total_customers }}</b></div>
            <div class="kpi"><span>Revenue Without Campaign</span><b>{{ revenue_without }}</b></div>
            <div class="kpi"><span>Incremental Revenue</span><b>{{ incremental_revenue }}</b></div>
            <div class="kpi"><span>Revenue After Campaign</span><b>{{ revenue_after }}</b></div>
        </div>

        <div class="cards">
            {{ cards|safe }}
        </div>
    </div>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))

    error = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Change this or use env variables
        if username == os.getenv("APP_USERNAME", "admin") and password == os.getenv("APP_PASSWORD", "admin123"):
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid username or password"

    return render_template_string(LOGIN_HTML, error=error)


@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    df = load_data()

    selected_brand = request.args.get("brand", "All")
    selected_segment = request.args.get("segment", "All")
    selected_strategy = request.args.get("strategy", "All")
    selected_confidence = request.args.get("confidence", "All")

    brands = sorted(df["brand"].dropna().unique())
    segments = sorted(df["customer_segment"].dropna().unique())
    strategies = sorted(df["strategy_type"].dropna().unique())
    confidences = sorted(df["confidence"].dropna().unique())

    filtered = df.copy()

    if selected_brand != "All":
        filtered = filtered[filtered["brand"] == selected_brand]

    if selected_segment != "All":
        filtered = filtered[filtered["customer_segment"] == selected_segment]

    if selected_strategy != "All":
        filtered = filtered[filtered["strategy_type"] == selected_strategy]

    if selected_confidence != "All":
        filtered = filtered[filtered["confidence"] == selected_confidence]

    total_customers = f"{filtered['customer_count'].sum():,.0f}"
    revenue_without = safe_money(filtered["revenue_without_campaign"].sum())
    incremental_revenue = safe_money(filtered["incremental_revenue"].sum())
    revenue_after = safe_money(filtered["revenue_after_campaign"].sum())

    filtered = filtered.sort_values("incremental_revenue", ascending=False)

    cards = "".join([render_card(row) for row in filtered.to_dict(orient="records")])

    return render_template_string(
        DASHBOARD_HTML,
        brands=brands,
        segments=segments,
        strategies=strategies,
        confidences=confidences,
        selected_brand=selected_brand,
        selected_segment=selected_segment,
        selected_strategy=selected_strategy,
        selected_confidence=selected_confidence,
        total_customers=total_customers,
        revenue_without=revenue_without,
        incremental_revenue=incremental_revenue,
        revenue_after=revenue_after,
        cards=cards
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
