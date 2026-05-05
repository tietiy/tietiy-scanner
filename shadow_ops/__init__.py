"""shadow_ops — forward-time process-validation harness for the audited rule library.

See doc/shadow_ops_v1_architecture.md for full design. v1 is process validation,
not edge proof. No live capital, no broker integration.

Modules:
- data_ingest:        daily yfinance refresh of lab/cache parquets (Step 1)
- regime_classifier:  daily incremental regime + sub_regime via canonical lab/ code (Step 2)
- (more to come per §15 implementation order)
"""
