"""Compact experiment cards and the explicit launch-analysis step."""

from dataclasses import asdict
from html import escape
import json

import plotly.graph_objects as go
import streamlit as st

from app.playground_state import Playground, restore_playground
from app.scenarios import SCENARIO_BY_KEY
from app.configuration import make_config, simulation_status
from app.corrections import render_actions
from src.simulation.engine import SimulationConfig


def get_playground() -> Playground:
    programs = st.session_state.setdefault("playgrounds", {})
    scenario = SCENARIO_BY_KEY[st.session_state.scenario]
    if scenario.key not in programs:
        programs[scenario.key] = Playground.create(make_config(scenario.key))
    elif not hasattr(programs[scenario.key].config, "calibration_id"):
        # Upgrade an existing checkpoint-2 browser session without regenerating its observations.
        programs[scenario.key].config = SimulationConfig(**asdict(programs[scenario.key].config))
    old = programs[scenario.key]
    if not isinstance(old, Playground) or not hasattr(old, "selection_version"):
        programs[scenario.key] = restore_playground(old)
    return programs[scenario.key]


def select_experiment(key: str, widget_key: str) -> None:
    get_playground().select(key, bool(st.session_state[widget_key]))


def clear_card_widgets() -> None:
    prefix=f"launch_{st.session_state.scenario}_"
    for key in list(st.session_state):
        if key.startswith(prefix):
            del st.session_state[key]


def sync_current_choices(program) -> None:
    for item in program.batch_items(program.batch):
        widget_key=f"launch_{program.config.scenario}_{program.config.fingerprint}_{item.experiment_id}"
        if widget_key in st.session_state and item.experiment_id in program.reviewed:
            program.select(item.experiment_id,bool(st.session_state[widget_key]))


def shuffle() -> None:
    get_playground().shuffle()
    clear_card_widgets()


def more_experiments() -> None:
    program=get_playground()
    sync_current_choices(program)
    if program.add_more():
        clear_card_widgets()


def edit_selection(widget_key: str) -> None:
    program=get_playground()
    chosen=set(st.session_state[widget_key])
    for key in program.current_ids:
        program.select(key,key in chosen)
        card_key=f"launch_{program.config.scenario}_{program.config.fingerprint}_{key}"
        if card_key in st.session_state:
            st.session_state[card_key]=key in chosen


def render_selection_review(program, visible):
    here=sum(program.selections.get(key,False) for key in program.current_ids)
    locked=[r for r in program.observed if r.experiment_id in program.active_ids-program.current_ids
            and program.selections.get(r.experiment_id)]
    st.markdown(f'<div class="scope-strip"><strong>{here+len(locked)} selected in total</strong> '
                f'· {here} in these {len(visible)} editable cards · 🔒 {len(locked)} saved</div>',unsafe_allow_html=True)
    if locked:
        with st.expander(f'🔒 Your saved selection · {len(locked)} treatments'):
            rounds={item.experiment_id:number+1 for number,batch in enumerate(program.locked_batches)
                    for item in program.batch_items(batch)}
            st.dataframe([{'Saved round':rounds[r.experiment_id],'Treatment':r.name,
                           'ID':r.experiment_id.rsplit('-',1)[-1]} for r in locked],hide_index=True,width='stretch')
            st.caption('These choices are locked. Shuffle and edits affect only the current cards. '
                       'To start all decisions again, use Generate a new portfolio in Advanced.')
    with st.expander('Review or edit this batch’s selection'):
        by_id={r.experiment_id:r for r in visible}
        widget_key=f'selection_review_{program.config.fingerprint}'
        st.session_state[widget_key]=[r.experiment_id for r in visible if program.selections.get(r.experiment_id)]
        st.multiselect('Your editable launch list · current batch',options=list(by_id),
            format_func=lambda key:f"{by_id[key].name} · {key.rsplit('-',1)[-1]}",
            key=widget_key,on_change=edit_selection,args=(widget_key,))
        st.caption('Analyze combines your saved choices with this editable selection. Shuffle discards this editable selection.')


def analyze() -> None:
    program = get_playground()
    sync_current_choices(program)
    program.analyze()


