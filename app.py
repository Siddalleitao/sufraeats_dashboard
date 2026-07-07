"""
SufraEats — Dubai Delivery Dashboard
=====================================
Reads the cleaned, merged dataset produced by the analysis notebook
(sufraeats_clean_merged.csv) and turns it into an interactive dashboard
a SufraEats manager can open and explore without any explanation.

Run locally with:
    streamlit run app.py
"""

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------
st.set_page_config(
    page_title="SufraEats — Dubai Delivery Dashboard",
    page_icon="🚚",
    layout="wide",
)

PRIMARY = "#2f6f4f"
ACCENT = "#c9683b"

# ---------------------------------------------------------------
# Load data
# ---------------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("sufraeats_clean_merged.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df


df = load_data()

# ---------------------------------------------------------------
# Header
# ---------------------------------------------------------------
st.title("🚚 SufraEats — Dubai Delivery Dashboard")
st.markdown(
    "Explore where SufraEats is genuinely strong — not just where the "
    "order volume looks biggest. Figures below are **cleaned and combined** "
    "from the orders and restaurants data: duplicates removed, zone/cuisine "
    "labels unified, and revenue shown as what SufraEats actually **keeps** "
    "(commission on delivered orders), not gross order value."
)
st.divider()

# ---------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------
st.sidebar.header("🔎 Filters")
st.sidebar.caption("Slice the whole dashboard by any combination below.")

zones = sorted(df["zone"].dropna().unique())
sel_zones = st.sidebar.multiselect("Zone", zones, default=zones)

cuisines = sorted(df["cuisine"].dropna().unique())
sel_cuisines = st.sidebar.multiselect("Cuisine", cuisines, default=cuisines)

channels = sorted(df["order_channel"].dropna().unique())
sel_channels = st.sidebar.multiselect("Order channel", channels, default=channels)

statuses = sorted(df["order_status"].dropna().unique())
sel_statuses = st.sidebar.multiselect("Order status", statuses, default=statuses)

min_date, max_date = df["date"].min().date(), df["date"].max().date()
date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

st.sidebar.divider()
include_no_zone = st.sidebar.checkbox(
    "Include orders with no matching restaurant (~4% of orders)",
    value=False,
    help=(
        "These orders reference a restaurant_id not found in the restaurants "
        "file, so they have no zone or cuisine. Included by default only in "
        "platform-wide totals, excluded from zone/cuisine breakdowns."
    ),
)

# ---------------------------------------------------------------
# Apply global filters
# ---------------------------------------------------------------
mask = (
    df["order_channel"].isin(sel_channels)
    & df["order_status"].isin(sel_statuses)
    & (df["date"].dt.date >= start_date)
    & (df["date"].dt.date <= end_date)
)

zone_cuisine_mask = df["zone"].isin(sel_zones) & df["cuisine"].isin(sel_cuisines)
if include_no_zone:
    zone_cuisine_mask = zone_cuisine_mask | df["zone"].isna()

fdf = df[mask & zone_cuisine_mask].copy()

if fdf.empty:
    st.warning("No orders match the current filters — try widening your selection in the sidebar.")
    st.stop()

# ---------------------------------------------------------------
# Headline metrics
# ---------------------------------------------------------------
total_orders = len(fdf)
realised_revenue = fdf["platform_revenue"].sum()
gross_value = fdf["basket_value"].sum()
avg_rating = fdf["rating"].mean()
cancel_rate = (fdf["order_status"] == "Cancelled").mean()
refund_rate = (fdf["order_status"] == "Refunded").mean()
avg_delivery = fdf.loc[fdf["order_channel"] == "Delivery", "delivery_time_min"].mean()

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total orders", f"{total_orders:,}")
c2.metric("Realised revenue", f"AED {realised_revenue:,.0f}")
c3.metric("Gross order value", f"AED {gross_value:,.0f}")
c4.metric("Avg rating", f"{avg_rating:.2f} / 5" if pd.notna(avg_rating) else "—")
c5.metric("Cancellation rate", f"{cancel_rate:.1%}")
c6.metric("Avg delivery time", f"{avg_delivery:.0f} min" if pd.notna(avg_delivery) else "—")

st.caption(
    "**Realised revenue** = commission on delivered orders (net of discount) + delivery fees. "
    "**Gross order value** = basket value before discounts, cancellations or refunds — shown "
    "side-by-side because the two can tell very different stories about the same zone."
)
st.divider()

# ---------------------------------------------------------------
# Chart 1 — Zone comparison
# ---------------------------------------------------------------
st.subheader("📍 Zone comparison — where is SufraEats actually strongest?")
zc1, zc2 = st.columns([1, 3])
with zc1:
    zone_metric = st.radio(
        "Compare zones by",
        ["Realised revenue", "Gross order value", "Total orders", "Cancellation rate", "Avg delivery time"],
        key="zone_metric",
    )

