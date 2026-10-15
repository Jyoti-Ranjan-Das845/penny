Requirements note for the export feature, drawn from a team conversation about failure on files over 2GB and related issues.

**Requirements**

1. **Large-file support**: The export must not fail on files over 2GB. Currently the whole file loads into memory. Proposed fix: streaming (Sam's suggestion, discussed in conversation). Effort: approximately one week — tentative, not confirmed ("don't hold me to that").

2. **Stable CSV column order**: The export must maintain stable column ordering. Finance complained about this. Sam noted it is a separate and easy fix.

**Deferred**

Evaluate whether parquet format makes sense — flagged for later, not currently in scope.
