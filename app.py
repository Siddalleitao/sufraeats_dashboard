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

# ---------------------------------------------------------------
# Design tokens — one place to control the whole look
# ---------------------------------------------------------------
INK = "#1C2331"          # primary text
MUTED = "#5B6472"         # secondary text / axis labels
BORDER = "#E3E1DA"        # hairlines, gridlines
BG = "#F7F6F2"            # page background (matches .streamlit/config.toml)
SURFACE = "#FFFFFF"       # card backgrounds

PRIMARY = "#14555A"       # deep teal — zones / core metric
PRIMARY_LIGHT = "#DCEEEA"
ACCENT = "#C89B3C"        # saffron gold — cuisine / secondary metric
ACCENT_LIGHT = "#F5E9CE"
SLATE = "#3D5A73"         # muted blue — promotions
SLATE_LIGHT = "#E4E7EB"
DANGER = "#B5424B"        # muted brick red — cancellations/refunds only

# One consistent qualitative palette for any chart colored by zone/cuisine/category
QUALITATIVE = [PRIMARY, ACCENT, DANGER, "#4A6B5A", SLATE, "#B5762C", "#7A5C3E", "#5C4A72"]

# Two-stop continuous scales, used so bar charts read as "darker = higher value"
# instead of an arbitrary rainbow per bar
TEAL_SCALE = [PRIMARY_LIGHT, PRIMARY]
GOLD_SCALE = [ACCENT_LIGHT, ACCENT]
SLATE_SCALE = [SLATE_LIGHT, SLATE]

FONT_STACK = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Roboto, sans-serif"


def style_fig(fig, show_colorbar=False):
    """Apply one consistent look to every Plotly chart: font, background, gridlines."""
    fig.update_layout(
        font=dict(family=FONT_STACK, color=INK, size=13),
        title_font=dict(family=FONT_STACK, color=INK, size=16),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=55, l=10, r=10, b=10),
        legend_title_text="",
    )
    fig.update_xaxes(showgrid=False, linecolor=BORDER, tickfont=dict(color=MUTED))
    fig.update_yaxes(showgrid=True, gridcolor=BORDER, zeroline=False, tickfont=dict(color=MUTED))
    if not show_colorbar:
        fig.update_layout(coloraxis_showscale=False)
    return fig


