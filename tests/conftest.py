import numpy as np
import pytest

from app.petrologix.compute_porosity import WellCurves
from app.schemas.predictions import LithologyInterval


def make_interval(top=1000.0, base=1100.0, lithology="Sandstone", confidence=0.95,
                  code=30000):
    return LithologyInterval(
        top=top, base=base, thickness=base - top,
        lithology_code=code, lithology=lithology,
        confidence=confidence, n_samples=int((base - top) * 10),
    )


@pytest.fixture
def sandstone_interval():
    return make_interval()


@pytest.fixture
def clean_curves():
    """A 1000-1100 m sand with RHOB 2.25 g/cc -- 25% density porosity."""
    depth = np.arange(1000.0, 1100.1, 0.5)
    rhob = np.full(depth.shape, 2.25)
    cali = np.full(depth.shape, 8.5)
    return WellCurves(depth, rhob, cali=cali, well_name="TEST-1")
