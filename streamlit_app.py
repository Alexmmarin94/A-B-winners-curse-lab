"""Learn, choose, and analyze a reproducible hypothetical experiment portfolio."""

import streamlit as st

from app.scenarios import SCENARIOS, SCENARIO_BY_KEY
from app.style import inject_style
from app.playground import render_playground
from app.calibration_view import render_calibration
from app.configuration import make_config
from app.deep_dive import render_deep_dive
from app.benchmark_view import render_benchmark
from app.model_diagnostics import render_predictive_checks
from app.learning import render_learning
from app.explainers import render_research_context


st.set_page_config(page_title="The Winner's Curse Lab", page_icon="↗", layout="wide")
inject_style()
SECTIONS = ["Learn", "Choose", "Launch", "Understand", "Benchmark", "Methodology"]
# Introduce the expanded learning entrance once, preserving existing portfolios.
if not st.session_state.get("_learning_entry_v2"):
    st.session_state.section = "Learn"
    st.session_state._learning_entry_v2 = True
requested_page = st.query_params.get("page")
if requested_page in SECTIONS and requested_page != st.session_state.get("_last_page_url"):
    st.session_state.section = requested_page
st.session_state._last_page_url = requested_page
st.session_state.setdefault("section", "Learn")
st.session_state.setdefault("scenario", "retention")


def navigate(section: str) -> None:
    st.session_state.section = section


def choose(key: str) -> None:
    st.session_state.scenario = key


def introduction() -> None:
    render_learning(navigate)


def data_story() -> None:
    st.markdown('<div class="pipeline">Real archive → Empirical calibration → Independent simulation '
                '→ Treatment selection → Estimator benchmarking</div>', unsafe_allow_html=True)
    st.write("The archive CTR laboratory connects exploratory-data calibration to independent binomial simulations. "
             "The four product challenges use explicit hypothetical assumptions. "
             "Upworthy provides aggregate headline-test counts. Synthetic experiments have known "
             "true effects because we generate them; archived tests do not reveal their true effects.")
    st.write("Upworthy click-through effects will not be passed off as retention, activation, or paid-conversion "
             "effects. Those contexts use separately documented assumptions. Estimators are trained "
             "on observable historical data and assessed on independent portfolios, including stress scenarios.")
    render_research_context()


