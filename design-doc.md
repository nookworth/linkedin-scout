# Overview
    The LinkedIn Scout is an agentic search tool meant to automate the process of discovering new connections on LinkedIn. It is meant for personal use by me, Christopher Morrison. Ideally, the search will be sophisticated enough to collate my own biographical data/experience/interests/affinities with each potential match for maximum likelihood of success.

# Acceptance Criteria
    The LinkedIn Scout must perform the following tasks:
    - login, or use an existing session, to the LinkedIn account of Chris Morrison (me)
    - search for new people to connect with
        - the search should take into account my criteria, such as specific companies of interest, conditions to be considered a match, etc.
        - it should also fall back to a default set of criteria
        - it should be able to intelligently expand its search to include companies, job titles, etc. similar to the ones provided
    - output a list of LinkedIn profiles to a file, along with a brief justification for the inclusion of each profile

# Implementation Details
    - it should be operated via a command-line interface
    - it should make use of a headless browser
    - it should use only local LLMs via Ollama
    - the CLI should take in the following arguments: total number of results to return, companies of interest, number of results per company, job titles of potential connections, match conditions
        - each of these arguments should have a default
    - agentic AI should only be used in places where it is necessary:
        - expanding the list of companies to include similar companies
        - evaluating profiles to include in the results set
        - generating justifications/summaries for each profile inclusion
    