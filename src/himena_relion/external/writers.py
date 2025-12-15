from __future__ import annotations
from pathlib import Path

import pandas as pd
from himena_relion import _job
from himena_relion.consts import ARG_NAME_REMAP

# https://deepwiki.com/3dem/relion/3.3-scheduling-and-automation

# mkdir External/job015
# relion_pipeliner --addJobFromStar External/job015/job.star
# relion_pipeliner --RunJobs "External/job015/"


def prep_job_star(
    fn_exe: str,
    **kwargs,
) -> dict[str, pd.DataFrame]:
    params = {
        "do_queue": "No",
        "fn_exe": f"{fn_exe}",
        "in_3dref": "",
        "in_coords": "",
        "in_mask": "",
        "in_mic": "",
        "in_mov": "",
        "in_part": "",
        "min_dedicated": 1,
        "nr_threads": 1,
        "other_args": "",
        "param1_label": "",
        "param1_value": "",
        "param2_label": "",
        "param2_value": "",
        "param3_label": "",
        "param3_value": "",
        "param4_label": "",
        "param4_value": "",
        "param5_label": "",
        "param5_value": "",
        "param6_label": "",
        "param6_value": "",
        "param7_label": "",
        "param7_value": "",
        "param8_label": "",
        "param8_value": "",
        "param9_label": "",
        "param9_value": "",
        "param10_label": "",
        "param10_value": "",
        "qsub": "sbatch",
        "qsubscript": "/public/EM/RELION/relion/bin/relion_qsub.csh",
        "queuename": "openmpi",
    }
    current_param_index = 1

    arg_map = dict(ARG_NAME_REMAP)
    for key, value in kwargs.items():
        if isinstance(value, Path):
            value = str(value)
        if isinstance(value, _job.JobDirectory):
            pass  # this is himena-relion internal use only
        elif key in [
            "in_mics",
            "in_movies",
            "in_parts",
            "in_3dref",
            "in_coords",
            "in_mask",
        ]:
            remapped_key = arg_map.get(key, key)
            params[remapped_key] = str(value)
        elif key == "o":
            pass  # output job dir
        elif key == "j":
            params["nr_threads"] = value
        else:
            if current_param_index > 10:
                raise ValueError("Maximum of 10 additional parameters supported.")
            param_label_key = f"param{current_param_index}_label"
            param_value_key = f"param{current_param_index}_value"
            params[param_label_key] = key
            if isinstance(value, bool):
                value = "Yes" if value else "No"
            params[param_value_key] = value
            current_param_index += 1

    variables = []
    values = []
    for key, value in params.items():
        variables.append(key)
        values.append(value)
    return {
        "job": {
            "rlnJobTypeLabel": "relion.external",
            "rlnJobIsContinue": 0,
            "rlnJobIsTomo": 0,
        },
        "joboptions_values": pd.DataFrame(
            {
                "rlnJobOptionVariable": variables,
                "rlnJobOptionValue": values,
            }
        ),
    }
