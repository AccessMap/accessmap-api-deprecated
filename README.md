AccessMap Web API
=================

## What is this?
This is the code for the AccessMap web API. It provides endpoints for
requesting data (like sidewalk and curb ramp information) as well as
turn-by-turn trip planning (routes).

## Using the API
The exact web URL for the web API is a poorly-guarded secret. Eventually, it
will live at a publicly-documented location, but for now we only share the URL
internally.

Once you have the URL, the API is simple to use. It is versioned to maintain
backwards compatibility (the 'v2' and 'v1' sections below). All data endpoints
(those ending with .geojson) return a few example data points by default. To
get more data points, use the `bbox` argument (described for each endpoint).

#### API Version 2 (v2)

The AccessMap Web API version 2 has three endpoints:

##### `v2/sidewalks.geojson`
* Data returned:
  * Sidewalk coordinates and metadata as a GeoJSON FeatureCollection. Each
  sidewalk Feature is a LineString, i.e. a line (potentially with multiple
  vertices)
    * Location information in the `geometry` sections (standard)
    * Metadata:
      * `grade`: Elevation change divided by sidewalk distance - an estimate of
      how steep the sidewalk is. A positive number means uphill from the first
      sidewalk coordinate to the last, and a negative number means downhill.
      * `id`: The unique ID of the sidewalk.
* Arguments:
  * `bbox`:
    * Description: A lat-lon description of a bounding box. All sidewalks
    within or intersecting this 'rectangle' will be returned.
    * Format: Standard comma-separated bbox format: minLat,minLon,maxLat,maxLon
    * Example: v2/sidewalks.geojson?bbox=-122.32893347740172,47.60685023396842,-122.32033967971802,47.61254994698394

##### `v2/crossings.geojson`
* Data returned:
  * Street crossing coordinates and metadata as a GeoJSON FeatureCollection.
  Each crossing Feature is a LineString, i.e. a line. Disclaimer: each
  'crossing' is automatically generated at a given intersections and does not
  imply the existence of a crosswalk or even that crossing the street at that
  location is safe.
    * Location information in the `geometry` sections (standard)
    * Metadata:
      * `grade`: Elevation change divided by crossing distance - an estimate of
      how steep the crossing is. A positive number means uphill from the first
      crossing coordinate to the last, and a negative number means downhill.
      * `curbramps`: A boolean indicating whether there is a curb ramp on both
      sides of the crossing (i.e. one should be able to use curb ramps to cross
      the street at this location).
      * `id`: The unique ID of the crossing.
* Arguments:
  * `bbox`:
    * Description: A lat-lon description of a bounding box. All crossings
    within or intersecting this 'rectangle' will be returned.
    * Format: Standard comma-separated bbox format: minLat,minLon,maxLat,maxLon
    * Example: v2/crossings.geojson?bbox=-122.32893347740172,47.60685023396842,-122.32033967971802,47.61254994698394

##### `v2/route.json`
* Data returned:
  * A JSON description of a trip plan - i.e. a 'route'. The formatting matches
  the [Mapbox directions API](https://www.mapbox.com/api-documentation/), but
  certain sections are currently not implemented (like the 'steps' section).
* Arguments:
  * `waypoints`:
    * Description: The coordinates for two points - the start (origin) and end
    (destination) of the trip.
    * Format: [lat1,lon1,lat2,lon2]
    * Example: v2/route.json?waypoints=[47.661083,-122.315366,47.659325,-122.313333]

#### API Version 1 (v1)

The AccessMap Web API version 1 has two endpoints:

##### `v1/sidewalks.geojson`
* Data returned:
  * Sidewalk coordinates and metadata as a GeoJSON FeatureCollection. Each
  sidewalk Feature is a LineString, i.e. a line (potentially with multiple
  vertices)
    * Location information in the `geometry` sections (standard)
    * Metadata:
      * `grade`: Elevation change divided by sidewalk distance - an estimate of
      how steep the sidewalk is. A positive number means uphill from the first
      sidewalk coordinate to the last, and a negative number means downhill.
      * `id`: The unique ID of the sidewalk.
* Arguments:
  * `bbox`:
    * Description: A lat-lon description of a bounding box. All sidewalks
    within or intersecting this 'rectangle' will be returned.
    * Format: Standard comma-separated bbox format: minLat,minLon,maxLat,maxLon
    * Example: v1/sidewalks.geojson?bbox=-122.32893347740172,47.60685023396842,-122.32033967971802,47.61254994698394

##### `v2/curbramps.geojson`
* Data returned:
  * Curb ramp locations and metadata as a GeoJSON FeatureCollection. Each
  curb ramp Feature is represented as a point.
    * Location information in the `geometry` sections (standard)
    * Metadata:
      * `id`: The unique ID of the curb ramp.
* Arguments:
  * `bbox`:
    * Description: A lat-lon description of a bounding box. All crossings
    within or intersecting this 'rectangle' will be returned.
    * Format: Standard comma-separated bbox format: minLat,minLon,maxLat,maxLon
    * Example: v1/curbramps.geojson?bbox=-122.32893347740172,47.60685023396842,-122.32033967971802,47.61254994698394

## Contributing
The AccessMap web API is written in Python 3.4+ and uses the Flask web
framework. You can install all of the tools needed (preferably into a
virtualenv environment titled `env`) using

    pip3 install -r requirements.txt

Set up the required environment variables. An included .sh script is listed -
rename it to 'set_envs.sh' and add the following information:

    export DATABASE_URL=postgres://login:pass@host:port/database

This is in the standard format of an SQL connection string for Postgres. To
enable this environment variable, run `source set_envs.sh`.

You can then run a local instance by running the following command in the main
directory:

    python3 ./runserver.py

In a production environment, use the (included) gunicorn server:

    gunicorn -b 0.0.0.0:5656 --access-logfile=- accessmapapi:app

You can then test your local copy by pointing your web browser to localhost,
e.g. for a v2 sidewalks request:

    localhost:5656/v2/sidewalks.geojson
