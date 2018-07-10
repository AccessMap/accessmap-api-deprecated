'''The flask application package.'''
import json
import os
# opening_hours screws up cwd, have to set it early
file_directory = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
import time  # noqa
from accessmapapi.build.trans_network import trans_network  # noqa


# TODO: drop the database first
def main():
    with open('./layers.json') as f:
        config = json.load(f)

    if 'PEDDATADIR' in os.environ:
        datadir = os.environ['PEDDATADIR']
    else:
        datadir = os.path.join(file_directory, 'data')

    # Embed full path into config
    for name, layer in config.items():
        layer['path'] = os.path.abspath(os.path.join(datadir, layer['path']))

    # Try to build the graph 10 times - usually just waiting on data
    n = 0
    while n < 10:
        failed = False
        if n > 1:
            print('Reading input data...')
        else:
            print('Reading input data (try {})...'.format(n + 1))
        try:
            trans_network(config)
        except Exception as e:
            print(e)
            failed = True

        if failed:
            n += 1
            print('Cannot read input data, checking in 2 secs.')
            time.sleep(2)
        else:
            break

    if failed:
        raise Exception('Graph failed to build - could not find input files')

    print('Graph built.')

if __name__ == '__main__':
    main()
