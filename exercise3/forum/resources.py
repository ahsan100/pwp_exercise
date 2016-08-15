'''
Created on 26.01.2013
Modified on 23.02.2016
@author: ivan
'''

import json

from flask import Flask, request, Response, g, jsonify, _request_ctx_stack, redirect
from flask.ext.restful import Resource, Api, abort
from werkzeug.exceptions import NotFound,  UnsupportedMediaType

from utils import RegexConverter
import database

#Constants for hypermedia formats and profiles
COLLECTIONJSON = "application/vnd.collection+json"
HAL = "application/hal+json"
FORUM_USER_PROFILE ="/profiles/user-profile"
FORUM_MESSAGE_PROFILE = "/profiles/message-profile"
ATOM_THREAD_PROFILE = "https://tools.ietf.org/html/rfc4685"
APIARY_PROFILES_URL = "STUDENT_APIARY_PROJECT/#reference/profiles/"

#Define the application and the api
app = Flask(__name__)
app.debug = True
# Set the database Engine. In order to modify the database file (e.g. for
# testing) provide the database path   app.config to modify the
#database to be used (for instance for testing)
app.config.update({'Engine': database.Engine()})
#Start the RESTful API.
api = Api(app)


def create_error_response(status_code, title, message=None):
    ''' Creates a: py: class:`flask.Response` instance when sending back an
      HTTP error response
     : param integer status_code: The HTTP status code of the response
     : param str title: A short description of the problem
     : param message: A long description of the problem
     : rtype:: py: class:`flask.Response`

    '''
    resource_type = None
    resource_url = None
    ctx = _request_ctx_stack.top
    if ctx is not None:
        resource_url = request.path
        resource_type = ctx.url_adapter.match(resource_url)[0]
    response = jsonify(title=title,
                       message=message,
                       resource_url=resource_url,
                       resource_type=resource_type)
    response.status_code = status_code
    return response

@app.errorhandler(404)
def resource_not_found(error):
    return create_error_response(404, "Resource not found",
                                 "This resource url does not exit")

@app.errorhandler(400)
def resource_not_found(error):
    return create_error_response(400, "Malformed input format",
                                 "The format of the input is incorrect")

@app.errorhandler(500)
def unknown_error(error):
    return create_error_response(500, "Error",
                    "The system has failed. Please, contact the administrator")


@app.before_request
def connect_db():
    '''Creates a database connection before the request is proccessed.

    The connection is stored in the application context variable flask.g .
    Hence it is accessible from the request object.'''

    g.con = app.config['Engine'].connect()


#HOOKS
@app.teardown_request
def close_connection(exc):
    ''' Closes the database connection
        Check if the connection is created. It migth be exception appear before
        the connection is created.'''
    if hasattr(g, 'con'):
        g.con.close()


