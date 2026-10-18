from google import genai
from db import save_input, save_output, save_scores, get_input, get_output, get_scores

client = genai.Client()

def call_llm(matches: list[tuple[str, float]]):
    strings = [s for s, _ in matches]
    input_str = ", ".join(strings)

    prompt = f"""
    You are analyzing an unknown program using a set of similar LeetCode problems retrieved by a GNN model.

    **Retrieved LeetCode problems:**
    {input_str}

    ## Objective

    Identify the strongest shared algorithmic principles among the retrieved problems. Determine whether they form one coherent group, multiple overlapping groups, or no clear group. Explain what these similarities suggest without making unsupported claims.

    ## Instructions

    - Identify up to three distinct algorithmic principles, ranked from strongest to weakest. Only include principles meaningfully supported by the retrieved problems; do not force multiple groups when one is sufficient.
    - Group problems by the algorithmic principles they commonly demonstrate. A problem may appear in multiple groups when it genuinely supports multiple principles.
    - For each principle, explain the specific shared algorithmic technique or computational pattern, not merely similarities in goals, inputs, or data types.
    - Distinguish related but different techniques. For example, graph traversal, topological sorting, and Union-Find are distinct approaches, even when they can address related problems.
    - Consider common solution approaches without assuming every problem has a single standard solution. Problem titles alone do not establish which algorithm or data structure a particular implementation uses.
    - Make complexity claims only when relevant and accurate. Qualify average-case, worst-case, and amortized complexities appropriately. Do not imply that every solution to a problem has the same complexity.
    - Do not assume every retrieved problem must fit a group. Identify outliers when appropriate.
    - Base conclusions on the retrieved problems and established algorithmic knowledge. Do not invent implementation details or claim that the unknown program definitely uses a particular technique.
    - Assign **Match confidence** based on how consistently and directly the retrieved problems support the proposed shared principle. Use High, Medium, or Low.
    - Keep the analysis concise, specific, and evidence-based. Prefer well-supported conclusions over speculative interpretations.
    - Do not speculate about the GNN's retrieval behavior, training distribution, or reasons for retrieving particular problems without supporting evidence.
    - Focus on identifying shared algorithmic techniques and computational patterns. Do not include Big O notation, time complexity, or space complexity unless explicitly necessary to explain a meaningful algorithmic distinction.
    
    ## Required Output

    ### Shared Principles

    List each supported principle from strongest to weakest. For each, provide:

    1. **Technique:** A specific algorithmic principle or technique.
    2. **Supporting matches:** The retrieved problem names that support this principle.
    3. **Reasoning:** One or two sentences explaining the specific shared algorithmic pattern and any important distinctions.
    4. **Match confidence:** High, Medium, or Low, reflecting the strength of the relationship among the retrieved problems.

    If only one principle is supported, report only one. If no clear principle is supported, state that the results are inconclusive.

    ### Limitations

    Briefly state the most important uncertainty in the algorithmic conclusions, such as alternative algorithms or data structures that can solve the same problems. Keep this section concise and avoid repeating.

    Do not mention the absence of source code, missing implementation details, or lack of direct evidence from the unknown program.
    """

    print(prompt)

    interaction = client.interactions.create(
        model="gemini-3.5-flash",
        input=prompt
    )

    return interaction.output_text

matches: list[tuple[str, float]] = [
    ("Clone Graph", 0.96),
    ("Number of Islands", 0.93),
    ("Two Sum", 0.91),
    ("Course Schedule", 0.89),
    ("Contains Duplicate", 0.86),
    ("Pacific Atlantic Water Flow", 0.84),
    ("Longest Consecutive Sequence", 0.82),
    ("Valid Sudoku", 0.79),
]

summary = call_llm(matches)
print("Summary of similarities between the problems:")
print(summary)