"""Numerical explanations of the fitted predictors for one observable experiment."""
import numpy as np
from scipy.special import logsumexp
import plotly.graph_objects as go
import streamlit as st
from app.explainers import COLORS, LABELS


def explanation_parts(effect, se, artifact):
    """Decompose the actual posterior mean, including data-dependent mixture weights."""
    version=artifact['model_version']
    if version=='normal-normal-rd-v1':
        centers=np.array([artifact['fit']['mean']])
        variances=np.array([artifact['fit']['variance']])
        mass=np.ones(1)
        split=None
    elif version=='hierarchical-normal-rd-v1':
        nodes=artifact['hierarchical']['nodes']
        centers=np.array(nodes['mu_mean'])
        variances=np.array(nodes['tau'])**2+np.array(nodes['mu_variance'])
        mass=np.array(nodes['weights'])
        split=None
    else:
        model=artifact['robust'];tau=np.array(model['tau']);weights=np.array(model['weights'])
        split=len(tau)
        centers=np.zeros(2*split)
        variances=np.r_[tau**2,(model['wide_scale']*tau)**2]
        mass=np.r_[(1-model['wide_probability'])*weights,model['wide_probability']*weights]
    total=variances+se**2
    log_mass=np.log(mass)-.5*(np.log(2*np.pi*total)+(effect-centers)**2/total)
    updated=np.exp(log_mass-logsumexp(log_mass))
    data_weights=variances/total
    conditional=data_weights*effect+(1-data_weights)*centers
    history_weight=float(updated@(1-data_weights))
    center=float((updated*(1-data_weights))@centers/history_weight) if history_weight else 0.
    result={'history_weight':history_weight,'center':center,'mean':float(updated@conditional)}
    if split is not None:
        q=float(updated[split:].sum())
        narrow_mass=float(updated[:split].sum())
        result.update(wide_probability=q,
                      narrow_mean=float(updated[:split]@conditional[:split]/narrow_mass) if narrow_mass else 0.,
                      wide_mean=float(updated[split:]@conditional[split:]/q) if q else 0.)
    return result


def weight_figure(data_weight):
    fig=go.Figure()
    for label,value,color in [('This test',data_weight,'#879ba1'),('History',1-data_weight,'#157566')]:
        fig.add_trace(go.Bar(x=[100*value],y=['Influence'],orientation='h',name=label,
            marker_color=color,text=[f'{100*value:.1f}%'] if value>=.08 else None,textposition='inside',
            hovertemplate=label+': %{x:.1f}%<extra></extra>'))
    fig.update_layout(barmode='stack',height=140,margin=dict(t=15,b=10,l=0,r=10),
        xaxis=dict(range=[0,100],ticksuffix='%',title=None),yaxis=dict(visible=False),
        legend=dict(orientation='h',y=1.6),paper_bgcolor='rgba(0,0,0,0)')
    return fig


