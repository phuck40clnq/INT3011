"""At-most-one (AMO) CNF encodings.

Every encoder has the same interface so they can be swapped in benchmarks:

    encoder(lits: list[int], next_var: int) -> tuple[list[list[int]], int]

`lits` are the literals constrained by "at most one is true", `next_var` is
the first unused variable id. The encoder returns the clauses and the new
first unused id (auxiliary variables are allocated from `next_var` upward and
never reused).

Hand-written encodings (k = len(lits)):

    name        clauses              auxiliary vars    reference
    pairwise    k(k-1)/2             0                 folklore
    sequential  3k - 4               k - 1             Sinz (2005)
    binary      k * ceil(log2 k)     ceil(log2 k)      Frisch et al. (2005)
    commander   ~3.5k (groups of 3)  ~k/2              Klieber & Kwon (2007)
    product     2k + 4 sqrt(k) + ... ~2 sqrt(k)        Chen (2010)

PySAT encodings (`pysat.card.CardEnc.atmost` with bound 1) are wrapped with
the same interface and registered with a "pysat_" prefix.
"""
from __future__ import annotations

import math
from typing import Callable

from pysat.card import CardEnc, EncType

AmoEncoder = Callable[[list[int], int], tuple[list[list[int]], int]]


def pairwise(lits: list[int], next_var: int) -> tuple[list[list[int]], int]:
    """Naive encoding: forbid every pair, (~a | ~b) for all a, b in lits."""
    clauses = [
        [-lits[i], -lits[j]]
        for i in range(len(lits))
        for j in range(i + 1, len(lits))
    ]
    return clauses, next_var


def sequential(lits: list[int], next_var: int) -> tuple[list[list[int]], int]:
    """Sequential counter (Sinz 2005) specialised to bound 1.

    Auxiliary s_i means "some x_1..x_i is true" (prefix OR). Clauses:
        x_1 -> s_1
        x_i -> s_i,  s_{i-1} -> s_i,  x_i -> ~s_{i-1}     for 1 < i < k
        x_k -> ~s_{k-1}
    so a second true literal after a true prefix is forbidden.
    """
    k = len(lits)
    if k <= 1:
        return [], next_var
    s = list(range(next_var, next_var + k - 1))   # s[0..k-2]
    clauses = [[-lits[0], s[0]]]
    for i in range(1, k - 1):
        clauses.append([-lits[i], s[i]])
        clauses.append([-s[i - 1], s[i]])
        clauses.append([-lits[i], -s[i - 1]])
    clauses.append([-lits[k - 1], -s[k - 2]])
    return clauses, next_var + k - 1


def binary(lits: list[int], next_var: int) -> tuple[list[list[int]], int]:
    """Binary / bitwise encoding (Frisch et al. 2005).

    Literal x_i is given the index i written in m = ceil(log2 k) bits
    b_0..b_{m-1}. Clause (~x_i | b_j) or (~x_i | ~b_j) forces the bits to
    spell i when x_i is true; two true literals would need two different
    bit patterns at once, which is impossible.
    """
    k = len(lits)
    if k <= 1:
        return [], next_var
    m = math.ceil(math.log2(k))
    bits = list(range(next_var, next_var + m))
    clauses = []
    for i, x in enumerate(lits):
        for j, b in enumerate(bits):
            clauses.append([-x, b] if (i >> j) & 1 else [-x, -b])
    return clauses, next_var + m


def commander(
    lits: list[int], next_var: int, group_size: int = 3
) -> tuple[list[list[int]], int]:
    """Commander encoding (Klieber & Kwon 2007), AMO version.

    Split lits into groups of `group_size`. Each group G gets a commander c
    with c <-> OR(G):
        pairwise AMO inside G
        x -> c          for every x in G
        c -> OR(G)      (one clause)
    then recursively AMO over the commanders. A group of a single literal
    uses that literal as its own commander (no new variable).
    """
    if len(lits) <= group_size:
        return pairwise(lits, next_var)
    clauses: list[list[int]] = []
    commanders: list[int] = []
    for start in range(0, len(lits), group_size):
        group = lits[start:start + group_size]
        if len(group) == 1:
            commanders.append(group[0])
            continue
        c = next_var
        next_var += 1
        commanders.append(c)
        group_clauses, next_var = pairwise(group, next_var)
        clauses.extend(group_clauses)
        clauses.extend([-x, c] for x in group)
        clauses.append([-c] + group)
    rest, next_var = commander(commanders, next_var, group_size)
    clauses.extend(rest)
    return clauses, next_var


def product(
    lits: list[int], next_var: int, base: int = 4
) -> tuple[list[list[int]], int]:
    """Product encoding (Chen 2010), applied recursively.

    Place the k literals row by row on a p x q grid with
    q = ceil(k / ceil(sqrt k)) columns and p = ceil(k / q) non-empty rows.
    Literal at cell (i, j) implies row variable u_i and column variable v_j:
        x_ij -> u_i,  x_ij -> v_j
    and AMO(u), AMO(v) are encoded recursively. Two true literals would sit
    in different rows or different columns, violating AMO(u) or AMO(v).
    Groups with at most `base` literals use pairwise directly.
    """
    k = len(lits)
    if k <= base:
        return pairwise(lits, next_var)
    q = math.ceil(k / math.ceil(math.sqrt(k)))   # columns
    p = math.ceil(k / q)                          # rows that actually hold literals
    u = list(range(next_var, next_var + p))
    v = list(range(next_var + p, next_var + p + q))
    next_var += p + q
    clauses: list[list[int]] = []
    for idx, x in enumerate(lits):
        i, j = divmod(idx, q)
        clauses.append([-x, u[i]])
        clauses.append([-x, v[j]])
    row_clauses, next_var = product(u, next_var, base)
    col_clauses, next_var = product(v, next_var, base)
    clauses.extend(row_clauses)
    clauses.extend(col_clauses)
    return clauses, next_var


def _pysat_amo(encoding: int) -> AmoEncoder:
    """Wrap `pysat.card.CardEnc.atmost(bound=1)` into the AMO interface."""

    def encode(lits: list[int], next_var: int) -> tuple[list[list[int]], int]:
        if len(lits) <= 1:
            return [], next_var
        cnf = CardEnc.atmost(lits=lits, bound=1, top_id=next_var - 1, encoding=encoding)
        return [list(cl) for cl in cnf.clauses], max(next_var, cnf.nv + 1)

    return encode


OWN_ENCODERS: dict[str, AmoEncoder] = {
    "pairwise": pairwise,
    "sequential": sequential,
    "binary": binary,
    "commander": commander,
    "product": product,
}

PYSAT_ENCODERS: dict[str, AmoEncoder] = {
    "pysat_pairwise": _pysat_amo(EncType.pairwise),
    "pysat_seqcounter": _pysat_amo(EncType.seqcounter),
    "pysat_bitwise": _pysat_amo(EncType.bitwise),
    "pysat_ladder": _pysat_amo(EncType.ladder),
    "pysat_totalizer": _pysat_amo(EncType.totalizer),
    "pysat_cardnetwrk": _pysat_amo(EncType.cardnetwrk),
}

ENCODERS: dict[str, AmoEncoder] = {**OWN_ENCODERS, **PYSAT_ENCODERS}