st.markdown(
    f"""
    <style>
    html, body, [class*="css"] {{
        font-family: {FONT_STACK};
    }}
    [data-testid="stMetricValue"] {{
        color: {INK};
        font-weight: 700;
    }}
    [data-testid="stMetricLabel"] {{
        color: {MUTED};
    }}
    h1, h2, h3 {{
        color: {INK};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

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
def format_aed(value):
    """Abbreviate large AED amounts so they fit inside a metric card."""
    if pd.isna(value):
        return "—"
    if abs(value) >= 1_000_000:
        return f"AED {value/1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"AED {value/1_000:.1f}K"
    return f"AED {value:,.0f}"


total_orders = len(fdf)
realised_revenue = fdf["platform_revenue"].sum()
gross_value = fdf["basket_value"].sum()
avg_basket = fdf["basket_value"].mean()
avg_rating = fdf["rating"].mean()
cancel_rate = (fdf["order_status"] == "Cancelled").mean()
refund_rate = (fdf["order_status"] == "Refunded").mean()
avg_delivery = fdf.loc[fdf["order_channel"] == "Delivery", "delivery_time_min"].mean()

row1 = st.columns(4)
with row1[0].container(border=True):
    st.metric("Total orders", f"{total_orders:,}")
with row1[1].container(border=True):
    st.metric(
        "Realised revenue", format_aed(realised_revenue),
        help=f"Exact: AED {realised_revenue:,.0f}",
    )
with row1[2].container(border=True):
    st.metric(
        "Gross order value", format_aed(gross_value),
        help=f"Exact: AED {gross_value:,.0f}",
    )
with row1[3].container(border=True):
    st.metric(
        "Avg basket value", format_aed(avg_basket),
        help=f"Exact: AED {avg_basket:,.2f}" if pd.notna(avg_basket) else None,
    )

row2 = st.columns(4)
with row2[0].container(border=True):
    st.metric("Avg rating", f"{avg_rating:.2f} / 5" if pd.notna(avg_rating) else "—")
with row2[1].container(border=True):
    st.metric("Cancellation rate", f"{cancel_rate:.1%}")
with row2[2].container(border=True):
    st.metric("Refund rate", f"{refund_rate:.1%}")
with row2[3].container(border=True):
    st.metric("Avg delivery time", f"{avg_delivery:.0f} min" if pd.notna(avg_delivery) else "—")

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
        ["Realised revenue", "Gross order value", "Total orders", "Cancellation rate",
         "Avg delivery time", "Revenue per Restaurant"],
        key="zone_metric",
    )

zone_df = fdf.dropna(subset=["zone"])
zone_agg = zone_df.groupby("zone").agg(
    realised_revenue=("platform_revenue", "sum"),
    gross_value=("basket_value", "sum"),
    total_orders=("order_id", "count"),
    cancel_rate=("order_status", lambda s: (s == "Cancelled").mean()),
    avg_delivery_time=("delivery_time_min", "mean"),
    n_restaurants=("restaurant_id", "nunique"),
).reset_index()
zone_agg["revenue_per_restaurant"] = zone_agg["realised_revenue"] / zone_agg["n_restaurants"]

metric_map = {
    "Realised revenue": ("realised_revenue", "AED"),
    "Gross order value": ("gross_value", "AED"),
    "Total orders": ("total_orders", "orders"),
    "Cancellation rate": ("cancel_rate", "%"),
    "Avg delivery time": ("avg_delivery_time", "min"),
    "Revenue per Restaurant": ("revenue_per_restaurant", "AED"),
}
col, unit = metric_map[zone_metric]
zone_agg_sorted = zone_agg.sort_values(col, ascending=False)

with zc2:
    fig = px.bar(
        zone_agg_sorted,
        x="zone",
        y=col,
        color=col,
        color_continuous_scale=TEAL_SCALE,
        text_auto=".2s" if unit != "%" else ".1%",
        title=f"{zone_metric} by zone",
        labels={"zone": "Zone", col: zone_metric},
    )
    fig.update_traces(textfont_color=INK, marker_line_width=0)
    fig.update_layout(yaxis_title=zone_metric, xaxis_title=None)
    if unit == "%":
        fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(style_fig(fig), use_container_width=True)

st.caption(
    "💡 Tip: switch the metric on the left. A zone that tops 'Gross order value' "
    "doesn't always top 'Realised revenue' — that gap is exactly what a naive "
    "'biggest zone wins' decision would miss. 'Revenue per Restaurant' is a "
    "different lens again: it shows whether a zone's revenue comes from genuinely "
    "strong individual restaurants, or just from having a lot of them."
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

freq_map = {"Day": "D", "Week": "W", "Month": "ME"}
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
    fig2.update_traces(line_color=PRIMARY, marker_color=PRIMARY, line_width=2.5)
    # Highlight Ramadan 2025 window if it's in view
    fig2.add_vrect(
        x0="2025-03-01", x1="2025-03-30",
        fillcolor=ACCENT, opacity=0.15, line_width=0,
        annotation_text="Ramadan 2025", annotation_position="top left",
        annotation_font_color=MUTED,
    )
    fig2.update_layout(xaxis_title=None)
    st.plotly_chart(style_fig(fig2), use_container_width=True)

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
    cuisine_zone_choice = st.selectbox(
        "Zone",
        ["All zones (current filter)"] + sorted(fdf["zone"].dropna().unique()),
        key="cuisine_zone_filter",
    )
    cuisine_metric = st.radio(
        "Compare cuisines by",
        ["Realised revenue", "Total orders", "Avg rating", "Cancellation rate"],
        key="cuisine_metric",
    )
    top_n = st.slider("Show top N cuisines", 3, 8, 8, key="cuisine_top_n")

cuisine_df = fdf.dropna(subset=["cuisine"])
if cuisine_zone_choice != "All zones (current filter)":
    cuisine_df = cuisine_df[cuisine_df["zone"] == cuisine_zone_choice]

if cuisine_df.empty:
    with cc2:
        st.info(f"No orders for {cuisine_zone_choice} in the current sidebar filters.")
else:
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

    chart_title = f"{cuisine_metric} by cuisine"
    if cuisine_zone_choice != "All zones (current filter)":
        chart_title += f" — {cuisine_zone_choice}"

    with cc2:
        fig3 = px.bar(
            cuisine_agg_sorted,
            x="cuisine",
            y=ccol,
            color=ccol,
            color_continuous_scale=GOLD_SCALE,
            title=chart_title,
            labels={"cuisine": "Cuisine", ccol: cuisine_metric},
        )
        fig3.update_traces(marker_line_width=0)
        fig3.update_layout(xaxis_title=None, yaxis_title=cuisine_metric)
        if ccol == "cancel_rate":
            fig3.update_yaxes(tickformat=".0%")
        st.plotly_chart(style_fig(fig3), use_container_width=True)

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
            color_discrete_sequence=[SLATE],
        )
        fig4.update_layout(xaxis_title="Delivery time (min)", yaxis_title="Orders")
        st.plotly_chart(style_fig(fig4), use_container_width=True)
    elif view == "Rating distribution":
        fig4 = px.histogram(
            view_df.dropna(subset=["rating"]),
            x="rating",
            nbins=20,
            title="Rating distribution",
            color_discrete_sequence=[PRIMARY],
        )
        fig4.update_layout(xaxis_title="Rating (1-5)", yaxis_title="Orders")
        st.plotly_chart(style_fig(fig4), use_container_width=True)
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
            color_discrete_sequence=QUALITATIVE,
            title="Avg delivery time vs avg rating, by zone (bubble size = orders)",
            labels={"avg_delivery_time": "Avg delivery time (min)", "avg_rating": "Avg rating"},
        )
        fig4.update_traces(marker_line_width=0)
        st.plotly_chart(style_fig(fig4), use_container_width=True)

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
            color=pcol,
            color_continuous_scale=SLATE_SCALE,
            title=f"{promo_metric} by promo code",
            labels={"promo_code": "Promo code", pcol: promo_metric},
        )
        fig5.update_traces(marker_line_width=0)
        fig5.update_layout(xaxis_title=None, yaxis_title=promo_metric)
        st.plotly_chart(style_fig(fig5), use_container_width=True)

st.divider()

# ---------------------------------------------------------------
# Chart 6 (bonus) — Customer behaviour
# ---------------------------------------------------------------
st.subheader("👥 Customer behaviour")
b1, b2, b3 = st.columns(3)
with b1:
    fig6 = px.pie(
        fdf, names="customer_type", title="New vs Repeat customers", hole=0.55,
        color_discrete_sequence=QUALITATIVE,
    )
    fig6.update_traces(marker_line_color=SURFACE, marker_line_width=2, textfont_color=INK)
    st.plotly_chart(style_fig(fig6), use_container_width=True)
with b2:
    fig7 = px.pie(
        fdf, names="order_channel", title="Order channel mix", hole=0.55,
        color_discrete_sequence=QUALITATIVE,
    )
    fig7.update_traces(marker_line_color=SURFACE, marker_line_width=2, textfont_color=INK)
    st.plotly_chart(style_fig(fig7), use_container_width=True)
with b3:
    fig8 = px.pie(
        fdf, names="payment_method", title="Payment method mix", hole=0.55,
        color_discrete_sequence=QUALITATIVE,
    )
    fig8.update_traces(marker_line_color=SURFACE, marker_line_width=2, textfont_color=INK)
    st.plotly_chart(style_fig(fig8), use_container_width=True)

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
