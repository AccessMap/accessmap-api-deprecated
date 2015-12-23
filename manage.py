#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand

from app import app, db
app.config.from_object("config")
# Get instance config (hidden from git, is in app dir/instance/config.py)
app.config.from_pyfile("config.py")

migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command("db", MigrateCommand)


@manager.command
def run():
    app.run('0.0.0.0', port=8000)

if __name__ == "__main__":
    manager.run()
