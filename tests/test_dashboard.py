"""The local dashboard must build from the real pipeline code."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../scripts"))
import build_dashboard  # noqa: E402


def test_dashboard_builds_with_real_pipeline_output():
    path = build_dashboard.build()
    html = open(path, encoding="utf-8").read()
    assert "__SCEN__" not in html
    for kind in ("HIGH_CPU", "DISK_FULL", "INSTANCE_FAILURE", "NETWORK_ISSUE"):
        assert kind in html
    assert "[IP_REDACTED]" in html and "S3cret!" in html.split("[CREDENTIAL_REDACTED]")[0]  # raw shown, redacted present


if __name__ == "__main__":
    test_dashboard_builds_with_real_pipeline_output()
    print("Results: 1 passed, 0 failed")
