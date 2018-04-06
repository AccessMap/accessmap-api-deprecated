'''The flask application package.'''
import os
# opening_hours screws up cwd, have to set it early
file_directory = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
import time  # noqa
from accessmapapi import network_handlers  # noqa


def main():
    if 'PEDDATADIR' in os.environ:
        datadir = os.environ['PEDDATADIR']
    else:
        datadir = os.path.join(file_directory, 'data')

    print(datadir)
    # Try to build the graph 10 times - usually just waiting on data
    n = 0
    while n < 10:
        failed = False
        layers = {}
        print('Reading input data (try {})...'.format(n + 1))
        try:
            for layer in ['sidewalks', 'crossings', 'elevator_paths']:
                path = os.path.join(datadir, '{}.geobuf'.format(layer))
                layers[layer] = network_handlers.get_geobuf(path)
        except Exception as e:
            print(e)
            failed = True

        if failed:
            n += 1
            print('Cannot read input data, checking in 2 secs.')
            time.sleep(2)
        else:
            break

    print('Input data read.')

    print('Building graph (this may take a few minutes) ...')
    G = network_handlers.build_G(layers['sidewalks'], layers['crossings'],
                                 layers['elevator_paths'],
                                 os.path.join(datadir, 'graph.pkl'))
    print('Graph built.')
    print('Building spatial index...')
    network_handlers.build_sindex(G, os.path.join(datadir, 'sindex.pkl'))
    print('Spatial index built.')


if __name__ == '__main__':
    main()
