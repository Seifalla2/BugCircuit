import json
from pathlib import Path

import pytest

from bugcircuit.analyze import analyze
from bugcircuit.automation import read_workflow
from bugcircuit.layout import layout_events
from bugcircuit.cli import main


def test_offline_workflow_findings():
    path = Path(__file__).parent.parent / 'examples/workflow-failures.json'
    events, warnings = read_workflow(path)
    report = analyze(events, 'fixture', warnings)
    assert {f.code for f in report.findings} == {
        'WORKFLOW_FAILURES', 'WORKFLOW_TIMEOUTS', 'DUPLICATE_TRIGGER_EXECUTIONS'
    }
    blob = json.dumps(report.as_dict())
    assert 'demo-lead-42' not in blob
    assert all(f.evidence_ids for f in report.findings)


def test_bad_export_rejected(tmp_path):
    path = tmp_path / 'data.json'
    path.write_text('{"executions":null}')
    with pytest.raises(ValueError):
        read_workflow(path)


def test_payload_not_imported(tmp_path):
    path = tmp_path / 'data.json'
    path.write_text(json.dumps({'executions':[{'status':'failed', 'workflow':'demo',
                       'payload':{'password':'DONTLEAK'}}]}))
    ev, _ = read_workflow(path)
    assert 'DONTLEAK' not in json.dumps(ev[0].__dict__)


def test_layout_overflow():
    results = layout_events({'overflow':True, 'viewport':375, 'scrollWidth':421,
                             'hits':[{'selector':'div.hero'}]}, viewport_name='375')
    report = analyze([type(results[0])(**{**results[0].__dict__, 'id':'E0001'})], 'fixture')
    assert 'UI_HORIZONTAL_OVERFLOW' in {f.code for f in report.findings}


def test_layout_no_overflow():
    assert layout_events({'overflow':False, 'viewport':375, 'scrollWidth':375}, viewport_name='375') == []


def test_cli_workflow(tmp_path):
    source = Path(__file__).parent.parent / 'examples/workflow-failures.json'
    assert main(['analyze-workflow', str(source), '--out', str(tmp_path)]) == 0
    assert (tmp_path / 'report.html').exists()
