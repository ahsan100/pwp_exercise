'''
Created on 26.01.2013
Modified on 18.02.2016
@author: ivan
'''

from flask import Flask, request, Response, g
from flask.ext.restful import Resource, Api, abort
from werkzeug.exceptions import NotFound,  UnsupportedMediaType

from utils import RegexConverter
import database

#Define the application and the api
app = Flask(__name__)
app.debug = True
# Set the database Engine. In order to modify the database file (e.g. for
# testing) provide the database path   app.config to modify the
#database to be used (for instance for testing)
app.config.update({'Engine': database.Engine()})
#Start the RESTful API.
api = Api(app)


@app.before_request
def connect_db():
    '''Creates a database connection before the request is proccessed.

    The connection is stored in the application context variable flask.g .
    Hence it is accessible from the request object.'''

    g.con = app.config['Engine'].connect()


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

        ENTITY BODY OUTPUT FORMAT:
        {'links':[{'title':'Users list', 'rel':'related',
                   'href':'/forum/api/users', 'method':'GET'
                   },
                  {'title':'New Message', 'rel':'create', 'method':'POST',
                   'href':'/forum/api/messages/'}
         ],
         'messages':[<message1>, <message2>, ..., <messagen>]
        }

        Each message is serialized as follow:
        {'title': <message_title>,
         'link':{'rel':'self','href'=:'/forum/api/messages/<messageid>'}
        '''
        #Extract messages from database
        messages_db = g.con.get_messages()

        #FILTER AND GENERATE RESPONSE
        messages = []
        for message in messages_db:
            _messageid = message["messageid"]
            _messagetitle = message["title"]
            _messageurl = api.url_for(Message, messageid=_messageid)
            message = {}
            message['title'] = _messagetitle
            message['link'] = {'href': _messageurl, 'rel': 'self'}
            messages.append(message)
        #Create the envelope
        envelope = {}
        envelope['links'] = [{'title': 'Users list', 'method': 'GET',
                              'rel': 'related', 'href': api.url_for(Users)},
                             {'title': 'New Message',
                              'method': 'POST',
                              'rel': 'create',
                              'href': api.url_for(Messages)}
                            ]
        envelope['messages'] = messages

        #RENDER
        return envelope

    def post(self):
        '''
        Adds a a new message.

        ENTITY BODY INPUT FORMAT:
        The entity body is a JSON representation with the following format:
            {'title':<newTitle>,'body':<newBody>, 'sender':<sender>}
        Use 'Anonymous' if 'sender' field does not exist.

        OUTPUT:
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
        # using JSON
        data = request.get_json()
        if not data:
           abort(415)

        #It throws a BadRequest exception, and hence a 400 code if the JSON is
        #not wellformed
        try:
            title = data['title']
            body = data['body']
            sender = data.get('sender', 'Anonymous')
            ipaddress = request.remote_addr
        except:
            #This is launched if either title or body does not exist.
            abort(400)

        #Create the new message and build the response code'
        newmessageid = g.con.create_message(title, body,
                                           sender, ipaddress)
        if not newmessageid:
            abort(500)

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
        :param str messageid: The id of the message to be retrieved from the
            system

        ENTITY BODY OUTPUT FORMAT:
        {
            'links':[
                {'href':<messages url>,
                 'rel':'collection', 'method': 'GET', title':'Messages list'},
                {'title':'parent', 'method':'GET', rel':'up',
                 'href': <parent message url>},
                {'rel':'edit', 'href': <url of this resource>},
                {'rel':'self', 'href': <url of this resource>}
            ],
            'message':{'body': <message body>,
                       'messageid': <id of the mesagge; format msg-\d>,
                       'title': <title of the message>,
                       'editor': <editor of the message (optional)>
                       'sender':{'href':'/forum/api/users/{nickname}',
                                 'rel':'author', 'title': <sender nickname>}
            }
        }
        NOTE: sender can be a string if the user is not registered.
              editor should not be in the output if the database return None.
        '''

        #PEFORM OPERATIONS INITIAL CHECKS
        #Get the message from db
        message_db = g.con.get_message(messageid)
        if not message_db:
            abort(404, message="There is no a message with id %s" % messageid,
                       resource_type="Message",
                       resource_url=request.path,
                       resource_id=messageid)

        #FILTER AND GENERATE RESPONSE
        #Create the envelope:
        envelope = {}

        #Now create the links, and add the first dictionary: link to messages
        links = []
        link_to_messages = {'href': api.url_for(Messages), 'rel': 'collection',
                            'title': 'Messages list', 'method': 'GET'}
        links.append(link_to_messages)

        #Extract the replyto from the dictionary returned from the database API.
        # If it exists create the reference in links
        parent = message_db.get('replyto', None)
        if parent is not None:
            link_to_parent = {'title': 'parent', 'rel': 'up', 'method': 'GET',
                              'href': api.url_for(Message, messageid=parent)}
            links.append(link_to_parent)

        #Add the edit and the self relation:
        _self = api.url_for(Message, messageid=messageid)
        links.append({'rel': 'self', 'href': _self})
        links.append({'rel': 'edit', 'href': _self})

        #Create the message to write in the envelope
        message = {'body': message_db['body'],
                   'messageid': message_db['messageid'],
                   'title': message_db['title']
                  }
        #Add editor if exist
        if message_db.get('editor', None) is not None:
            message['editor'] = message_db['editor']

        #If sender is not Anonymous extract the nickname from message_db
        sender_db = message_db.get('sender', None)
        if sender_db is not None and sender_db != 'Anonymous':
            senderurl = api.url_for(User, nickname=message_db["sender"])
            message['sender'] = {'href': senderurl,
                                 'rel': 'author', 'title': sender_db}
        else:
            message['sender'] = 'Anonymous'

        #Fill the envelope
        envelope['links'] = links
        envelope['message'] = message

        #RENDER
        return envelope

    def delete(self, messageid):
        '''
        Deletes a message from the Forum API.

        INPUT PARAMETERS:
        :param str messageid: The id of the message to be deleted

        OUTPUT
         * Returns 204 if the message was deleted
        Returns 404 if the messageid is not associated to any message.
        '''
      

        if g.con.delete_message(messageid):
            #RENDER RESPONSE
            return '', 204
        else:
            #GENERATE ERROR RESPONSE
            abort(404, message="There is no a message with id %s" % messageid,
                       resource_type="Message",
                       resource_url=request.path,
                       resource_id=messageid)


    def put(self, messageid):
        '''
        Modifies the title, body and editor properties of this message.

        INPUT PARAMETERS:
        :param str messageid: The id of the message to be updated

        ENTITY BODY INPUT FORMAT:
        The entity body is a JSON representation with the following format:
            {'title': <newTitle>, 'body': <newBody>, 'editor': <editor name>}

        If <editor> is empty, use 'Anonymous' instead.

        OUTPUT:
         * Returns 204 if the message is modified correctly
         * Returns 400 if the body of the request is not well formed or it is
           empty.
         * Returns 404 if there is no message with messageid
         * Returns 415 if the input is not JSON.

        '''
       

        #CHECK THAT MESSAGE EXISTS
        #If the message with messageid does not exist return status code 404
        if not g.con.contains_message(messageid):
          abort(404)

        #Extract the request body. In general would be request.data
        #Since the request is JSON I use request.get_json
        #get_json returns a python dictionary after serializing the request body
        #get_json returns None if the body of the request is not formatted
        # using JSON
        data = request.get_json()
        if not data:
            abort(415)

        #It throws a BadRequest exception, and hence a 400 code if the JSON is
        #not wellformed
        try:
            title = data['title']
            body = data['body']
            editor = data.get('editor', 'Anonymous')
        except:
            #This is launched if either title or body does not exist.
            abort(400)

        #Modify the message and build the response code'
        newmessageid =  g.con.modify_message(messageid,title,body,editor)
        
        #Create the Location header with the id of the message modified
        url = api.url_for(Message, messageid=newmessageid)
        #RENDER
        #Return the response
        return Response(status=204, headers={'Location': url})


    def post(self, messageid):
        '''
        Adds a response to a message with id <messageid>.

        INPUT PARAMETERS:
        :param str messageid: The id of the message to be deleted

        ENTITY BODY INPUT FORMAT:
        The entity body is a JSON representation with the following format:
            {'title': <newTitle>,'body': <newBody>, 'sender': <sender user>}
        Use 'Anonymous' is 'sender' field does not exist.

        OUTPUT:
         * Returns 201 if the message has been added correctly.
           The Location header contains the path of the new message
         * Returns 400 if the message is not well formed or the entity body is
           empty.
         * Returns 404 if there is no message with messageid
         * Returns 415 if the format of the response is not json
         * Returns 500 if the message could not be added to database.
        '''

        #CHECK THAT MESSAGE EXISTS
        #If the message with messageid does not exist return status code 404
        if not g.con.contains_message(messageid):
            raise NotFound()

        #Extract the request body. In general would be request.data
        #Since the request is JSON I use request.get_json
        #get_json returns a python dictionary after serializing the request body
        #get_json returns None if the body of the request is not formatted
        # using JSON
        data = request.get_json()
        if not data:
            raise UnsupportedMediaType()

        #It throws a BadRequest exception, and hence a 400 code if the JSON is
        #not wellformed
        try:
            title = data['title']
            body = data['body']
            sender = data.get('sender', 'Anonymous')
            ipaddress = request.remote_addr
        except:
            #This is launched if either title or body does not exist.
            abort(400)

        #Create the new message and build the response code'
        newmessageid = g.con.append_answer(messageid, title, body,
                                           sender, ipaddress)
        if not newmessageid:
            abort(500)

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

        ENTITITY BODY OUTPUT FORMAT:

        {'links':[{'title':'Messages list', 'rel':'related', 'method': 'GET',
                   'href':'/forum/api/messages'},
                   {'title':'New user', 'rel':'create', 'method': 'PUT',
                   'href':'/forum/api/users/{nickname}'}],
         'users':[<user1>, <user2>, <usern>]}

        where each user has the following serialization format:

        {'nickname': <user nickname>,
         'link':{'title':'user',
                 'rel':'self',
                 'href'=:'/forum/api/users/{user nickname}'}
        }

        '''
        #PERFORM OPERATIONS
        #Create the messages list
        users_db = g.con.get_users()

        #FILTER AND GENERATE THE RESPONSE
        users = []
        for user_db in users_db:
            _nickname = user_db["nickname"]
            _userurl = api.url_for(User, nickname=_nickname)
            user = {}
            user['nickname'] = _nickname
            user['link'] = {'rel': 'self', 'href': _userurl, 'title': 'user'}
            #print 'user', user
            users.append(user)

        #Create the envelope
        envelope = {}
        envelope['links'] = [{'title': 'Messages list',
                              'method': 'GET',
                              'rel': 'related',
                              'href': api.url_for(Messages)},
                             {'title': 'New User',
                              'method': 'PUT',
                              'rel': 'create',
                              'href': api.url_for(User, nickname='{nickname}')}
                            ]
        envelope['users'] = users
        #RENDER
        return envelope
   
class User(Resource):
    '''
    User Resource. Public and private profile are separate resources.
    '''

    def get(self, nickname):
        '''
        Get basic information of a user:

        INPUT PARAMETER:
        :param str nickname: Nickname of the required user.

        OUTPUT:
         * Return 200 if the nickname exists.
         * Return 404 if the nickname is not stored in the system.

        ENTITY BODY OUTPUT FORMAT:

        {'links':[{'title':'users',
                   'rel':'collection',
                   'method': 'GET',
                   'href': /forum/api/users/},
                  {'rel':'edit', 'href': <url of this resource>},
                  {'rel':'self', 'href': <url of this resource>},
                  {'rel':'public-profile', 'title':  'Public Profile', 
                   'href': '/forum/api/users/<nickname>/public_profile',
                   'method': 'GET'}, 
                  {'rel':'restricted-profile', 'title':  'Private Profile', 
                   'href': '/forum/api/users/<nickname>/restricted_profile',
                   'method': 'GET'},
                  {'rel':'history', 'title':  'History', 
                   'href': '/forum/api/users/<nickname>/history',
                   'method': 'GET'}
                   ],
         'user': <user info>}

        where user info is:
        {'nickname': <nickname>,
         'registrationdate': <registrationdate>}
        '''
        #PERFORM OPERATIONS
        user_db = g.con.get_user(nickname)
        if not user_db:
            abort(404, message="There is no a user with nickname %s"
                                 % nickname,
                       resource_type="User",
                       resource_url=request.path,
                       resource_id=nickname)
        print user_db
        #FILTER AND GENERATE RESPONSE
        envelope = {}
        links = []
        links.append({'title': 'users',
                      'rel': 'collection',
                      'href': api.url_for(Users)})
        links.append({'rel': 'edit',
                      'href': api.url_for(User, nickname=nickname)})
        links.append({'rel': 'self',
                      'href': api.url_for(User, nickname=nickname)})
        links.append({'rel': 'public-profile', 'title':  'Public Profile',
                      'href':  api.url_for(User_public, nickname=nickname),
                      'method': 'GET'})
        links.append({'rel': 'restricted-profile', 'title':  'Private Profile',
                      'href':  api.url_for(User_restricted, nickname=nickname),
                      'method': 'GET'})
        links.append({'rel': 'history', 'title':  'History',
                      'href':  api.url_for(History, nickname=nickname),
                      'method': 'GET'})

        envelope['links'] = links

        user = {'nickname': nickname,
                'registrationdate': user_db['public_profile']['registrationdate'],
               }
        envelope['user'] = user

        #RENDER
        return envelope

    def delete(self, nickname):
        '''
        Delete a user in the system.

        :param str nickname: Nickname of the required user.

        OUTPUT:
         * If the user is deleted returns 204.
         * If the nickname does not exist return 404
        '''

        #PEROFRM OPERATIONS
        #Try to delete the user. If it could not be deleted, the database
        #returns None.
        if g.con.delete_user(nickname):
            #RENDER RESPONSE
            return '', 204
        else:
            #GENERATE ERROR RESPONSE
            abort(404, message="There is no a user with nickname %s"
                                 % nickname,
                       resource_type="User",
                       resource_url=request.path,
                       resource_id=nickname)

    def put(self, nickname):
        '''
        Adds a new user in the database.

        :param str nickname: Nickname of the required user.

        ENTITY BODY INPUT FORMAT:
        {
            'public_profile':{'signature': <signature>,'avatar': <avatar>},
            'restricted_profile':{'firstname': <name>,
                                  'lastname': <surname>,
                                  'email': <email address>,
                                  'website': <webpage url> (optional attribute),
                                  'mobile': <mobile phone number> (optional),
                                  'skype': <skype nickname> (optional),
                                  'birtday': <birthday>,
                                  'residence': <address>,
                                  'gender': <gender>,
                                  'picture': <picture file name> (optional)
                                  }
        }

        OUTPUT:
         * Returns 201 + the url of the new resource in the Location header
         * Return 409 Conflict if there is another user with the same nickname
         * Return 400 if the body is not well formed
         * Return 415 if it receives a media type != application/json
        '''
        #PERFORM INITAL CHECKING:
        #Check that there is no other user with the same nickname
        if g.con.contains_user(nickname):
            abort(409, message="There is already a user with same nickname %s.\
                                  Try another user " % nickname,
                       resource_type="User",
                       resource_url=request.path,
                       resource_id = nickname)

        #PARSE THE REQUEST:
        user = request.get_json()
        if not user:
            raise UnsupportedMediaType()
        #Get the request body and serialize it to object
        #We should check that the format of the request body is correct. Check
        #That mandatory attributes are there.
        if not all(attr in user['public_profile'] for attr in\
            ('signature', 'avatar')):
            abort(400)
        if not all(attr in user['restricted_profile'] for attr in\
            ('firstname', 'lastname', 'birthday', 'residence', 'gender', 'email')):
            abort(400)

        #But we are not going to do this exercise
        nickname = g.con.append_user(nickname, user)

        #CREATE RESPONSE AND RENDER
        return Response(status=201,
                        headers={"Location": api.url_for(User, nickname=nickname)}
               )

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

            OUTPUT:
            Returns 200 if the list is correct
            Returns 404 if no message meets the requirement

            ENTITY BODY OUTPUT FORMAT:
            {'links':[
                      {'title':'Sender',
                       'rel':'parent',
                       'method':'GET'
                       'href':'/forum/api/users/{nickname}'},
                      {'title':'Users',
                       'method':'GET',
                       'rel':'collection',
                       'href':'/forum/api/users/'}
                      ],
             'messages':[<messag1>, <message2>, ..., <messagen>]
            }

            where <messagen> is:
            {'link':{'href': <message_url>,'rel':'self',
                    'title': <message title>}}
        '''
      
        
        params = request.args;
        
        length = -1
        if params.has_key('length'):
           length = int(params['length'])
        
        before = -1
        if params.has_key('before'):
            before = int(params['before'])
        
        after = -1
        if params.has_key('after'):
            after = int(params['after'])

        messages_db = g.con.get_messages(nickname,length, before,after)

        if not messages_db:
           abort(404)

        envelope = {}
        envelope['links'] = [{'title':'Sender', 'rel':'parent','method':'GET','href':api.url_for(User,nickname = nickname)},
                             {'title':'Users','method':'GET','rel':'collection','href':api.url_for(Users)}
                            ]
 
        messages = []
        for message in messages_db:
            _messageid = message["messageid"]
            _messagetitle = message["title"]
            _messageurl = api.url_for(Message, messageid=_messageid)
            message = {}
            message['link'] = {'href': _messageurl, 'rel': 'self','title' :  _messagetitle}
            messages.append(message)

        envelope['messages'] = messages
        
        return envelope

            

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


'''
#TASK1 TODO: Add the routes for Users, User and History
resources.

The URL of the resources are in the Appendix 1 of the Exercise guide. Note,
that the nickname must be any string (you do not have to use any regex
expression)
'''


#Start the application
#DATABASE SHOULD HAVE BEEN POPULATED PREVIOUSLY
if __name__ == '__main__':
    #Debug true activates automatic code reloading and improved error messages

    app.run(debug=True)

    
