"""Brain state — single write chokepoint for output/brain/*.json (atomic write + schema_version stamp).

See doc/brain_design_v1.md §2 (single chokepoint) + §4 Step 3 for write helper contract.
Step 2 stub: no logic yet; Step 3 fills (mirrors bridge state_writer pattern).
"""
