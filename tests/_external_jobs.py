"""External jobs for testing, picked by "tests._external_jobs:<class name>"."""

from himena_relion.external import RelionExternalJob


class CountLinesJob(RelionExternalJob):
    """Count the lines of the input micrographs.star file."""

    def output_nodes(self):
        return [("count.txt", "LogFile.txt.himena.count")]

    @classmethod
    def job_title(cls) -> str:
        return "Count Lines"

    def run(self, in_mics, repeat: int = 1, fail: bool = False, j=1):
        job_dir = self.output_job_dir
        lines = job_dir.resolve_path(in_mics).read_text().splitlines()
        self.console.log(f"{len(lines)} lines, {j} threads")
        for i in range(repeat):
            job_dir.path.joinpath("progress.txt").write_text(str(i))
            yield
        if fail:
            raise ValueError("failed as requested")
        job_dir.path.joinpath("count.txt").write_text(str(len(lines) * repeat))


class TouchJob(RelionExternalJob):
    """Write an empty file (the job is not a generator)."""

    def output_nodes(self):
        return []

    def run(self, in_parts, in_mask="", name: str = "touched.txt"):
        if name == "":
            raise ValueError("name must be given")
        self.output_job_dir.path.joinpath(name).touch()
