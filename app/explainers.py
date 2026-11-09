"""Shared plain-language labels and visual explanations; no statistical output is invented here."""
from html import escape
import streamlit as st

LABELS = {'naive': 'Observed result', 'empirical_bayes': 'History-adjusted · EB',
          'hierarchical': 'Uncertain history · Normal', 'robust': 'Outlier-aware · Robust'}
COLORS = {'naive': '#879ba1', 'empirical_bayes': '#157566', 'hierarchical': '#6b59a8', 'robust': '#3973ac'}


def tile(icon, title, body, tag='', tone='teal'):
    st.markdown(f'<div class="explain-card {escape(tone)}"><div class="eyebrow">{escape(tag)}</div>'
                f'<h3><span class="explain-icon" aria-hidden="true">{escape(icon)}</span> {escape(title)}</h3>'
                f'<p>{escape(body)}</p></div>', unsafe_allow_html=True)


def render_model_guide():
    st.markdown('**Four ways to estimate the same effect**')
    descriptions = [
        ('naive', '📊', 'Naive estimator', 'Use the test result as measured. It reflects signal and noise; choosing a winner does not remove the noise.'),
        ('empirical_bayes', '🧮', 'Normal–normal Empirical Bayes', 'Combine this test with a historical center and spread. Those fitted historical parameters are treated as fixed. This is the main challenge correction.'),
        ('hierarchical', '📚', 'Hierarchical Normal Bayes', 'Also allow uncertainty about the historical center and spread. It keeps the bell-shaped effect assumption; a more complex model can give a similar answer.'),
        ('robust', '🛡️', 'Robust hierarchical mixture', 'Allow a narrow group and a small, broader group of effects. The center is fixed at zero and the shared scale is learned. It can preserve unusual effects, but can also be wrong.')]
    for start in (0,2):
        for col,(key,icon,technical,copy) in zip(st.columns(2),descriptions[start:start+2]):
            with col:tile(icon,LABELS[key],copy,technical,'blue' if key=='robust' else 'teal')
    st.caption('Normal and robust are two different hierarchical models. “Robust mixture hierarchy” is the robust '
               'Bayesian model in this lab: 95% narrow / 5% broad, with five times the SD in the broad component. '
               '“Robust” describes its design, not a promise of better accuracy. None of these estimates is ground truth.')


def render_estimate_key(revealed=False):
    a,b,c=st.columns(3)
    with a:tile('📊','Observed result','What the sampled test reported. This is the number used to choose launches.','SLATE · MEASUREMENT')
    with b:tile('🧮','History-adjusted · EB','What the fitted model estimates after combining this result with history. It can be closer to the truth or farther away.','TEAL · ESTIMATE')
    with c:tile('🎯','True simulated effect',
        'What the generator set before sampling. It is the answer against which we can check errors; it is not another Bayesian estimate.' if revealed else
        'What the generator set before sampling. Still hidden. The combined correction and reveal action will disclose it.',
        'GOLD · KNOWN ONLY IN SIMULATION' if revealed else 'LOCKED · COMPARE TO REVEAL','gold')


def render_research_context():
    st.subheader('Research behind the lab')
    st.caption('These ideas inform the questions and checks. Only Upworthy supplies experiment records for calibration; '
               'we do not have the companies’ private data or reproduce their proprietary systems.')
    sources=[
        ('Amazon · estimate impact after selection','Kessler studies how reporting the effects of launched winners can distort program impact and resource allocation.',
         'We compare the observed and history-adjusted estimates on the same selected treatments, including cases where a poor prior makes accuracy worse.',
         'https://www.amazon.science/publications/overcoming-the-winners-curse-leveraging-bayesian-inference-to-improve-estimates-of-the-impact-of-features-launched-via-a-b-tests'),
        ('Netflix · evaluate the decision, too','Return-aware experimentation asks which launch rules improve outcomes across a program, rather than stopping at whether individual tests are significant.',
         'Benchmark separates effect-estimation error from decision regret. Our utility is explicit and simplified; the hierarchies are independent implementations.',
         'https://netflixtechblog.medium.com/return-aware-experimentation-3dd93c94b67a'),
        ('Airbnb · explain the launch-summary gap','Airbnb describes selection bias when summarizing successful experiments. A collection of winning estimates can tell an optimistic impact story.',
         'You make launch choices first, then see their observed and true mean effects separately. We do not turn arbitrary uplift sums into business impact.',
         'https://medium.com/airbnb-engineering/selection-bias-in-online-experimentation-c3d67795cceb'),
        ('Spotify · test the prior, not the label','Spotify discusses why the quality of historical priors and the required decision guarantees matter more than a Bayesian label.',
         'We keep failure cases visible and stress-test shifts, heterogeneous programs and exceptional effects. We do not assume Bayesian estimates always improve accuracy.',
         'https://engineering.atspotify.com/2026/9/why-spotify-is-not-using-bayesian-a-b-testing')]
    for start in (0,2):
        for col,(title,idea,application,url) in zip(st.columns(2),sources[start:start+2]):
            with col,st.container(border=True):
                st.markdown(f"**{ {'Amazon':'📈','Netflix':'🎬','Airbnb':'🏠','Spotify':'🎧'}[title.split(' · ')[0]]} {title}**")
                st.write(idea)
                st.markdown(f'**In this lab:** {application}')
                st.markdown(f'[Read the source]({url})')
    st.info('Optimizely is context, not a second calibration dataset. Its published aggregate report uses its own '
            'eligibility and winning definitions. We do not import its win rates or winning uplifts as true effects; '
            'doing so would risk treating selected noisy results as a population of real effects.')
    st.markdown('[Optimizely aggregate report](https://www.optimizely.com/field-notes/guides/173000-experiments) · '
                '[LiftArchive research](https://liftarchive.com/research/): published-case context only, also not used for calibration.')
