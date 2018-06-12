from heapq import heappop, heappush
from itertools import count
import time

from accessmapapi.exceptions import NoPath
from accessmapapi.utils import strip_null_fields


def dijkstra_multi(table, sources, weight, pred=None, paths=None,
                   cutoff=None, target=None):
    '''
    db: database
    G: graph
    sources: list of node ids
    weight: weight function or param
    pred: ?. Get filled with predecessors?
    paths: dictionary of start nodes: lists, e.g. { 354: [354] }
    cutoff: cutoff for weight. Otherwise, search is exhaustive.
    target: node id
    '''
    if paths is None:
        paths = {}
        for source in sources:
            paths[source] = [source]

    db = table._meta.database
    ignore = ['id', 'geometry', 'u']
    colnames = [c for c in table._meta.sorted_field_names if c not in ignore]

    with db.atomic():
        push = heappush
        pop = heappop
        dist = {}  # dictionary of final distances
        seen = {}
        # fringe is heapq with 3-tuples (distance,c,node)
        # use the count c to avoid comparing nodes (may not be able to)
        c = count()
        fringe = []
        for source in sources:
            seen[source] = 0
            push(fringe, (0, next(c), source))
        while fringe:
            (d, _, v) = pop(fringe)
            if v in dist:
                continue  # already searched this node.
            dist[v] = d
            if v == target:
                break
            for u, e in adj_nodes(table, colnames, v):
                cost = weight(v, u, e)
                if cost is None:
                    continue
                # NOTE: dist[v] could be precalculated if it's a bottleneck
                vu_dist = dist[v] + cost
                if cutoff is not None:
                    if vu_dist > cutoff:
                        continue
                if u in dist:
                    if vu_dist < dist[u]:
                        raise ValueError('Contradictory paths found:',
                                         'negative weights?')
                elif u not in seen or vu_dist < seen[u]:
                    seen[u] = vu_dist
                    push(fringe, (vu_dist, next(c), u))
                    if paths is not None:
                        paths[u] = paths[v] + [u]
                    if pred is not None:
                        pred[u] = [v]
                elif vu_dist == seen[u]:
                    if pred is not None:
                        pred[u].append(v)

    if target is None:
        return (dist, paths)
    try:
        return (dist[target], paths[target])
    except KeyError:
        # TODO: create a custom no path exception class
        raise NoPath('No path to {}'.format(target))

    return dist


def adj_nodes(table, colnames, u):
    db = table._meta.database

    # The first part of the result is the node ID, rest is edge attr
    neighbors = []

    # TODO: the SQL queries take up ~40% of runtime for large-ish traversals (whole
    # graph of 75k pahs), with 50% of that taken up by the execute_sql line and 25%
    # taken up by iterating over the cursor. Two ideas for speeding this up:
    # 1) Find a way to more rapidly get all of the rows without the iterator - we just
    #    want all of it at once. fetchall() does not make anything faster.
    # 2) The check for whether a node has already been visited happens after the SQL
    #    query and after coercing to dict. Any reasonable way to restrict query to
    #    only 'unseen' nodes (note that 'seen' list grows massively, has heavy i/o
    #    burden).
    colreplace = ', '.join(colnames)
    query = 'SELECT {} FROM edges WHERE u = ?'.format(colreplace)
    cursor = db.execute_sql(query, (u,))

    for row in cursor:
        data = dict(zip(colnames, row))
        strip_null_fields(data)
        v = int(data.pop('v'))
        neighbors.append((v, data))

    return neighbors
