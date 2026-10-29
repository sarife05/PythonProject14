import pandas as pd
import plotly.graph_objects as go
import streamlit as st

LEVELS = 6
SLOT_DX = {"a": -0.3, "b": 0.0, "c": 0.3}
EMPTY_FILL, EMPTY_LINE = "#d9dee4", "#98a3af"
FALLBACK_COLOR = "#8a8f95"
PRODUCTS = {  # code:(name, color)
    "2261410A": ("Pritt Color Stick Orange 15000×10g", "#e07b2c"),
    "1173983": ("ACCO PP STATICMIXER INJECTION", "#7a5fc4"),
    "2675905": ("PKU6K Pritt Stick 8300×22g UK", "#2a8f6f"),
    "2109642": ("SFG Pritt Corr R Compact 4,2 mm", "#c4457a"),
    "1634782": ("WERN/240×193×220 (carton)", "#8a7a3a"),
    "2755471": ("Blistercard (2755566)", "#2f7fb8"),
    "3053789": ("Blistercard Box/3178041321204 (2755566)", "#b84f3a"),
}
PM = "PM-13178/26 (goods receipt)"
MM = "MMW-16707/26 (issue to production)"
PRITT_STICK = (
    "K-005-026-004-a K-006-019-002-b K-006-019-003-a K-006-019-003-b K-006-019-004-b "
    "K-006-025-002-c K-006-029-002-b K-006-030-002-c K-007-028-003-b K-008-026-002-b "
    "K-008-026-003-c K-008-026-004-a K-008-026-004-b K-008-026-004-c K-008-027-002-a "
    "K-008-027-002-b K-008-027-002-c K-008-027-003-a K-008-027-003-b K-008-027-003-c "
    "K-008-027-004-a K-008-027-004-b K-008-027-004-c K-008-028-002-a K-008-028-002-b "
    "K-008-028-002-c K-008-028-003-a K-008-028-003-b K-008-028-003-c K-008-028-004-a"
).split()
COLUMN_NAMES = {"address": "Location", "code": "Item code", "name": "Product",
                "qty": "Quantity (pcs)", "doc": "Document", "batch": "Batch"}


@st.cache_data
def load_pallets() -> pd.DataFrame:
# need replacement
    data = []

    def add(code, qty, doc, addrs):
        for i, a in enumerate(addrs):
            q = qty[i] if isinstance(qty, list) else qty
            data.append({"address": a, "code": code, "qty": q, "doc": doc, "batch": ""})

    add("2261410A", 15000, PM, ["K-005-023-003-b", "K-005-024-002-c", "K-005-024-004-b", "K-005-025-002-c"])
    add("1173983", 4000, PM, ["K-005-025-004-a"])
    add("2675905", 8300, PM, PRITT_STICK)
    add("2109642", [695, 3627], MM, ["K-004-032-005-b", "K-004-032-005-c"])
    add("1634782", 216, MM, ["K-002-016-001-c"])
    add("2755471", [1581, 580], MM, ["K-014-025-001-a", "K-014-025-001-a"])
    add("3053789", 2161, MM, ["K-013-031-006-c"])

    df = pd.DataFrame(data)
    p = df["address"].str.split("-", expand=True)  # K-008-027-003-b
    df["row_id"] = p[0] + "-" + p[1]  # zone + row
    df["bay"] = p[2].astype(int)
    df["name"] = df["code"].map(lambda c: PRODUCTS.get(c, (c, FALLBACK_COLOR))[0])
    df["color"] = df["code"].map(lambda c: PRODUCTS.get(c, (c, FALLBACK_COLOR))[1])
    return df


def address_from_click(row_id: str, x: float, y: float) -> str:
    bay = round(x)
    dx = x - bay
    slot = "a" if dx < -0.15 else "c" if dx > 0.15 else "b"
    return f"{row_id}-{bay:03d}-{int(round(y)):03d}-{slot}"


