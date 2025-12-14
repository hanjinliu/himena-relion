from __future__ import annotations

import pandas as pd
from himena_relion import _job

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
    for key, value in kwargs.items():
        if isinstance(value, _job.JobDirectory):
            pass  # this is himena-relion internal use only
        elif key == "in_mics":
            params["in_mic"] = str(value)
        elif key == "in_movies":
            params["in_mov"] = str(value)
        elif key == "in_parts":
            params["in_part"] = str(value)
        elif key == "in_3dref":
            params["in_3dref"] = str(value)
        elif key == "in_coords":
            params["in_coords"] = str(value)
        elif key == "in_mask":
            params["in_mask"] = str(value)
        elif key == "o":
            pass  # output job dir
        elif key == "j":
            params["nr_threads"] = value
        else:
            param_label_key = f"param{current_param_index}_label"
            param_value_key = f"param{current_param_index}_value"
            params[param_label_key] = key
            params[param_value_key] = str(value)
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
