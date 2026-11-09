"""Inspect one reviewed experiment without bypassing correction or truth-reveal stages."""
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from app.playground import get_playground
from src.models.artifacts import load_model,correct_observations
from src.models.normal_normal import stabilized_rate_difference
from app.explainers import render_model_guide,LABELS,COLORS
from app.estimate_walkthrough import render_method_walkthrough


def render_deep_dive():
    st.markdown('<div class="eyebrow">UNDERSTAND · ONE EXPERIMENT AT A TIME</div>',unsafe_allow_html=True)
    st.title('Look beyond the winning number.')
    program=get_playground()
    reviewed=[r for r in program.observed if r.experiment_id in program.reviewed]
    if not reviewed:
        st.info('Open Launch and review a batch first. This inspector will use exactly those observed results.')
        return
    selected={r.experiment_id for r in reviewed
              if r.experiment_id in program.active_ids and program.selections.get(r.experiment_id)}
    with st.container(border=True,key='experiment_inspector'):
        st.subheader('Choose an experiment to unpack')
        st.write('Every chart, formula and explanation below follows this choice. Compare the methods on one test, then switch to another.')
        include_unselected=st.toggle('Include experiments not selected for launch',
                                     key=f'dive_include_unselected_{program.config.fingerprint}')
        available=reviewed if include_unselected else [r for r in reviewed if r.experiment_id in selected]
        lookup={r.experiment_id:r for r in available}
        if not lookup:
            st.info('No experiments selected for launch. Select treatments in Launch, or turn on the option above to explore reviewed experiments.')
            return
        widget_key=f'dive_{program.config.fingerprint}'
        if st.session_state.get(widget_key) not in lookup:
            st.session_state[widget_key]=next(iter(lookup))
        key=st.selectbox('Experiment',list(lookup),format_func=lambda k:lookup[k].name+' · '+k.rsplit('-',1)[-1]
                         +(' · Selected' if k in selected else ' · Not selected'),key=widget_key)
        scope='reviewed' if include_unselected else 'selected for launch'
        st.caption(f'Experiment {list(lookup).index(key)+1} of {len(lookup)} {scope}')
        if include_unselected:
            st.caption(f'{len(selected)} selected for launch · {len(reviewed)-len(selected)} not selected. '
                       'Simulated truth is available only for selected treatments included in your revealed comparison.')
    item=lookup[key];e=item.estimate
    a,b,c=st.columns(3)
    a.metric('Observed effect',f'{100*e.effect:+.2f} pp')
    b.metric('Standard error',f'{100*e.standard_error:.2f} pp')
    c.metric('Your launch choice','Selected' if program.selections.get(key) else 'Not selected')
    st.caption(f'Month {item.month} · {item.metric} · {item.control_n:,} control / {item.treatment_n:,} treatment observations')
    estimates=[('Observed result · 95% confidence interval',e.effect,e.ci_low,e.ci_high,'#879ba1')]
    details=[]
    if program.corrections is not None:
        for method in ('empirical_bayes','hierarchical','robust'):
            label=LABELS[method]+' · 95% CrI'
            color=COLORS[method]
            try:
                artifact=load_model(program.config,estimator=method)
                predicted,unsupported=correct_observations((item,),(key,),artifact)
                if key in unsupported:
                    st.warning(f'{label}: {unsupported[key]}');continue
                p=predicted[key]
                estimates.append((label,p.mean,p.ci_low,p.ci_high,color))
                details.append((method,artifact,p))
            except (OSError,ValueError,KeyError) as error:
                st.warning(f'{label} unavailable: {error}')
    else:
        st.info('Use Correct estimates & reveal truth in Launch to unlock model comparisons. No correction has been applied automatically.')
    fig=go.Figure()
    for label,mean,lo,hi,color in estimates:
        fig.add_trace(go.Scatter(x=[100*mean],y=[label],mode='markers',marker=dict(size=12,color=color),
            error_x=dict(type='data',symmetric=False,array=[100*(hi-mean)],arrayminus=[100*(mean-lo)]),name=label,
            hovertemplate='%{x:.3f} pp<extra>%{fullData.name}</extra>'))
    fig.add_vline(x=0,line_dash='dot',line_color='#879ba1')
    if program.revealed_effects is not None and key in program.revealed_effects:
        truth=program.revealed_effects[key]
        fig.add_vline(x=100*truth,line_dash='dash',line_color='#c18424')
        fig.add_annotation(x=0,y=1.13,xref='paper',yref='paper',xanchor='left',showarrow=False,
                           text=f'True effect · orange dashed line: {100*truth:+.2f} pp',
                           font=dict(color='#9a6415',size=13))
        errors=[f'{label.split(" · ")[0]}: {100*abs(mean-truth):.3f} pp absolute error' for label,mean,*_ in estimates]
        st.write(' · '.join(errors))
    else:
        if key not in selected:
            st.info('No orange truth line: this experiment was not selected for launch, so its simulated truth has not been revealed.')
        else:
            st.info('No orange truth line yet. Use Correct estimates & reveal truth in Launch to reveal the selected experiments.')
    fig.update_layout(height=310,showlegend=False,xaxis_title='Treatment − control (percentage points)',
                      margin=dict(t=65,l=10,r=15,b=20),yaxis_autorange='reversed')
    st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})
    if program.revealed_effects is not None and key in program.revealed_effects:
        st.markdown(f'**Orange dashed vertical line = true simulated effect ({100*truth:+.3f} pp).** '
                    'This is the effect set by the simulator before sampling, not an estimate or a significance threshold. '
                    'The closer a dot is to this line, the more accurate that estimate is for this experiment.')
    st.caption('Dots are estimates; horizontal whiskers are uncertainty intervals. '
               'The gray dotted vertical line at 0 pp means no difference between treatment and control.')
    st.subheader('How each method arrived at its answer')
    st.write('Follow the calculation for **'+item.name+'**. Weights describe how much each source contributes to the estimate.')
    truth=program.revealed_effects.get(key) if program.revealed_effects is not None else None
    tabs=st.tabs(['📊 Observed result']+[LABELS[method] for method,_,_ in details])
    with tabs[0]:
        st.subheader('Start with what happened in the test')
        control=100*item.control_successes/item.control_n
        treatment=100*item.treatment_successes/item.treatment_n
        st.write(f'The control group recorded **{item.control_successes:,} successes out of {item.control_n:,}** '
                 f'({control:.3f}%). The treatment group recorded **{item.treatment_successes:,} out of {item.treatment_n:,}** '
                 f'({treatment:.3f}%). Subtract the two rates:')
        st.latex(r'\mathrm{observed}=100\left(\frac{'
                 +f'{item.treatment_successes}'+'}{'+f'{item.treatment_n}'
                 +r'}-\frac{'+f'{item.control_successes}'+'}{'+f'{item.control_n}'
                 +r'}\right)='+f'{100*e.effect:+.4f}'+r'\;\mathrm{pp}')
        st.write(f'This method keeps the measured effect of **{100*e.effect:+.3f} pp** without using history. '
                 f'The standard error is **{100*e.standard_error:.3f} pp**: an estimate of sampling variability, '
                 'not a correction or a bound on the error. Selecting this result does not remove that variability.')
        if truth is not None:
            st.info(f'The simulated truth is {100*truth:+.3f} pp. This observed result has '
                    f'{100*abs(e.effect-truth):.3f} pp absolute error. Compare the other methods to see whether history helps.')
    for tab,(method,artifact,p) in zip(tabs[1:],details):
        with tab:
            render_method_walkthrough(item,method,artifact,p,truth)
    with st.expander('Compare the assumptions behind the four methods'):
        render_model_guide()
        st.write('Both Normal models can under-cover selected or exceptional effects. The robust mixture can also fail. '
                 'Benchmark compares repeated portfolios, including cases where corrections make estimates worse.')
    with st.expander('Selection threshold and statistical details'):
        st.write(f'Unadjusted two-sided p = {e.p_value:.6g}. Default selection requires p < 0.05 and a positive observed effect. '
                 'This is a decision rule, not a posterior probability.')
        pooled=(item.control_successes+item.treatment_successes)/(item.control_n+item.treatment_n)
        threshold=1.95996398454*np.sqrt(pooled*(1-pooled)*(1/item.control_n+1/item.treatment_n))
        st.caption(f'For the pooled-score approximation, the positive threshold at this observed pooled rate is '
                   f'about {100*threshold:.3f} pp. For sparse tables the app uses Fisher’s test instead.')
        st.write(f'Control successes: {item.control_successes:,}; treatment successes: {item.treatment_successes:,}.')
        _,se=stabilized_rate_difference(item.control_successes,item.control_n,item.treatment_successes,item.treatment_n)
        st.caption(f'Model SE: {100*se:.3f} pp (half-count stabilization). Card CI: Newcombe–Wilson; '
                   'posterior intervals are different inferential quantities.')
