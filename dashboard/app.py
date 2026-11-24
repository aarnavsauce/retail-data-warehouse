import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text

# ---------------------------------------------------------
# 1. PAGE CONFIG & POWER BI CARD STYLING
# ---------------------------------------------------------
st.set_page_config(
    page_title="Enterprise Retail BI | Star Schema Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Power BI-style KPI metric cards */
    div[data-testid="stMetric"] {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-left: 4px solid #F2C811;
        padding: 14px 18px;
        border-radius: 6px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.35);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.85rem;
        color: #8B949E;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.75rem;
        font-weight: 700;
        color: #F0F6FC;
    }
    /* Clean header spacing */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. DATABASE CONNECTION & CACHED QUERY RUNNER
# ---------------------------------------------------------
# Set PG_URI in your environment or update the default fallback below
DB_URI = os.getenv(
    "PG_URI",
    "postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/YOUR_DB_NAME"
)

@st.cache_resource
def get_engine():
    return create_engine(DB_URI)

@st.cache_data(ttl=600)
def run_query(sql: str, params: dict | None = None) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})

def style_fig(fig: go.Figure, title: str, height: int = 380) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color="#F0F6FC"), x=0.01),
        paper_bgcolor="#161B22",
        plot_bgcolor="#161B22",
        font=dict(color="#C9D1D9", size=12),
        height=height,
        margin=dict(l=20, r=20, t=48, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(gridcolor="#21262D", zeroline=False),
    )
    return fig

# ---------------------------------------------------------
# 3. GLOBAL SIDEBAR SLICERS (CONFORMED DIMENSIONS)
# ---------------------------------------------------------
st.sidebar.markdown("## Report Slicers")

years_list = run_query("SELECT DISTINCT year_number FROM dim_date ORDER BY year_number;")["year_number"].tolist()
cities_list = run_query("SELECT DISTINCT city FROM dim_store ORDER BY city;")["city"].tolist()
cats_list = run_query("SELECT DISTINCT category_name FROM dim_product ORDER BY category_name;")["category_name"].tolist()

sel_years = st.sidebar.multiselect("Fiscal Year", years_list, default=years_list)
sel_cities = st.sidebar.multiselect("Store Location", cities_list, default=cities_list)
sel_cats = st.sidebar.multiselect("Product Category", cats_list, default=cats_list)

if not sel_years or not sel_cities or not sel_cats:
    st.warning("Select at least one Year, Store Location, and Product Category in the sidebar.")
    st.stop()

filter_params = {
    "years": tuple(sel_years),
    "cities": tuple(sel_cities),
    "cats": tuple(sel_cats),
}

st.sidebar.markdown("---")
st.sidebar.caption("Model: Kimball Star Schema (PostgreSQL)")
st.sidebar.caption("Grain: Line-Item Sales (`fact_sales`)")

# ---------------------------------------------------------
# 4. HEADER & REPORT PAGE NAVIGATION
# ---------------------------------------------------------
st.markdown("### Enterprise Retail Data Warehouse — Executive BI")

page_exec, page_rfm, page_ops = st.tabs([
    "1. Executive Revenue & Margin",
    "2. Customer RFM & Cohorts",
    "3. Operations & Logistics"
])

