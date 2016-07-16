import os
import sqlalchemy as sa
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

engine = sa.create_engine(os.environ['DATABASE_URL'], convert_unicode=True)
#                           echo=True)
session = scoped_session(sessionmaker(autocommit=False,
                                      autoflush=False,
                                      bind=engine))
PublicBase = declarative_base(metadata=sa.MetaData(schema='public'))
PublicBase.query = session.query_property()
