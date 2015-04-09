# hackcessible-api  
RESTful API that stores and serves Hackcessible team data


## Installation

Install the packages in requirements.txt using pip (pip install -r requirements.txt)  


## Running the server

Make a directory called `instance` in the main folder and add a plain text file named config.py. To that file, add a single line: `SQLALCHEMY_DATABASE_URI = 'uri_for_your_database'`.  

Now, hackcessble-api knows where your database is and it needs to be set up. Run the following lines to run your first migration, creating the tables:  

`python app.py db init`  
`python app.py db migrate`  
`python app.py db upgrade`  

If all goes well, the database has been set up and everything is ready to go! Run the server with this command:  

`python app.py runserver`

## Requesting data from the server

The RESTful routes are a WIP, but currently are at `<the_running_site>/sidewalks.json` and `<the_running_site>/curbs.json`. There are no rows created by default - those need to be added manually (for now).
