"""Read frozen Monte Carlo reports; never run expensive jobs in the public UI."""
import json
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from src.models.artifacts import content_id,load_model
from src.simulation.engine import SimulationConfig
from app.explainers import LABELS,COLORS,render_model_guide

REPORT=Path(__file__).resolve().parents[1]/'data/benchmarks/stress_v1.json'
CASES={'matched':'Matched hypothetical program','null':'No true effects','heterogeneous':'Different experiment families',
       'rare_breakthroughs':'Rare breakthroughs','prior_shift':'Prior mismatch','temporal_shift':'Temporal shift',
       'low_power':'Low power','abn':'A/B/n · shared control','archive_ctr':'Archive-calibrated CTR'}
METRICS={'Mean absolute error (pp)':'mae_pp','RMSE (pp)':'rmse_pp','Selected-effect bias (pp)':'bias_pp',
         'Interval coverage':'coverage','Exceptional-effect MAE (pp)':'exceptional_mae_pp',
         'Cumulative absolute error (conversions)':'cumulative_absolute_error_conversions',
         'Decision regret (conversions per experiment)':'decision_regret_conversions',
         'Paired MAE change vs naive (pp)':'mae_change_vs_naive_pp'}


def load_report():
    report=json.loads(REPORT.read_text());identifier=report.pop('artifact_id')
    if content_id(report)!=identifier:raise ValueError('Benchmark checksum mismatch.')
    report['artifact_id']=identifier
    return report