#Define the resources
class Messages(Resource):
    '''
    Resource Messages implementation
    '''
    def get(self):
        '''
        Get all messages.

        INPUT parameters:
          None

        RESPONSE ENTITY BODY:
        * Media type: Collection+JSON:
             http://amundsen.com/media-types/collection/
           - Extensions: template validation and value-types
             https://github.com/collection-json/extensions
         * Profile: Forum_Message
           http://atlassian.virtues.fi: 8090/display/PWP
           /Exercise+4#Exercise4-Forum_Message

        Link relations used in items: None
        Semantic descriptions used in items: headline
        Link relations used in links: users-all
        Semantic descriptors used in template: headline, articleBody, author,
        editor.

        NOTE:
         * The attribute articleBody is obtained from the column messages.body
         * The attribute headline is obtained from the column messages.title
         * The attribute author is obtained from the column messages.sender
        '''
        #Extract messages from database
        messages_db = g.con.get_messages()

        #Create the envelope
        envelope = {}
        collection = {}
        envelope["collection"] = collection
        collection['version'] = "1.0"
        collection['href'] = api.url_for(Messages)
        collection['links'] = [
                                {'prompt': 'List of all users in the Forum',
                                'rel': 'users-all', 'href': api.url_for(Users)
                                }
            ]
        collection['template'] = {
            "data": [
                {"prompt": "", "name": "headline",
                 "value": "", "required": True},
                {"prompt": "", "name": "articleBody",
                 "value": "", "required": True},
                {"prompt": "", "name": "author",
                 "value": "", "required": False},
                {"prompt": "", "name": "editor",
                 "value": "", "required": False}
            ]
        }
        #Create the items
        items = []
        for message in messages_db:
            _messageid = message['messageid']
            _headline = message['title']
            _url = api.url_for(Message, messageid=_messageid)
            message = {}
            message['href'] = _url
            message['data'] = []
            value = {'name':'headline', 'value': _headline}
            message['data'].append(value)
            message['links'] = []
            items.append(message)
        collection['items'] = items
        string_data = json.dumps(envelope)

        #RENDER
        return Response(string_data, 200, mimetype="application/vnd.collection+json;/profiles/message-profile")

    def post(self):
        '''
        Adds a a new message.

        REQUEST ENTITY BODY:
         * Media type: Collection+JSON:
             http://amundsen.com/media-types/collection/
           - Extensions: template validation and value-types
             https://github.com/collection-json/extensions
         * Profile: Forum_Message
           http://atlassian.virtues.fi: 8090/display/PWP
           /Exercise+4#Exercise4-Forum_Message

        NOTE:
         * The attribute articleBody is obtained from the column messages.body
         * The attribute headline is obtained from the column messages.title
         * The attribute author is obtained from the column messages.sender

        The body should be a Collection+JSON template.
        Semantic descriptors used in template: headline, articleBody and author.
        If author is not there consider it  "Anonymous".

        RESPONSE STATUS CODE:
         * Returns 201 if the message has been added correctly.
           The Location header contains the path of the new message
         * Returns 400 if the message is not well formed or the entity body is
           empty.
         * Returns 415 if the format of the response is not json
         * Returns 500 if the message could not be added to database.

        '''

        #Extract the request body. In general would be request.data
        #Since the request is JSON I use request.get_json
        #get_json returns a python dictionary after serializing the request body
        #get_json returns None if the body of the request is not formatted
        # using JSON. We use force=True since the input media type is not
        # application/json.

        if COLLECTIONJSON != request.headers.get('Content-Type',''):
            return create_error_response(415, "UnsupportedMediaType",
                                         "Use a JSON compatible format")
        request_body = request.get_json(force=True)
         #It throws a BadRequest exception, and hence a 400 code if the JSON is
        #not wellformed
        try:
            data = request_body['template']['data']
            title = None
            body = None
            sender = "Anonymous"
            ipaddress = request.remote_addr

            for d in data:
                #This code has a bad performance. We write it like this for
                #simplicity. Another alternative should be used instead.
                if d['name'] == 'headline':
                    title = d['value']
                elif d['name'] == 'articleBody':
                    body = d['value']
                elif d['name'] == 'author':
                    sender = d['value']

            #CHECK THAT DATA RECEIVED IS CORRECT
            if not title or not body:
                return create_error_response(400, "Wrong request format",
                                             "Be sure you include message title and body")
        except:
            #This is launched if either title or body does not exist or if
            # the template.data array does not exist.
            return create_error_response(400, "Wrong request format",
                                         "Be sure you include message title and body")
        #Create the new message and build the response code'
        newmessageid = g.con.create_message(title, body, sender, ipaddress)
        if not newmessageid:
            return create_error_response(500, "Problem with the database",
                                         "Cannot access the database")

        #Create the Location header with the id of the message created
        url = api.url_for(Message, messageid=newmessageid)

        #RENDER
        #Return the response
        return Response(status=201, headers={'Location': url})

