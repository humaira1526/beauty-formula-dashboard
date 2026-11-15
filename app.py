
import io
import zipfile
from pathlib import Path
from urllib.request import urlopen

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="The Beauty Formula", page_icon="✦", layout="wide")

DATA_URL = "https://raw.githubusercontent.com/INCIDB/cosmetics-skincare-inci-database/master/samples/incidb_free_samples.zip"

st.markdown("""
<style>
    .stApp {background: #00000;}
    h1, h2, h3 {color: #493b35;}
    [data-testid="stMetric"] {background: #fff; padding: 14px; border-radius: 12px; border: 1px solid #eee2da;}
    [data-testid="stMetricValue"] {
    color: black !important;
    }
    [data-testid="stMetricLabel"] {
        color: black !important;
    }
    [data-testid="stMetricDelta"] {
        color: black !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner="Loading the public cosmetics dataset…")
def load_tables():
    raw = urlopen(DATA_URL, timeout=30).read()
    zf = zipfile.ZipFile(io.BytesIO(raw))
    tables = {}
    for member in zf.namelist():
        base = Path(member).name.lower()
        if base.endswith(".csv"):
            key = base.replace(".csv", "")
            with zf.open(member) as f:
                tables[key] = pd.read_csv(f, sep="|", dtype_backend="numpy_nullable")
    return tables

def find_table(tables, fragment):
    for name, df in tables.items():
        if fragment in name:
            return df
    raise KeyError(f"Could not find a table containing '{fragment}'. Found: {list(tables)}")

def classify_category(tags):
    """Create a broad, transparent category from Open Beauty Facts source tags."""
    if pd.isna(tags) or not str(tags).strip():
        return "Uncategorized"
    value = str(tags).lower()
    rules = [
        ("Skincare", ["skin care", "skincare", "face cream", "moisture", "serum", "cleanser", "toner", "mask", "exfoliate"]),
        ("Makeup", ["make-up", "makeup", "lipstick", "mascara", "foundation", "eyeshadow", "blush", "concealer"]),
        ("Haircare", ["hair", "shampoo", "conditioner"]),
        ("Body care", ["body", "hand cream", "bath", "soap"]),
        ("Sun care", ["sun", "sunscreen", "suncare", "spf"]),
        ("Fragrance", ["perfume", "fragrance", "eau de"]),
    ]
    for label, words in rules:
        if any(word in value for word in words):
            return label
    return "Other tagged"

@st.cache_data(show_spinner="Preparing product and ingredient tables…")
def prepare_data():
    tables = load_tables()
    products = find_table(tables, "products").copy()
    ingredients = find_table(tables, "ingredients").copy()
    links = find_table(tables, "product_ingredients").copy()
    brands = find_table(tables, "brands").copy()

    products["product_id"] = pd.to_numeric(products["product_id"], errors="coerce")
    links["product_id"] = pd.to_numeric(links["product_id"], errors="coerce")
    links["ingredient_id"] = pd.to_numeric(links["ingredient_id"], errors="coerce")
    ingredients["ingredient_id"] = pd.to_numeric(ingredients["ingredient_id"], errors="coerce")
    products = products.dropna(subset=["product_id"]).drop_duplicates("product_id")
    links = links.dropna(subset=["product_id", "ingredient_id"]).drop_duplicates(["product_id", "ingredient_id"])
    ingredients = ingredients.dropna(subset=["ingredient_id"]).drop_duplicates("ingredient_id")

    if "brand_id" in products.columns and "brand_id" in brands.columns:
        products = products.merge(brands[["brand_id", "name"]].rename(columns={"name":"brand"}), on="brand_id", how="left")
    else:
        products["brand"] = "Unknown"

    products["brand"] = products["brand"].fillna("Unknown")
    products["product_name"] = products["name"].fillna("Unnamed product")
    products["category"] = products.get("obf_categories_tags", pd.Series(index=products.index, dtype="object")).apply(classify_category)

    merged = links.merge(products[["product_id", "product_name", "brand", "category"]], on="product_id", how="inner")
    merged = merged.merge(ingredients, on="ingredient_id", how="left")
    merged["inci_name"] = merged["inci_name"].fillna("Unresolved / unavailable")
    merged["functions"] = merged["functions"].fillna("Function not recorded")
    merged["position_index"] = pd.to_numeric(merged.get("position_index"), errors="coerce")
    counts = merged.groupby("product_id")["ingredient_id"].nunique().rename("ingredient_count")
    products = products.merge(counts, on="product_id", how="left")
    products["ingredient_count"] = products["ingredient_count"].fillna(0).astype(int)
    return products, merged

try:
    products, detail = prepare_data()
except Exception as exc:
    st.error("The dataset could not be loaded. Check the source archive and try again.")
    st.exception(exc)
    st.stop()

st.title("✦ The Beauty Formula")
st.caption("An interactive exploration of ingredient patterns across skincare and cosmetic product labels.")
st.markdown("**Research question:** How do product categories differ in the ingredients and ingredient functions listed on their labels?")

with st.sidebar:
    st.header("Explore the data")
    categories = sorted(products["category"].dropna().unique().tolist())
    selected = st.multiselect("Product category", categories, default=categories)
    top_n = st.slider("Number of top ingredients", 5, 20, 12)
    st.caption("The category filter updates every chart below.")

filtered_products = products[products["category"].isin(selected)].copy()
filtered_ids = filtered_products["product_id"].tolist()
filtered = detail[detail["product_id"].isin(filtered_ids)].copy()

if filtered_products.empty or filtered.empty:
    st.warning("No records match the selected categories. Select at least one category.")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("Products in view", f"{filtered_products['product_id'].nunique():,}")
c2.metric("Ingredient records", f"{len(filtered):,}")
c3.metric("Distinct ingredients", f"{filtered['ingredient_id'].nunique():,}")

st.divider()

# 1. Bar chart: most frequently listed ingredients
st.subheader("1. Which ingredients appear most often?")
top_ingredients = (filtered.groupby("inci_name")["product_id"].nunique()
                   .sort_values(ascending=False).head(top_n).reset_index(name="products"))
fig1 = px.bar(top_ingredients.sort_values("products"), x="products", y="inci_name",
              orientation="h", labels={"products":"Number of products","inci_name":"Ingredient"},
              color="products", color_continuous_scale="pinkyl")
fig1.update_layout(coloraxis_showscale=False, height=470, margin=dict(l=10,r=10,t=20,b=10))
st.plotly_chart(fig1, use_container_width=True)

left, right = st.columns(2)

# 2. Histogram: ingredient-list lengths
with left:
    st.subheader("2. How long are ingredient lists?")
    fig2 = px.histogram(filtered_products, x="ingredient_count", nbins=18,
                        labels={"ingredient_count":"Number of listed ingredients"},
                        color_discrete_sequence=["#b77b86"])
    fig2.update_layout(height=400, margin=dict(l=10,r=10,t=20,b=10))
    st.plotly_chart(fig2, use_container_width=True)

# 3. Sunburst: category -> function
with right:
    st.subheader("3. What functions appear in each category?")
    role_rows = filtered.assign(function=filtered["functions"].astype(str).str.split(";")).explode("function")
    role_rows["function"] = role_rows["function"].str.strip()
    role_rows = role_rows[role_rows["function"].ne("") & role_rows["function"].notna()]
    sun = role_rows.groupby(["category","function"])["product_id"].nunique().reset_index(name="products")
    fig3 = px.sunburst(sun, path=["category","function"], values="products",
                       color="products", color_continuous_scale="pinkyl")
    fig3.update_layout(height=400, margin=dict(l=10,r=10,t=20,b=10))
    st.plotly_chart(fig3, use_container_width=True)

# 4. Sankey: category -> ingredient function (new-to-course method)
st.subheader("4. How do product categories connect to ingredient functions?")
st.caption("Sankey diagram (new-to-course method): link width represents the number of product–ingredient records in each category/function pathway.")
flow = filtered.assign(function=filtered["functions"].astype(str).str.split(";")).explode("function")
flow["function"] = flow["function"].str.strip()
flow = flow[flow["function"].ne("") & flow["function"].notna()]
flow_counts = flow.groupby(["category","function"]).size().reset_index(name="records")
flow_counts = flow_counts.sort_values("records", ascending=False).head(35)
if not flow_counts.empty:
    labels = list(flow_counts["category"].drop_duplicates()) + list(flow_counts["function"].drop_duplicates())
    index = {label:i for i,label in enumerate(labels)}
    fig4 = go.Figure(data=[go.Sankey(
        node=dict(label=labels, pad=14, thickness=18),
        link=dict(source=flow_counts["category"].map(index),
                  target=flow_counts["function"].map(index),
                  value=flow_counts["records"])
    )])
    fig4.update_layout(height=520, margin=dict(l=10,r=10,t=20,b=10))
    st.plotly_chart(fig4, use_container_width=True)
else:
    st.info("No ingredient-function links are available for this selection.")

st.divider()
st.subheader("Product-level detail")
st.caption("Use this table to inspect the records behind the aggregate views.")
show_cols = [c for c in ["product_name","brand","category","ingredient_count"] if c in filtered_products.columns]
st.dataframe(filtered_products[show_cols].sort_values("product_name"), use_container_width=True, hide_index=True)

st.markdown("""
---
**Data note:** This dashboard describes ingredients recorded on product labels. Ingredient order is a label-order proxy, not an exact concentration measure. A function or regulatory flag being absent may mean the source did not provide a match; it does not prove that an ingredient has no function or is risk-free. This dashboard is for data exploration, not medical advice.

**Dataset:** INCIDB free sample (200 products), derived from Open Beauty Facts and enriched with European Commission CosIng information. The sample is intentionally selected from products with at least 80% CosIng-matched linked ingredients, so it is not a random representation of the entire cosmetics market. Product data are ODbL 1.0; schema/documentation are CC BY 4.0. Attribute Open Beauty Facts contributors and INCIDB; share adapted product data under ODbL.
""")