def render_benchmark():
    st.markdown('<div class="eyebrow">MODEL & METHODOLOGY LAB</div>',unsafe_allow_html=True)
    st.title('Which estimator earns your trust?')
    st.write('Compare estimation accuracy and launch decisions across independent synthetic portfolios. '
             'A more complex model is not automatically a better model.')
    render_model_guide()
    try:report=load_report()
    except (OSError,ValueError,KeyError) as error:
        st.error(f'Benchmark unavailable: {error}. No example performance values are substituted.');return
    case=st.selectbox('Stress scenario',list(report['cases']),format_func=lambda k:CASES[k])
    result=report['cases'][case]
    cfg={**result['config'],'interventions':tuple(result['config']['interventions'])};config=SimulationConfig(**cfg)
    try:
        for method,identifier in result['model_ids'].items():
            if load_model(config,estimator=method)['artifact_id']!=identifier:raise ValueError('Model version changed; rebuild benchmark.')
    except (OSError,ValueError,KeyError) as error:
        st.error(f'Benchmark/model mismatch: {error}');return
    plain_cases={
        'matched':'A new portfolio from the same hypothetical program as the training history.',
        'null':'Nothing truly works. Any selected positive winner owes its apparent uplift to noise.',
        'heterogeneous':'Different experiment families behave differently. The historical model pools them.',
        'rare_breakthroughs':'Some treatments have unusually large real effects. Can correction preserve them?',
        'prior_shift':'The new program has stronger effects than its history. The models are not retrained.',
        'temporal_shift':'Effects and traffic change across the four months, while the historical model stays fixed.',
        'low_power':'Smaller tests produce noisier estimates. Historical information may have more influence.',
        'abn':'Four variants compete against one shared control. At most one can be launched.',
        'archive_ctr':'New synthetic headline pairs use the frozen Upworthy calibration and archive-trained models.'}
    st.info(plain_cases[case])
    a,b,c=st.columns(3)
    a.metric('Independent portfolios',report['replications'])
    b.metric('Experiments per portfolio',report['size'])
    c.metric('Selected treatments',result['selected_total'])
    st.caption(f"{result['unsupported_experiments']} experiments excluded from every estimator for unsupported approximations. "
               f"{result['methods']['naive']['selected_supported']} selected treatments remain in the common comparison.")
    metric_label=st.selectbox('Compare',list(METRICS));metric=METRICS[metric_label]
    metric_help={
        'mae_pp':('Lower is better','Average distance between estimate and truth among selected treatments. Errors cannot cancel.'),
        'rmse_pp':('Lower is better','Like average error, but penalizes large misses more strongly.'),
        'bias_pp':('Closer to zero is better','Average signed estimate minus truth. Positive means overstatement; opposite errors can cancel.'),
        'coverage':('Compare with the nominal 95%','How often each interval contains the true effect among selected treatments. A 95% label does not ensure 95% winner coverage.'),
        'exceptional_mae_pp':('Lower is better','Average error for selected treatments with unusually large true effects. This probes whether shrinkage erases real breakthroughs.'),
        'cumulative_absolute_error_conversions':('Lower is better','Error in the selected total under disjoint 10,000-user populations. This is a defined scenario, not general business ROI.'),
        'decision_regret_conversions':('Lower is better','Conversions missed by each model’s own launch policy versus a perfect-information policy. This tests decisions, not just estimation.'),
        'mae_change_vs_naive_pp':('Negative means improvement','Paired difference from the observed-result baseline. If the interval crosses zero, the mean advantage is uncertain in this simulation.')}
    direction,meaning=metric_help[metric]
    st.markdown(f'**{direction}.** {meaning}')
    fig=go.Figure();table=[]
    for method in report['methods']:
        value=result['methods'][method][metric];mean=value['mean'];interval=value['interval_95']
        if mean is None:continue
        fig.add_trace(go.Scatter(x=[mean],y=[LABELS[method]],mode='markers',marker=dict(size=13,color=COLORS[method]),
            error_x=dict(type='data',symmetric=False,array=[max(0,interval[1]-mean)] if interval else [0],
                         arrayminus=[max(0,mean-interval[0])] if interval else [0]),name=LABELS[method],
            hovertemplate='%{x:.4f}<extra>%{fullData.name}</extra>'))
        table.append({'Estimator':LABELS[method],'Mean':mean,'95% lower':interval[0] if interval else None,
                      '95% upper':interval[1] if interval else None,'Contributing portfolios':value['replications']})
    if table:
        if metric in ('bias_pp','mae_change_vs_naive_pp'):fig.add_vline(x=0,line_dash='dot')
        if metric=='coverage':fig.add_vline(x=.95,line_dash='dash',annotation_text='Nominal 95%')
        fig.update_layout(height=290,showlegend=False,xaxis_title=metric_label,yaxis_autorange='reversed',margin=dict(t=25,b=20,l=10,r=15))
        st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})
        with st.expander('Exact results and Monte Carlo intervals'):
            st.dataframe(pd.DataFrame(table),hide_index=True,use_container_width=True)
    else:st.info('No qualifying treatments in these replications; this metric is undefined, not zero.')
    st.caption('Whiskers are confidence intervals for mean metrics across independent portfolios, not individual-treatment '
               'credible intervals. Empty selected subsets are omitted from conditional metrics and counted by contributing portfolios.')
    st.subheader('Read the comparison correctly')
    st.write('Bias, MAE, RMSE and coverage use a fixed launch rule based on observed results. Decision regret instead '
             'compares each estimator’s own positive-mean launch policy against an oracle with known synthetic effects. '
             'These answer different questions.')
    if metric=='exceptional_mae_pp':
        st.caption(f"Exceptional means |true effect| ≥ {100*result['exception_threshold_probability']:.1f} pp, fixed before evaluation. "
                   f"Qualifying selected treatments: {result['methods']['naive']['exceptional_selected']}.")
    with st.expander('Selection, covariance, utility, and reproducibility'):
        st.write(result['description'])
        st.write(report['selection_policy']);st.write(report['fairness'])
        st.write(report['decision_utility']);st.write(report['cumulative_estimand'])
        st.write('A/B/n comparisons share one sampled control. All three Bayesian estimators use the full contrast covariance '
                 'matrix; the default decision chooses at most one treatment with Holm adjustment. Card challenges remain A/B.')
        st.code(f"Benchmark: {report['artifact_id']}\nSeeds: {result['seeds'][0]}–{result['seeds'][-1]}",language=None)
        for limitation in report['limitations']:st.write('• '+limitation)
        st.download_button('Download benchmark report',json.dumps(report,indent=2),file_name=REPORT.name,mime='application/json')
    st.warning('The robust mixture fixes its center at zero and its broad-component weight and scale multiplier. '
               'These are assumptions, not proof of robustness. Monte Carlo intervals condition on fitted histories; '
               'they do not include variation from refitting on new historical programs.')
