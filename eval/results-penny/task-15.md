# Review: migration status draft

## The pattern worth noticing first

Every deviation from your notes runs in the same direction: toward more completeness, more certainty, and more commitment than you gave the writer. There are no places where the draft is more cautious than the source. That consistency matters more than any single error — it means the draft was written to reassure rather than to report, and it can't be fixed by patching individual sentences. A reader who later discovers one overstatement has reason to distrust all of it.

## Claims that contradict the source

**"All 12 services have been moved."** False. Eleven moved; billing is still pending, blocked on a vendor firewall rule. This is the draft's central factual error, and it's in the lead sentence.

**"The migration is complete."** Unsupported for the same reason, and it does more damage than the service count because it sets the reader's frame. Anyone who reads that line and skims the rest leaves believing the project is closed.

**"The remaining work is documentation."** False as a consequence of the above. It doesn't just omit the billing service — it affirmatively tells the reader nothing else is outstanding.

**"John has signed off on the database layer."** Overstated. He reviewed it and raised two non-blocking concerns. "Signed off" reads as clean approval; the two concerns vanish entirely. Non-blocking is not the same as absent, and whoever owns the DB layer still has two items to address.

**"We expect no further issues."** Invented. You said there are no known blockers — a statement about present knowledge. The draft converts it into a forward-looking prediction, which is both unsupported and the kind of sentence that gets quoted back at you. It's also self-contradicting given the open vendor dependency.

**"Sarah will finish by Friday."** Two separate fabrications in one clause. Sarah hasn't been asked — you suggested her as the likely owner. And no deadline appears anywhere in your notes; Friday came from nowhere. If this circulates, Sarah may learn of her assignment and her due date from a document she was never consulted on.

## Claim that is true but misleading

**"Performance is better than before."** p99 improved 20%; p50 is unchanged. The draft's vaguer phrasing is defensible word by word, but it invites the reader to assume across-the-board improvement, which is wrong. It also discards the one hard number you supplied — the specific claim was both more accurate and more persuasive than the generality that replaced it. Vagueness here is not caution; it's a way of implying more than the data supports while staying deniable.

## What a reader would do wrong

Acting on this draft, a reasonable reader would: treat the migration as closed and stop tracking it; stop chasing the vendor firewall rule; consider the DB layer finished; and expect documentation Friday. The vendor rule is the single item in your notes that someone could actually act on, and it is the one thing the draft omits completely. That inversion — the actionable fact dropped, the unactionable reassurance added — is the clearest sign the draft optimized for tone over use.

## Structural note

The billing service isn't a footnote to be appended. It's the reason the migration is not complete, so it belongs in the first sentence, not in a caveat after it. Likewise, the two DB concerns and the p50 figure aren't hedges on good news — they're part of the status. A version that led with the facts would be shorter than this one, not longer.