def challenges() -> None:
    st.markdown('<div class="eyebrow">YOU ARE THE EXPERIMENTATION LEAD</div>', unsafe_allow_html=True)
    st.title("Choose your next challenge.")
    st.markdown('<p class="lede">Choose the experience closest to your day-to-day work. '
                'Use a familiar metric to put yourself in the experimentation lead’s seat.</p>', unsafe_allow_html=True)
    st.write("Work on retention, acquisition, onboarding or monetization—or explore the separate headline CTR lab. "
             "Then choose which treatments you would launch at your own company, using the evidence available.")
    st.caption("Fictional product contexts · Baselines below are proposed scenario assumptions, not Upworthy estimates.")
    for row in (SCENARIOS[:2], SCENARIOS[2:]):
        for col, scenario in zip(st.columns(2, gap="medium"), row):
            with col, st.container(border=True):
                st.markdown(f'<div class="eyebrow">{scenario.category}</div>', unsafe_allow_html=True)
                st.subheader(f"{scenario.icon}  {scenario.title}")
                st.write(scenario.context)
                st.caption(f"{scenario.metric} · Proposed baseline {scenario.proposed_baseline:.0%}")
                selected = st.session_state.scenario == scenario.key
                st.button("Selected ✓" if selected else "Choose this challenge →",
                          key=f"choose_{scenario.key}", type="primary" if selected else "secondary",
                          on_click=choose, args=(scenario.key,), use_container_width=True)
    with st.container(border=True):
        st.markdown('<div class="eyebrow">SEPARATE ARCHIVE LABORATORY</div>', unsafe_allow_html=True)
        st.subheader("Explore headline CTR")
        st.write("Try synthetic A/B pairs calibrated to the Upworthy archive. Traffic patterns and an approximate "
                 "latent-effect distribution come from exploratory data; this is not a retention or monetization model.")
        st.button("Selected ✓" if st.session_state.scenario == "upworthy_ctr" else "Choose archive CTR →",
                  key="choose_upworthy_ctr", on_click=choose, args=("upworthy_ctr",),
                  type="primary" if st.session_state.scenario == "upworthy_ctr" else "secondary")
    scenario = SCENARIO_BY_KEY[st.session_state.scenario]
    st.subheader("Your brief")
    with st.container(border=True):
        a, b, c = st.columns([2, 1, 1])
        a.metric("Primary metric", scenario.metric)
        if scenario.key == "upworthy_ctr":
            try:
                b.metric("Median source pair CTR", f"{make_config(scenario.key).baseline:.2%}")
            except (OSError, ValueError, KeyError):
                b.warning("Calibration unavailable; restore the checked artifact.")
        else:
            b.metric("Proposed baseline", f"{scenario.proposed_baseline:.0%}")
        c.metric("Program period", "4 months")
        st.write(scenario.definition)
        st.caption("Experiments take place throughout the period; they need not run simultaneously. "
                   "Each experiment must complete its metric observation window.")
        with st.expander("Preview the intervention themes"):
            for intervention in scenario.interventions:
                st.write(f"• {intervention}")
            st.caption("Intervention themes only. Generated outcomes are shown in the playground.")
    st.info("The four product challenges use hypothetical assumptions. The archive CTR laboratory uses "
            "approximate empirical calibration. After launch analysis, compare Empirical Bayes with the simulated truth in one click.")
    st.button("Open experiment playground →", type="primary", on_click=navigate, args=("Launch",))


def methodology() -> None:
    st.markdown('<div class="eyebrow">TRANSPARENCY BY DESIGN</div>', unsafe_allow_html=True)
    st.title("The methodology lab")
    st.write("A place to inspect assumptions, compare estimators, and understand when they fail.")
    data_story()
    render_calibration()
    render_predictive_checks()
    with st.expander("Data foundation · what has been verified", expanded=True):
        st.write("Four local CSV packages were found: exploratory, confirmatory, holdout, and undeployed. "
                 "Their verified schema includes clickability_test_id, created_at, impressions, clicks, "
                 "significance, and winner. No randomization-risk column was found in these copies.")
        st.write("Implemented exclusion: remove complete experiments with package creation dates from "
                 "June 25, 2013 through January 10, 2014, including both calendar days. "
                 "Archive timestamps have an unknown timezone; we use their recorded dates without converting them. "
                 "Exclusion counts and overlapping reasons are available in the data-quality report above.")
        st.write("The archive’s significance field is not a usable p-value; winner records an editorial choice. "
                 "Undeployed packages will not be treated as completed tests.")
    with st.expander("Partition policy · defined before calibration"):
        st.write("Exploratory: develop cleaning and calibration. Confirmatory: evaluate frozen calibration choices. "
                 "Holdout: final observable-data validation after choices are frozen. "
                 "Inspecting file schemas does not fit a model or tune a parameter. "
                 "Deployed partitions were checked for experiment-ID overlap before fitting; none was found. "
                 "The final holdout check is now available above, so this partition is no longer untouched.")
    with st.expander("Model and benchmark status"):
        st.write("Implemented: hypothetical two-arm binomial simulations, observed rate differences, "
                 "standard errors, Newcombe–Wilson intervals, two-sided tests, and descriptive launch summaries.")
        st.write("Normal-normal Empirical Bayes correction and selected-treatment truth are shown together. "
                 "Priors are fitted offline on independent observable histories. Initial simulation checks show "
                 "undercoverage, particularly for CTR, and do not establish universal improvement.")
        st.write("Understand compares individual estimates with a Normal hierarchy that integrates program-level uncertainty. "
                 "Benchmark evaluates nine predefined mechanisms, including covariance-aware A/B/n comparisons and Holm selection.")
        st.write("A fixed-center robust mixture hierarchy is also fitted and benchmarked. Its assumptions and numerical "
                 "integration checks are explicit; robustness is not presumed.")
        st.warning("Main challenge cards remain A/B; A/B/n is available in Benchmark. "
                   "The main correction action uses Empirical Bayes; hierarchical comparisons are available in Understand.")
        st.write("One action calculates corrections and then reveals ground truth. Estimators receive "
                 "observable outcomes only. Hidden truth is reserved for evaluation and the explicit reveal.")
    with st.expander("What If You Only Run a Few Experiments?"):
        st.write("Selection can affect even one experiment when a favorable result determines whether it is reported "
                 "or launched. With only a few experiments, a historical prior may be poorly determined. "
                 "Keep unsuccessful results, report uncertainty, and separate launch decisions from ROI forecasts. "
                 "Independent replication can be useful; arbitrary percentage discounts are not a statistical correction.")
        st.write("A program running 2–10 experiments per quarter or roughly 30 per year may not have enough "
                 "comparable history to estimate a stable prior. More complicated hierarchies do not manufacture "
                 "that information. Use external priors only with a clear relevance argument and sensitivity checks.")