zone_df = fdf.dropna(subset=["zone"])
zone_agg = zone_df.groupby("zone").agg(
    realised_revenue=("platform_revenue", "sum"),
    gross_value=("basket_value", "sum"),
    total_orders=("order_id", "count"),
    cancel_rate=("order_status", lambda s: (s == "Cancelled").mean()),
    avg_delivery_time=("delivery_time_min", "mean"),
).reset_index()

metric_map = {
    "Realised revenue": ("realised_revenue", "AED"),
    "Gross order value": ("gross_value", "AED"),
    "Total orders": ("total_orders", "orders"),
    "Cancellation rate": ("cancel_rate", "%"),
    "Avg delivery time": ("avg_delivery_time", "min"),
}
col, unit = metric_map[zone_metric]
zone_agg_sorted = zone_agg.sort_values(col, ascending=False)

with zc2:
    fig = px.bar(
        zone_agg_sorted,
        x="zone",
        y=col,
        color="zone",
        text_auto=".2s" if unit != "%" else ".1%",
        title=f"{zone_metric} by zone",
        labels={"zone": "Zone", col: zone_metric},
    )
    fig.update_layout(showlegend=False, yaxis_title=zone_metric)
    if unit == "%":
        fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)

st.caption(
    "💡 Tip: switch the metric on the left. A zone that tops 'Gross order value' "
    "doesn't always top 'Realised revenue' — that gap is exactly what a naive "
    "'biggest zone wins' decision would miss."
)
st.divider()

# ---------------------------------------------------------------
# Chart 2 — Time trend
# ---------------------------------------------------------------
st.subheader("📈 Demand over time")
tc1, tc2 = st.columns([1, 3])
with tc1:
    granularity = st.radio("Group by", ["Day", "Week", "Month"], key="granularity")
    trend_metric = st.radio("Show", ["Total orders", "Realised revenue"], key="trend_metric")

freq_map = {"Day": "D", "Week": "W", "Month": "M"}
trend_df = fdf.set_index("date").resample(freq_map[granularity]).agg(
    total_orders=("order_id", "count"),
    realised_revenue=("platform_revenue", "sum"),
).reset_index()

trend_col = "total_orders" if trend_metric == "Total orders" else "realised_revenue"

with tc2:
    fig2 = px.line(
        trend_df,
        x="date",
        y=trend_col,
        markers=True,
        title=f"{trend_metric} by {granularity.lower()}",
        labels={"date": "Date", trend_col: trend_metric},
    )
    fig2.update_traces(line_color=PRIMARY)
    # Highlight Ramadan 2025 window if it's in view
    fig2.add_vrect(
        x0="2025-03-01", x1="2025-03-30",
        fillcolor="orange", opacity=0.12, line_width=0,
        annotation_text="Ramadan 2025", annotation_position="top left",
    )
    st.plotly_chart(fig2, use_container_width=True)

st.caption(
    "The shaded band marks Ramadan 2025 (~1–30 March) — the demand shift here "
    "is a real seasonal event, not a data issue."
)
st.divider()

# ---------------------------------------------------------------
# Chart 3 — Cuisine breakdown
# ---------------------------------------------------------------
st.subheader("🍽️ Cuisine breakdown — for onboarding priorities")
cc1, cc2 = st.columns([1, 3])
with cc1:
    cuisine_metric = st.radio(
        "Compare cuisines by",
        ["Realised revenue", "Total orders", "Avg rating", "Cancellation rate"],
        key="cuisine_metric",
    )
    top_n = st.slider("Show top N cuisines", 3, 8, 8, key="cuisine_top_n")

cuisine_df = fdf.dropna(subset=["cuisine"])
cuisine_agg = cuisine_df.groupby("cuisine").agg(
    realised_revenue=("platform_revenue", "sum"),
    total_orders=("order_id", "count"),
    avg_rating=("rating", "mean"),
    cancel_rate=("order_status", lambda s: (s == "Cancelled").mean()),
).reset_index()

cuisine_metric_map = {
    "Realised revenue": "realised_revenue",
    "Total orders": "total_orders",
    "Avg rating": "avg_rating",
    "Cancellation rate": "cancel_rate",
}
ccol = cuisine_metric_map[cuisine_metric]
cuisine_agg_sorted = cuisine_agg.sort_values(ccol, ascending=False).head(top_n)

with cc2:
    fig3 = px.bar(
        cuisine_agg_sorted,
        x="cuisine",
        y=ccol,
        color="cuisine",
        title=f"{cuisine_metric} by cuisine",
        labels={"cuisine": "Cuisine", ccol: cuisine_metric},
    )
    fig3.update_layout(showlegend=False)
    if ccol == "cancel_rate":
        fig3.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ---------------------------------------------------------------
