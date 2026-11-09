"""One comparison action: observable-only correction followed by checked truth replay."""
from dataclasses import asdict
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from src.models.artifacts import MODEL_DIR,load_model
from app.explainers import render_estimate_key


def apply_correction(program):
    """Estimate from observations first; then replay truth for the same selection."""
    try:
        program.correct()
        program.reveal()
    except (OSError,ValueError,KeyError) as error:
        program.stage_error=f'Comparison unavailable: {error}'


def render_actions(program):
    compatible=True
    try:
        load_model(program.config)
    except (OSError,ValueError,KeyError) as error:
        compatible=False
        st.warning(f'The historical model is unavailable or incompatible: {error}')
    has_selected=bool(program.summary.selected_ids)
    complete=program.corrections is not None and program.revealed_effects is not None
    st.button('Correction & truth shown ✓' if complete else 'Correct estimates & reveal truth',
              on_click=apply_correction,args=(program,),key='apply_correction',
              disabled=not has_selected or not compatible or complete,
              type='secondary' if complete else 'primary',use_container_width=True)
    if not has_selected:
        st.caption('No treatments in the analyzed selection. Select a checkbox, then click Analyze My Launches again.')
    elif not complete:
        st.caption(f'Ready to compare {len(program.summary.selected_ids)} selected treatment(s). '
                   'One click shows the estimates, simulated truth and accuracy insights together. '
                   'The model calculates its correction before the answer key is opened.')
    if program.stage_error:
        st.error(program.stage_error)
    if complete:
        render_correction(program)


def render_correction(program):
    st.divider()
    st.markdown('<div class="eyebrow">CORRECT · NORMAL–NORMAL EMPIRICAL BAYES</div>',unsafe_allow_html=True)
    st.subheader('A second estimate, informed by history.')
    artifact=program.correction_model
    st.write('**Empirical Bayes is a second estimate, not the answer.** It combines the observed result with '
             'a center and spread fitted from comparable historical experiments. How far it moves depends on precision.')
    st.caption(artifact['training']['description'])
    render_estimate_key(program.revealed_effects is not None)
    if program.corrections:
        st.plotly_chart(mean_effect_figure(program,include_truth=True),width='stretch',config={'displayModeBar':False},key='correction_overview')
        st.caption(f"All three means use the same {len(program.corrections)} supported selected treatments. "
                   'These are averages, not summed business impact or uncertainty intervals. Compare each estimate with the gold answer.')
    render_reveal(program)
    st.caption('The prior is fitted offline using observed historical effects and measurement uncertainty. '
               'No hidden effects or results from this evaluation portfolio were used to fit it.')
    st.warning('Approximate, conditional posterior intervals: prior parameters and measurement SEs are treated '
               'as known. These intervals omit fitting uncertainty and can under-cover selected or exceptional effects. '
               'The posterior mean is not ground truth.')
    try:
        diagnostics = json.loads((MODEL_DIR/'validation_v1.json').read_text())
        check = diagnostics['scenarios'][program.config.scenario]
        if check['artifact_id'] == artifact['artifact_id']:
            coverage = check['metrics']['posterior_coverage']['mean']
            if coverage is not None and coverage < .95:
                st.warning(f'Known calibration limitation: these nominal 95% intervals covered only {coverage:.1%} '
                           f'of supported selected effects on average across {diagnostics["replications"]} independent '
                           'validation portfolios. Do not treat them as calibrated 95% uncertainty for winners.')
            mae_change = check['metrics']['paired_mae_change']['mean']
            if mae_change is not None and mae_change > 0:
                st.warning(f'In those initial checks, correction increased average absolute error by '
                           f'{100*mae_change:.3f} pp. This is a demonstrated failure case for this model, '
                           'not a recommended adjustment for this scenario.')
    except (OSError, ValueError, KeyError):
        st.info('Coverage diagnostics could not be loaded. No coverage guarantee is made.')
    supported=program.corrections
    if supported:
        col1,col2=st.columns(2)
        col1.metric('Mean adjusted effect',f"{100*np.mean([r.mean for r in supported.values()]):+.2f} pp")
        col2.metric('Treatments with corrections',f'{len(supported)} / {len(program.summary.selected_ids)}')
        st.caption('Equal-weight mean of supported selected treatments only; not cumulative business impact.')
    for key,reason in program.unsupported.items():
        item=next(r for r in program.observed if r.experiment_id==key)
        st.warning(f'{item.name}: {reason}')
    st.write('Each estimate moves toward the historical mean. Less precise results generally move more. '
             'This is not a fixed percentage discount: a result below the prior mean can move upward.')
    render_comparison(program)
    with st.expander('Adjusted estimates and shrinkage details'):
        rows=[]
        by_id={r.experiment_id:r for r in program.observed}
        for key,p in supported.items():
            item=by_id[key]
            row={'Experiment':item.name,'Observed (pp)':100*item.estimate.effect,
                 'Posterior mean (pp)':100*p.mean,'95% CrI low (pp)':100*p.ci_low,
                 '95% CrI high (pp)':100*p.ci_high,'Prior weight (%)':100*p.prior_weight,
                 'Adjustment (pp)':100*(p.mean-item.estimate.effect),'Model SE (pp)':100*p.model_se}
            if program.revealed_effects is not None:
                truth=program.revealed_effects[key]
                change=abs(p.mean-truth)-abs(item.estimate.effect-truth)
                row['True simulated effect (pp)']=100*truth
                row['Accuracy change']='Improved' if change < -1e-12 else 'Worsened' if change > 1e-12 else 'Unchanged'
            rows.append(row)
        if rows:
            st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
        st.caption('Prior weight is the fraction of the distance toward the prior mean, not the percent reduction '
                   'in reported uplift. Model SE uses half-count-stabilized binomial variance; card SE is the raw plug-in SE.')
    with st.expander('Historical model, uncertainty, and initial diagnostics'):
        fit=artifact['fit']; uncertainty=artifact['fitting_uncertainty']
        st.write(f"Historical prior mean: {100*fit['mean']:+.3f} pp; prior SD: {100*np.sqrt(fit['variance']):.3f} pp. "
                 f"Fitted from {fit['n_history']:,} observations.")
        st.write(f"Bootstrap 95% range for prior mean: [{100*uncertainty['mean_interval_95'][0]:+.3f}, "
                 f"{100*uncertainty['mean_interval_95'][1]:+.3f}] pp; for prior SD: "
                 f"[{100*uncertainty['sd_interval_95'][0]:.3f}, {100*uncertainty['sd_interval_95'][1]:.3f}] pp.")
        st.caption('Bootstrap ranges describe prior-fitting uncertainty; they are not integrated into the displayed posterior intervals.')
        render_model_diagnostics(artifact,program.config.scenario)
        st.code(f"Model: {artifact['model_version']}\nArtifact: {artifact['artifact_id']}",language=None)
        st.download_button('Download fitted model',json.dumps(artifact,indent=2),
                           file_name=f"{program.config.scenario}-normal-normal.json",mime='application/json')
        st.caption('Understand provides separately fitted hierarchical Normal and fixed-center robust-mixture comparisons. '
                   'The main correction action remains normal-normal Empirical Bayes.')


