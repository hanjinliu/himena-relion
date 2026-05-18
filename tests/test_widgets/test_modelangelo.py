from typing import Callable
from pathlib import Path

import numpy as np
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5.widgets._modelangelo import QModelAngeloViewer
from himena_relion.testing import JobWidgetTester

_CIF_TEXT = """data_1
#
loop_
_atom_site.group_PDB
_atom_site.id
_atom_site.type_symbol
_atom_site.label_atom_id
_atom_site.label_alt_id
_atom_site.label_comp_id
_atom_site.label_asym_id
_atom_site.label_entity_id
_atom_site.label_seq_id
_atom_site.pdbx_PDB_ins_code
_atom_site.Cartn_x
_atom_site.Cartn_y
_atom_site.Cartn_z
_atom_site.occupancy
_atom_site.B_iso_or_equiv
_atom_site.auth_seq_id
_atom_site.auth_asym_id
_atom_site.pdbx_PDB_model_num
ATOM 1     N N   . GLU A ? 160 ? 108.817 89.640  122.580 1 100.0     160 Aa 1
ATOM 2     C CA  . GLU A ? 160 ? 110.069 90.337  122.300 1 100.0     160 Aa 1
ATOM 3     C C   . GLU A ? 160 ? 110.264 91.521  133.243 1 100.0     160 Aa 1
ATOM 4     N N   . GLU A ? 160 ? 158.817 59.640  132.580 1 100.0     160 Aa 1
ATOM 5     C CA  . GLU A ? 160 ? 160.069 40.337  112.300 1 100.0     160 Aa 1
ATOM 6     C C   . GLU A ? 160 ? 170.264 51.521  113.243 1 100.0     160 Aa 1
ATOM 7     N N   . GLU A ? 160 ? 148.817 79.640  152.580 1 100.0     160 Aa 1
ATOM 8     C CA  . GLU A ? 160 ? 150.069 60.337  152.300 1 100.0     160 Aa 1
ATOM 9     C C   . GLU A ? 160 ? 130.264 31.521  163.243 1 100.0     160 Aa 1
"""
def test_modelangelo(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_spa,
):
    star_text = Path(jobs_dir_spa / "ModelAngelo" / "job001" / "job.star").read_text()
    lines = []
    for line in star_text.splitlines():
        if line.strip().startswith("fn_map"):
            line = "fn_map   Refine3D/job100/run_class001.mrc"
        lines.append(line)
    star_text = "\n".join(lines)


    prev_job_dir = make_job_directory(
        Path(jobs_dir_spa / "Refine3D" / "job001" / "job.star").read_text(),
        "Refine3D/job100"
    )
    mrc0 = np.arange(32 * 32 * 32, dtype=np.float32).reshape((32, 32, 32))
    refine3d = JobWidgetTester.no_widget(prev_job_dir)
    refine3d.write_mrc("run_class001.mrc", mrc0)

    job_dir = make_job_directory(star_text, "ModelAngelo")

    tester = JobWidgetTester(QModelAngeloViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)

    assert len(tester.widget._line_visuals) == 0
    tester.write_text("job025.cif", _CIF_TEXT)
    assert len(tester.widget._line_visuals) == 1