# =========================================================
# PAGE 1: EXECUTIVE REVENUE & MARGIN PERFORMANCE
# =========================================================
with page_exec:
    kpi_df = run_query("""
        SELECT
            COALESCE(SUM(f.final_revenue), 0) AS net_revenue,
            COALESCE(SUM(f.net_profit), 0) AS net_profit,
            COUNT(DISTINCT f.order_id) AS total_orders,
            COALESCE(SUM(f.qty), 0) AS units_sold
        FROM fact_sales f
        JOIN dim_date d ON f.order_date_key = d.date_key
        JOIN dim_store s ON f.store_key = s.store_key
        JOIN dim_product p ON f.product_key = p.product_key
        WHERE d.year_number IN :years
          AND s.city IN :cities
          AND p.category_name IN :cats;
    """, filter_params).iloc[0]

    margin_pct = (kpi_df["net_profit"] / kpi_df["net_revenue"] * 100) if kpi_df["net_revenue"] else 0
    aov = (kpi_df["net_revenue"] / kpi_df["total_orders"]) if kpi_df["total_orders"] else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Net Realized Revenue", f"${kpi_df['net_revenue']:,.0f}")
    k2.metric("Net Profit (60% COGS)", f"${kpi_df['net_profit']:,.0f}", f"{margin_pct:.1f}% Margin")
    k3.metric("Total Orders", f"{int(kpi_df['total_orders']):,}")
    k4.metric("Avg Order Value (AOV)", f"${aov:,.2f}")

    st.markdown("")

    # Row 1: Monthly Combo Chart (Revenue Bars + 3M Rolling & Profit Lines)
    monthly_df = run_query("""
        WITH monthly AS (
            SELECT
                MAKE_DATE(d.year_number, d.month_number, 1) AS month_start,
                SUM(f.final_revenue) AS final_revenue,
                SUM(f.net_profit) AS net_profit
            FROM fact_sales f
            JOIN dim_date d ON f.order_date_key = d.date_key
            JOIN dim_store s ON f.store_key = s.store_key
            JOIN dim_product p ON f.product_key = p.product_key
            WHERE d.year_number IN :years
              AND s.city IN :cities
              AND p.category_name IN :cats
            GROUP BY d.year_number, d.month_number
        )
        SELECT
            month_start,
            final_revenue,
            net_profit,
            AVG(final_revenue) OVER (
                ORDER BY month_start ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
            ) AS rolling_3m_rev
        FROM monthly
        ORDER BY month_start;
    """, filter_params)

    fig_combo = go.Figure()
    fig_combo.add_trace(go.Bar(
        x=monthly_df["month_start"], y=monthly_df["final_revenue"],
        name="Net Revenue", marker_color="#2F81F7", opacity=0.85
    ))
    fig_combo.add_trace(go.Scatter(
        x=monthly_df["month_start"], y=monthly_df["rolling_3m_rev"],
        name="3-Month Rolling Avg", line=dict(color="#F2C811", width=3)
    ))
    fig_combo.add_trace(go.Scatter(
        x=monthly_df["month_start"], y=monthly_df["net_profit"],
        name="Net Profit", line=dict(color="#3FB950", width=2.5, dash="dot")
    ))
    fig_combo.update_layout(hovermode="x unified", yaxis_tickprefix="$")
    st.plotly_chart(style_fig(fig_combo, "Monthly Net Revenue Trajectory, 3M Rolling Average & Net Profit", 400), use_container_width=True)

    # Row 2: Category Profitability vs. Store Revenue Leaderboard
    col_left, col_right = st.columns(2)

    with col_left:
        cat_perf = run_query("""
            SELECT
                p.category_name,
                SUM(f.final_revenue) AS net_revenue,
                SUM(f.net_profit) AS net_profit
            FROM fact_sales f
            JOIN dim_date d ON f.order_date_key = d.date_key
            JOIN dim_store s ON f.store_key = s.store_key
            JOIN dim_product p ON f.product_key = p.product_key
            WHERE d.year_number IN :years
              AND s.city IN :cities
              AND p.category_name IN :cats
            GROUP BY p.category_name
            ORDER BY net_revenue ASC;
        """, filter_params)

        fig_cat = go.Figure()
        fig_cat.add_trace(go.Bar(
            y=cat_perf["category_name"], x=cat_perf["net_revenue"],
            name="Net Revenue", orientation="h", marker_color="#2F81F7"
        ))
        fig_cat.add_trace(go.Bar(
            y=cat_perf["category_name"], x=cat_perf["net_profit"],
            name="Net Profit", orientation="h", marker_color="#3FB950"
        ))
        fig_cat.update_layout(barmode="group", xaxis_tickprefix="$")
        st.plotly_chart(style_fig(fig_cat, "Net Revenue vs. Net Profit by Category", 380), use_container_width=True)

    with col_right:
        store_perf = run_query("""
            SELECT
                s.city AS store_city,
                SUM(f.final_revenue) AS net_revenue,
                ROUND((SUM(f.net_profit) / NULLIF(SUM(f.final_revenue), 0)) * 100, 2) AS margin_pct
            FROM fact_sales f
            JOIN dim_date d ON f.order_date_key = d.date_key
            JOIN dim_store s ON f.store_key = s.store_key
            JOIN dim_product p ON f.product_key = p.product_key
            WHERE d.year_number IN :years
              AND s.city IN :cities
              AND p.category_name IN :cats
            GROUP BY s.city
            ORDER BY net_revenue DESC
            LIMIT 10;
        """, filter_params)

        fig_store = px.bar(
            store_perf, x="store_city", y="net_revenue",
            text=store_perf["margin_pct"].apply(lambda x: f"{x:.1f}%"),
            color="margin_pct", color_continuous_scale="Tealgrn"
        )
        fig_store.update_traces(textposition="outside")
        fig_store.update_layout(yaxis_tickprefix="$", coloraxis_showscale=False)
        st.plotly_chart(style_fig(fig_store, "Top Stores by Net Revenue (Labeled with Net Margin %)", 380), use_container_width=True)

