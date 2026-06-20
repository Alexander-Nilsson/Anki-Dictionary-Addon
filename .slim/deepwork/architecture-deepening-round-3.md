# Architecture Deepening Round 3

## Plan

| Phase | Candidate | Description | Status |
|-------|-----------|-------------|--------|
| 1 | 5 | Consolidate HTML rendering — extract dedicated HTMLRenderer from SearchPipeline | Pending |
| 2 | 2 | Collapse DictDB pass-through — remove 12 delegating methods, expose SearchQueryBuilder directly | Pending |
| 3 | 1 | Deepen SearchPipeline — replace `SearchPipeline(midict)` with explicit narrow deps | Pending |
| 4 | 3 | Extract MIDict action dispatch — registry pattern for 15+ JS commands | Pending |
| 5 | 4 | Decompose CardExporter — extract NoteAssembler, BulkProcessor, MediaTransfer | Pending |

## Order rationale

1. HTML rendering first — pure extraction, no behavior change, unblocks SearchPipeline deepening
2. DictDB pass-through — SearchPipeline and CardCreationHandler both call these; cleaning first simplifies SearchPipeline deepening
3. SearchPipeline deepening — depends on cleaner DictDB and HTML renderer
4. MIDict action dispatch — mostly independent, touches dictionary.py
5. CardExporter — largest/most independent, saved for last

## Files involved

- `core/dictionary.py` — MIDict, DictInterface (phases 3, 4)
- `core/search/pipeline.py` — SearchPipeline (phases 1, 3)
- `core/search/renderer.py` — currently 4 pure functions, will grow (phase 1)
- `core/search/query.py` — SearchQueryBuilder (phase 2)
- `core/database.py` — DictDB (phase 2)
- `core/card_handler.py` — CardCreationHandler (phase 3)
- `exporters/card_exporter.py` — CardExporter (phase 5)
