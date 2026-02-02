import simulator_core, whatif

def test_runway_negative():
    r = simulator_core.compute_runway(2000, 3000, 6000)
    assert r == 6.0

def test_whatif_baseline_present():
    out = whatif.run_scenarios(3000, 2500, 10000)
    assert "baseline" in out and "scenarios" in out
