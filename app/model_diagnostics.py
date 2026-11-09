"""Compact observable predictive diagnostics, separate from latent-effect benchmarks."""
import json
from pathlib import Path
import pandas as pd
import streamlit as st
from app.configuration import make_config
from src.models.artifacts import content_id,load_model
from app.benchmark_view import LABELS


def render_predictive_checks():
    with st.expander('Model predictive checks · new observable outcomes'):
        path=Path(__file__).resolve().parents[1]/'data/models/predictive_checks_v1.json'
        try:
            report=json.loads(path.read_text());identifier=report.pop('artifact_id')
            if content_id(report)!=identifier:raise ValueError('Predictive report checksum mismatch.')
            report['artifact_id']=identifier
            config=make_config(st.session_state.scenario);entry=report['scenarios'][config.scenario]
            for method,value in entry['methods'].items():
                if load_model(config,estimator=method)['artifact_id']!=value['artifact_id']:
                    raise ValueError('Predictive check does not match current model.')
        except (OSError,ValueError,KeyError) as error:
            st.info(f'Predictive checks unavailable: {error}');return
        st.write(f"Current challenge: {config.metric}. {entry['n']:,} observations from {entry['source']['partition']}.")
        st.write(report['interpretation'])
        st.dataframe(pd.DataFrame([{'Estimator':LABELS[m],
            'Observed predictive coverage (nominal 95%)':v['central_95_predictive_coverage']['mean'],
            'Mean log predictive density (nats)':v['mean_log_density_nats']['mean']}
            for m,v in entry['methods'].items()]),hide_index=True,use_container_width=True)
        st.caption('This checks the distribution of new noisy estimates. It does not establish accuracy or coverage '
                   'for selected true effects. Sparse observations remain in this diagnostic to avoid outcome-based filtering.')
        for limitation in report['limitations']:st.caption(limitation)
        st.download_button('Download model predictive checks',json.dumps(report,indent=2),file_name=path.name,mime='application/json')
