'''Defines cost functions for use with pgRouting. The output should be
executable SQL (as a string) that refers to the correct tables, so each cost
function is written as an actual function that requires specification of the
input column names. In addition, cost function parameters can be made tunable
using keyword arguments following required column name arguments.'''


def manual_wheelchair(dist_col, grade_col, crossing_col, kdist=1.0, kele=1e10,
                      kcrossing=1e2):
    '''Calculates a cost-to-travel that balances distance vs. steepness vs.
    needing to cross the street.

    '''
    dist_cost = '{} * {}'.format(kdist, dist_col)
    grade_cost = '{} * POW(ABS({}), 4)'.format(kele, grade_col)
    crossing_cost = '{} * {}'.format(kcrossing, crossing_col)
    cost = ' + '.join([dist_cost, grade_cost, crossing_cost])

    return cost