def rack_figure(sub: pd.DataFrame, row_id: str, lo: int, hi: int, hits: set, picked) -> go.Figure:
    by_addr = sub.drop_duplicates("address").set_index("address")
    n = hi - lo + 1
    size = int(max(10, min(26, 0.3 * 1000 / n * 0.85)))
    xs, ys, fills, texts = [], [], [], []
    rx, ry, rc = [], [], []
    for lvl in range(1, LEVELS + 1):
        for b in range(lo, hi + 1):
            for s, dx in SLOT_DX.items():
                addr = f"{row_id}-{b:03d}-{lvl:03d}-{s}"
                xs.append(round(b + dx, 2))
                ys.append(lvl)
                if addr in by_addr.index:
                    r = by_addr.loc[addr]
                    fills.append(r["color"])
                    texts.append(f"{addr}<br>{r['name']}<br>{r['qty']:,} pcs")
                else:
                    fills.append(EMPTY_FILL)
                    texts.append(f"{addr}<br>Empty")
                if addr == picked or addr in hits:
                    rx.append(xs[-1])
                    ry.append(lvl)
                    rc.append("#ff2d55" if addr == picked else "#f5a623")

    shapes = [
        dict(type="rect", x0=b - 0.46, x1=b + 0.46, y0=l - 0.42, y1=l + 0.42,
             fillcolor="rgba(128,128,128,0.16)", line_width=0, layer="below")
        for l in range(1, LEVELS + 1) for b in range(lo, hi + 1)
    ]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=rx, y=ry, mode="markers", hoverinfo="skip", showlegend=False,
                             marker=dict(symbol="square", size=size + 9, color=rc)))
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="markers", hovertext=texts, hoverinfo="text", showlegend=False,
        marker=dict(symbol="square", size=size, color=fills, line=dict(width=1, color=EMPTY_LINE)),
        selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)),
    ))
    fig.update_layout(
        height=70 * LEVELS + 90, margin=dict(l=70, r=10, t=10, b=50), shapes=shapes,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        clickmode="event+select", dragmode=False, showlegend=False,
        xaxis=dict(tickmode="array", tickvals=list(range(lo, hi + 1)),
                   ticktext=[f"{b:03d}" for b in range(lo, hi + 1)], range=[lo - 0.6, hi + 0.6],
                   fixedrange=True, showgrid=False, zeroline=False, title="Bay"),
        yaxis=dict(tickmode="array", tickvals=list(range(1, LEVELS + 1)),
                   ticktext=[f"Level {l}" for l in range(1, LEVELS + 1)], range=[0.4, LEVELS + 0.6],
                   fixedrange=True, showgrid=False, zeroline=False),
    )
    return fig


st.set_page_config(page_title="Hillwood Warehouse", layout="wide")
st.title("Warehouse")

df = load_pallets()
q = st.sidebar.text_input("Search", placeholder="location, batch, item code or product name").strip().lower()
hits, found, first_row = set(), pd.DataFrame(), None
if q:
    hay = (df["address"] + " " + df["code"] + " " + df["name"] + " " + df["batch"]).str.lower()
    found = df[hay.str.contains(q, regex=False)]
    hits = set(found["address"])
    first_row = found["row_id"].iloc[0] if len(found) else None
    st.sidebar.write(f"Slots found: {len(hits)}" if hits else "Nothing found")

st.sidebar.markdown("**Legend**")
for code, (name, color) in PRODUCTS.items():
    st.sidebar.markdown(
        f'<span style="background:{color};padding:0 8px;border-radius:2px">&nbsp;</span> {code} {name}',
        unsafe_allow_html=True,
    )
st.sidebar.markdown(
    f'<span style="background:{EMPTY_FILL};padding:0 8px;border-radius:2px">&nbsp;</span> Empty slot',
    unsafe_allow_html=True,
)

rows = sorted(df["row_id"].unique())
counts = df.groupby("row_id")["address"].nunique()
st.subheader("Warehouse plan")
st.caption("Number of occupied slots in each row")
for col, r in zip(st.columns(len(rows)), rows):
    col.metric(r, int(counts[r]))

default = first_row or ("K-008" if "K-008" in rows else rows[0])
current = st.radio("Row", rows, index=rows.index(default), horizontal=True)
sub = df[df["row_id"] == current]
lo, hi = max(1, sub["bay"].min() - 2), sub["bay"].max() + 2
total = (hi - lo + 1) * LEVELS * 3
occupied = sub["address"].nunique()
st.caption(f"Row {current}, bays {lo}–{hi}. Occupied {occupied} of {total} slots ({occupied / total:.0%}). "
           "Click any slot, empty or occupied, to see its details.")

key = f"rack_{current}"
state = st.session_state.get(key)
points = (state.get("selection") or {}).get("points", []) if state else []
picked = address_from_click(current, points[0]["x"], points[0]["y"]) if points else None

st.plotly_chart(rack_figure(sub, current, lo, hi, hits, picked), key=key,
                on_select="rerun", selection_mode="points", width="stretch")

if picked:
    st.subheader(f"Slot {picked}")
    zone, row, bay, level, slot = picked.split("-")
    here = df[df["address"] == picked]
    info = pd.DataFrame([{"Zone": zone, "Row": row, "Bay": bay, "Level": int(level), "Slot": slot,
                          "Max load": "750 kg", "Status": "Occupied" if len(here) else "Empty"}])
    st.dataframe(info, hide_index=True, width="stretch")
    if len(here):
        st.dataframe(here[list(COLUMN_NAMES)].rename(columns=COLUMN_NAMES).replace({"Batch": {"": "no data"}}),
                     hide_index=True, width="stretch")
    else:
        st.info("This slot is empty.")

if hits:
    st.subheader("Search results")
    st.dataframe(found[list(COLUMN_NAMES)].rename(columns=COLUMN_NAMES).replace({"Batch": {"": "no data"}}),
                 hide_index=True, width="stretch")