class Message(Resource):
    '''
    Resource that represents a single message in the API.
    '''

    def get(self, messageid):
        '''
        Get the body, the title and the id of a specific message.

        Returns status code 404 if the messageid does not exist in the database.

        INPUT PARAMETER
       : param str messageid: The id of the message to be retrieved from the
            system

        RESPONSE ENTITY BODY:
         * Media type: application/hal+json:
             http://stateless.co/hal_specification.html
         * Profile: Forum_Message
           /profiles/message-profile

            Link relations used: self, collection, author, replies and
            in-reply-to

            Semantic descriptors used: articleBody, headline, editor and author
            NOTE: editor should not be included in the output if the database
            return None.

        RESPONSE STATUS CODE
         * Return status code 200 if everything OK.
         * Return status code 404 if the message was not found in the database.

        NOTE:
         * The attribute articleBody is obtained from the column messages.body
         * The attribute headline is obtained from the column messages.title
         * The attribute author is obtained from the column messages.sender
        '''

        #PEFORM OPERATIONS INITIAL CHECKS
        #Get the message from db
        message_db = g.con.get_message(messageid)
        if not message_db:
            create_error_response(404,"Message error", message="There is no a message with id %s" % messageid)

        #FILTER AND GENERATE RESPONSE
        #Create the envelope:
        envelope = {}
        #Now create the links
        links = {}
        envelope["_links"] = links

        #Fill the links
        _curies = [
            {
                "name": "msg",
                "href": FORUM_MESSAGE_PROFILE + "/{rels}",
                "templated": True
            },
            {
                "name": "atom-thread",
                "href": ATOM_THREAD_PROFILE + "/{rels}",
                "templated": True
            }
        ]
        links['curies'] = _curies
        links['self'] = {'href': api.url_for(Message, messageid=messageid),
                         'profile': FORUM_MESSAGE_PROFILE}
        links['collection'] = {'href': api.url_for(Messages),
                               'profile': FORUM_MESSAGE_PROFILE,
                               'type': COLLECTIONJSON}
        links['msg:reply'] = {'href': api.url_for(Message, messageid=messageid),
                              'profile': FORUM_MESSAGE_PROFILE}
        #Extract the author and add the link
        #If sender is not Anonymous extract the nickname from message_db,
        #the link exista but its href points to None.
        sender_db = message_db.get('sender', 'Anonymous')
        if sender_db != 'Anonymous':
            links['msg:author'] = {
                'href': api.url_for(User, nickname=sender_db),
                'profile': FORUM_USER_PROFILE,
                'type': HAL}
        else:
            links['msg: author'] = {'href': None,
                                   'profile': FORUM_USER_PROFILE,
                                   'type': HAL}
        #Extract the parent and add the corresponding link
        parent = message_db.get('replyto', None)
        if parent:
            links['atom-thread:in-reply-to'] = {
                'href': api.url_for(Message, messageid=parent),
                'profile': FORUM_MESSAGE_PROFILE,
                'type': HAL}
        else:
            links['atom-thread:in-reply-to'] = {
                'href': None,
                'profile': FORUM_MESSAGE_PROFILE,
                'type': HAL}



        #Fill the template
        envelope['template'] = {
            "data": [
                {"prompt": "", "name": "headline",
                 "value": "", "required": True},
                {"prompt": "", "name": "articleBody",
                 "value": "", "required": True},
                {"prompt": "", "name": "author",
                 "value": "", "required": False},
                {"prompt": "", "name": "editor",
                 "value": "", "required": False}
            ]
        }

        #Fill the rest of properties
        envelope['articleBody'] = message_db['body']
        envelope['headline'] = message_db['title']
        envelope['author'] = sender_db  # Calculated before. It can be Anonymous
        envelope['editor'] = message_db['editor']

        #RENDER
        string_data = json.dumps(envelope)
        return Response(string_data, 200, mimetype="application/hal+json;/profiles/message-profile")

    def delete(self, messageid):
        '''
        Deletes a message from the Forum API.

        INPUT PARAMETERS:
       : param str messageid: The id of the message to be deleted

        RESPONSE STATUS CODE
         * Returns 204 if the message was deleted
         * Returns 404 if the messageid is not associated to any message.
        '''

        #PERFORM DELETE OPERATIONS
        if g.con.delete_message(messageid):
            return '', 204
        else:
            #Send error message
            return create_error_response(404, "Unknown message",
                                         "There is no a message with id %s" % messageid
                                        )

    def put(self, messageid):
        '''
        Modifies the title, body and editor properties of this message.

        INPUT PARAMETERS:
       : param str messageid: The id of the message to be deleted

        REQUEST ENTITY BODY:
        * Media type: Collection+JSON:
             http://amundsen.com/media-types/collection/
           - Extensions: template validation and value-types
             https://github.com/collection-json/extensions
        * Profile: Forum_Message
          /profiles/message-profile

        The body should be a Collection+JSON template.
        Semantic descriptors used in template: headline, articleBody and editor.
        If author is not there consider it  "Anonymous".

        OUTPUT:
         * Returns 204 if the message is modified correctly
         * Returns 400 if the body of the request is not well formed or it is
           empty.
         * Returns 404 if there is no message with messageid
         * Returns 415 if the input is not JSON.
         * Returns 500 if the database cannot be modified

        NOTE:
         * The attribute articleBody is obtained from the column messages.body
         * The attribute headline is obtained from the column messages.title
         * The attribute author is obtained from the column messages.sender

        '''

        #CHECK THAT MESSAGE EXISTS
        if not g.con.contains_message(messageid):
            return create_error_response(404, "Message not found",
                                         "There is no a message with id %s" % messageid
                                        )

        if COLLECTIONJSON != request.headers.get('Content-Type',''):
            return create_error_response(415, "UnsupportedMediaType",
                                         "Use a JSON compatible format")

        #PARSE THE REQUEST
        #Extract the request body. In general would be request.data
        #Since the request is JSON I use request.get_json
        #get_json returns a python dictionary after serializing the request body
        #get_json returns None if the body of the request is not formatted
        # using JSON
        request_body = request.get_json(force=True)
        if not request_body:
            return create_error_response(415, "Unsupported Media Type",
                                         "Use a JSON compatible format"
                                        )

       #It throws a BadRequest exception, and hence a 400 code if the JSON is
        #not wellformed
        try:
            data = request_body['template']['data']
            title = None
            body = None
            editor = "Anonymous"
            for d in data:
                #This code has a bad performance. We write it like this for
                #simplicity. Another alternative should be used instead.
                if d['name'] == 'headline':
                    title = d['value']
                elif d['name'] == 'articleBody':
                    body = d['value']
                elif d['name'] == 'editor':
                    editor = d['value']
            #CHECK THAT DATA RECEIVED IS CORRECT
            if not title or not body:
                return create_error_response(400, "Wrong request format",
                                             "Be sure you include message title and body"
                                             )
        except:
            #This is launched if either title or body does not exist or the
            #template.data is not there.
            return create_error_response(400, "Wrong request format",
                                         "Be sure you include message title and body",
                                          )
        else:
            #Modify the message in the database
            if not g.con.modify_message(messageid, title, body, editor):
                return create_error_response(500, "Internal error",
                                         "Message information for %s cannot be updated" % messageid
                                        )
            return '', 204

    def post(self, messageid):
        '''
        Adds a response to a message with id <messageid>.

        INPUT PARAMETERS:
       : param str messageid: The id of the message to be deleted

        REQUEST ENTITY BODY:
        * Media type: Collection+JSON:
             http://amundsen.com/media-types/collection/
           - Extensions: template validation and value-types
             https://github.com/collection-json/extensions
         * Profile: Forum_Message
          /profiles/message-profile

         The body should be a Collection+JSON template.
         Semantic descriptors used in template: headline, articleBody and author.
         If author is not there consider it  "Anonymous".

        RESPONSE HEADERS:
         * Location: Contains the URL of the new message

        RESPONSE STATUS CODE:
         * Returns 201 if the message has been added correctly.
           The Location header contains the path of the new message
         * Returns 400 if the message is not well formed or the entity body is
           empty.
         * Returns 404 if there is no message with messageid
         * Returns 415 if the format of the response is not json
         * Returns 500 if the message could not be added to database.

         NOTE:
         * The attribute articleBody is obtained from the column messages.body
         * The attribute headline is obtained from the column messages.title
         * The attribute author is obtained from the column messages.sender
        '''

        #CHECK THAT MESSAGE EXISTS
        #If the message with messageid does not exist return status code 404
        if not g.con.contains_message(messageid):
            return create_error_response(404, "Message not found",
                                         "There is no a message with id %s" % messageid
                                        )

        if COLLECTIONJSON != request.headers.get('Content-Type',''):
            return create_error_response(415, "UnsupportedMediaType",
                                         "Use a JSON compatible format")
        #Extract the request body. In general would be request.data
        #Since the request is JSON I use request.get_json
        #get_json returns a python dictionary after serializing the request body
        #get_json returns None if the body of the request is not formatted
        # using JSON
        request_body = request.get_json(force=True)
        if not request_body:
            return create_error_response(415, "Unsupported Media Type",
                                         "Use a JSON compatible format"
                                        )

        #It throws a BadRequest exception, and hence a 400 code if the JSON is
        #not wellformed
        try:
            data = request_body['template']['data']
            title = None
            body = None
            sender = "Anonymous"
            ipaddress = request.remote_addr

            for d in data:
                #This code has a bad performance. We write it like this for
                #simplicity. Another alternative should be used instead.
                if d['name'] == 'headline':
                    title = d['value']
                elif d['name'] == 'articleBody':
                    body = d['value']
                elif d['name'] == 'author':
                    sender = d['value']

            #CHECK THAT DATA RECEIVED IS CORRECT
            if not title or not body:
                return create_error_response(400, "Wrong request format","Be sure you include message title and body")
        except:
            #This is launched if either title or body does not exist or if
            # the template.data array does not exist.
            return create_error_response(400, "Wrong request format",
                                         "Be sure you include message title and body"
                                          )

        #Create the new message and build the response code'
        newmessageid = g.con.append_answer(messageid, title, body,
                                           sender, ipaddress)
        if not newmessageid:
            return create_error_response(500, "Internal error","Message information for %s cannot be updated" % messageid)

        #Create the Location header with the id of the message created
        url = api.url_for(Message, messageid=newmessageid)

        #RENDER
        #Return the response
        return Response(status=201, headers={'Location': url})