# =========================================================
# PAGE 2: CUSTOMER RFM & RETENTION SEGMENTATION
# =========================================================
with page_rfm:
    rfm_base = run_query("""
        WITH customer_aggregates AS (
            SELECT
                c.customer_key,
                c.customer_id,
                c.city,
                c.signup_date,
                MAX(d.full_date) AS last_order_date,
                ((SELECT MAX(full_date) FROM dim_date WHERE date_key = (SELECT MAX(order_date_key) FROM fact_sales)) - MAX(d.full_date)) AS recency_days,
                COUNT(DISTINCT f.order_id) AS order_frequency,
                SUM(f.final_revenue) AS total_monetary_spend
            FROM fact_sales f
            JOIN dim_customer c ON f.customer_key = c.customer_key
            JOIN dim_date d ON f.order_date_key = d.date_key
            JOIN dim_store s ON f.store_key = s.store_key
            JOIN dim_product p ON f.product_key = p.product_key
            WHERE d.year_number IN :years
              AND s.city IN :cities
              AND p.category_name IN :cats
            GROUP BY c.customer_key, c.customer_id, c.city, c.signup_date
        ),
        rfm_scores AS (
            SELECT *,
                NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
                NTILE(5) OVER (ORDER BY order_frequency ASC) AS f_score,
                NTILE(5) OVER (ORDER BY total_monetary_spend ASC) AS m_score
            FROM customer_aggregates
        )
        SELECT
            customer_id, city, signup_date, last_order_date,
            recency_days, order_frequency, total_monetary_spend,
            (r_score + f_score + m_score) AS composite_rfm_score,
            CASE
                WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions / VIP'
                WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
                WHEN r_score <= 2 AND f_score >= 4 THEN 'At Risk (Churning)'
                WHEN r_score <= 2 AND f_score <= 2 THEN 'Hibernating / Lost'
                ELSE 'Standard Customer'
            END AS customer_segment
        FROM rfm_scores;
    """, filter_params)

    vip_count = len(rfm_base[rfm_base["customer_segment"] == "Champions / VIP"])
    at_risk_count = len(rfm_base[rfm_base["customer_segment"] == "At Risk (Churning)"])

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Active Customers", f"{len(rfm_base):,}")
    r2.metric("Champions / VIPs", f"{vip_count:,}", f"{(vip_count / max(len(rfm_base), 1) * 100):.1f}% of Base")
    r3.metric("At-Risk High-Value", f"{at_risk_count:,}", "Retention Target", delta_color="inverse")
    r4.metric("Avg Customer LTV", f"${rfm_base['total_monetary_spend'].mean():,.2f}")

    st.markdown("")

    seg_summary = rfm_base.groupby("customer_segment", as_index=False).agg(
        customer_count=("customer_id", "count"),
        total_spend=("total_monetary_spend", "sum"),
        avg_freq=("order_frequency", "mean")
    ).sort_values("total_spend", ascending=False)

    c_rfm1, c_rfm2 = st.columns(2)
    with c_rfm1:
        fig_donut = px.pie(
            seg_summary, names="customer_segment", values="customer_count",
            hole=0.5, color_discrete_sequence=["#F2C811", "#2F81F7", "#3FB950", "#F85149", "#8B949E"]
        )
        fig_donut.update_traces(textinfo="percent+label")
        st.plotly_chart(style_fig(fig_donut, "Customer Base Share by RFM Lifecycle Tier", 380), use_container_width=True)

    with c_rfm2:
        fig_seg_rev = px.bar(
            seg_summary, x="customer_segment", y="total_spend",
            color="customer_segment",
            color_discrete_sequence=["#F2C811", "#2F81F7", "#3FB950", "#F85149", "#8B949E"]
        )
        fig_seg_rev.update_layout(yaxis_tickprefix="$", showlegend=False)
        st.plotly_chart(style_fig(fig_seg_rev, "Total Revenue Contribution by RFM Tier", 380), use_container_width=True)

    st.markdown("#### High-Priority Customer Action Table (Top 25 by Spend)")
    st.dataframe(
        rfm_base.sort_values("total_monetary_spend", ascending=False).head(25),
        use_container_width=True,
        hide_index=True
    )

