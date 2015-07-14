import datetime
import json
import requests


SOCRATA_KEY = 'HyursDSMdzrAfLroxKO1rztA5'

# FIXME: make these dates smarter:
#        1) Make the sidewalk_close_end_date use datetime
#        2) Also include sidewalk_close_start_date - should be < today.


def fetch_current_permits(isodate):
    '''isodate should be of form yyyy-m-d - i.e. %Y-%m-%d'''

    condition1 = "sidewalk_close_end_date > '{}'".format(isodate)
    condition2 = "sidewalk_close_start_date < '{}'".format(isodate)
    params = {'$where': '{} AND {}'.format(condition1, condition2),
              'sidewalk_closed_flag': 'Y',
              '$limit': 50000}

    print "Sending request for data..."
    req = requests.get('https://data.seattle.gov/resource/w47m-dg37',
                       params=params,
                       headers={'X-App-Token': SOCRATA_KEY})
    print "Data received"

    try:
        if 'message' in req.json():
            print req.json()['message']
    except:
        msg = 'Error decoding the JSON'

        raise Exception(msg + '\n\n{}'.format(req.json()))

    json_list = req.json()

    return json_list


if __name__ == '__main__':
    today = datetime.date.today().strftime('%Y-%m-%d')
    permits = fetch_current_permits(today)

    with open('./permits-by-street-segment-{}.json'.format(today), 'w') as f:
        json.dump(permits, f)

    with open('./permits-by-street-segment-latest.json', 'w') as f:
        json.dump(permits, f)