def replace_portfolio() -> None:
    old = get_playground()
    seed = int(st.session_state[f"new_seed_{old.config.scenario}"])
    config = SimulationConfig(**{**asdict(old.config), "interventions": old.config.interventions, "seed": seed})
    st.session_state.playgrounds[old.config.scenario] = Playground.create(config)
    # Widget state must not override the new portfolio's default policy, including same-seed replay.
    for key in list(st.session_state):
        if key.startswith(f"launch_{old.config.scenario}_"):
            del st.session_state[key]


def interval_html(low: float, estimate: float, high: float, extent: float) -> str:
    position = lambda x: 100 * (x + extent) / (2 * extent)
    left, middle, right = (position(x) for x in (low, estimate, high))
    label = escape(f"Observed effect {100 * estimate:+.2f} percentage points; "
                   f"95% confidence interval {100 * low:+.2f} to {100 * high:+.2f}.")
    return f'''<div role="img" aria-label="{label}" title="{label}"
      style="height:36px;position:relative;margin:5px 4px 0">
      <div style="position:absolute;top:15px;left:0;right:0;height:2px;background:#e0e7e6"></div>
      <div style="position:absolute;top:3px;bottom:5px;left:50%;border-left:1px dashed #788b90"></div>
      <div style="position:absolute;top:13px;left:{left:.3f}%;width:{right-left:.3f}%;height:6px;
        border-radius:4px;background:#62a898"></div>
      <div style="position:absolute;top:10px;left:calc({middle:.3f}% - 6px);width:12px;height:12px;
        border-radius:50%;background:#176f61;border:2px solid white"></div>
      </div>'''


def show_summary(program: Playground) -> None:
    summary = program.summary
    if summary is None:
        return
    st.divider()
    st.markdown('<div class="eyebrow">YOUR LAUNCH SUMMARY</div>', unsafe_allow_html=True)
    st.subheader("What are you taking forward?")
    a, b, c = st.columns(3)
    a.metric("Experiments reviewed", len(summary.reviewed_ids))
    b.metric("Treatments selected", len(summary.selected_ids))
    c.metric("Mean reported effect", "—" if summary.mean_reported_effect is None
             else f"{summary.mean_reported_effect * 100:+.2f} pp")
    st.caption("Reviewed here means the current batch plus saved rounds; discarded batches are excluded. Each selected experiment has equal weight. "
               "This is an observed mean for your chosen treatments, not a forecast of cumulative business impact.")
    if not summary.selected_ids:
        st.info("No treatments selected. There is no selected-effect mean to estimate. "
                "Choose a treatment above and analyze again, or keep this no-launch decision.")
    else:
        selected = set(summary.selected_ids)
        reviewed = [item for item in program.observed if item.experiment_id in summary.reviewed_ids]
        effects = [item.estimate.effect * 100 for item in reviewed]
        lower, upper = min(min(effects), 0) - 0.25, max(max(effects), 0) + 0.25
        bins = dict(start=lower, end=upper, size=max((upper - lower) / 12, 0.1))
        fig = go.Figure()
        for label, included, color in (("Not selected", False, "#aabbbb"), ("Selected", True, "#157566")):
            values = [item.estimate.effect * 100 for item in reviewed
                      if (item.experiment_id in selected) == included]
            fig.add_trace(go.Histogram(x=values, name=label, xbins=bins, marker_color=color,
                                      hovertemplate="Observed effect bin: %{x} pp<br>Experiments: %{y}<extra>%{fullData.name}</extra>"))
        fig.add_vline(x=0, line_dash="dot", line_color="#72858b")
        fig.update_layout(height=290, barmode="stack", bargap=0.12, margin=dict(l=12, r=12, t=15, b=10),
                          xaxis_title="Observed treatment − control (percentage points)",
                          yaxis_title="Experiments", yaxis=dict(dtick=1),
                          legend=dict(orientation="h", y=1.15), paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#172D35"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.write("Selection changes which estimates enter this summary. A positive mean alone does not "
                 "tell us how much is genuine impact or sampling noise. That comparison will require "
                 "the combined correction and truth comparison below.")
    render_actions(program)
    payload = {**program.snapshot(), "status": simulation_status(program.config)}
    st.download_button("Download launch snapshot", data=json.dumps(payload, indent=2),
                       file_name=f"launches-{program.config.fingerprint}.json", mime="application/json")


