"""Comparing Chess Engine — CO3061 BTL.

Design patterns
---------------
- **Strategy** : ``evaluation.Evaluator`` hierarchy (Material, Positional,
  Mobility, KingSafety) composed via ``CompositeEvaluator``.
- **Template Method** : ``uci.UCIEngine`` defines the UCI loop; subclasses
  ``SmartEngine`` and ``DumbEngine`` override ``_think()``.
- **Composite** : ``CompositeEvaluator`` aggregates multiple strategies.
"""
