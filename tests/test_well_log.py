"""Upload validation: the check that turns a bad file into a message rather
than a wrong prediction.
"""

import pandas as pd

from app.utils import validator

BUNDLE = {"required_curves": ["GR", "RHOB"], "optional_curves": ["CALI"]}


def test_a_present_but_all_null_curve_counts_as_missing():
    df = pd.DataFrame({"GR": [40.0, 50.0], "RHOB": [None, None], "CALI": [8.5, 8.5]})
    report = validator.build_curve_report(df, BUNDLE)
    assert report.required_missing == ["RHOB"]
    assert report.required_present == ["GR"]
    assert report.optional_present == ["CALI"]
