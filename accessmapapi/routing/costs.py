'''Defines cost function generators for optimal path finding in networkx.'''
import math


def tobler(grade):
    # Modified to be in meters / second rather than km / h
    return (10. / 6) * math.exp(-3.5 * grade + 0.05)


def piecewise_generator(val_min=-0.09, val_ideal=-0.01, val_max=0.0833):
    '''Produces a piecewise linear function describe by three control points:
    A) The maximum downhill incline (val_min)
    B) The ideal, easiest incline (val_ideal)
    C) The maximum uphill incline (val_max)

    All are in units of incline, i.e. 1% = 0.01. The y values are set to 1.0
    for the maximum inclines and 0 for the ideal incline. The values
    interpolated are derived from educated guesses and are the subject of
    future research: clearly, the function should be overall convex, as e.g. a
    4% incline is more than twice as 'difficult' as a 2% incline. The exact
    level of convexity is unclear without more data, however.

    This function currently hard-codes a piecewise approximation of convexity,
    setting intermediate control points at 1/4 of maximum cost (i.e 0.25)
    half-way between the max incline points and the ideal incline point.

    It's assumed that val_min < ideal < val_max. Input values outside of the
    range of [val_min, val_max] are given a very large cost.

    :param val_min: Maximum downhill incline in units of incline (e.g. 1% =
                    0.01). Must be between 0 and 1.
    :type val_min: float
    :param val_ideal: Ideal incline in units of incline (e.g. 1% = 0.01). Often
                      slightly downhill, like -0.01.
    :type val_ideal: float
    :param val_max: Maximum uphill incline in units of incline
                    (e.g. 1% = 0.01). Must be between 0 and 1.
    :type val_max: float

    '''
    MID_COST = 0.0

    val_min = float(val_min)
    val_ideal = float(val_ideal)
    val_max = float(val_max)

    #
    # Function to find the equation for a line
    #

    def line_mb(pt1, pt2):
        '''Given two xy points, return the m and b variables in the line
        equation (y = mx + b).

        :param pt1: Point 1
        :type pt1: 2-tuple of xy coord
        :param pt2: Point 2
        :type pt2: 2-tuple of xy coord
        :returns: dictionary of 'm' and 'b'
        :rtype: dict

        '''

        x1, y1 = pt1
        x2, y2 = pt2

        dx = x2 - x1
        if dx == 0:
            # Line is vertical, has no meaning - return 0 cost
            return (0, 0)
        dy = y2 - y1

        m = dy / dx
        b = y2 - m * x2

        return (m, b)

    # # Piecewise part - figure out which function to use to calculate y #

    # Calculate mid-control points as being half-way between the min and max
    # values, and with a set y value of 1/4.
    mid_low = [(val_min + val_ideal) / 2, MID_COST]
    mid_high = [(val_max + val_ideal) / 2, MID_COST]

    m1, b1 = line_mb([val_min, 1], mid_low)
    m2, b2 = line_mb(mid_low, [val_ideal, 0])
    m3, b3 = line_mb([val_ideal, 0], mid_high)
    m4, b4 = line_mb(mid_high, [val_max, 1])

    # TODO: work around returning infinite/large cost - useful for showing
    # 'bad' routes to users, which may still be informative
    def piecewise(x):
        out_of_range = math.inf

        if x < val_min:
            return out_of_range
        elif x < mid_low[0]:
            return m1 * x + b1
        elif x < val_ideal:
            return m2 * x + b2
        elif x < mid_high[0]:
            return m3 * x + b3
        elif x < val_max:
            return m4 * x + b4
        else:
            return out_of_range

    return piecewise


def cost_fun_generator(kdist=0.1, kincline=0.8, kcrossing=0.1,
                       incline_min=-0.1, incline_max=0.085,
                       avoid_curbs=True):
    '''Calculates a cost-to-travel that balances distance vs. steepness vs.
    needing to cross the street.

    :param kdist: scaling factor for length of route traveled.
    :type kdist: float
    :param kincline: scaling factor for elevation function, which is itself
                     scaled from 0 to 1.
    :type kincline: float
    :param kcrossing: scaling factor for cost of crossing the street.
    :type kcrossing: float
    :param incline_min: Maximum downhill incline indicated by the user, e.g.
                        -0.1 for 10% downhill.
    :type incline_min: float
    :param incline_max: Positive incline (uphill) maximum, as grade.
    :type incline_max: float
    :param avoid_curbs: Whether curb ramps should be avoided.
    :type avoid_curbs: bool

    '''
    # piecewise = piecewise_generator(INCLINE_MIN, INCLINE_IDEAL, INCLINE_MAX)

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
        speed = tobler(incline)

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
