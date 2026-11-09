"""An explanation-first entrance; the teaching example is explicitly separate from simulation."""
import plotly.graph_objects as go
import streamlit as st
from app.explainers import tile, render_research_context


def render_learning(navigate):
    st.markdown('<div class="eyebrow">AN INTERACTIVE GUIDE TO A/B TESTING & BUSINESS IMPACT</div>',unsafe_allow_html=True)
    st.markdown('<p class="lede">A/B tests compare a new experience with the current one. '
                'You launch the winners and count their uplift as growth. Sounds reasonable—'
                'until you realize that <strong>the results that look best can also be the ones that got luckiest.</strong></p>',
                unsafe_allow_html=True)
    left,right=st.columns([1.45,1],gap='large')
    with left:
        st.title('Your winners look great. How much is real?')
        st.markdown('<p class="lede">Your launch dashboard can overstate the growth you have earned. '
                    'See how much of a winning result is impact—and how much is luck.</p>',unsafe_allow_html=True)
        st.write('A hidden risk sits between a successful A/B test and a business forecast: **we choose launches '
                 'using noisy results, then reuse those same results to claim impact**. That can inflate expectations, '
                 'distort budget allocation and make the roadmap look more productive than it is.')
        st.markdown('<div class="business-hook"><strong>Make the decisions. See the hidden truth.</strong><br>'
                    'Experience the Winner’s Curse in an interactive lab informed by real experimentation data* '
                    'and test whether a historical correction earns your trust.</div>',unsafe_allow_html=True)
        st.caption('*All challenge results are simulated. The headline CTR lab uses Upworthy-derived calibration '
                   'plus explicit generation rules; the four product challenges use hypothetical assumptions. '
                   'Realism is checked, not guaranteed. The rules and limitations are explained below.')
    with right:
        st.markdown('''<div class="illustration">
          <div class="eyebrow">ONE RESULT · TWO INGREDIENTS</div>
          <h3 style="color:#ecf6f1">Reported lift = real effect + sampling noise</h3>
          <p>A treatment moves conversion from 20% to 21%. Its true effect is <b>+1 percentage point</b>.</p>
          <p>A lucky test might report <b>+2 points</b>. Launching it does not make the extra point real.</p>
          <p>For a hypothetical rollout to 100,000 users, those estimates imply <b>2,000</b> versus
          <b>1,000</b> additional conversions—if the effect transfers to that population.</p>
          <div class="quiet">Single-treatment illustration only, not a measured company loss or an ROI forecast.</div>
        </div>''',unsafe_allow_html=True)
    st.divider()
    st.subheader('Selection changes the story')
    st.markdown('**The Winner’s Curse:** selecting favorable noisy results can make the chosen treatments’ '
                'reported effects look better, on average, than their underlying effects justify.')
    st.write('Consider five illustrative tests whose treatments all truly improve conversion by **1 percentage point**. '
             'Their observed effects differ because of noise. In this deliberately balanced example, '
             'the average of all five results equals the truth. Now keep only the strongest results.')
    selected_only=st.toggle('Keep only the results we would launch',key='learning_selected_only')
    observed=[0.,.5,1.,1.5,2.]
    selected=[i for i,value in enumerate(observed) if value>=1.5]
    shown=selected if selected_only else list(range(len(observed)))
    fig=go.Figure()
    if selected_only:
        fig.add_trace(go.Scatter(x=observed,y=['A','B','C','D','E'],mode='markers',
            marker=dict(color='#d5dfe0',size=11),name='Not in the launch summary',hoverinfo='skip'))
    fig.add_trace(go.Scatter(x=[observed[i] for i in shown],y=[chr(65+i) for i in shown],mode='markers',
        marker=dict(color='#157566',size=15),name='Included in the summary',
        hovertemplate='Test %{y}: %{x:.1f} pp observed<extra></extra>'))
    fig.add_vline(x=1,line_dash='dash',line_color='#b77532',annotation_text='True effect of every treatment: +1 pp')
    fig.update_layout(height=280,showlegend=False,xaxis=dict(title='Observed effect (percentage points)',range=[-.2,2.4]),
        yaxis=dict(title='Illustrative test',categoryorder='array',categoryarray=['E','D','C','B','A']),
        margin=dict(t=40,b=20,l=10,r=20))
    chart,explanation=st.columns([1.55,1],gap='large')
    with chart:st.plotly_chart(fig,width='stretch',config={'displayModeBar':False})
    with explanation:
        mean=sum(observed[i] for i in shown)/len(shown)
        st.metric('Mean reported effect · selected tests' if selected_only else 'Mean reported effect · all tests',f'+{mean:.2f} pp')
        st.metric('Mean true effect · same treatments','+1.00 pp')
        if selected_only:
            st.write('**The selected average is +1.75 pp, but the true average is still +1 pp.** '
                     'Selection retained the two positive noise errors. The tests did not change; the subset did.')
        else:
            st.write('The positive and negative noise errors balance here. Switch on the launch filter '
                     'to see why that balance disappears among winners.')
    st.caption('Teaching illustration only: five hand-chosen observations, not a Monte Carlo result. '
               'The illustrative launch rule is observed effect ≥1.5 pp, not a significance test. '
               'Real finite samples need not average exactly to the true effect.')
    a,b,c=st.columns(3,gap='large')
    with a:
        st.markdown('**A valid test can still be noisy**')
        st.write('Random assignment supports causal inference. It does not guarantee that one estimated effect is close to the truth.')
    with b:
        st.markdown('**Significance does not certify the size**')
        st.write('A small p-value is evidence against a null model. It does not mean the reported uplift is an accurate launch forecast.')
    with c:
        st.markdown('**Selection is the key step**')
        st.write('The distortion concerns a selection process across possible results. It does not mean every winner is exaggerated.')
    with st.expander('Selecting experiments versus selecting variants'):
        st.write('Selecting successful tests from a portfolio creates post-selection estimation bias. Choosing the best '
                 'variant within an A/B/n test adds the Optimizer’s Curse. Both select on noisy estimates. Shared-control '
                 'comparisons are correlated, so the A/B/n benchmark models that covariance and applies Holm adjustment '
                 'to its significance-based launch rule. Adjustment does not eliminate effect-size selection bias.')

    st.divider()
    st.subheader('We simulate so we can check the answer')
    st.markdown('**A real experiment gives us an estimate. This lab also gives us the answer key.** '
                'To ask whether a correction is closer to the true effect, we need to know that effect. '
                'Upworthy records alone cannot reveal it: their measured lifts contain sampling noise too.')
    a,b,c=st.columns(3)
    with a:tile('🗄️','Real-world grounding','For headline CTR, cleaned Upworthy experiments inform traffic, '
        'conversion-rate anchors and plausible effect variation. Separate real partitions check the generated observables.',
        'WHAT THE ARCHIVE CONTRIBUTES')
    with b:tile('🧪','The same kind of evidence','The generator produces visitors and conversions for each arm. '
        'The analysis uses those counts to calculate effects, standard errors, intervals and p-values, just as with aggregate A/B data.',
        'WHAT THE ESTIMATOR RECEIVES')
    with c:tile('🎯','A known answer for evaluation','Underlying probabilities are fixed before counts are sampled. '
        'We can measure estimation error exactly against their difference and reveal when a correction helps or harms.',
        'WHAT SIMULATION ADDS','gold')
    st.markdown('<div class="pipeline"><b>Archive-informed design</b> → Explicit probability model '
                '→ Sample visitor/conversion counts → Apply the same statistical analysis → Check against known truth</div>',unsafe_allow_html=True)
    st.write('**Why this approach fits the question:** using only real winning estimates as the answer key would '
             'reuse the very noise and selection bias we want to study. Calibrated Monte Carlo lets us repeat '
             'independent experiments, hold the evaluation rules constant and deliberately test situations where '
             'a historical model is wrong. A particular algorithm does not get to define all the simulated truths.')
    st.write('The counts follow **binomial sampling**, a standard model for independent binary outcomes. '
             'That makes them valid inputs to the same A/B calculations under that model. '
             'They remain generated observations: their relevance to a real business depends on the assumptions '
             'and calibration matching that business. Repeated users, interference or changing behavior can require a different model.')
    st.success('Use this lab to understand selection bias and compare methods under transparent conditions. '
               'Use your company’s own experiments and independent validation to forecast its actual impact.')
    st.caption('The four product challenges are hypothetical; the empirical calibration applies to headline CTR only. '
               'No estimator can see the answer key before evaluation, and the interface reveals it only on your explicit action.')

    st.subheader('Where the assumptions come from')
    a,b=st.columns(2,gap='large')
    with a,st.container(border=True):
        st.markdown('<div class="eyebrow">EMPIRICALLY INFORMED · HEADLINE CTR</div>',unsafe_allow_html=True)
        st.markdown('**A separate Upworthy laboratory**')
        st.write('Historical headline experiments inform traffic patterns, baseline CTR anchors and an approximate '
                 'distribution of underlying effects. New synthetic A/B pairs are then sampled from those assumptions.')
        st.write('We account for measurement noise when fitting the effect distribution. Treating every observed '
                 'historical uplift as a true effect would bake sampling noise into the simulator.')
    with b,st.container(border=True):
        st.markdown('<div class="eyebrow">HYPOTHETICAL · PRODUCT CHALLENGES</div>',unsafe_allow_html=True)
        st.markdown('**Retention, acquisition, onboarding and monetization**')
        st.write('These fictional programs use explicit baseline, traffic and effect assumptions. They let you '
                 'explore the mechanism in familiar product settings.')
        st.write('Headline click-through effects do not establish retention or revenue effects. These challenges '
                 'are not claimed to be calibrated from Upworthy or measured at a real company.')
    st.caption('Archive source: [Upworthy documentation](https://upworthy.natematias.com/about-the-archive.html) · '
               '[Randomization-risk correction](https://upworthy.natematias.com/2024-06-upworthy-archive-update.html). '
               'Methodology contains source attribution, exact assumptions and diagnostic reports.')

    st.subheader('How we check the simulations and models')
    st.write('The value is not just knowing the answer. It is constructing a comparison that avoids '
             '**giving a correction an unfair advantage** and makes the remaining uncertainty visible.')
    checks=[
        ('🧹','Clean at experiment level','We exclude the documented randomization-risk period and invalid experiments. '
         'Undeployed packages do not enter calibration.','AVOID: UNRELIABLE SOURCE OUTCOMES'),
        ('🔬','Separate signal from noise','A measurement-error-aware mixture fits effect variation. '
         'Bootstrap refits and alternative pair/support choices expose uncertainty.','AVOID: CALLING OBSERVED LIFT THE TRUTH'),
        ('🧩','Preserve realistic design features','CTR sample sizes and pooled-rate anchors are sampled together '
         'from source-derived records; counts come from binomial sampling. Effect/design independence remains an assumption.',
         'AVOID: ARBITRARY UPLIFTS AND INTERVALS'),
        ('🔎','Check on separate data','Exploratory data fit the calibration. Confirmatory and final holdout data '
         'check observable distributions without refitting. We publish the mismatches too.','AVOID: CHECKING ONLY THE FITTING DATA'),
        ('🌍','Make models face unfamiliar worlds','Independent histories train the estimators. Non-Normal effects, '
         'rare breakthroughs and distribution shifts challenge their assumptions. No hidden truth enters fitting.',
         'AVOID: DESIGNING THE GENERATOR TO MAKE BAYES WIN'),
        ('🔁','Repeat the comparison fairly','All methods receive the same observable data. Independent portfolios '
         'measure errors and decision regret with Monte Carlo intervals; seeds and artifact IDs make results replayable.',
         'AVOID: A CHERRY-PICKED SUCCESS STORY')]
    for start in (0,2,4):
        for col,(icon,title,copy,tag) in zip(st.columns(2),checks[start:start+2]):
            with col:tile(icon,title,copy,tag)
    st.info('Reproducible does not mean perfectly realistic. The held-out Upworthy checks show distributional '
            'discrepancies, especially in CTR and tails. The model likelihoods are approximations. '
            'These simulations support conditional comparisons under documented assumptions, not guaranteed business forecasts.')
    st.write('A Bayesian correction uses historical information to pull a noisy estimate toward effects the model '
             'considers plausible. Less precise results often move more. **An unsuitable history can pull in the wrong '
             'direction.** Benchmark reports improvements and failures; it does not assume that Bayes wins.')

    render_research_context()
    st.divider()
    st.subheader('Your turn: choose, then check')
    a,b,c=st.columns(3,gap='large')
    with a:
        st.markdown('**Choose → Launch**')
        st.write('Choose a program, inspect a stable portfolio and decide what to launch. Analyze your choices before seeing any correction.')
    with b:
        st.markdown('**Correct & reveal**')
        st.write('One click shows the historical correction, the simulated truth and where the adjustment helped or hurt.')
    with c:
        st.markdown('**Understand**')
        st.write('Inspect individual intervals and compare estimators. Use Benchmark for repeated comparisons and Methodology for the evidence.')
    st.button('Choose your challenge →',type='primary',on_click=navigate,args=('Choose',))
    st.caption('Navigation remains available above. Returning here does not erase your portfolio or launch choices.')