class Users(Resource):

    def get(self):
        '''
        Gets a list of all the users in the database.

        It returns always status code 200.

        RESPONSE ENTITITY BODY:


         OUTPUT:
            * Media type: Collection+JSON:
             http://amundsen.com/media-types/collection/
             - Extensions: template validation and value-types
               https://github.com/collection-json/extensions
            * Profile: Forum_User
                /profiles/user-profile

        Link relations used in items: messages

        Semantic descriptions used in items: nickname, registrationdate

        Link relations used in links: messages-all

        Semantic descriptors used in template: address, avatar, birthday,
        email,familyname,gender,givenName,image, nickname, signature, skype, telephone,
        website

        NOTE:
         * The attribute signature is obtained from the column users_profile.signature
         * The attribute givenName is obtained from the column users_profile.firstname
         * The attribute familyName is obtained from the column users_profile.lastname
         * The attribute address is obtained from the column users_profile.residence
            The address from users_profile.residence has the format:
                addressLocality, addressCountry
         * The attribute image is obtained from the column users_profile.picture
         * The rest of attributes match one-to-one with column names in the
           database.
        '''
        #PERFORM OPERATIONS
        #Create the messages list
        users_db = g.con.get_users()

        #FILTER AND GENERATE THE RESPONSE
       #Create the envelope
        envelope = {}
        collection = {}
        envelope["collection"] = collection
        collection['version'] = "1.0"
        collection['href'] = api.url_for(Users)
        collection['links'] = [{'prompt': 'List of all messages in the Forum',
                                'rel': 'messages-all',
                                'href': api.url_for(Messages)}
                              ]

        collection['template'] = {
            "data": [
                {"prompt": "Insert nickname", "name": "nickname",
                 "value": "", "required": True},
                {"prompt": "Insert user address", "name": "address",
                 "object": {}, "required": False},
                {"prompt": "Insert user avatar", "name": "avatar",
                 "value": "", "required": True},
                {"prompt": "Insert user birthday", "name": "birthday",
                 "value": "", "required": True},
                {"prompt": "Insert user email", "name": "email",
                 "value": "", "required": True},
                {"prompt": "Insert user familyName", "name": "familyName",
                 "value": "", "required": True},
                {"prompt": "Insert user gender", "name": "gender",
                 "value": "", "required": True},
                {"prompt": "Insert user givenName", "name": "givenName",
                 "value": "", "required": True},
                {"prompt": "Insert user image", "name": "image",
                 "value": "", "required": False},
                {"prompt": "Insert user signature", "name": "signature",
                 "value": "", "required": True},
                {"prompt": "Insert user skype", "name": "skype",
                 "value": "", "required": False},
                {"prompt": "Insert user telephone", "name": "telephone",
                 "value": "", "required": False},
                {"prompt": "Insert user website", "name": "website",
                 "value": "", "required": False}
            ]
        }
        #Create the items
        items = []
        for user in users_db:
            _nickname = user['nickname']
            _registrationdate = user['registrationdate']
            _url = api.url_for(User, nickname=_nickname)
            _history_url = api.url_for(History, nickname=_nickname)
            user = {}
            user['href'] = _url
            user['read-only'] = True
            user['data'] = []
            value = {'name': 'nickname', 'value': _nickname}
            user['data'].append(value)
            value = {'name': 'registrationdate', 'value': _registrationdate}
            user['data'].append(value)
            user['links'] = [{'href': _history_url,
                              'rel': "messages",
                              'name': "history",
                              'prompt': "History of user"
                            }]
            items.append(user)
        collection['items'] = items
        #RENDER
        string_data = json.dumps(envelope)
        return Response(string_data, 200, mimetype="application/vnd.collection+json;/profiles/user-profile")

    def post(self):
        '''
        Adds a new user in the database.


        REQUEST ENTITY BODY:
         * Media type: Collection+JSON:
             http://amundsen.com/media-types/collection/
           - Extensions: template validation and value-types
             https://github.com/collection-json/extensions
         * Profile: Forum_User
           http://atlassian.virtues.fi: 8090/display/PWP
           /Exercise+4#Exercise4-Forum_User

        The body should be a Collection+JSON template.

        Semantic descriptors used in template: address(optional),
        avatar(mandatory), birthday(mandatory),email(mandatory),
        familyName(mandatory), gender(mandatory), givenName(mandatory),
        image(optional), signature(mandatory), skype(optional),
        telephone(optional), website(optional).

        RESPONSE STATUS CODE:
         * Returns 201 + the url of the new resource in the Location header
         * Return 409 Conflict if there is another user with the same nickname
         * Return 400 if the body is not well formed
         * Return 415 if it receives a media type != application/json

        NOTE:
         * The attribute signature is obtained from the column users_profile.signature
         * The attribute givenName is obtained from the column users_profile.firstname
         * The attribute familyName is obtained from the column users_profile.lastname
         * The attribute address is obtained from the column users_profile.residence
            The address from users_profile.residence has the format:
                addressLocality, addressCountry
         * The attribute image is obtained from the column users_profile.picture
         * The rest of attributes match one-to-one with column names in the
           database.

        NOTE:
        The: py: method:`Connection.append_user()` receives as a parameter a
        dictionary with the following format.
        {'public_profile':{'nickname':''
                           'signature':'','avatar':''},
         'restricted_profile':{'firstname':'','lastname':'','email':'',
                                  'website':'','mobile':'','skype':'',
                                  'birthday':'','residence':'','gender':'',
                                  'picture':''}
            }

        '''

        if COLLECTIONJSON != request.headers.get('Content-Type', ''):
            return create_error_response(415, "UnsupportedMediaType","Use a JSON compatible format")
        #PARSE THE REQUEST:
        request_body = request.get_json(force=True)
        if not request_body:
            return create_error_response(415, "Unsupported Media Type",
                                         "Use a JSON compatible format",
                                         )
        #Get the request body and serialize it to object
        #We should check that the format of the request body is correct. Check
        #That mandatory attributes are there.

        data = request_body['template']['data']
        _nickname = None
        _residence = None
        _avatar = None
        _birthday = None
        _email = None
        _lastname = None
        _gender = None
        _firstname = None
        _picture = None
        _signature = None
        _skype = None
        _mobile = None
        _website = None

        for d in data:
        #This code has a bad performance. We write it like this for
        #simplicity. Another alternative should be used instead. E.g.
        #generation expressions
            if d['name'] == "address":
                try:
                    _residence = d['object']['addressLocality'] + \
                        ","+d['object']['addressCountry']
                except KeyError:
                    return create_error_response(400, "Wrong request format",
                                                 "Incorrect format of address field"
                                                )
            elif d['name'] == "avatar":
                _avatar = d['value']
            elif d['name'] == "birthday":
                _birthday = d['value']
            elif d['name'] == "email":
                _email = d['value']
            elif d['name'] == "familyName":
                _lastname = d['value']
            elif d['name'] == "gender":
                _gender = d['value']
            elif d['name'] == "givenName":
                _firstname = d['value']
            elif d['name'] == "image":
                _picture = d['value']
            elif d['name'] == "signature":
                _signature = d['value']
            elif d['name'] == "skype":
                _skype = d['value']
            elif d['name'] == "telephone":
                _mobile = d['value']
            elif d['name'] == "website":
                _website = d['value']
            elif d['name'] == "nickname":
                _nickname = d['value']
        if not _avatar or not _birthday or not _email or not _lastname or \
           not _gender or not _firstname or not _signature or not _nickname:
            return create_error_response(400, "Wrong request format",
                                         "Be sure you include all"
                                         " mandatory properties"
                                        )
        #Conflict if user already exist
        if g.con.contains_user(_nickname):
            return create_error_response(409, "Wrong nickname",
                                         "There is already a user with same"
                                         "nickname:%s." % _nickname)

        user = {'public_profile': {'nickname': _nickname,
                                   'signature': _signature, 'avatar': _avatar},
                'restricted_profile': {'firstname': _firstname,
                                       'lastname': _lastname,
                                       'email': _email,
                                       'website': _website,
                                       'mobile': _mobile,
                                       'skype': _skype,
                                       'birthday': _birthday,
                                       'residence': _residence,
                                       'gender': _gender,
                                       'picture': _picture}
        }

        try:
            nickname = g.con.append_user(_nickname, user)
        except ValueError:
            return create_error_response(400, "Wrong request format",
                                         "Be sure you include all"
                                         " mandatory properties"
                                        )

        #CREATE RESPONSE AND RENDER
        if nickname:
            return Response(
                status=201,
                headers={"Location": api.url_for(User,
                                                 nickname=nickname)})
        #User in the database
        else:
            return create_error_response(409, "User in database",
                                         "Nickname: %s already in use" % nickname)

