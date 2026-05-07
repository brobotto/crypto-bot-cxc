# V0 Framework Spikes

All spikes use the same common test spec from `doc/design/implementation_plan.md`.

Required:

- Spike A: Freqtrade
- Spike B: VectorBT
- Spike C: Custom mini engine
- Spike D: NautilusTrader

Optional:

- Spike E: Jesse free tier

Each spike should write the same output files so the framework decision is evidence-based.

Decision:

- See `doc/design/framework_decision.md`.
- Custom core is the V1 primary engine.
- VectorBT is the research companion.
- Freqtrade and NautilusTrader remain references, not primary V1 engines.
