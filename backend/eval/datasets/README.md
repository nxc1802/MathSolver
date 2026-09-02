# MathSolver Benchmark Datasets

Standardized evaluation benchmarks for regression testing, metric tracking, and ablation studies.

## Dataset Structure

Each JSON file in `eval/datasets/` contains problem samples adhering to the `BenchmarkSample` schema:

```json
{
  "id": "geo_01_square_pyramid",
  "category": "3d_pyramid",
  "problem_text": "Cho hình chóp S.ABCD...",
  "expected_type": "pyramid",
  "expected_entities": ["S", "A", "B", "C", "D"],
  "expected_dsl": "PYRAMID(S_ABCD)\nSQUARE(ABCD)...",
  "expected_answer": "32"
}
```

## Running Evaluation

To evaluate deterministic DSL solvability & geometry validator pass rates:

```python
from eval.benchmark import BenchmarkDataset
from eval.runner import EvalRunner

dataset = BenchmarkDataset.load_all_standard()
runner = EvalRunner()
metrics = runner.evaluate_dsl_deterministic(dataset)
print(metrics.to_dict())
```