def render_playground() -> None:
    try:
        program = get_playground()
    except (OSError, ValueError, KeyError) as error:
        st.error(f"This portfolio cannot be loaded: {error}. No substitute simulation has been generated.")
        return
    scenario = SCENARIO_BY_KEY[program.config.scenario]
    st.markdown('<div class="eyebrow">CHOOSE WHAT EARNS A LAUNCH</div>', unsafe_allow_html=True)
    st.title("Promising results. Your call.")
    st.write(f"**{scenario.title}** · {scenario.metric} · Four months of experiments")
    st.markdown('**Act as the experimentation lead at your company. Which treatments would you actually launch?** '
                'Review the evidence, tick the changes you would ship and untick those you would hold back.')
    st.caption('Some cards are checked for you by the starting rule below. They are suggestions, not recommendations. '
               'Edit the current choices, replace them with Shuffle, or save them with More experiments.')
    st.warning(simulation_status(program.config))
    if program.ever_revealed:
        st.caption("You have already revealed truth from this portfolio. Subsequent selections are no longer a blind exercise.")
    if program.config.calibration_id:
        st.caption("One outcome-blind pair per source experiment informs calibration. The synthetic cards are A/B comparisons, "
                   "not full A/B/n tests. Intervention names and the four-month schedule are fictional.")
    st.caption("Default: select positive effects with unadjusted two-sided p < 0.05. "
               "You can override every choice. One treatment per A/B experiment; no portfolio-wide multiplicity correction.")
    with st.expander("How to read these cards"):
        st.write("An uplift of +1 percentage point (pp) means a change such as 24% → 25%, not a 1% relative increase. "
                 "The dot is the observed treatment-minus-control difference. The bar is a marginal 95% confidence "
                 "interval; the dashed line is zero. All cards in this portfolio share the same horizontal scale.")
        st.write("These intervals describe pre-selection uncertainty and need not cover 95% of selected winners. "
                 "Significance is not an effect-size accuracy guarantee. Experiments occurred across months 1–4; "
                 "all outcomes are assumed mature, including the full metric observation window.")
    st.markdown('**🔀 Shuffle** replaces these nine cards and discards their selections. '
                '**➕ More experiments** locks in your current choices and brings another nine cards. '
                'Saved choices stay protected while you edit or shuffle the new batch.')
    visible = program.visible()
    extent = max(max(abs(item.estimate.ci_low), abs(item.estimate.ci_high)) for item in program.observed) * 1.1
    for start in range(0, len(visible), 3):
        for col, item in zip(st.columns(3, gap="medium"), visible[start:start + 3]):
            e = item.estimate
            with col, st.container(border=True, key=f"experiment_card_{item.experiment_id}"):
                st.caption(f"MONTH {item.month} · A/B · {item.experiment_id.rsplit('-', 1)[-1]}")
                st.subheader(item.name)
                st.caption(item.metric)
                st.markdown(f'<div class="effect-value">{e.effect * 100:+.2f}<span> pp observed</span></div>',
                            unsafe_allow_html=True)
                st.html(interval_html(e.ci_low, e.effect, e.ci_high, extent))
                st.caption(f"95% CI [{e.ci_low * 100:+.2f}, {e.ci_high * 100:+.2f}] pp · SE {e.standard_error * 100:.2f} pp")
                significance = "Significant" if e.significant else "Not significant"
                p_label = "< 0.001" if e.p_value < 0.001 else f"= {e.p_value:.3f}"
                st.caption(f"{significance} · p {p_label}")
                widget_key = f"launch_{program.config.scenario}_{program.config.fingerprint}_{item.experiment_id}"
                # Streamlit clears widget keys when a batch is hidden; keep durable selections separately.
                if widget_key not in st.session_state:
                    st.session_state[widget_key] = program.selections[item.experiment_id]
                st.checkbox("Launch this treatment", key=widget_key,
                            on_change=select_experiment, args=(item.experiment_id, widget_key))
                with st.expander("Observed counts"):
                    st.write(f"Control: {item.control_successes:,} / {item.control_n:,} "
                             f"({item.control_successes / item.control_n:.2%})")
                    st.write(f"Treatment: {item.treatment_successes:,} / {item.treatment_n:,} "
                             f"({item.treatment_successes / item.treatment_n:.2%})")
                    st.caption(f"P-value: {e.p_method}. CI: Newcombe–Wilson. SE: unpooled plug-in binomial.")
    render_selection_review(program, visible)
    left,right=st.columns(2)
    left.button('Shuffle 🔀',key='shuffle',on_click=shuffle,width='stretch')
    right.button('More experiments ➕',key='more_experiments',on_click=more_experiments,
                 disabled=not program.can_add_more,width='stretch')
    if not program.can_add_more:
        st.info('😊 You’ve built a full demo selection! Three rounds are safely saved. '
                'You can still edit or shuffle these last nine cards, then analyze your launches. '
                'That is plenty to explore the Winner’s Curse—no more rounds needed.')
    if program.summary_invalidated:
        st.info("Your reviewed set or selections changed. Analyze again to update the launch summary.")
    st.button("Analyze My Launches", type="primary", on_click=analyze, key="analyze_launches")
    show_summary(program)
    with st.expander("Advanced · assumptions and reproducibility"):
        st.caption('Shuffle uses another batch from a fixed seeded pool and never changes an experiment’s counts. '
                   'Discarded batches may return after further shuffles, with their default choices reset. '
                   'Saved rounds never return to the editable pool.')
        st.code(f"Generator: {program.config.version}\nSeed: {program.config.seed}\nPortfolio: {program.config.fingerprint}", language=None)
        if program.config.calibration_id:
            st.code(f"Calibration: {program.config.calibration_id}", language=None)
            st.write("Traffic and pooled CTR anchors are sampled jointly from an exploratory-data reservoir. "
                     "Latent log-odds effects come from a fitted symmetric histogram mixture that accounts for "
                     "approximate measurement noise. True arm probabilities are placed around the pooled anchor on the log-odds scale.")
            st.caption("Effect/design independence, sparse-count approximations, and weak tail identification remain limitations. "
                       "Inspect the Methodology tab for exclusions, bootstrap intervals, and confirmatory checks.")
        else:
            hypothetical_assumptions(program)
        st.caption("CI and p-value use different methods and may disagree very close to a threshold. "
                   "Selection uses p < 0.05. Understand compares hierarchical estimates; Benchmark includes shared-control A/B/n stress tests.")
        st.markdown("Interval method: [Newcombe (1998)](https://pubmed.ncbi.nlm.nih.gov/9595617/).")
        st.download_button("Download simulation configuration", json.dumps(asdict(program.config), indent=2),
                           file_name=f"config-{program.config.fingerprint}.json", mime="application/json")
        st.number_input("Seed for a new portfolio", min_value=0, max_value=2**32 - 1,
                        value=program.config.seed + 1 if program.config.seed < 2**32 - 1 else 0,
                        step=1, key=f"new_seed_{program.config.scenario}")
        st.caption("Generating replaces this challenge’s portfolio and resets its selections and summary. "
                   "Other challenges are preserved. Reusing a seed reproduces the same results.")
        st.button("Generate a new portfolio", on_click=replace_portfolio, key="generate_portfolio")


def hypothetical_assumptions(program: Playground) -> None:
    st.write("Assumed baseline: " + f"{program.config.baseline:.0%}. Independent binomial arms; "
                 "control sample size is log-uniform from 2,500–20,000, with treatment allocation "
                 "between 80% and 120% of control. Baseline is constant within the program.")
    st.write("Hypothetical log-odds-change mixture: 25% exactly zero, 50% uniform [−0.10, 0.12], "
                 "15% uniform [0.12, 0.30], and 10% uniform [−0.30, −0.12]. "
                 "These assumptions have not been empirically estimated. No seed or portfolio is "
                 "rejected for lacking a desired mix of significant or positive results.")
