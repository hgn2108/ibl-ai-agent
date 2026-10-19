"""Create configurable GEval metrics for scientific answer evaluation."""

from deepeval.metrics import GEval
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import SingleTurnParams


GENERAL_SCIENTIFIC_CRITERIA = (
    "Evaluate whether the answer is factually supported by the "
    "provided retrieval context. Penalize unsupported claims "
    "and incorrect conclusions."
)


def build_scientific_geval(
    evaluator: DeepEvalBaseLLM,
    criteria: str | None = None,
    evaluation_steps: list[str] | None = None,
    threshold: float = 0.5,
) -> GEval:
    """Build GEval with caller-supplied criteria or evaluation steps.

    Parameters
    ----------
    evaluator : DeepEvalBaseLLM
        Configured judge model.
    criteria : str | None
        Evaluation criteria. Defaults to general scientific criteria.
    evaluation_steps : list[str] | None
        Explicit evaluation steps. When provided, GEval uses these
        instead of generating steps from criteria.
    threshold : float
        Minimum normalized score required to pass.

    Returns
    -------
    GEval
        Configured metric for evidence-grounded evaluation.
    """
    if evaluator is None:
        raise ValueError("An evaluator model is required")
    if not 0 <= threshold <= 1:
        raise ValueError("Threshold must be between 0 and 1")

    if evaluation_steps is not None:
        if not evaluation_steps or any(not step.strip() for step in evaluation_steps):
            raise ValueError("Evaluation steps must be nonempty")
        if criteria is not None:
            raise ValueError("Provide criteria or evaluation_steps, not both")
    else:
        criteria = GENERAL_SCIENTIFIC_CRITERIA if criteria is None else criteria
        if not criteria.strip():
            raise ValueError("Evaluation criteria must not be empty")

    return GEval(
        name="Scientific GEval",
        criteria=criteria,
        evaluation_steps=evaluation_steps,
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.RETRIEVAL_CONTEXT,
        ],
        model=evaluator,
        threshold=threshold,
        async_mode=False,
    )