class User(Resource):
    '''
    User Resource. Public and private profile are separate resources.
    '''

    def get(self, nickname):
        '''
        Get basic information of a user:

        INPUT PARAMETER:
       : param str nickname: Nickname of the required user.

        OUTPUT:
         * Return 200 if the nickname exists.
         * Return 404 if the nickname is not stored in the system.

        RESPONSE ENTITY BODY:

        * Media type recommended: application/hal+json:
             http://stateless.co/hal_specification.html
         * Profile recommended: Forum_User
           /profiles/user-profile

        Link relations used: self, collection, public-data, private-data,
        messages.

        Semantic descriptors used: nickname and registrationdate

        NOTE:
        The: py: method:`Connection.get_user()` returns a dictionary with the
        the following format.

        {'public_profile':{'registrationdate':,'nickname':''
                               'signature':'','avatar':''},
        'restricted_profile':{'firstname':'','lastname':'','email':'',
                              'website':'','mobile':'','skype':'',
                              'birthday':'','residence':'','gender':'',
                              'picture':''}
            }
        '''

        user_db = g.con.get_user(nickname)
        if not user_db:
            return create_error_response(404, "Unknown user",
                                         "There is no a user with nickname %s"
                                         % nickname)
        envelope = {}
        links = {}
        envelope["_links"] = links
        _curies = [
            {
                "name": "user",
                "href": FORUM_USER_PROFILE + "/{rels}",
                "templated": True
            }
        ]
        links['curies'] = _curies
        links['self'] = {'href': api.url_for(User, nickname=nickname),
                         'profile': FORUM_USER_PROFILE}
        links['collection'] = {'href': api.url_for(Users),
                               'profile': FORUM_USER_PROFILE,
                               'type': COLLECTIONJSON}
        links['user:messages'] = {
            'href': api.url_for(History, nickname=nickname),
            'profile': FORUM_MESSAGE_PROFILE,
            'type': COLLECTIONJSON}
        links['user:public-data'] = {
            'href': api.url_for(User_public, nickname=nickname),
            'profile': FORUM_USER_PROFILE,
            'type': HAL}
        links['user:restricted-data'] = {
            'href': api.url_for(User_restricted, nickname=nickname),
            'profile': FORUM_USER_PROFILE,
            'type': HAL}
        links['user:delete'] = {
            'href': api.url_for(User, nickname=nickname),
            'profile': FORUM_USER_PROFILE
        }
        envelope['nickname'] = nickname
        envelope['registrationdate'] = user_db['public_profile']['registrationdate']
        return Response(json.dumps(envelope), 200,
                        mimetype=HAL+";"+FORUM_USER_PROFILE)

    def delete(self, nickname):
        '''
        Delete a user in the system.

       : param str nickname: Nickname of the required user.

        RESPONSE STATUS CODE:
         * If the user is deleted returns 204.
         * If the nickname does not exist return 404
        '''
        if g.con.delete_user(nickname):
            return '', 204
        else:
            return create_error_response(404, "Unknown user",
                                         "There is no a user with nickname %s"
                                         % nickname)


