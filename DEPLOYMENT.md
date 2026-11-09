# Streamlit Community Cloud deployment

Create an app at https://share.streamlit.io/ using the GitHub account that owns this repository.

| Setting | Value |
| --- | --- |
| Repository | `Alexmmarin94/A-B-winners-curse-lab` |
| Branch | `main` |
| Main file path | `streamlit_app.py` |
| Advanced settings → Python version | `3.12` |
| Secrets | Leave empty; the app needs no credentials |
| Suggested subdomain | `winners-curse-lab` (subject to availability) |

Alternatively, paste this entrypoint URL into the deployment form:
https://github.com/Alexmmarin94/A-B-winners-curse-lab/blob/main/streamlit_app.py

Click Deploy after checking those values. The application is not live until Community Cloud
finishes building it and provides its `streamlit.app` address. The optional subdomain is not reserved.
The `.python-version` file documents the local version; select 3.12 explicitly in Advanced settings.

## What the host installs and runs

- `requirements.txt` pins the tested runtime dependencies. No system packages are required.
- `.streamlit/config.toml` enables headless mode, disables source watching and usage telemetry,
  and supplies the visual theme. The host controls network binding; no localhost address is configured.
- All calibration, fitted model and benchmark artifacts are committed under `data/`.
  Raw CSVs, model fitting, external APIs and background simulation jobs are unnecessary at startup.
- Each viewer's selections live in their own Streamlit session and can reset after a reconnect or restart.
  Download a launch snapshot to retain a record. No database or persistent account data is configured.

## Verify the deployment

1. Check that the **Scientific and app checks** GitHub Actions workflow passes on the deployed commit.
2. Open Learn, choose a challenge and select two experiment cards in Launch.
3. Analyze, then use **Correct estimates & reveal truth**. Confirm observed, adjusted and true effects appear.
4. Open Understand: it should offer only the two selected experiments by default. Turn on the option
   to include unselected experiments and confirm truth remains hidden for those treatments.
5. Open Benchmark and Methodology. Try the headline CTR scenario as well.
6. Check desktop and narrow-screen layouts; automated AppTest checks do not render pixels.

Subsequent changes to the deployed branch are picked up by Community Cloud. Inspect its build logs
if a dependency installation fails. Do not substitute unsupported versions without running the tests.
The source project has 107 passing local tests; GitHub Actions provides the Linux verification.

## Local development

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.runOnSave true --server.fileWatcherType poll
```

The macOS development snapshot in `requirements.lock.txt` is retained for provenance. Production
and Linux CI use `requirements.txt` and `requirements-dev.txt`, respectively.

Official guides: [Deploy an app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
and [App dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies).
