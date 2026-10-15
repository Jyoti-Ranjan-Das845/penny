# Export requirements

From a conversation with Sam.

**1. Handle exports larger than 2GB.** The export currently fails on large files because the whole thing is loaded into memory. Sam's view is that streaming the output would fix it. Rough guess at effort was about a week, but that was off the top of his head — not an estimate to plan against.

**2. Keep CSV column order stable.** Finance has complained about the order changing between exports. Separate from the size problem, and Sam expects it to be easy.

**3. Parquet — open question.** Worth looking at whether it makes sense as an export format. Not now; no decision either way.