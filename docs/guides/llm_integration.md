# LLM Integration Guide

`ROOT-MCP` is designed primarily to give Large Language Models (LLMs) like Claude capabilities to interact with High Energy Physics (HEP) data. This guide explains how to effectively use `ROOT-MCP` in an agentic workflow.

## The Analyst Agent Pattern

When using `ROOT-MCP`, you should view the LLM not just as a text processor, but as an **Autonomous Research Assistant**.

The LLM helps you by:
1.  **Exploring** unknown datasets to understand their content.
2.  **Formulating** analysis strategies (e.g., "I need to check the muon pT distribution").
3.  **Executing** the analysis using tools (`compute_histogram`, `apply_selection`).
4.  **Interpreting** the results (e.g., "The mean value is lower than expected").

### Recommended Workflow

We recommend encouraging the LLM to follow this iterative loop:

1.  **Discovery**: "What files do I have? What is inside them?" (`list_files` -> `inspect_file` -> `list_branches`)
2.  **Sampling**: "Let me see a few real events to understand the structure." (`sample_tree`)
3.  **Prototyping**: "Let's try a simple cut and see if it works." (`apply_selection`)
4.  **Analysis**: "Now let's compute the full histograms." (`compute_histogram`)
5.  **Export/Plot**: "Save the data or show me a plot." (`export_branches`, `generate_plot`)

## System Prompting

If you are building a custom agent using `ROOT-MCP`, consider adding the following to your system prompt:

> You are an expert High Energy Physics analyst assistant. You have access to ROOT files via a set of tools.
> When asked to analyze data, always start by exploring the file structure to verify branch names and types.
> Use `sample_tree` to check the actual data values before writing complex selections.
> ROOT data often contains "jagged arrays" (variable-length lists per event). Remember that operations on jagged arrays in selections usually imply "ANY" semantics (e.g., `Muon_PT > 20` means "at least one muon has PT > 20").

## Example Conversation

Here is how a typical interaction looks:

**User**: "Can you check the MET distribution for the sample events file?"

**Agent (Thought)**: I need to find the file first, then check the tree name, and finally compute the histogram.

**Agent (Tool Call)**: `list_files(pattern="*sample_events*")`
**Result**: `Found: /data/sample_events.root`

**Agent (Tool Call)**: `inspect_file(path="/data/sample_events.root")`
**Result**: `Tree "events" found.`

**Agent (Tool Call)**: `list_branches(path="/data/sample_events.root", tree="events", pattern="*met*")`
**Result**: `Found branch "met" (float).`

**Agent (Tool Call)**: `compute_histogram(path="/data/sample_events.root", tree="events", branch="met", bins=50)`
**Result**: `{ "bin_counts": [...], "mean": 29.3, ... }`

**Agent (Response)**: "I found the file `sample_events.root`. The `events` tree contains a `met` branch. I computed the histogram, and the mean MET is approximately 29.3 GeV. The distribution looks exponentially falling as expected."

## Best Practices for Users

When chatting with Claude (or other LLMs) with `ROOT-MCP` enabled:

- **Be Specific about Files**: If you know the filename, mention it. "Look at `run2024.root`".
- **Ask for "Why"**: The LLM can explain *why* it chose a certain binning or selection if you ask.
- **Iterate**: If a selection fails (e.g., "Branch not found"), the LLM can self-correct. ask it to "Check the branch names again".

## Jagged Array Handling

One of the hardest parts for LLMs is understanding jagged arrays (e.g., multiple muons per event).

- **Tip**: Remind the LLM that `nmuon_pt` or `Muon_PT` is a list.
- **Selection Logic**: `Muon_PT > 50` selects events where *any* muon has pT > 50.
- **Flattening**: Use `read_branches(flatten=True)` if you want a flat list of all muons from all events, ignoring event boundaries.
