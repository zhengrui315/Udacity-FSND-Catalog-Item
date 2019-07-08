from flask import (Flask,
                   render_template,
                   request, redirect,
                   jsonify,
                   url_for,
                   flash,
                   make_response,
                   session as login_session)

from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from models import Base, Item, User, Category

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import requests
import random
import string
from functools import wraps

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

# Connect to Database and create database session
engine = create_engine('sqlite:///categoryitems.db?check_same_thread=False')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getCategoryID(category_name):
    category = session.query(Category).filter_by(name=category_name).one()
    return category.id


# create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/catalog.json')
def catalogJSON():
    try:
        categories = session.query(Category).all()
        return jsonify(Category=[c.serialize for c in categories])
    except:
        return jsonify(dict())
# @app.route('/catalog.json')
# def catalogJSON():
#     categories = session.query(Category).all()
#     Categories = []
#     for c in categories:
#         items = session.query(Item).filter_by(category_id=c.id).all()
#         d = {
#             "name": c.name,
#             "id": c.id,
#             "Item": [item.serialize for item in items],
#         }
#         Categories.append(d)
#     return jsonify(Category=Categories)


@app.route('/catalog/<category_name>/<title>/JSON/')
def itemJSON(category_name, title):
    try:
        category = session.query(Category).filter_by(name=category_name).one()
        item = session.query(Item).filter_by(category_id=category.id,
                                             title=title).one()
        return jsonify(item.serialize)
    except:
        return jsonify(dict())


@app.route('/')
@app.route('/catalog/')
def index():
    latest = session.query(Category, Item) \
                    .join(Item, Category.id == Item.category_id) \
                    .order_by(desc(Item.timestamp)).limit(5)
    categories = session.query(Category).order_by(asc(Category.name))
    if 'username' not in login_session:
        return render_template("publiccategory.html", latest=latest,
                               categories=categories)
    else:
        return render_template("category.html", latest=latest,
                               categories=categories)


@app.route('/catalog/<category_name>/items/')
def showItems(category_name):
    category_id = getCategoryID(category_name)
    items = session.query(Item) \
                   .filter_by(category_id=category_id) \
                   .order_by(asc(Item.title))
    categories = session.query(Category).order_by(asc(Category.name))
    if 'username' not in login_session:
        return render_template("publicitem.html", category_name=category_name,
                               items=items, count=items.count(),
                               categories=categories)
    else:
        return render_template("item.html", category_name=category_name,
                               items=items, count=items.count(),
                               categories=categories)


@app.route('/catalog/<category_name>/<title>/')
def showDescription(category_name, title):
    category, item = session.query(Category, Item) \
                            .filter(Category.id == Item.category_id,
                                    Category.name == category_name,
                                    Item.title == title) \
                            .one()
    if 'username' not in login_session:
        return render_template("publicitemdescription.html", title=title,
                               description=item.description)
    else:
        return render_template("itemdescription.html", title=title,
                               description=item.description,
                               user_id=login_session['user_id'])


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' in login_session:
            return f(*args, **kwargs)
        else:
            flash("You are not allowed to access there")
            return redirect('/login')
    return decorated_function


@app.route('/catalog/additem/', methods=['GET', 'POST'])
@login_required
def addItem():
    """ add new item

    :return:
        go to login page if not logged in
        on GET: page to create a new item
        on POST: redirect to the main page after item has been created
    """
    if request.method == 'GET':
        categories = session.query(Category).order_by(asc(Category.name))
        return render_template("additem.html", categories=categories)
    else:
        title = request.form['title'] if request.form['title'] else ''
        description = request.form['description'] \
            if request.form['description'] else ''
        category_id = session.query(Category) \
                             .filter_by(name=request.form['category_name']) \
                             .one().id
        user_id = login_session['user_id']
        item = Item(title=title, description=description,
                    category_id=category_id,
                    user_id=user_id)
        session.add(item)
        session.commit()
        flash("add %s successfully!" % title)
        return redirect(url_for('index'))


@app.route('/catalog/<title>/edit/', methods=['GET', 'POST'])
@login_required
def editItem(title):
    """ edit item

    :return:
        go to login page if not logged in
        return warning page if user is not the owner of the item
        on GET: page to edit item
        on POST: redirect to the category page after item has been edited
    """
    item = session.query(Item).filter_by(title=title).one()
    if item.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized \
                to edit this item. Please create your own item in order to \
                edit.');}</script><body onload='myFunction()''>"
    if request.method == 'GET':
        categories = session.query(Category).order_by(asc(Category.name))
        return render_template("edititem.html", title=title,
                               categories=categories)
    else:
        item = session.query(Item).filter_by(title=title).one()
        if request.form['title']:
            item.title = request.form['title']
        if request.form['description']:
            item.description = request.form['description']
        item.category_id = session.query(Category) \
            .filter_by(name=request.form['category_name']) \
            .one().id
        session.commit()
        return redirect(url_for('showItems',
                                category_name=request.form['category_name']))


@app.route('/catalog/<title>/delete/', methods=['GET', 'POST'])
@login_required
def deleteItem(title):
    """ delete item

    :return:
        go to login page if not logged in
        return warning page if user is not the owner of the item
        on GET: page to delete item
        on POST: redirect to the main page after item has been deleted
    """
    item = session.query(Item).filter_by(title=title).one()
    if item.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized \
                to delete this item Please create your own item in order to \
                delete.');}</script><body onload='myFunction()''>"
    if request.method == 'GET':
        return render_template("deleteitem.html", title=title)
    else:
        item = session.query(Item).filter_by(title=title).one()
        category_id = item.category_id
        session.delete(item)
        session.commit()
        category = session.query(Category).filter_by(id=category_id).one()
        return redirect(url_for('showItems', category_name=category.name))


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token  # NOQA
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
                        json.dumps('Current user is already connected.'),
                        200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserID(login_session['email'])
    if user_id is None:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px; \
                            -webkit-border-radius: 150px; \
                            -moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(
                        json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['access_token']  # NOQA
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(
                    json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    # app.config['JSON_SORT_KEYS'] = False
    app.run(host='0.0.0.0', port=5000)
