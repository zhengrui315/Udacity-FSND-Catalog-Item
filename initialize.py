from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Item, User, Category

engine = create_engine('sqlite:///categoryitems.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()



# Create dummy user
user1 = User(name="Robo Barista", email="tinnyTim@udacity.com",
             picture='https://pbs.twimg.com/profile_images/2671170543/18debd694829ed78203a5a36dd364160_400x400.png')
session.add(user1)
session.commit()

category1 = Category(name="Soccer")
session.add(category1)
session.commit()

category2 = Category(name="Basketball")
session.add(category2)
session.commit()

category3 = Category(name="Baseball")
session.add(category3)
session.commit()


item1 = Item(user_id=1, title="Soccerball", description="a soccer ball", category=category1)
session.add(item1)
session.commit()

item2 = Item(user_id=1, title="Cleats", description="soccer cleat", category=category1)
session.add(item2)
session.commit()

item3 = Item(user_id=1, title="Basketball", description="a basket ball", category=category2)
session.add(item3)
session.commit()

item4 = Item(user_id=1, title="Shin Guard", description="shin guards", category=category1)
session.add(item4)
session.commit()

print("Items added successfully")