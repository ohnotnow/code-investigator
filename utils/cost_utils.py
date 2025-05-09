"""
This module contains utilities for cost estimation.
"""

from typing import Union


def estimate_cost(total_input_tokens: int, total_output_tokens: int, model: str) -> Union[float, str]:
    """
    Calculate the estimated cost of an LLM API call.

    Args:
        total_input_tokens: Number of input tokens
        total_output_tokens: Number of output tokens
        model: Model name (o4-mini, gpt-4.1, o3, gpt-4o)

    Returns:
        Estimated cost in USD or 'Unknown model' if the model is not recognized
    """
    if model == "o4-mini":
        input_cost = (total_input_tokens / 1_000_000) * 2.00
        output_cost = (total_output_tokens / 1_000_000) * 8.00
        return input_cost + output_cost
    elif model == "gpt-4.1":
        input_cost = (total_input_tokens / 1_000_000) * 1.10
        output_cost = (total_output_tokens / 1_000_000) * 4.40
        return input_cost + output_cost
    elif model == "o3":
        input_cost = (total_input_tokens / 1_000_000) * 10.00
        output_cost = (total_output_tokens / 1_000_000) * 40.00
        return input_cost + output_cost
    elif model == "gpt-4o":
        input_cost = (total_input_tokens / 1_000_000) * 5.00
        output_cost = (total_output_tokens / 1_000_000) * 20.00
        return input_cost + output_cost
    else:
        return "Unknown model"


def print_usage(result, model: str, total_time_in_seconds: float) -> None:
    """
    Print usage information after an agent run.

    Args:
        result: The run result from Runner.run_sync
        model: The model used
        total_time_in_seconds: Total execution time in seconds
    """
    print(f"\n\n- Usage:")
    total_input_tokens = 0
    total_output_tokens = 0
    for response in result.raw_responses:
        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens
    print(f"  - Total input tokens: {total_input_tokens}")
    print(f"  - Total output tokens: {total_output_tokens}")
    cost = estimate_cost(total_input_tokens, total_output_tokens, model)
    print(f"  - Total cost: ${cost}")
    print(f"  - Total time taken: {total_time_in_seconds} seconds")