# Chart 4 — Delivery time & ratings
# ---------------------------------------------------------------
st.subheader("⏱️ Delivery experience & ratings")
dc1, dc2 = st.columns([1, 3])
with dc1:
    view = st.radio(
        "View",
        ["Delivery time distribution", "Rating distribution", "Delivery time vs rating by zone"],
        key="delivery_view",
    )
    only_delivery = st.checkbox("Delivery orders only", value=True, key="only_delivery_toggle")

view_df = fdf.copy()
if only_delivery:
    view_df = view_df[view_df["order_channel"] == "Delivery"]

with dc2:
    if view == "Delivery time distribution":
        fig4 = px.histogram(
            view_df.dropna(subset=["delivery_time_min"]),
            x="delivery_time_min",
            nbins=40,
            title="Delivery time distribution (minutes)",
            color_discrete_sequence=[ACCENT],
        )
        fig4.update_layout(xaxis_title="Delivery time (min)", yaxis_title="Orders")
        st.plotly_chart(fig4, use_container_width=True)
    elif view == "Rating distribution":
        fig4 = px.histogram(
            view_df.dropna(subset=["rating"]),
            x="rating",
            nbins=20,
            title="Rating distribution",
            color_discrete_sequence=[PRIMARY],
        )
        fig4.update_layout(xaxis_title="Rating (1-5)", yaxis_title="Orders")
        st.plotly_chart(fig4, use_container_width=True)
    else:
        zr = view_df.dropna(subset=["zone"]).groupby("zone").agg(
            avg_delivery_time=("delivery_time_min", "mean"),
            avg_rating=("rating", "mean"),
            total_orders=("order_id", "count"),
        ).reset_index()
        fig4 = px.scatter(
            zr,
            x="avg_delivery_time",
            y="avg_rating",
            size="total_orders",
            color="zone",
            title="Avg delivery time vs avg rating, by zone (bubble size = orders)",
            labels={"avg_delivery_time": "Avg delivery time (min)", "avg_rating": "Avg rating"},
        )
        st.plotly_chart(fig4, use_container_width=True)

st.divider()

# ---------------------------------------------------------------
# Chart 5 (bonus) — Promotions
# ---------------------------------------------------------------
st.subheader("🏷️ Promotions — are they paying off?")
pc1, pc2 = st.columns([1, 3])
with pc1:
    promo_metric = st.radio(
        "Compare promo codes by",
        ["Realised revenue", "Total orders", "Total discount given"],
        key="promo_metric",
    )

promo_df = fdf.dropna(subset=["promo_code"])
if promo_df.empty:
    with pc2:
        st.info("No promo-code orders in the current filter selection.")
else:
    promo_agg = promo_df.groupby("promo_code").agg(
        realised_revenue=("platform_revenue", "sum"),
        total_orders=("order_id", "count"),
        total_discount=("discount_amount", "sum"),
    ).reset_index()
    promo_metric_map = {
        "Realised revenue": "realised_revenue",
        "Total orders": "total_orders",
        "Total discount given": "total_discount",
    }
    pcol = promo_metric_map[promo_metric]
    with pc2:
        fig5 = px.bar(
            promo_agg.sort_values(pcol, ascending=False),
            x="promo_code",
            y=pcol,
            color="promo_code",
            title=f"{promo_metric} by promo code",
            labels={"promo_code": "Promo code", pcol: promo_metric},
        )
        fig5.update_layout(showlegend=False)
        st.plotly_chart(fig5, use_container_width=True)

st.divider()

# ---------------------------------------------------------------
# Chart 6 (bonus) — Customer behaviour
# ---------------------------------------------------------------
st.subheader("👥 Customer behaviour")
b1, b2, b3 = st.columns(3)
with b1:
    fig6 = px.pie(
        fdf, names="customer_type", title="New vs Repeat customers", hole=0.45,
    )
    st.plotly_chart(fig6, use_container_width=True)
with b2:
    fig7 = px.pie(
        fdf, names="order_channel", title="Order channel mix", hole=0.45,
    )
    st.plotly_chart(fig7, use_container_width=True)
with b3:
    fig8 = px.pie(
        fdf, names="payment_method", title="Payment method mix", hole=0.45,
    )
    st.plotly_chart(fig8, use_container_width=True)

st.divider()

# ---------------------------------------------------------------
# Raw data (optional, collapsed)
# ---------------------------------------------------------------
with st.expander("🔍 View filtered raw data"):
    st.dataframe(
        fdf[[
            "order_id", "date", "zone", "cuisine", "order_channel", "order_status",
            "basket_value", "discount_amount", "platform_revenue",
            "delivery_time_min", "rating",
        ]].sort_values("date", ascending=False),
        use_container_width=True,
        height=350,
    )

st.caption(
    "Data: cleaned & merged SufraEats orders + restaurants (Jan–May 2025). "
    "Built with Streamlit."
)
