import subprocess
from himena_relion.external import RelionExternalJob

class FlipHandedness(RelionExternalJob):
    def output_nodes(self):
        return [
            ("map_flipped.mrc", "DensityMap.mrc"),
        ]

    # @classmethod
    # def job_title(cls):
    #     return "Flip Handedness"

    def run(self, in_3dref):
        save_path = self.output_job_dir.path / "map_flipped.mrc"
        self.console.log(f"Flip handedness of {in_3dref} and write to {save_path}")
        subprocess.run(["relion_image_handler", "--i", in_3dref, "--o", save_path, "--invert_hand"], check=True)
