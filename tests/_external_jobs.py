"""External jobs for testing, picked by "tests._external_jobs:<class name>"."""

from himena_relion.external import RelionExternalContinue, RelionExternalJob


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


class AccumulateJob(RelionExternalJob):
    """Write `value` to total.txt. The total is updated by continuing the job."""

    def output_nodes(self):
        return [("total.txt", "LogFile.txt.himena.total")]

    def run(self, in_mics, value: int = 1, label: str = "a", j=1):
        self.output_job_dir.path.joinpath("total.txt").write_text(str(value))
        yield


def _update_total(job: RelionExternalJob, func) -> None:
    path = job.output_job_dir.path.joinpath("total.txt")
    path.write_text(str(func(int(path.read_text()))))


class AddToTotal(RelionExternalContinue):
    """Add the value to the total `repeat` times (`repeat` is only for continuing)."""

    original_class = AccumulateJob

    def run(self, in_mics, value: int = 1, repeat: int = 1):
        _update_total(self, lambda total: total + value * repeat)
        self.output_job_dir.path.joinpath("continued_with.txt").write_text(in_mics)
        yield


class MultiplyTotal(RelionExternalContinue):
    """Multiply the total by the value (not a generator)."""

    original_class = AccumulateJob

    @classmethod
    def job_title(cls) -> str:
        return "Multiply Total"

    def run(self, value: int = 2):
        _update_total(self, lambda total: total * value)


class TouchJob(RelionExternalJob):
    """Write an empty file (the job is not a generator)."""

    def output_nodes(self):
        return []

    def run(self, in_parts, in_mask="", name: str = "touched.txt"):
        if name == "":
            raise ValueError("name must be given")
        self.output_job_dir.path.joinpath(name).touch()