def render_method_walkthrough(item, method, artifact, posterior, truth):
    e=item.estimate;p=posterior
    parts=explanation_parts(e.effect,p.model_se,artifact)
    w=1-parts['history_weight'];center=parts['center']
    st.subheader(LABELS[method])
    a,b,c=st.columns(3)
    a.metric('This test reported',f'{100*e.effect:+.3f} pp')
    b.metric('This method estimates',f'{100*p.mean:+.3f} pp',f'{100*(p.mean-e.effect):+.3f} pp adjustment',delta_color='off')
    c.metric('95% credible interval',f'{100*p.ci_low:+.2f} to {100*p.ci_high:+.2f} pp')
    if method=='empirical_bayes':
        tau=100*np.sqrt(artifact['fit']['variance']);se=100*p.model_se
        st.write(f"**The historical mean ({100*center:+.3f} pp)** is the fitted center of underlying effects across "
                 f"{artifact['fit']['n_history']:,} independent historical experiments. It includes unsuccessful results; "
                 'it is neither this test’s control rate nor the average of your selected winners.')
        st.write(f'**Weight means influence, not confidence or a success probability.** This test gets {100*w:.1f}% '
                 f'of the estimate and history gets {100*(1-w):.1f}%. The model compares this test’s noise '
                 f'(SE **{se:.3f} pp**) with historical effect variation (SD **{tau:.3f} pp**). '
                 'More measurement noise gives history more influence; more variation between true effects gives this test more influence.')
        st.latex(r'w_{\mathrm{test}}=\frac{\tau^2}{\tau^2+s^2}'
                 +rf'=\frac{{{tau:.4f}^2}}{{{tau:.4f}^2+{se:.4f}^2}}\approx {w:.4f}')
    elif method=='hierarchical':
        lo,hi=artifact['hierarchical']['hyperparameter_intervals_95']['mu']
        st.write(f"**History does not pin down a single center and spread.** Its fitted center is "
                 f"{100*artifact['fit']['mean']:+.3f} pp, with a 95% historical posterior range of "
                 f"{100*lo:+.3f} to {100*hi:+.3f} pp for that center.")
        st.write('The model calculates an adjusted estimate for each plausible historical center and spread, '
                 'updates their relative plausibility using this test, then averages those estimates. '
                 f'For this experiment, the combined calculation gives **{100*w:.1f}% influence to the test** '
                 f'and **{100*(1-w):.1f}% to history**, with an effective historical target of **{100*center:+.3f} pp**.')
        st.caption('That effective target summarizes the weighted calculation for this experiment; '
                   'it is not a newly fitted historical mean. The interval also includes uncertainty between the plausible histories.')
        with st.expander('How the different histories are combined'):
            st.latex(r'\hat\theta=\sum_j q_j\,[w_j y+(1-w_j)\mu_j],\qquad '
                     r'w_j=\frac{\tau_j^2+v_{\mu,j}}{\tau_j^2+v_{\mu,j}+s^2}')
            st.write('y is this test’s measured effect; s is its model SE. Each j is a plausible historical scale, '
                     'with center μ, uncertainty vμ about that center, and between-effect variance τ². '
                     'q is its probability after history and this test. The numeric formula below is the exact mean calculation regrouped into two contributions.')
    else:
        model=artifact['robust'];q=parts['wide_probability']
        st.write(f"**Could this be an unusually large effect?** Before seeing this test, the model assigns "
                 f"{100*model['wide_probability']:.0f}% probability to a broad group whose effect SD is "
                 f"{model['wide_scale']:.0f} times larger. Both groups are centered at **zero**, by assumption. "
                 'Historical data inform the shared scale and its uncertainty.')
        st.write(f'After seeing this result and its SE of **{100*p.model_se:.3f} pp**, the broad-group probability '
                 f'is **{100*q:.1f}%**. The estimate conditional on the ordinary group is '
                 f'**{100*parts["narrow_mean"]:+.3f} pp**; conditional on the broad group it is '
                 f'**{100*parts["wide_mean"]:+.3f} pp**. The final estimate averages these two possibilities.')
        st.latex(r'\hat\theta=(1-q)\,\hat\theta_{\mathrm{ordinary}}+q\,\hat\theta_{\mathrm{broad}}'
                 )
        st.latex(rf'\hat\theta\approx {1-q:.4f}\times({100*parts["narrow_mean"]:+.4f})'
                 +rf'+{q:.4f}\times({100*parts["wide_mean"]:+.4f})={100*p.mean:+.4f}\;\mathrm{{pp}}')
        st.caption('Broad-group probability is not the chance the treatment works. It is a model-based classification '
                   'of effect scale. A larger broad-group probability usually allows less shrinkage; the zero center can still be unsuitable.')
        st.write(f'Equivalently, this estimate keeps **{100*w:.1f}% of the observed effect** and puts '
                 f'**{100*(1-w):.1f}% weight on zero**:')
    st.plotly_chart(weight_figure(w),width='stretch',config={'displayModeBar':False},key=f'weights_{method}')
    st.latex(r'\hat\theta=w_{\mathrm{test}}\times\mathrm{observed}+(1-w_{\mathrm{test}})\times\mathrm{history}'
             )
    st.latex(rf'\hat\theta\approx {w:.4f}\times({100*e.effect:+.4f})+{1-w:.4f}\times({100*center:+.4f})'
             +rf'={100*p.mean:+.4f}\;\mathrm{{pp}}')
    direction='down' if p.mean<e.effect else 'up' if p.mean>e.effect else 'neither up nor down'
    st.write(f'**Why it moved {direction}:** the historical target is {100*center:+.3f} pp, '
             f'compared with the observed {100*e.effect:+.3f} pp. The model moves {100*(1-w):.1f}% '
             'of the distance toward that target. This is not a fixed discount on every winner.')
    if truth is not None:
        before=100*abs(e.effect-truth);after=100*abs(p.mean-truth)
        verdict='closer to' if after<before else 'farther from' if after>before else 'equally close to'
        st.info(f'For this experiment, the correction is {verdict} the simulated truth ({100*truth:+.3f} pp). '
                f'Absolute error: {before:.3f} → {after:.3f} pp. '
                'This checks the result after estimation; truth did not enter the formula.')
    st.caption('Formula values are rounded and expressed in percentage points. The model SE uses half-count '
               'stabilization for the binary counts. Credible intervals depend on model assumptions; '
               'a narrower interval does not guarantee a more accurate estimate.')