# =========================================================
# PAGE 3: OPERATIONS & LOGISTICS PERFORMANCE
# =========================================================
with page_ops:
    leak_df = run_query("""
        SELECT
            COALESCE(SUM(f.gross_revenue), 0) AS gross_rev,
            COALESCE(SUM(f.discount_amount), 0) AS discount_loss,
            COALESCE(SUM(f.refund_amount), 0) AS refund_loss,
            COUNT(f.sales_key) AS total_items,
            COUNT(CASE WHEN f.refund_amount > 0 THEN 1 END) AS returned_items
        FROM fact_sales f
        JOIN dim_date d ON f.order_date_key = d.date_key
        JOIN dim_store s ON f.store_key = s.store_key
        JOIN dim_product p ON f.product_key = p.product_key
        WHERE d.year_number IN :years
          AND s.city IN :cities
          AND p.category_name IN :cats;
    """, filter_params).iloc[0]

    ret_rate = (leak_df["returned_items"] / leak_df["total_items"] * 100) if leak_df["total_items"] else 0

    o1, o2, o3, o4 = st.columns(4)
    o1.metric("Gross Catalog Revenue", f"${leak_df['gross_rev']:,.0f}")
    o2.metric("Promotional Discounts", f"${leak_df['discount_loss']:,.0f}")
    o3.metric("Refund Revenue Leakage", f"${leak_df['refund_loss']:,.0f}")
    o4.metric("Line-Item Return Rate", f"{ret_rate:.2f}%", f"{int(leak_df['returned_items']):,} Returned Units", delta_color="inverse")

    st.markdown("")

    col_op1, col_op2 = st.columns(2)

    with col_op1:
        ship_df = run_query("""
            SELECT
                COALESCE(f.shipment_status, 'Unshipped / Pending') AS shipment_status,
                COUNT(DISTINCT f.order_id) AS order_count
            FROM fact_sales f
            JOIN dim_date d ON f.order_date_key = d.date_key
            JOIN dim_store s ON f.store_key = s.store_key
            JOIN dim_product p ON f.product_key = p.product_key
            WHERE d.year_number IN :years
              AND s.city IN :cities
              AND p.category_name IN :cats
            GROUP BY COALESCE(f.shipment_status, 'Unshipped / Pending');
        """, filter_params)

        fig_ship = px.pie(
            ship_df, names="shipment_status", values="order_count",
            hole=0.5, color_discrete_sequence=["#3FB950", "#2F81F7", "#F2C811", "#F85149"]
        )
        fig_ship.update_traces(textinfo="percent+label")
        st.plotly_chart(style_fig(fig_ship, "Fulfillment Pipeline Distribution (Distinct Orders)", 380), use_container_width=True)

    with col_op2:
        cat_ret_df = run_query("""
            SELECT
                p.category_name,
                ROUND((COUNT(CASE WHEN f.refund_amount > 0 THEN 1 END)::NUMERIC / NULLIF(COUNT(f.sales_key), 0)) * 100, 2) AS return_rate_pct,
                SUM(f.refund_amount) AS total_refunded
            FROM fact_sales f
            JOIN dim_date d ON f.order_date_key = d.date_key
            JOIN dim_store s ON f.store_key = s.store_key
            JOIN dim_product p ON f.product_key = p.product_key
            WHERE d.year_number IN :years
              AND s.city IN :cities
              AND p.category_name IN :cats
            GROUP BY p.category_name
            ORDER BY return_rate_pct ASC;
        """, filter_params)

        fig_ret = px.bar(
            cat_ret_df, x="return_rate_pct", y="category_name", orientation="h",
            text=cat_ret_df["return_rate_pct"].apply(lambda x: f"{x:.2f}%"),
            color="total_refunded", color_continuous_scale="OrRd"
        )
        fig_ret.update_traces(textposition="outside")
        fig_ret.update_layout(xaxis_ticksuffix="%", coloraxis_colorbar_title="Refund $")
        st.plotly_chart(style_fig(fig_ret, "Category Return Rate % (Colored by Refund Dollar Loss)", 380), use_container_width=True)