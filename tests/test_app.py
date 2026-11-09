"""Integration tests for durable observable-only UI state."""

from dataclasses import asdict
import json
from pathlib import Path
import pytest

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def launch_app():
    app = AppTest.from_file(str(APP), default_timeout=15).run()
    app.radio[0].set_value("Launch").run()
    assert not app.exception
    return app


def button(app, label):
    return next(item for item in app.button if item.label == label)


def test_initial_journey_and_persistent_challenge():
    app = AppTest.from_file(str(APP)).run()
    assert not app.exception
    assert "Your winners look great" in app.title[0].value
    app.button[0].click().run()
    app.button(key="choose_monetization").click().run()
    assert any(metric.value == "5%" for metric in app.metric)
    button(app, "Open experiment playground →").click().run()
    assert len(app.checkbox) == 9
    assert app.session_state["scenario"] == "monetization"
    assert not app.exception
    app.radio[0].set_value("Learn").run()
    app.radio[0].set_value("Choose").run()
    assert app.session_state["scenario"] == "monetization"


def test_learning_explains_selection_and_provenance_before_the_challenge(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("The teaching illustration must not generate a challenge portfolio.")
    monkeypatch.setattr("app.playground_state.generate_observed", forbidden)
    app = AppTest.from_file(str(APP)).run()
    assert not app.exception
    assert app.session_state["section"] == "Learn"
    assert app.query_params["page"] == "Learn"
    headings = [item.value for item in app.subheader]
    assert "Selection changes the story" in headings
    assert "We simulate so we can check the answer" in headings
    assert "Where the assumptions come from" in headings
    assert "How we check the simulations and models" in headings
    assert any("Teaching illustration only" in item.value for item in app.caption)
    assert [item.value for item in app.metric] == ["+1.00 pp", "+1.00 pp"]
    app.toggle(key="learning_selected_only").set_value(True).run()
    assert not app.exception
    assert [item.value for item in app.metric] == ["+1.75 pp", "+1.00 pp"]
    assert "playgrounds" not in app.session_state


def test_explicit_learning_link_preserves_existing_launch_choices():
    app = launch_app()
    program = app.session_state["playgrounds"]["retention"]
    original_observed = program.observed
    key = app.checkbox[0].key
    selection = not app.checkbox[0].value
    app.checkbox[0].set_value(selection).run()
    app.query_params["page"] = "Learn"
    app.run()
    assert not app.exception
    assert app.session_state["section"] == "Learn"
    app.toggle(key="learning_selected_only").set_value(True).run()
    assert app.session_state["section"] == "Learn"
    app.radio[0].set_value("Launch").run()
    assert app.query_params["page"] == "Launch"
    assert app.checkbox(key=key).value == selection
    assert app.session_state["playgrounds"]["retention"].observed == original_observed


def test_checkbox_shuffle_navigation_do_not_regenerate(monkeypatch):
    app = launch_app()
    program = app.session_state["playgrounds"]["retention"]
    initial = program.observed
    key, selected = app.checkbox[0].key, app.checkbox[0].value
    def forbidden(*args):
        raise AssertionError("Widget interaction must not regenerate the portfolio.")
    monkeypatch.setattr("app.playground_state.generate_observed", forbidden)
    app.checkbox[0].set_value(not selected).run()
    assert not app.exception
    first_ids=program.current_ids.copy()
    app.button(key="shuffle").click().run()
    assert not app.exception
    assert first_ids.isdisjoint(program.current_ids)
    assert not any(program.selections[k] for k in first_ids)
    assert program.observed == initial
    # Returning to a discarded batch resets default choices, not previous manual choices.
    for _ in range(program.batches-1):app.button(key="shuffle").click().run()
    default=program.batch_items(program.batch)[0].estimate
    assert app.checkbox(key=key).value == (default.effect > 0 and default.significant)
    app.checkbox(key=key).set_value(not default.significant).run()
    current_value=app.checkbox(key=key).value
    app.radio[0].set_value("Learn").run()
    app.radio[0].set_value("Launch").run()
    assert app.checkbox(key=key).value == current_value
    assert not app.exception


def test_explicit_summary_invalidation_and_zero_launches():
    app = launch_app()
    assert len(app.metric) == 0
    for checkbox in app.checkbox:
        checkbox.set_value(False)
    app.run()
    app.button(key="analyze_launches").click().run()
    assert not app.exception
    assert [metric.value for metric in app.metric] == ["9", "0", "—"]
    assert any("No treatments selected" in message.value for message in app.info)
    assert app.button(key="apply_correction").disabled
    app.checkbox[0].set_value(True).run()
    assert len(app.metric) == 0
    assert any("Analyze again" in message.value for message in app.info)
    app.button(key="analyze_launches").click().run()
    assert [metric.value for metric in app.metric][:2] == ["9", "1"]
    assert len(app.get("plotly_chart")) == 1
    app.button(key="shuffle").click().run()
    assert len(app.metric) == 0
    assert not app.exception


def test_new_seed_and_same_seed_replay_reset():
    app = launch_app()
    initial = app.session_state["playgrounds"]["retention"].observed
    app.number_input[0].set_value(17).run()
    app.button(key="generate_portfolio").click().run()
    program = app.session_state["playgrounds"]["retention"]
    assert program.config.seed == 17
    assert program.observed != initial
    assert len(program.reviewed) == 9
    regenerated = program.observed
    app.checkbox[0].set_value(not app.checkbox[0].value).run()
    app.button(key="generate_portfolio").click().run()
    program = app.session_state["playgrounds"]["retention"]
    assert program.observed == regenerated
    assert program.summary is None
    for checkbox, item in zip(app.checkbox, program.visible()):
        assert checkbox.value == (item.estimate.effect > 0 and item.estimate.significant)
    assert not app.exception


def test_truth_absent_and_corrections_not_faked():
    app = launch_app()
    state = json.dumps(asdict(app.session_state["playgrounds"]["retention"]), default=list)
    for forbidden in ('"truth"', '"control_probability"', '"treatment_probability"', '"true_effect"'):
        assert forbidden not in state
    assert any("not calibrated" in message.value for message in app.warning)
    app.radio[0].set_value("Methodology").run()
    assert any("Main challenge cards remain A/B" in message.value for message in app.warning)
    assert not app.exception


def test_scenario_switch_preserves_prior_choices():
    app = launch_app()
    key, original = app.checkbox[0].key, app.checkbox[0].value
    app.checkbox[0].set_value(not original).run()
    retained = app.session_state["playgrounds"]["retention"].observed
    app.radio[0].set_value("Choose").run()
    app.button(key="choose_acquisition").click().run()
    button(app, "Open experiment playground →").click().run()
    assert app.session_state["playgrounds"]["acquisition"].config.metric == "Signup conversion"
    app.button(key="generate_portfolio").click().run()
    app.radio[0].set_value("Choose").run()
    app.button(key="choose_retention").click().run()
    button(app, "Open experiment playground →").click().run()
    assert app.session_state["playgrounds"]["retention"].observed == retained
    assert app.checkbox(key=key).value == (not original)
    assert not app.exception


def test_archive_playground_and_methodology_work_without_raw_reads(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("The interactive demo must not read raw CSVs.")
    monkeypatch.setattr("pandas.read_csv", forbidden)
    app = AppTest.from_file(str(APP), default_timeout=15).run()
    app.radio[0].set_value("Choose").run()
    app.button(key="choose_upworthy_ctr").click().run()
    button(app, "Open experiment playground →").click().run()
    assert not app.exception
    assert len(app.checkbox) == 9
    program = app.session_state["playgrounds"]["upworthy_ctr"]
    assert program.config.calibration_id
    assert any("Archive-calibrated" in warning.value for warning in app.warning)
    app.checkbox[0].set_value(True).run()
    app.button(key="analyze_launches").click().run()
    assert not app.exception
    app.button(key="apply_correction").click().run()
    assert not app.exception
    assert program.revealed_effects is not None
    assert any("demonstrated failure case" in warning.value for warning in app.warning)
    assert not app.exception
    assert program.revealed_effects is not None
    app.radio[0].set_value("Methodology").run()
    assert not app.exception
    assert any("3,823" == metric.value for metric in app.metric)
    assert len(app.get("plotly_chart")) == 3


def test_one_action_corrects_then_reveals_and_selection_changes_invalidate_both(monkeypatch):
    from src.models import artifacts
    original_predict=artifacts.correct_observations
    calls=[]
    app = launch_app()
    app.checkbox[0].set_value(True).run()
    app.button(key="analyze_launches").click().run()
    program = app.session_state["playgrounds"]["retention"]
    original = program.observed
    assert program.corrections is None and program.revealed_effects is None
    assert 'revealed_effects' not in program.snapshot()
    assert not any(b.key=='reveal_truth' for b in app.button)
    def predict_before_truth(observed, selected, artifact):
        assert program.revealed_effects is None
        calls.append(selected)
        return original_predict(observed,selected,artifact)
    monkeypatch.setattr('app.playground_state.correct_observations',predict_before_truth)
    app.button(key="apply_correction").click().run()
    assert not app.exception
    assert calls and program.corrections is not None and program.revealed_effects is not None
    assert any("Mean true effect" in metric.label for metric in app.metric)
    assert any("Estimates improved" in metric.label for metric in app.metric)
    assert program.observed == original
    assert not app.button(key='next_understand').disabled
    app.checkbox[0].set_value(False).run()
    assert not app.exception
    assert program.corrections is None and program.revealed_effects is None
    assert not any("Mean true effect" in metric.label for metric in app.metric)


def test_training_seed_disables_correction_with_explanation():
    app = launch_app()
    app.number_input[0].set_value(73000001).run()
    app.button(key="generate_portfolio").click().run()
    app.checkbox[0].set_value(True).run()
    app.button(key="analyze_launches").click().run()
    assert app.button(key="apply_correction").disabled
    assert any("overlaps" in warning.value for warning in app.warning)
    assert not app.exception


@pytest.mark.parametrize('scenario', ['retention', 'acquisition', 'onboarding', 'monetization', 'upworthy_ctr'])
def test_two_checked_cards_unlock_correction_from_visible_widget_values(scenario):
    app = AppTest.from_file(str(APP), default_timeout=15).run()
    app.session_state['scenario'] = scenario
    app.radio[0].set_value('Launch').run()
    for index, checkbox in enumerate(app.checkbox):
        checkbox.set_value(index < 2)
    app.run()
    program = app.session_state['playgrounds'][scenario]
    # Reproduce durable selections lagging behind visible widgets after a reload.
    program.selections = dict.fromkeys(program.reviewed, False)
    app.button(key='analyze_launches').click().run()
    assert len(program.summary.selected_ids) == 2
    assert not app.button(key='apply_correction').disabled
    assert any('Ready to compare 2' in caption.value for caption in app.caption)
    app.button(key='apply_correction').click().run()
    assert app.button(key='apply_correction').label == 'Correction & truth shown ✓'
    assert len(program.revealed_effects) == 2
    assert not app.exception


def test_deep_dive_respects_progressive_disclosure_and_benchmark_navigation():
    app=launch_app()
    app.checkbox[0].set_value(True).run()
    program=app.session_state['playgrounds']['retention']
    selected_id=program.visible()[0].experiment_id
    app.radio[0].set_value('Understand').run()
    app.selectbox[0].set_value(selected_id).run()
    before=json.loads(app.get('plotly_chart')[0].proto.spec)
    assert len(before['data'])==1
    assert not any('True effect' in str(a) for a in before['layout'].get('annotations',[]))
    app.radio[0].set_value('Launch').run()
    app.button(key='analyze_launches').click().run()
    app.button(key='apply_correction').click().run()
    app.radio[0].set_value('Understand').run()
    app.selectbox[0].set_value(selected_id).run()
    corrected=json.loads(app.get('plotly_chart')[0].proto.spec)
    assert len(corrected['data'])==4
    assert any('True effect' in str(a) for a in corrected['layout'].get('annotations',[]))
    assert len(app.tabs)==4
    assert len(app.latex)>=5
    app.radio[0].set_value('Benchmark').run()
    for case in ['rare_breakthroughs','abn','archive_ctr']:
        app.selectbox[0].set_value(case).run()
        assert not app.exception
        assert len(app.get('plotly_chart'))==1


def test_saved_rounds_survive_shuffle_and_only_current_editor_is_mutable():
    app=launch_app()
    for i,c in enumerate(app.checkbox):c.set_value(i<3)
    app.run()
    program=app.session_state['playgrounds']['retention']
    saved={key for key in program.current_ids if program.selections[key]}
    app.button(key='more_experiments').click().run()
    for i,c in enumerate(app.checkbox):c.set_value(i<4)
    app.run()
    assert sum(program.selections.values())==7
    assert len(app.multiselect[0].value)==4
    assert any('7 selected in total' in item.value and '4 in these 9 editable cards' in item.value for item in app.markdown)
    current=program.current_ids.copy()
    app.button(key='shuffle').click().run()
    assert all(program.selections[key] for key in saved)
    assert not any(program.selections[key] for key in current)
    assert saved.isdisjoint(program.current_ids)
    for i,c in enumerate(app.checkbox):c.set_value(i<4)
    app.run()
    app.button(key='analyze_launches').click().run()
    assert len(program.summary.selected_ids)==7
    app.button(key='apply_correction').click().run()
    from app.corrections import comparison_figure,mean_effect_figure
    assert len(comparison_figure(program).data[0].x)==7
    assert len(mean_effect_figure(program).data)==2
    assert not app.button(key='next_understand').disabled
    assert len(comparison_figure(program).data[2].x)==7
    assert len(mean_effect_figure(program,include_truth=True).data)==3
    from statistics import mean
    keys=tuple(program.corrections)
    assert mean_effect_figure(program,include_truth=True).data[2].x[0]==pytest.approx(
        100*mean(program.revealed_effects[k] for k in keys))
    app.multiselect[0].set_value(app.multiselect[0].value[:2]).run()
    assert not app.exception
    assert sum(c.value for c in app.checkbox)==2
    assert all(program.selections[key] for key in saved)
    assert program.summary is None and program.corrections is None and program.revealed_effects is None
    app.button(key='analyze_launches').click().run()
    assert len(program.summary.selected_ids)==5


def test_three_more_rounds_limit_keeps_shuffle_and_analysis_available():
    app=launch_app()
    assert not any('full demo selection' in x.value for x in app.info)
    saved=set()
    for round_index in range(3):
        for i,c in enumerate(app.checkbox):c.set_value(i<2)
        app.run()
        program=app.session_state['playgrounds']['retention']
        saved.update(key for key in program.current_ids if program.selections[key])
        app.button(key='more_experiments').click().run()
        assert len(program.locked_batches)==round_index+1
        assert all(program.selections[key] for key in saved)
    assert app.button(key='more_experiments').disabled
    assert any('full demo selection' in x.value for x in app.info)
    assert not app.button(key='shuffle').disabled
    for _ in range(5):
        before=program.current_ids.copy()
        app.button(key='shuffle').click().run()
        assert program.current_ids.isdisjoint(before|saved)
        assert all(program.selections[key] for key in saved)
    for i,c in enumerate(app.checkbox):c.set_value(i==0)
    app.run()
    app.button(key='analyze_launches').click().run()
    assert len(program.summary.selected_ids)==7
    assert len(program.summary.reviewed_ids)==36
    app.button(key='apply_correction').click().run()
    app.button(key='next_understand').click().run()
    assert app.session_state['section']=='Understand'
    app.button(key='next_section').click().run()
    assert app.session_state['section']=='Benchmark'
    app.button(key='next_section').click().run()
    assert app.session_state['section']=='Methodology'
    app.button(key='next_section').click().run()
    assert app.session_state['section']=='Choose'
    assert not app.exception


def test_experiment_switch_updates_all_formulas_and_weight_charts():
    app=launch_app()
    for i,c in enumerate(app.checkbox):c.set_value(i<2)
    app.run()
    app.button(key='analyze_launches').click().run()
    app.button(key='apply_correction').click().run()
    program=app.session_state['playgrounds']['retention']
    ids=program.summary.selected_ids
    app.radio[0].set_value('Understand').run()
    app.selectbox[0].set_value(ids[0]).run()
    first=[x.value for x in app.latex]
    first_charts=[x.proto.spec for x in app.get('plotly_chart')]
    app.selectbox[0].set_value(ids[1]).run()
    assert not app.exception
    assert first != [x.value for x in app.latex]
    assert all(a!=b.proto.spec for a,b in zip(first_charts,app.get('plotly_chart')))
    assert len(app.tabs)==4
    assert any('Absolute error:' in x.value for x in app.info)


def test_inspector_defaults_to_selected_and_explains_truth_visibility():
    app=launch_app()
    for i,c in enumerate(app.checkbox):c.set_value(i<2)
    app.run()
    app.button(key='analyze_launches').click().run()
    app.button(key='apply_correction').click().run()
    program=app.session_state['playgrounds']['retention']
    selected=set(program.summary.selected_ids)
    app.radio[0].set_value('Understand').run()
    assert len(app.selectbox[0].options)==2
    assert app.selectbox[0].value in selected
    assert any('of 2 selected for launch' in x.value for x in app.caption)
    assert any('Orange dashed vertical line = true simulated effect' in x.value for x in app.markdown)
    assert any('gray dotted vertical line at 0 pp' in x.value for x in app.caption)
    app.toggle[0].set_value(True).run()
    assert len(app.selectbox[0].options)==9
    assert any('of 9 reviewed' in x.value for x in app.caption)
    unselected=next(r.experiment_id for r in program.visible() if r.experiment_id not in selected)
    app.selectbox[0].set_value(unselected).run()
    assert any('No orange truth line: this experiment was not selected' in x.value for x in app.info)
    chart=json.loads(app.get('plotly_chart')[0].proto.spec)
    assert not any(shape.get('line',{}).get('color')=='#c18424' for shape in chart['layout']['shapes'])
    app.toggle[0].set_value(False).run()
    assert not app.exception
    assert app.selectbox[0].value in selected
    assert len(app.selectbox[0].options)==2
    chart=json.loads(app.get('plotly_chart')[0].proto.spec)
    assert any('True effect · orange dashed line:' in a['text'] for a in chart['layout']['annotations'])


def test_inspector_with_zero_selections_can_opt_into_reviewed_experiments():
    app=launch_app()
    for c in app.checkbox:c.set_value(False)
    app.run()
    app.radio[0].set_value('Understand').run()
    assert not app.exception
    assert not app.selectbox
    assert any('No experiments selected for launch' in x.value for x in app.info)
    app.toggle[0].set_value(True).run()
    assert len(app.selectbox[0].options)==9
    assert not app.exception
