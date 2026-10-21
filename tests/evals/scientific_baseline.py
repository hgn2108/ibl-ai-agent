"""Generic model-graded baseline to compare with the custom judge."""

from __future__ import annotations

from inspect_ai.scorer import Scorer, model_graded_qa

GENERAL_CRITERIA = (
    "Evaluate whether the answer is factually supported by the reference evidence. "
    "Penalize unsupported claims and incorrect conclusions."
)


def scientific_baseline(
    criteria: str = GENERAL_CRITERIA, model: str = "anthropic/claude-sonnet-5-5"
) -> Scorer:
    """Inspect's ``model_graded_qa`` with scientific criteria.

    The sample's ``target`` is the evidence. Grades C / P / I give 1 / 0.5 / 0,
    comparable to the custom judge's normalized 0-2 score.

    Parameters
    ----------
    criteria
        Grading instructions; the judge's rubric when comparing configurations.
    model
        Inspect model id of the grader.
    """
    if not criteria.strip():
        raise ValueError("Evaluation criteria must not be empty")
    return model_graded_qa(instructions=criteria, partial_credit=True, model=model)
