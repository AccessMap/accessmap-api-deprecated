'''Defines cost functions for use with pgRouting. The output should be
executable SQL (as a string) that refers to the correct tables, so each cost
function is written as an actual function that requires specification of the
input column names. In addition, cost function parameters can be made tunable
using keyword arguments following required column name arguments.'''

from sqlalchemy.sql import text


def piecewise_linear(maxdown=-0.09, ideal=-0.01, maxup=0.0833):
    '''Produces the SQL necessary to calculate a cost function described by
    three control points:
    A) The maximum downhill incline (maxdown)
    B) The ideal, easiest incline (ideal)
    C) The maximum uphill incline (maxup)

    All are in units of grade, i.e. 1% = 0.01. The y values are set to 1.0 for
    the maximum inclines and 0 for the ideal incline. The values interpolated
    are derived from educated guesses and are the subject of future research:
    clearly, the function should be overall convex, as e.g. a 4% grade is more
    than twice as 'difficult' as a 2% grade. The exact level of convexity is
    unclear without more data, however.

    This function currently hard-codes a piecewise approximation of convexity,
    setting intermediate control points at 1/4 of maximum cost (i.e 0.25)
    half-way between the max incline points and the ideal incline point.

    It's assumed that maxdown < ideal < maxup. Input values outside of the
    range of [maxdown, maxup] are given a very large cost.

    :param maxdown: Maximum downhill incline in units of grade (e.g. 1% =
                    0.01). Must be between 0 and 1.
    :type maxdown: float
    :param ideal: Ideal incline in units of grade (e.g. 1% = 0.01). Often
                  slightly downhill, like -0.01.
    :type ideal: float
    :param maxup: Maximum uphill incline in units of grade (e.g. 1% = 0.01).
                  Must be between 0 and 1.
    :type maxup: float
    :param ideal: Ideal incline in units of grade (e.g. 1% = 0.01). Often
                  slightly downhill, like -0.01.
    :type ideal: float

    '''

    # Input checking/coercion, prevents SQL injection
    maxdown = float(maxdown)
    ideal = float(ideal)
    maxup = float(maxup)

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

    #
    # Piecewise part - figure out which function to use to calculate y
    #

    # Calculate mid-control points as being half-way between the min and max
    # values, and with a set y value of 1/4.
    mid_low = [(maxdown + ideal) / 2, 0.1]
    mid_high = [(maxup + ideal) / 2, 0.1]

    m1, b1 = line_mb([maxdown, 1], mid_low)
    m2, b2 = line_mb(mid_low, [ideal, 0])
    m3, b3 = line_mb([ideal, 0], mid_high)
    m4, b4 = line_mb(mid_high, [maxup, 1])

    # TODO: work around returning infinite/large cost - useful for showing
    # 'bad' routes to users, which may still be informative
    sql = '''
    CASE WHEN grade = {ideal} THEN 0.0
         WHEN (grade < {maxdown}) OR (grade > {maxup}) THEN 1000.0
         WHEN grade < {mid_low} THEN {m1} * grade + {b1}
         WHEN grade < {ideal} THEN {m2} * grade + {b2}
         WHEN grade < {mid_high} THEN {m3} * grade + {b3}
         ELSE {m4} * grade + {b4}
    END
    '''.format(maxdown=maxdown, ideal=ideal, maxup=maxup, mid_low=mid_low[0],
               mid_high=mid_high[0], m1=m1, m2=m2, m3=m3, m4=m4, b1=b1, b2=b2,
               b3=b3, b4=b4)

    # Ensure that the value is nonnegative (note: turn this off to debug any
    # apparent routing errors - this will mask some bugs in the cost function)
    sql = 'ABS({sql})'.format(sql=sql)

    return sql


def manual_wheelchair(kdist=1e6, kele=1e10, kcrossing=1e2, maxdown=-0.09,
                      ideal=-0.01, maxup=0.0833, avoid_construction=True,
                      avoid_curbs=True):
    '''Calculates a cost-to-travel that balances distance vs. steepness vs.
    needing to cross the street.

    :param kdist: scaling factor for length of route traveled.
    :type kdist: float
    :param kele: scaling factor for elevation function, which is itself scaled
                 from 0 to 1.
    :type kele: float
    :param kcrossing: scaling factor for cost of crossing the street.
    :type kcrossing: float
    :param maxdown: Maximum downhill incline indicated by the user, e.g. -0.1
                    for 10% downhill.
    :type maxdown: float
    :param ideal: Ideal incline indicated by the user, e.g. -0.01 for 1%
                  downhill.
    :type ideal: float
    :param maxup: Maximum uphill incline indicated by the user.
    :type maxup: float
    :param avoid_construction: Whether construction should be avoided.
    :type avoid_construction: bool
    :param avoid_curbs: Whether curbs should be avoided (currently implies that
                        crossing has curb ramps on both sides).
    :type avoid_curbs: bool

    '''
    ele_cost = piecewise_linear(maxdown, ideal, maxup)

    if avoid_construction:
        kconstruction = 1e12
    else:
        kconstruction = 0

    if avoid_curbs:
        kcurb = 1e12
    else:
        kcurb = 0

    sql = text('''
    :kdist * length +
    CASE WHEN iscrossing=1 THEN 0 ELSE :kele * {ele_cost} END +
    CASE WHEN iscrossing=1 AND NOT curbramps THEN :kcurb ELSE 0 END +
    :kcrossing * iscrossing +
    :kconstruction * construction::integer
    '''.format(ele_cost=ele_cost))

    cost = sql.bindparams(kdist=kdist, kele=kele, kcrossing=kcrossing,
                          kconstruction=kconstruction, kcurb=kcurb)
    cost = cost.compile(compile_kwargs={'literal_binds': True})

    return cost
