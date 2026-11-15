# The Beauty Formula — SIADS 521 Assignment 3

Interactive dashboard exploring skincare and cosmetics ingredient-label patterns.

## Run locally
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app downloads the INCIDB free sample archive from the public GitHub repository when it first runs. Internet access is required.

## Dataset
INCIDB free sample: https://github.com/INCIDB/cosmetics-skincare-inci-database  
The sample contains 200 products and 1,123 referenced ingredients. It is selected using an eligibility rule requiring at least 80% of linked ingredients to be CosIng-matched, followed by a seeded uniform draw from the eligible pool. This selection bias must be disclosed and limits generalization.

Product/brand/composition data are derived from Open Beauty Facts under ODbL 1.0. Ingredient enrichment uses the European Commission CosIng inventory. Attribution: Open Beauty Facts contributors and INCIDB. Adapted product data must remain under ODbL 1.0 (share-alike). Schema/documentation are CC BY 4.0.

## Important interpretation limits
- Category labels are derived from the source's original category tags using a simple keyword mapping documented in `app.py`; uncategorized records are retained.
- Ingredient-list length is a count of linked ingredient records, not concentration.
- Function labels are multi-valued and may be missing when no CosIng function was matched.
- Allergen and ingredient flags are informational, not medical advice.
- The dashboard currently uses a free sample, not the full 20,435-product corpus.

## Deployment
Push `app.py`, `requirements.txt`, and `README.md` to a GitHub repository. On Streamlit Community Cloud, create a new app, select the repository and `app.py`, then deploy. Test the public URL in a private browser window.
