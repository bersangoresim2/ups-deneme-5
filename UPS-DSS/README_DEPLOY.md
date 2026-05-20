# UPS DSS Streamlit Deployment

## Streamlit Community Cloud

1. Upload this `UPS-DSS` folder to a GitHub repository.
2. Do not upload the local `venv` folder.
3. In Streamlit Community Cloud, create a new app from the GitHub repository.
4. Set the main file path to:

```text
app_login.py
```

5. Deploy the app.

## Required files

- `app_login.py` is the Streamlit entry point.
- `requirements.txt` lists the Python packages Streamlit Cloud must install.
- `runtime.txt` requests Python 3.12 for deployment compatibility.
- `assets/`, `src/`, `data/denemeDATA.xlsx`, JSON files, and `applications.xlsx` are used by the app.

## Important note

`users.json` contains application login data. If this app will be public, move real credentials to Streamlit secrets or replace them with demo accounts before publishing.
