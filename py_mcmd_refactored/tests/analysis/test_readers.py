from pathlib import Path
import pytest

from py_mcmd_refactored.analysis.readers import (
    configuration, console_records, histogram_records, read_csv, read_hybrid, read_mc,
)


def log_text(counts=(4,7)):
    return ('ETITLE: STEP TOTAL INTER(LJ) LRC TOTAL_ELECT\n'
            'STITLE: STEP TOTALMOL MOLFRAC_ZI8 MOLFRAC_ZI8 MOLFRAC_CH4\n' +
            ''.join(f'ENER_0: {step} -100 -99 -1 0\n'
            f'STAT_0: {step} {2208+n} {96/(2208+n):.10e} {2112/(2208+n):.10e} {n/(2208+n):.10e}\n'
            for step,n in zip((0,1000), counts)))


def conf_text(run=1000):
    return f'InitStep 0\nRunSteps {run}\nEqSteps 100\nSampleFreq 100\nHistogramFreq true 1000\nTemperature 298\n'


def test_console_count_duplicate_species_and_repeated_headers(tmp_path):
    p = tmp_path/'out.dat'
    p.write_text(log_text()+log_text())
    rows, kinds = console_records(p)
    assert [r['guest_count'] for r in rows] == [4,7]
    assert kinds == ['ZI8','ZI8','CH4']
    assert rows[1]['local_step'] == 1000
    assert rows[1]['nonbonded_energy_kcal_mol'] == pytest.approx(-0.198720425864083)


def test_energy_stat_join_uses_step_not_arrival(tmp_path):
    p = tmp_path/'out.dat'
    lines = log_text().splitlines()
    p.write_text('\n'.join(lines[:2]+[lines[2],lines[4],lines[3],lines[5]]))
    rows, _ = console_records(p)
    assert len(rows)==2 and all('nonbonded_energy_kcal_mol' in r for r in rows)


def test_conflicting_duplicate_rejected(tmp_path):
    p=tmp_path/'out.dat'
    p.write_text(log_text()+log_text((4,8)))
    with pytest.raises(ValueError,match='conflicting duplicate'):
        console_records(p)


def test_histogram_counts_step_reconstruction_and_truncation(tmp_path):
    conf=tmp_path/'in.conf'
    conf.write_text(conf_text())
    his=tmp_path/'his1a.dat'
    his.write_text('298 3 0 0 0 34 34 34\n'+'96 2112 7 -100\n'*9)
    rows, warnings = histogram_records(his,configuration(conf),['ZI8','ZI8','CH4'],'CH4')
    assert [r['local_step'] for r in rows] == list(range(200,1001,100))
    assert all(r['guest_count']==7 for r in rows)
    his.write_text('298 3 0 0 0 34 34 34\n96 2112 7 -100\n')
    _, warnings=histogram_records(his,configuration(conf),['ZI8','ZI8','CH4'],'CH4')
    assert any('Incomplete' in w for w in warnings)
    his.write_text(his.read_text()+'96 2112\n')
    with pytest.raises(ValueError,match='malformed'):
        histogram_records(his,configuration(conf),['ZI8','ZI8','CH4'],'CH4')


def test_explicit_histogram_kind_without_console(tmp_path):
    (tmp_path/'in.conf').write_text(conf_text())
    (tmp_path/'his1a.dat').write_text('298 2 0 0 34 34 34\n1 7 -100\n'*1)
    dataset=read_mc(tmp_path,kind_index=1)
    assert dataset.rows[0]['guest_count']==7


def make_segment(root, run, final=7, conf=None):
    directory=root/'GOMC'/f'{run:010d}'
    directory.mkdir(parents=True)
    (directory/'in.conf').write_text(conf or conf_text())
    (directory/'out.dat').write_text(log_text((4,final)))


def test_hybrid_endpoints_not_initial_records_and_complete_timings(tmp_path):
    make_segment(tmp_path,1,7)
    make_segment(tmp_path,3,7)  # unchanged states are retained
    (tmp_path/'logs').mkdir()
    (tmp_path/'logs'/'run.log').write_text('TIME_STATS_DATA: 0 2 1 1 4\nTIME_STATS_DATA: 1 3 1 1 5\n')
    dataset=read_hybrid(tmp_path)
    assert [r['guest_count'] for r in dataset.rows]==[7,7]
    assert [r['acquisition_seconds'] for r in dataset.rows]==[4,5]
    assert all(r['local_step']==1000 for r in dataset.rows)
    assert any('drain' in w for w in dataset.warnings)


@pytest.mark.parametrize("sectioned", [False, True])
def test_hybrid_continuation_warning_reads_both_json_layouts(tmp_path, sectioned):
    import json

    make_segment(tmp_path, 1)
    settings = {"starting_at_cycle_namd_gomc_sims": 2}
    if sectioned:
        settings = {"run_control": settings}
    (tmp_path / "user_input.json").write_text(json.dumps(settings))
    dataset = read_hybrid(tmp_path)
    assert any("parent cycles" in warning for warning in dataset.warnings)


def test_missing_cycle_or_changed_protocol_rejected(tmp_path):
    make_segment(tmp_path,1)
    make_segment(tmp_path,5)
    with pytest.raises(ValueError,match='Missing hybrid cycles'):
        read_hybrid(tmp_path)
    (tmp_path/'GOMC'/'0000000005').rename(tmp_path/'GOMC'/'0000000003')
    (tmp_path/'GOMC'/'0000000003'/'in.conf').write_text(conf_text()+'Temperature 300\n')
    with pytest.raises(ValueError,match='protocol'):
        read_hybrid(tmp_path)


def test_incomplete_hybrid_segment_rejected(tmp_path):
    make_segment(tmp_path,1,conf=conf_text(2000))
    with pytest.raises(ValueError,match='completed segment endpoint'):
        read_hybrid(tmp_path)


def test_csv_irregular_nonfinite_and_costs(tmp_path):
    p=tmp_path/'values.csv'
    p.write_text('sample_index,guest_count,acquisition_seconds\n0,7,2\n2,7,3\n4,8,4\n')
    dataset=read_csv(p)
    assert dataset.metadata['record_spacing']==2
    assert dataset.rows[1]['acquisition_seconds']==3
    p.write_text('sample_index,guest_count\n0,7\n1,8\n3,7\n')
    with pytest.raises(ValueError,match='regularly spaced'):
        read_csv(p)
    p.write_text('sample_index,guest_count\nnan,7\n')
    with pytest.raises(ValueError,match='finite'):
        read_csv(p)


def test_real_zif8_console_and_histogram_fixture():
    root=Path('/home/ia5498/zif8_methane/py_mcmd/physics_validation/switch_probe/GOMC/0000000013')
    if not root.exists():
        pytest.skip('Local real-output fixture unavailable; portable format tests remain active')
    rows,kinds=console_records(root/'out.dat')
    assert rows[-1]['guest_count']==7
    assert kinds.count('ZI8')==7
    samples,_=histogram_records(root/'his1a.dat',configuration(root/'in.conf'),kinds,'CH4')
    assert len(samples)==9 and samples[-1]['guest_count']==7
