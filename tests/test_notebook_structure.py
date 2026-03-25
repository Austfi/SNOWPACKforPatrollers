import json
from pathlib import Path


def test_main_notebook_is_package_backed():
    notebook = json.loads(Path("SNOWPACKforPatrollers.ipynb").read_text())
    sources = ["".join(cell.get("source", [])) for cell in notebook["cells"]]
    combined = "\n".join(sources)
    combined_lower = combined.lower()

    assert "run_full_workflow(" in combined
    assert 'forcing_provider = "auto"' in combined
    assert "snowpack_patrollers.models" in combined
    assert "run top-to-bottom in colab on the first try" in combined_lower
    assert "enable_custom_widget_manager" in combined
    assert "num_slopes = 1" in combined
    assert 'north_slope = False' in combined
    assert 'sys.path.insert(0, str(repo_dir))' in combined
    assert '"-e"' not in combined
    assert 'NOTEBOOK_BRANCH = "feature/colab-oneclick"' in combined
    assert '"--branch"' in combined
