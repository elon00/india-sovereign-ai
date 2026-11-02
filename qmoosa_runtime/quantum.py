"""Bounded classical QUBO solver, without quantum hardware or speedup claims."""
import itertools
import math

def solve_qubo(matrix):
    if not isinstance(matrix, list) or not 1 <= len(matrix) <= 12:
        raise ValueError("Use 1 to 12 binary variables")
    n = len(matrix)
    if any(not isinstance(row, list) or len(row) != n for row in matrix):
        raise ValueError("Square matrix required")
    if any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1e6 for row in matrix for v in row):
        raise ValueError("Finite bounded coefficients required")
    best = None
    for state in itertools.product((0,1),repeat=n):
        energy = sum(matrix[i][j]*state[i]*state[j] for i in range(n) for j in range(n))
        if best is None or energy < best["energy"]:
            best = {"state":list(state),"energy":energy}
    return dict(best,execution="CLASSICAL_EXHAUSTIVE_REFERENCE",quantumHardwareUsed=False,statesEvaluated=2**n)
