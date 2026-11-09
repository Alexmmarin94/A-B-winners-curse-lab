"""Progressive disclosure of actual calibration artifacts and validation limitations."""
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from src.calibration.artifacts import ARTIFACT_PATH, load_calibration


def render_calibration():
    st.subheader('Archive calibration · what was actually fitted')
    try:
        artifact = load_calibration()
        quality = json.loads((ARTIFACT_PATH.parent/'quality_report.json').read_text())
        validation = json.loads((ARTIFACT_PATH.parent/'confirmatory_validation.json').read_text())
        if validation['artifact_id'] != artifact['artifact_id']:
            raise ValueError('Validation report refers to a different calibration artifact.')
    except (OSError, ValueError, KeyError) as error:
        st.error(f'Calibration unavailable: {error}. No empirical fallback is substituted.')
        return
    a,b,c = st.columns(3)
    a.metric('Exploratory experiments used', f"{artifact['training']['experiments']:,}")
    b.metric('Bootstrap refits', artifact['mixture']['uncertainty']['replications'])
    c.metric('Confirmatory experiments checked', f"{validation['real_experiments']:,}")
    st.write('The CTR laboratory uses real archive-derived traffic patterns and a fitted effect distribution, '
             'then draws new binomial outcomes. It does not replay historical experiments. The four product '
             'challenges remain hypothetical because headline CTR effects do not directly calibrate their metrics.')
    st.warning('Approximate calibration, not identification of real true effects. Confirmatory checks show '
               'mismatches in CTR and effect tails. Sparse counts, noisy baseline anchors, and effect/design '
               'independence remain limitations; the fitted artifact has not been tuned on those checks.')
    with st.expander('Data quality and exclusions', expanded=True):
        table = []
        for name, report in quality['partitions'].items():
            table.append({'Partition': name, 'Experiments': report['experiments_in'],
                          'Retained': report['experiments_retained'], 'Excluded': report['experiments_excluded'],
                          'Rows missing experiment ID': report['missing_id_rows']})
        st.dataframe(pd.DataFrame(table), hide_index=True, use_container_width=True)
        st.caption('Whole experiments are excluded for any flagged row. The randomization window includes '
                   'June 25, 2013 and January 10, 2014. Undeployed packages are excluded in full. '
                   'Overlapping exclusion reasons are documented in the downloadable report.')
        st.write('No experiment IDs overlap between exploratory, confirmatory, and holdout. '
                 'Five confirmatory and one holdout experiment IDs also occur in the excluded undeployed file. '
                 'Holdout is never used for fitting; the final frozen-artifact check is reported separately below.')
        st.download_button('Download data-quality report', json.dumps(quality, indent=2),
                           file_name='upworthy-quality-report.json', mime='application/json')
    with st.expander('Latent-effect calibration and its uncertainty'):
        st.write('One hash-selected, randomly oriented pair per experiment avoids treating correlated '
                 'shared-control comparisons as independent evidence. Half-count log-odds estimates and their '
                 'individual SEs enter a measurement-error likelihood. A symmetric histogram mixture can '
                 'represent non-Normal shapes; its bounded support and symmetry are explicit assumptions.')
        edges = artifact['policy']['edges']; weights = np.array(artifact['mixture']['weights'])
        intervals = np.array(artifact['mixture']['uncertainty']['weight_intervals_95'])
        labels = ['Exactly zero'] + [f'{a:g}–{b:g}' for a,b in zip(edges[:-1],edges[1:])]
        fig = go.Figure(go.Bar(x=labels, y=weights, marker_color='#157566',
            error_y=dict(type='data', symmetric=False, array=np.maximum(intervals[:,1]-weights,0),
                         arrayminus=np.maximum(weights-intervals[:,0],0))))
        fig.update_layout(height=320, xaxis_title='Absolute log-odds effect component',
                          yaxis_title='Fitted probability mass', yaxis_tickformat='.0%', margin=dict(t=10))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})
        st.caption('95% percentile bootstrap ranges, conditional on the model and pair rule. These are '
                   'not credible intervals for individual treatment effects. Near-zero components are weakly '
                   'separated: do not interpret the point-mass estimate as a known fraction of null effects.')
        st.write(f"{artifact['training']['sparse_pairs']} training pairs have an observed cell count below five. "
                 'They were retained to avoid selecting training observations by their outcomes, but the '
                 'Normal measurement approximation can be inaccurate for them.')
        st.json(artifact['sensitivity'], expanded=False)
    with st.expander('Confirmatory observable checks · frozen artifact'):
        st.write(f"Compared {validation['simulated_experiments']:,} new synthetic pairs against "
                 f"{validation['real_experiments']:,} confirmatory pairs. This checks observable distributions, "
                 'not latent truth or Bayesian correction performance.')
        choices = {'Observed effect (pp)': 'observed_effect_pp', 'Pooled CTR': 'pooled_ctr',
                   'Pair impressions': 'pair_impressions', 'Observed log odds ratio': 'observed_log_odds_ratio'}
        label = st.selectbox('Diagnostic', list(choices))
        result = validation['observable_comparisons'][choices[label]]
        fig = go.Figure()
        for key, title, color in [('confirmatory','Real confirmatory','#607b85'),('synthetic','Synthetic','#157566')]:
            fig.add_trace(go.Scatter(x=list(result[key]), y=list(result[key].values()), name=title,
                                    mode='lines+markers', line_color=color))
        fig.update_layout(height=300, yaxis_title=label, xaxis_title='Distribution quantile', margin=dict(t=20))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})
        st.caption(f"KS distance: {result['ks_distance']:.3f}. Descriptive discrepancy, not a pass/fail threshold. "
                   'This is one validation portfolio, not a repeated estimator benchmark.')
        st.download_button('Download confirmatory checks', json.dumps(validation,indent=2),
                           file_name='upworthy-confirmatory-validation.json', mime='application/json')
    with st.expander('Traffic, precision, and changes over time'):
        monthly = artifact['descriptive']['monthly']
        dates = pd.period_range(monthly[0]['month'], monthly[-1]['month'], freq='M').astype(str).tolist()
        ctr = {r['month']: 100*r['median_anchor_ctr'] for r in monthly}
        fig = go.Figure(go.Scatter(x=dates, y=[ctr.get(date) for date in dates], connectgaps=False,
                                  mode='lines+markers', line_color='#157566'))
        fig.update_layout(height=280, yaxis_title='Median paired CTR anchor (%)', xaxis_title='Archive month', margin=dict(t=10))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})
        st.caption('Exploratory data after exclusions. Gaps in the affected period are not interpolated observations. '
                   'The generator pools periods; its four month labels do not reproduce this history.')
        st.json({k:v for k,v in artifact['descriptive'].items() if k != 'monthly'}, expanded=False)
    with st.expander('Provenance and limitations'):
        st.code(artifact['artifact_id'], language=None)
        st.caption('Artifact notes record the fitting stage. The later confirmatory and holdout checks are shown separately; '
                   'the original reserved-partition note is historical.')
        for limitation in artifact['limitations']:
            st.write('• '+limitation)
        st.download_button('Download calibration artifact', json.dumps(artifact,indent=2),
                           file_name=ARTIFACT_PATH.name, mime='application/json')
        st.markdown('[Upworthy archive](https://upworthy.natematias.com/about-the-archive.html) · '
                    '[2024 correction](https://upworthy.natematias.com/2024-06-upworthy-archive-update.html) · '
                    '[Measurement-error mixture reference: Stephens (2017)](https://doi.org/10.1093/biostatistics/kxw041)')
    holdout_path=ARTIFACT_PATH.parent/'holdout_validation.json'
    if holdout_path.exists():
        with st.expander('Final holdout check · no refitting'):
            holdout=json.loads(holdout_path.read_text())
            if holdout['artifact_id']!=artifact['artifact_id']:
                st.error('Holdout check references a different artifact.')
            else:
                st.write(f"Final observable check on {holdout['real_experiments']:,} eligible holdout pairs, "
                         'after calibration choices were frozen. No parameters were changed in response. '
                         'This partition has now been inspected and must not be described as an untouched future holdout.')
                st.dataframe(pd.DataFrame([{'Observable':name,'KS distance':values['ks_distance']}
                    for name,values in holdout['observable_comparisons'].items()]),hide_index=True,use_container_width=True)
                st.download_button('Download holdout check',json.dumps(holdout,indent=2),
                    file_name='holdout_validation.json',mime='application/json')
