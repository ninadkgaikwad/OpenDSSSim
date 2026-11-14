from opendsssim.plant.solution import SolutionResult


def test_solution_result_is_serializable():
    result = SolutionResult(
        converged=True,
        iterations=2,
        total_iterations=2,
        control_iterations=1,
        process_time_s=0.01,
        solve_mode="Snap",
        circuit_name="a01",
        num_buses=2,
        num_nodes=6,
        num_circuit_elements=3,
        total_power_kw=-300.0,
        total_power_kvar=-100.0,
        engine_version="engine",
        altdss_version="0.2.4",
        context_identity=123,
    )
    payload = result.to_dict()
    assert payload["converged"] is True
    assert payload["context_identity"] == 123
