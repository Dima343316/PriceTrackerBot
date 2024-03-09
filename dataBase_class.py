from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

DATABASE_URL = 'postgresql://constantine:dox123456@localhost/people'
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    product_name = Column(String)
    product_article = Column(String)
    product_price = Column(String)
    product_rating = Column(String)
    product_volume = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow())
