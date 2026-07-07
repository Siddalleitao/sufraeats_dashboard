# SufraEats — Dubai Delivery Dashboard

An interactive Streamlit dashboard built on **cleaned, merged** SufraEats order
and restaurant data (Jan–May 2025). It answers the core capstone question —
*which Dubai zone should SufraEats expand into?* — plus supporting views for
cuisine priorities, seasonality, promotions, and customer behaviour.

## Files

| File | Purpose |
|---|---|
| `app.py` | The Streamlit dashboard |
| `sufraeats_clean_merged.csv` | Cleaned & merged dataset produced by the analysis notebook — the dashboard reads this directly, no cleaning logic lives in `app.py` |
| `requirements.txt` | Python dependencies |

If you re-run the analysis notebook and it produces an updated
`sufraeats_clean_merged.csv`, just replace this file (keep the same name) —
the dashboard will pick up the new data automatically.

## Run it locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL Streamlit prints (usually `http://localhost:8501`).

## Deploy to Streamlit Community Cloud (with Git)

**1. Create a GitHub repo and push these three files**

```bash
cd streamlit_app
git init
git add app.py requirements.txt sufraeats_clean_merged.csv README.md
git commit -m "SufraEats dashboard"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git push -u origin main
```

(Create the empty repo on GitHub first — via github.com → New repository —
then copy its URL into the `git remote add` command above.)

**2. Deploy on Streamlit Cloud**

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. Click **"Create app"** → **"Deploy a public app from GitHub"**.
3. Select your repository, branch `main`, and set **Main file path** to `app.py`.
4. Click **Deploy**.

Streamlit Cloud will install `requirements.txt` automatically and launch the
app — you'll get a public `*.streamlit.app` URL to share with your team or
include in the presentation.

**Updating the live app later:** just `git push` any changes (e.g. an updated
CSV or a new chart) to the same branch — Streamlit Cloud redeploys
automatically within a minute or two.

## Notes on the data shown

- **Realised revenue** = commission on **Delivered** orders only, applied to
  `(basket_value − discount_amount)`, plus delivery fees. Cancelled and
  Refunded orders contribute AED 0 — they're shown in the cancellation/refund
  rate metrics instead.
- **Gross order value** = basket value before discounts/cancellations — shown
  alongside realised revenue on purpose, since the two can rank zones
  differently.
- Orders whose restaurant couldn't be matched (~4% of orders — see the
  analysis notebook) are included in platform-wide totals but excluded from
  zone/cuisine breakdowns, since neither can be determined for them. There's
  a sidebar toggle to include them in platform totals if desired.
