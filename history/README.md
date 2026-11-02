# Legacy backup history

This directory records the provenance of legacy backup files found in the private working tree.

`legacy-backup-inventory.json` preserves each original relative filename, byte size, and SHA-256 digest. The original files remain in the private workspace and are not copied into this repository. Several historical snapshots contain crash-oriented or memory-corruption test material; retaining hashes allows local integrity checks without adding those old test implementations to a repository that may later be made public.

The inventory is metadata, not a substitute for the original artifacts. It does not claim that a backup was executed or that its contents are safe to publish.
