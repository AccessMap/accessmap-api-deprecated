'''Defines cost functions for use with pgRouting. The output should be
executable SQL (as a string) that refers to the correct tables, so each cost
function is written as an actual function that requires specification of the
input column names. In addition, cost function parameters can be made tunable
using keyword arguments following required column name arguments.'''


def piecewise_linear(col, xlow, xhigh, xmin, control_low, control_high):
    '''Given description of cost function for e.g. elevation in piecewise
    linear terms (x axis cutoffs, a zero-cost x axis point, and two control
    points between them - convex function), return a function that returns
    a cost from 0 to 1 for a given x point.

    :param col: Name of the column to use as input to this function, e.g.
                'grade'.
    :type col: str
    :param xlow: Low 'cutoff' for input value to function. Values below this
                 number will return a large or infinite cost.
    :type xlow: float
    :param xhigh: Low 'cutoff' for input value to function. Values above this
                  number will return a large or infinite cost.
    :type xhigh: float
    :param xmin: 'ideal' x point - will return cost of 0. For x = elevation
                 change, this is likely a slightly downhill value (e.g. -0.01)
    :type xmin: float
    :param control_low: (x, y)-valued control point for adjusting the shape
                        of the lines between the xmin and xlow values. The
                        resulting lines can range from being colinear (slope 1)
                        or orthogonal - like a step function - and everything
                        in between. The domain of x is between xmin and xlow,
                        while the range of y is from 0 to 1.
    :type control_low: 2-tuple of floats
    :param control_high: (x, y)-valued control point for adjusting the shape
                         of the lines between the xmin and xlow values. The
                         resulting lines can range from being colinear (slope
                         1) or orthogonal - like a step function - and
                         everything in between. The domain of x is between xmin
                         and xlow, while the range of y is from 0 to 1.
    :type control_high: 2-tuple of floats

    '''

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
        dy = y2 - y1

        m = dy / dx
        b = y2 - m * x2

        return (m, b)

    #
    # Piecewise part - figure out which function to use to calculate y
    #

    m1, b1 = line_mb([xlow, 1], control_low)
    m2, b2 = line_mb(control_low, [xmin, 0])
    m3, b3 = line_mb([xmin, 0], control_high)
    m4, b4 = line_mb(control_high, [xhigh, 1])

    # TODO: work around returning infinite/large cost - useful for showing
    # 'bad' routes to users, which may still be informative
    sql = '''
    CASE WHEN {x} = {xmin} THEN 0.0
         WHEN ({x} < {xlow}) OR ({x} > {xhigh}) THEN 100.0
         WHEN {x} < {control_lowx} THEN {m1} * {x} + {b1}
         WHEN {x} < {xmin} THEN {m2} * {x} + {b2}
         WHEN {x} < {control_highx} THEN {m3} * {x} + {b3}
         ELSE {m4} * {x} + {b4}
    END
    '''

    # FIXME: Use safe SQL (prevent injection attack)
    sql_fmt = sql.format(x=col, xmin=xmin, xlow=xlow, xhigh=xhigh,
                         control_lowx=control_low[0],
                         control_highx=control_high[0],
                         m1=m1, b1=b1, m2=m2, b2=b2, m3=m3, b3=b3, m4=m4,
                         b4=b4)

    # Ensure that the value is nonnegative (note: turn this off to debug any
    # apparent routing errors - this will mask some bugs in the cost function)
    sql_fmt = 'ABS({sql})'.format(sql=sql_fmt)

    return sql_fmt


def manual_wheelchair(dist_col, grade_col, crossing_col, kdist=1.0, kele=1e10,
                      kcrossing=1e2):
    '''Calculates a cost-to-travel that balances distance vs. steepness vs.
    needing to cross the street.

    '''
    dist_cost = '{} * {}'.format(kdist, dist_col)
    grade_base = piecewise_linear(grade_col, -0.09, 0.0833, 0, [-0.045, 0.3],
                                  [0.04165, 0.3])
    grade_cost = '{kele} * {base}'.format(kele=kele, base=grade_base)
    crossing_cost = '{} * {}'.format(kcrossing, crossing_col)
    cost = ' + '.join([dist_cost, grade_cost, crossing_cost])

    return cost
