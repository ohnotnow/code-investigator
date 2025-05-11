"""
Code Investigator - A tool for investigating codebases using LLMs.
"""

import os
import argparse
import asyncio
import time
from agents import Agent, Runner, ModelSettings
from agents.extensions.models.litellm_model import LitellmModel
from tools import (
    get_project_structure,
    list_files,
    cat_file,
    grep_file,
    get_git_remotes,
    write_report
)
from prompts import DOCS_PROMPT, CODE_PROMPT, MERMAID_PROMPT, TESTING_PROMPT
from utils import print_usage, sanitise_mermaid_syntax, strip_markdown


async def main():
    """Main entry point for the application."""
    args = parse_arguments()
    request = args.request
    mode = args.mode
    prompt = get_prompt_for_mode(mode)

    request = ""
    if mode == "code" or mode == "mermaid" or mode == "testing":
        if not args.request:
            request = input("Enter a request: ")
        else:
            request = args.request
    elif mode == "docs":
        if not args.no_readme:
            request = f"Please provide a GitHub style Readme.md for the codebase."
        if args.request:
            request += f"\n\n## User note\n\n{args.request}"
    else:
        print(f"Invalid mode: {mode}")
        exit(1)

    if not request:
        print("No request provided or inferrable from mode")
        exit(1)

    # Run the agent
    await run_agent(mode, args.model, request, args.rewrite_output, args.output_file)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=str, required=False, help="The request to the agent")
    parser.add_argument("--mode", type=str, required=False, default="code", help="The mode to run the agent in")
    parser.add_argument("--model", type=str, required=False, default="o4-mini", help="The model to use for the agent")
    parser.add_argument("--no-readme", action="store_true", required=False, default=False, help="Do not use a GitHub Readme style for the output")
    parser.add_argument("--output-file", type=str, required=False, default=None, help="The file to write the output to")
    parser.add_argument("--rewrite-output", action="store_true", required=False, default=False, help="Rewrite the output using a more creative LLM model before writing to the output file")
    return parser.parse_args()


async def run_agent(mode, model_name, request, rewrite_output, output_file):
    """Run the agent with the given parameters."""
    start_time = time.time()

    # model_name = "openrouter/mistralai/mistral-medium-3"
    # api_key = os.getenv("OPENROUTER_API_KEY")
    # model = LitellmModel(model=model_name, api_key=api_key)
    agent = Agent(
        name=f"{mode.capitalize()} Agent",
        model=model_name,
        tools=[list_files, cat_file, grep_file, get_project_structure, get_git_remotes],
        instructions=get_prompt_for_mode(mode),
        model_settings=ModelSettings(include_usage=True)
    )

    print(f"\n\n- Starting agent using {model_name}...")
    result = await Runner.run(agent, max_turns=50, input=request)
    print(f"\n\n- Agent finished")
    end_time = time.time()
    total_time_in_seconds = round(end_time - start_time, 2)
    print_usage(result, model_name, total_time_in_seconds)
    print(f"\n\n- Final output:\n\n")

    # Sanitize mermaid diagrams before writing
    if mode == "mermaid":
        final_output = sanitise_mermaid_syntax(result.final_output)
    else:
        final_output = result.final_output

    if rewrite_output:
        final_output = rewrite_with_creative_model(final_output)

    print(final_output)

    # Write output to file
    output_filename = get_output_filename(output_file, mode)
    with open(output_filename, "w") as f:
        f.write(final_output)


def get_prompt_for_mode(mode):
    """Get the appropriate prompt for the given mode."""
    if mode == "code":
        return CODE_PROMPT
    elif mode == "docs":
        return DOCS_PROMPT
    elif mode == "mermaid":
        return MERMAID_PROMPT
    elif mode == "testing":
        return TESTING_PROMPT
    else:
        raise ValueError(f"Invalid mode: {mode}")


def rewrite_with_creative_model(original_output):
    """Rewrite the output using a more creative model."""
    print(f"\n\n- Rewriting output ...")
    start_time = time.time()
    agent = Agent(
        name=f"Rewrite Agent",
        model="gpt-4o",
        instructions="You are an expert technical writer.  The user will provide you with a GitHub style Readme.md for a codebase.  They will also give you some guidence on how they would like you to improve the readme.  Your response should just be the updated readme - no other chat or explanations.  Please do not change the technical content of the readme however.  Do not wrap your response in markdown tags as the response will be used to overwrite the users existing Readme.md file.",
        model_settings=ModelSettings(include_usage=True)
    )
    user_prompt = f"Hi there! I have a github readme which was generated by a very old LLM a few years ago.  I was wondering if you could read through it and improve it?  It should still be written for a professional technical audience - but just a little less.... 'dry' I guess?  <original_readme>\n\n{original_output}\n\n</original_readme>\n\n"
    rewrite_result = Runner.run_sync(agent, max_turns=50, input=user_prompt)
    end_time = time.time()
    total_time_in_seconds = round(end_time - start_time, 2)
    print(f"\n\n- Rewriting finished in {total_time_in_seconds} seconds")
    print_usage(rewrite_result, "gpt-4o", total_time_in_seconds)
    return strip_markdown(rewrite_result.final_output)


def get_output_filename(output_file, mode):
    """Get the output filename."""
    if output_file:
        return output_file
    else:
        return f"report_{mode}_{time.strftime('%Y_%m_%d_%H_%M_%S')}.md"


if __name__ == "__main__":
    asyncio.run(main())
