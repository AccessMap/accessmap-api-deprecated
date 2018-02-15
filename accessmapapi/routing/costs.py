'''Defines cost function generators for optimal path finding in networkx.'''
import math

# Default base moving speeds for different modes. All in m/s.
WALK_BASE = 10. / 6  # Tobler's hiking function for hikers
WHEELCHAIR_BASE = 0.6  # Rough estimate
POWERED_BASE = 2  # Roughly 5 mph

# 1 / DIVISOR = speed where cutoff starts to apply, dictates exponential's k.
DIVISOR = 5

# 'fastest' incline. -0.0087 is straight from Tobler's hiking function
INCLINE_IDEAL = -0.0087

# TODO: Minimum base speeds for wheelchairs - derive from torque etc and
# safety, use to determine aggressiveness of cost function. Parameterize from
# client somehow.


def find_k(g, m, n):
    return math.log(n) / abs(g - m)


def tobler(grade, k=3.5, m=INCLINE_IDEAL, base=WALK_BASE):
    # Modified to be in meters / second rather than km / h
    return base * math.exp(-k * abs(grade - m))


def cost_fun_generator(base_speed=WALK_BASE, incline_min=-0.1,
                       incline_max=0.085, avoid_curbs=True):
    '''Calculates a cost-to-travel that balances distance vs. steepness vs.
    needing to cross the street.

    :param incline_min: Maximum downhill incline indicated by the user, e.g.
                        -0.1 for 10% downhill.
    :type incline_min: float
    :param incline_max: Positive incline (uphill) maximum, as grade.
    :type incline_max: float
    :param avoid_curbs: Whether curb ramps should be avoided.
    :type avoid_curbs: bool

    '''
    # piecewise = piecewise_generator(INCLINE_MIN, INCLINE_IDEAL, INCLINE_MAX)
    k_up = find_k(incline_max, INCLINE_IDEAL, DIVISOR)
    k_down = find_k(incline_min, INCLINE_IDEAL, DIVISOR)

    def cost_fun(u, v, d):
        '''Networkx dijkstra-format cost function. Networkx provides access to
        the incoming node, the outgoing node, and the edge itself, which can
        provide pretty complex functionality.

        :param u: incoming node (or 'current node')
        :type u: networkx.Node
        :param v: ougoing node (or 'next node')
        :type v: networkx.Node
        :param d: The edge to evaluate.
        :type d: networkx MultiDiGraph edge

        '''
        # MultiDigraph may have multiple edges. Right now, we ignore this
        # and just pick the first edge. A simple DiGraph may be more
        # appropriate?

        # Set up initial costs - these should start at 0, and be max of 1 or
        # inf.
        time = 0

        path_type = d['path_type']

        # Initial speed based on incline
        if path_type == 'sidewalk':
            if (d['from'] == u) or (d['to'] == v):
                # Going in same direction as the geometry
                incline = d['incline']
            else:
                # Going in opposite direction as the geometry
                incline = -1 * d['incline']

            # incline_cost = piecewise(-1.0 * d['incline'])
        else:
            # Assume all other paths are flat
            incline = 0

        if incline > incline_max:
            return math.inf
        if incline < incline_min:
            return math.inf

        # Speed based on incline
        if incline > INCLINE_IDEAL:
            speed = tobler(incline, k=k_up, m=INCLINE_IDEAL, base=base_speed)
        else:
            speed = tobler(incline, k=k_down, m=INCLINE_IDEAL, base=base_speed)

        # Initial time estimate (in seconds) - based on speed
        time = d['length'] / speed

        # Crossings imply a delay. Would be good to make this driven by data,
        # but can guess for now
        if path_type == 'crossing':
            time += 30

        # Curb cost
        if avoid_curbs:
            if (path_type == 'crossing') and d['curbramps'] == 0:
                # A hard barrier - exit early with infinite cost
                return math.inf

        # Return time estimate - this is currently the cost

        return time

    return cost_fun