class User_public(Resource):

    def get (self, nickname):
        '''
        Not implemented
        '''
        abort(501)

    def put (self, nickname):
        '''
        Not implemented
        '''
        abort(501)

class User_restricted(Resource):

    def get (self, nickname):
        '''
        Not implemented
        '''
        abort(501)

    def put (self, nickname):
        '''
        Not implemented
        '''
        abort(501)

class History(Resource):
    def get (self, nickname):
        '''
            This method returns a list of messages that has been sent by an user
            and meet certain restrictions (result of an algorithm).
            The restrictions are given in the URL as query parameters.

            INPUT:
            The query parameters are:
             * length: the number of messages to return
             * after: the messages returned must have been modified after
                      the time provided in this parameter.
                      Time is UNIX timestamp
             * before: the messages returned must have been modified before the
                       time provided in this parameter. Time is UNIX timestamp

            RESPONSE STATUS CODE:
             * Returns 200 if the list can be generated and it is not empty
             * Returns 404 if no message meets the requirement

            RESPONSE ENTITY BODY:
            * Media type recommended: Collection+JSON:
             http://amundsen.com/media-types/collection/
             - Extensions: template validation and value-types
               https://github.com/collection-json/extensions
            * Profile recommended: Forum_Message
                /profiles/user-profile

            Link relations used in items: None

            Semantic descriptions used in items: headline

            Link relations used in links: messages-all, author

            Semantic descriptors used in queries: after, before, lenght
        '''
        parameters = request.args
        length = int(parameters.get('length', -1))
        before = int(parameters.get('before', -1))
        after = int(parameters.get('after', -1))
        messages_db = g.con.get_messages(nickname, length, before, after)
        if messages_db is None or not messages_db:
            return create_error_response(404, "Empty list",
                                         "Cannot find any message with the"
                                         " provided restrictions")
        envelope = {}
        collection = {}
        envelope["collection"] = collection
        collection['version'] = "1.0"
        collection['href'] = api.url_for(History, nickname=nickname)
        collection['links'] = [{'prompt': 'List of all messages in the Forum',
                                'rel': 'messages-all',
                                'href': api.url_for(Messages)},
                               {'href': api.url_for(User, nickname=nickname),
                                'rel': "author",
                                'prompt': "User's profile"}
                              ]
        collection['queries'] = [
            {'href': api.url_for(History, nickname=nickname),
             'rel': 'search',
             'prompt': "Search in the user history",
             'data': [
                    {"prompt": "Return the messages published after this timestamp",
                     "name": "after",
                     "value": "",
                     "required": False},
                    {"prompt": "Return the messages published before this timestamp",
                     "name": "before",
                     "value": "",
                     "required": False},
                    {"prompt": "Limit the number of messages returned",
                     "name": "length",
                     "value": "",
                     "required": False}
             ]
            }
        ]
        items = []
        for message in messages_db:
            _messageid = message['messageid']
            _headline = message['title']
            _url = api.url_for(Message, messageid=_messageid)
            message = {}
            message['href'] = _url
            message['data'] = []
            value = {'name': 'headline', 'value': _headline}
            message['data'].append(value)
            message['links'] = []
            items.append(message)
        collection['items'] = items

        return Response(json.dumps(envelope), 200,
                        mimetype=COLLECTIONJSON+";"+FORUM_MESSAGE_PROFILE)
        

#Add the Regex Converter so we can use regex expressions when we define the
#routes
app.url_map.converters['regex'] = RegexConverter


#Define the routes
api.add_resource(Messages, '/forum/api/messages/',
                 endpoint='messages')
api.add_resource(Message, '/forum/api/messages/<regex("msg-\d+"):messageid>/',
                 endpoint='message')
api.add_resource(User_public, '/forum/api/users/<nickname>/public_profile/',
                 endpoint='public_profile')
api.add_resource(User_restricted, '/forum/api/users/<nickname>/restricted_profile/',
                 endpoint='restricted_profile')
api.add_resource(Users, '/forum/api/users/',
                 endpoint='users')
api.add_resource(User, '/forum/api/users/<nickname>/',
                 endpoint='user')
api.add_resource(History, '/forum/api/users/<nickname>/history/',
                 endpoint='history')


#Redirect profile
@app.route('/profiles/<profile_name>')
def redirect_to_profile(profile_name):
    return redirect(APIARY_PROFILES_URL + profile_name)


#Start the application
#DATABASE SHOULD HAVE BEEN POPULATED PREVIOUSLY
if __name__ == '__main__':
    #Debug true activates automatic code reloading and improved error messages
    app.run(debug=True)