brand, status = st.columns([2, 1])
brand.markdown('<div class="brand"><span class="brand-mark">🧪</span> THE WINNER’S CURSE LAB</div>', unsafe_allow_html=True)
status.markdown('<div class="status">INTERACTIVE LAB &nbsp; / &nbsp; v0.9.1</div>', unsafe_allow_html=True)
st.radio("Explore the lab", SECTIONS, horizontal=True, key="section", label_visibility="collapsed")
# Keep explicit page links usable on reruns and when returning to an existing session.
if st.query_params.get("page") != st.session_state.section:
    st.query_params["page"] = st.session_state.section
st.session_state._last_page_url = st.session_state.section
active = st.session_state.section
stage = active
if active == "Launch":
    program = st.session_state.get("playgrounds", {}).get(st.session_state.scenario)
    if program is not None and getattr(program, "revealed_effects", None) is not None:
        stage = "Correct & reveal"
    elif program is not None and getattr(program, "corrections", None) is not None:
        stage = "Correct & reveal"
st.markdown('<div class="journey">' + ' <span>→</span> '.join(
    f'<span class="{"active" if step == stage else "future"}">{step}</span>'
    for step in ("Learn", "Choose", "Launch", "Correct & reveal", "Understand")
) + '</div>', unsafe_allow_html=True)
{"Learn": introduction, "Choose": challenges, "Launch": render_playground, "Understand": render_deep_dive,
 "Benchmark": render_benchmark, "Methodology": methodology}[active]()
# Continue from the foot of each screen without returning to the top navigation.
if active == 'Launch':
    current=st.session_state.get('playgrounds',{}).get(st.session_state.scenario)
    ready=current is not None and (current.revealed_effects is not None or
        (current.summary is not None and not current.summary.selected_ids))
    st.divider()
    st.button('Understand my results →',key='next_understand',type='primary',disabled=not ready,
              on_click=navigate,args=('Understand',))
    if not ready:st.caption('Analyze your launches, compare corrections with truth to continue the guided journey.')
elif active in ('Understand','Benchmark','Methodology'):
    destination,label={'Understand':('Benchmark','Compare methods in Benchmark →'),
                       'Benchmark':('Methodology','Explore the methodology →'),
                       'Methodology':('Choose','Try another challenge →')}[active]
    st.divider()
    st.button(label,key='next_section',type='primary',on_click=navigate,args=(destination,))
st.markdown('<div class="footer">The Winner’s Curse Lab &nbsp; · &nbsp; '
            'Selection is a decision. Estimation is a different question.</div>', unsafe_allow_html=True)
