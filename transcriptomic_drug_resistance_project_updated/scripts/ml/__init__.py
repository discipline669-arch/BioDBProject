"""ML track for the NSCLC osimertinib drug-resistance project (Phase 4-8)."""
import warnings

# sklearn 1.8 deprecates the explicit penalty/elasticnet API and the saga
# solver is noisy on tiny-n data; both are noise for this pipeline.
try:
    from sklearn.exceptions import ConvergenceWarning
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
except Exception:  # pragma: no cover
    pass
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