def render_reveal(program):
    st.markdown('<div class="eyebrow">REVEAL · SIMULATED GROUND TRUTH</div>',unsafe_allow_html=True)
    st.subheader('Now we can check what was real.')
    st.write('**The gold diamond is the answer set by the simulator.** The teal dot is the model’s estimate '
             'of that answer. It was calculated without access to the gold value. Compare each estimate with gold '
             'to judge accuracy; a more conservative estimate is not automatically a better one.')
    truth=program.revealed_effects
    st.metric('Mean true effect · all selected treatments',f'{100*np.mean(list(truth.values())):+.2f} pp')
    st.caption('Known only because these experiments are synthetic. A negative or zero mean is retained as-is; '
               'no ratio to true impact is calculated.')
    by_id={r.experiment_id:r for r in program.observed}
    if program.corrections:
        keys=list(program.corrections)
        naive=np.array([abs(by_id[k].estimate.effect-truth[k]) for k in keys])
        adjusted=np.array([abs(program.corrections[k].mean-truth[k]) for k in keys])
        difference=adjusted-naive
        improved=int(np.sum(difference < -1e-12)); worsened=int(np.sum(difference > 1e-12))
        a,b,c=st.columns(3)
        a.metric('Estimates improved',improved)
        b.metric('Estimates worsened',worsened)
        c.metric('MAE change',f'{100*difference.mean():+.3f} pp')
        st.caption(f'Comparison uses the same {len(keys)} supported selected treatments. Negative MAE change means '
                   f'lower average absolute error. {len(keys)-improved-worsened} unchanged. This one portfolio is not a benchmark.')
        st.write('Shrinkage can remove favorable noise, but it can also pull a genuinely unusual effect toward '
                 'an unsuitable historical average. Neither estimator is guaranteed to be closer for a particular treatment.')


def selected_comparison_items(program):
    chosen=set(program.summary.selected_ids)
    return [r for r in program.observed if r.experiment_id in chosen]


def mean_effect_figure(program,include_truth=False):
    items=[r for r in selected_comparison_items(program) if r.experiment_id in program.corrections]
    if not items:
        raise ValueError('A mean comparison needs supported selected treatments.')
    values=[100*np.mean([r.estimate.effect for r in items]),
            100*np.mean([program.corrections[r.experiment_id].mean for r in items])]
    labels=['Observed mean','History-adjusted mean · EB']
    colors=['#879ba1','#157566'];symbols=['circle','circle']
    if include_truth:
        if program.revealed_effects is None:
            raise ValueError('Ground truth must be explicitly revealed before plotting it.')
        values.append(100*np.mean([program.revealed_effects[r.experiment_id] for r in items]))
        labels.append('True simulated mean');colors.append('#c18424');symbols.append('diamond')
    fig=go.Figure()
    for position,(value,label,color,symbol) in enumerate(zip(values,labels,colors,symbols)):
        fig.add_trace(go.Scatter(x=[value],y=[position],mode='markers+text',
            marker=dict(color=color,size=15,symbol=symbol),text=[f'{value:+.2f} pp'],textposition='top center',cliponaxis=False,
            name=label,hovertemplate='%{x:.3f} pp<extra>%{fullData.name}</extra>'))
    fig.add_vline(x=0,line_dash='dot',line_color='#b8c7c9')
    fig.update_layout(height=220 if not include_truth else 285,showlegend=False,
        xaxis=dict(title='Mean treatment − control (percentage points)',
                   range=[min(values)-max(np.ptp(values)*.18,.15),max(values)+max(np.ptp(values)*.18,.15)]),
        yaxis=dict(tickmode='array',tickvals=list(range(len(labels))),ticktext=labels,
                   range=[len(labels)-.35,-.75],fixedrange=True),
        margin=dict(t=45,b=45,l=10,r=45),paper_bgcolor='rgba(0,0,0,0)')
    return fig


