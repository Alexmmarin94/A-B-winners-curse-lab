"""Small visual layer; interaction stays in accessible native Streamlit widgets."""

import streamlit as st


def inject_style() -> None:
    st.markdown("""
    <style>
    .block-container {max-width: 1180px; padding-top: 5rem; padding-bottom: 3rem;}
    h1 {font-size: clamp(2.1rem, 4vw, 3.35rem) !important; letter-spacing: -.055em;
        line-height: 1.08 !important; font-weight: 750 !important;}
    h2 {letter-spacing: -.035em; font-size: 1.7rem !important;}
    h3 {letter-spacing: -.02em; font-size: 1.16rem !important;}
    p {line-height: 1.6;}
    .brand {font-size: .81rem; font-weight: 750; letter-spacing: .08em; line-height:1.7; min-height:1.8rem; padding:.2rem 0;}
    .brand-mark {color: #157566; margin-right: .6rem;}
    .status {text-align: right; color: #63777e; font-size: .76rem; padding-top: .2rem;}
    .eyebrow {font-size: .7rem; font-weight: 750; letter-spacing: .13em; color: #157566;
              margin: .4rem 0 .8rem;}
    .lede {font-size: 1.09rem; color: #53666d; max-width: 640px;}
    .journey {display: flex; flex-wrap: wrap; gap: .55rem; padding: .9rem 0 1.4rem;
              color: #708088; font-size: .79rem; align-items: center;}
    .journey .active {background: #dceee8; color: #146858; border-radius: 20px;
                      padding: .3rem .7rem; font-weight: 700;}
    .journey .future {color: #7c898f;}
    .illustration {background: #163f3e; border-radius: 18px; padding: 1.65rem;
                    color: #ecf6f1; margin: .4rem 0 1rem;}
    .illustration .eyebrow {color: #a3d3be;}
    .illustration .bar {border-radius: 5px; padding: .55rem .7rem; font-size: .8rem;
                        margin: .5rem 0; background: #3f7770; width: 62%;}
    .illustration .selected {width: 100%; background: #c7ead4; color: #153f3e; font-weight: 700;}
    .illustration .quiet {font-size: .77rem; color: #bbd3cd; margin-top: 1rem;}
    .explain-card {height:100%; border:1px solid #dce7e4; border-top:3px solid #157566;
      background:linear-gradient(140deg,#fff,#f0f7f4); border-radius:14px; padding:1rem 1.15rem; margin:.3rem 0 .7rem;}
    .explain-icon {font-family:"Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif; font-size:1.35rem; margin-right:.3rem;}
    .explain-card p {font-size:.9rem; line-height:1.5; margin:0; color:#405b61;}
    .explain-card .eyebrow {font-size:.62rem; margin:0 0 .45rem;}
    .explain-card.gold {border-top-color:#b77532; background:linear-gradient(140deg,#fff,#fbf4e8);}
    .explain-card.blue {border-top-color:#3973ac; background:linear-gradient(140deg,#fff,#edf4fb);}
    .business-hook {background:linear-gradient(120deg,#123c3b,#246b5c); border-radius:18px; padding:1.3rem 1.5rem;
      color:#edf8f3; margin:.7rem 0 1rem; font-size:1rem;}
    .business-hook strong {color:#d1f2db;}
    .scope-strip {padding:.8rem 1rem; border-left:4px solid #157566; background:#e8f2ed;
      border-radius:0 10px 10px 0; margin:.6rem 0; font-size:.9rem;}
    .scenario-icon {font-size: 1.7rem; color: #157566; margin-bottom: .25rem;}
    .effect-value {font-size: 1.8rem; font-weight: 700; letter-spacing: -.04em; color: #172d35;}
    .effect-value span {font-size: .76rem; font-weight: 400; letter-spacing: 0; color: #63777e;}
    [class*="st-key-experiment_card_"] [data-testid="stVerticalBlock"] {gap: .4rem;}
    [class*="st-key-experiment_card_"] h3 {font-size: 1.02rem !important; line-height: 1.3 !important;}
    .pipeline {background: #edf2f1; padding: 1.1rem; border-radius: 10px;
               font-size: .86rem; line-height: 1.9; color: #35514e;}
    div[data-testid="stVerticalBlockBorderWrapper"] > div {border-radius: 14px;}
    div[data-testid="stMetricValue"] {font-size: 1.45rem;}
    .st-key-experiment_inspector {background:#edf5f2; border-radius:16px;}
    .st-key-experiment_inspector [data-baseweb="select"] > div {min-height:3.5rem; font-size:1.15rem;}
    .st-key-experiment_inspector [data-testid="stWidgetLabel"] p {font-size:1.05rem; font-weight:700;}
    .footer {border-top: 1px solid #dce4e4; padding-top: 1rem; margin-top: 2rem;
             color: #708088; font-size: .75rem;}
    @media (max-width: 640px) {
      .block-container {padding-top: 5rem;}
      .status {text-align: left;}
    }
    </style>
    """, unsafe_allow_html=True)