def comparison_figure(program):
    items=selected_comparison_items(program)
    fig=go.Figure()
    saved={r.experiment_id:round_number+1 for round_number,batch in enumerate(program.locked_batches)
           for r in program.batch_items(batch)}
    names=[f"{r.name} · {'saved '+str(saved[r.experiment_id]) if r.experiment_id in saved else 'current'} · {r.experiment_id.rsplit('-',1)[-1]}" for r in items]
    positions=list(range(len(items)))
    fig.add_trace(go.Scatter(x=[100*r.estimate.effect for r in items],y=[p+.13 for p in positions],
        error_x=dict(type='data',symmetric=False,array=[100*(r.estimate.ci_high-r.estimate.effect) for r in items],
                     arrayminus=[100*(r.estimate.effect-r.estimate.ci_low) for r in items]),
        mode='markers',marker=dict(color='#879ba1',size=8),name='Observed · 95% confidence interval',
        customdata=names,hovertemplate='%{customdata}<br>%{x:.3f} pp<extra>%{fullData.name}</extra>'))
    supported=[(i,r,program.corrections[r.experiment_id]) for i,r in enumerate(items) if r.experiment_id in program.corrections]
    if supported:
        fig.add_trace(go.Scatter(x=[100*p.mean for _,_,p in supported],y=[i-.13 for i,_,_ in supported],
            error_x=dict(type='data',symmetric=False,array=[100*(p.ci_high-p.mean) for _,_,p in supported],
                         arrayminus=[100*(p.mean-p.ci_low) for _,_,p in supported]),
            mode='markers',marker=dict(color='#157566',size=9),name='History-adjusted · EB · 95% credible interval',
            customdata=[names[i] for i,_,_ in supported],hovertemplate='%{customdata}<br>%{x:.3f} pp<extra>%{fullData.name}</extra>'))
    if program.revealed_effects is not None:
        fig.add_trace(go.Scatter(x=[100*program.revealed_effects[r.experiment_id] for r in items],y=positions,
            mode='markers',marker=dict(color='#c18424',symbol='diamond',size=10),name='True simulated effect',
            customdata=names,hovertemplate='%{customdata}<br>%{x:.3f} pp<extra>%{fullData.name}</extra>'))
    fig.add_vline(x=0,line_dash='dot',line_color='#879ba1')
    fig.update_layout(height=max(320,min(1100,110+len(items)*48)),xaxis_title='Treatment − control (percentage points)',
        yaxis=dict(tickmode='array',tickvals=positions,ticktext=names,autorange='reversed'),
        margin=dict(t=80,b=35,l=10,r=10),legend=dict(orientation='h',y=1.2),paper_bgcolor='rgba(0,0,0,0)')
    return fig


def render_comparison(program):
    st.subheader(f'Shrinkage · your {len(program.summary.selected_ids)} selected treatments')
    st.caption('Only your saved choices and selected current cards appear here. '
               'Every row is selected. Saved rounds are locked; the current selection remains editable.')
    st.plotly_chart(comparison_figure(program),width='stretch',config={'displayModeBar':False},key='selected_shrinkage')
    st.caption('Slate: observed result and 95% confidence interval. Teal: Empirical Bayes estimate and conditional '
               '95% credible interval. Gold diamond: known synthetic truth, with no sampling interval. '
               'Intervals describe uncertainty under different assumptions; they are not guarantees of winner coverage.')


def render_model_diagnostics(artifact,scenario):
    try:
        report=json.loads((MODEL_DIR/'validation_v1.json').read_text())
        result=report['scenarios'][scenario]
        if result['artifact_id']!=artifact['artifact_id']:
            raise ValueError('Diagnostic artifact does not match this model.')
        coverage=result['metrics']['posterior_coverage']['mean']
        if coverage is not None:
            st.write(f"Initial selected-treatment interval coverage: {coverage:.1%} across "
                     f"{report['replications']} independent synthetic portfolios. Nominal level: 95%.")
        st.caption('Diagnostics include unsupported-case counts and portfolio-level uncertainty intervals. '
                   'They are conditional on the frozen prior and matched scenarios; broader stress tests are available in Benchmark.')
        st.json(result,expanded=False)
    except (OSError,KeyError,ValueError) as error:
        st.info(f'Initial diagnostics unavailable: {error}')
