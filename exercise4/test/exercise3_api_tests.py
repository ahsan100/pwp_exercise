'''
Created on 26.01.2013
Modified on 24.02.2016
@author: ivan
'''
import unittest, copy
import json

import flask

import forum.resources as resources
import forum.database as database

DB_PATH = 'db/forum_test.db'
ENGINE = database.Engine(DB_PATH)

COLLECTIONJSON = "application/vnd.collection+json"
HAL = "application/hal+json"
FORUM_USER_PROFILE ="/profiles/user-profile"
FORUM_MESSAGE_PROFILE = "/profiles/message-profile"
ATOM_THREAD_PROFILE = "https://tools.ietf.org/html/rfc4685"

#Tell Flask that I am running it in testing mode.
resources.app.config['TESTING'] = True
#Necessary for correct translation in url_for
resources.app.config['SERVER_NAME'] = 'localhost:5000'

#Database Engine utilized in our testing
resources.app.config.update({'Engine': ENGINE})

#Other database parameters.
initial_messages = 20
initial_users = 5


class ResourcesAPITestCase(unittest.TestCase):
    #INITIATION AND TEARDOWN METHODS
    @classmethod
    def setUpClass(cls):
        ''' Creates the database structure. Removes first any preexisting
            database file
        '''
        print "Testing ", cls.__name__
        ENGINE.remove_database()
        ENGINE.create_tables()

    @classmethod
    def tearDownClass(cls):
        '''Remove the testing database'''
        print "Testing ENDED for ", cls.__name__
        ENGINE.remove_database()

    def setUp(self):
        '''
        Populates the database
        '''
        #This method load the initial values from forum_data_dump.sql
        ENGINE.populate_tables()
        #Activate app_context for using url_for
        self.app_context = resources.app.app_context()
        self.app_context.push()
        #Create a test client
        self.client = resources.app.test_client()

    def tearDown(self):
        '''
        Remove all records from database
        '''
        ENGINE.clear()
        self.app_context.pop()

class MessagesTestCase (ResourcesAPITestCase):

    #Anonymous user
    message_1_request = {"template": {
        "data": [
            {"name": "headline", "value": "Hypermedia course"},
            {"name": "articleBody", "value": "Do you know any good online"
                                             " hypermedia course?"}
        ]}
    }

    #Existing user
    message_2_request = {"template": {
        "data": [
            {"name": "headline", "value": "Hypermedia course"},
            {"name": "articleBody", "value": "Do you know any good online"
                                             " hypermedia course?"},
            {"name": "author", "value": "Axel"}
        ]}
    }

    #Non exsiting user
    message_3_request = {"template": {
        "data": [
            {"name": "headline", "value": "Hypermedia course"},
            {"name": "articleBody", "value": "Do you know any good online"
                                             " hypermedia course?"},
            {"name": "author", "value": "Onethatwashere"}
        ]}
    }

    #Missing the headline
    message_4_wrong = {"template": {
        "data": [
            {"name": "articleBody", "value": "Do you know any good online"
                                             " hypermedia course?"},
            {"name": "author", "value": "Onethatwashere"}
        ]}
    }

    #Missing the articleBody
    message_5_wrong = {"template": {
        "data": [
            {"name": "articleBody", "value": "Do you know any good online"
                                             " hypermedia course?"},
            {"name": "author", "value": "Onethatwashere"}
        ]}
    }


    url = "/forum/api/messages/"

    def test_url(self):
        '''
        Checks that the URL points to the right resource
        '''
        #NOTE: self.shortDescription() shuould work.
        print '('+self.test_url.__name__+')', self.test_url.__doc__,
        with resources.app.test_request_context(self.url):
            rule = flask.request.url_rule
            view_point = resources.app.view_functions[rule.endpoint].view_class
            self.assertEquals(view_point, resources.Messages)

    def test_get_messages(self):
        '''
        Checks that GET Messages return correct status code and data format
        '''
        print '('+self.test_get_messages.__name__+')', self.test_get_messages.__doc__

        #Check that I receive status code 200
        resp = self.client.get(flask.url_for('messages'))
        self.assertEquals(resp.status_code, 200)

        # Check that I receive a collection and adequate href
        data = json.loads(resp.data)['collection']
        self.assertEquals(resources.api.url_for(resources.Messages,
                                                _external=False),
                          data['href'])

        #Check that template is correct
        template_data = data['template']['data']
        self.assertEquals(len(template_data), 4)
        for t_data in template_data:
            self.assertIn('required' and 'prompt' and 'name' and 'value',
                          t_data)
            self.assertIn(t_data['name'], ('headline', 'articleBody',
                                           'author', 'editor'))
        #Check that links are correct
        links = data['links']
        self.assertEquals(len(links), 1)  # Just one link
        self.assertIn('prompt', links[0])
        self.assertEquals(links[0]['rel'], 'users-all')
        self.assertEquals(links[0]['href'],
                          flask.url_for('users', _external=False))

        #Check that items are correct.
        items = data['items']
        self.assertEquals(len(items), initial_messages)
        for item in items:
            self.assertIn(flask.url_for('messages', _external=False),
                          item['href'])
            self.assertIn('links', item)
            self.assertEquals(1, len(item['data']))
            self.assertEquals('headline', item['data'][0]['name'])
            self.assertIn('value', item['data'][0])

    def test_get_messages_mimetype(self):
        '''
        Checks that GET Messages return correct status code and data format
        '''
        print '('+self.test_get_messages_mimetype.__name__+')', self.test_get_messages_mimetype.__doc__

        #Check that I receive status code 200
        resp = self.client.get(flask.url_for('messages'))
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp.headers.get('Content-Type',None),
                          COLLECTIONJSON+";"+FORUM_MESSAGE_PROFILE)

    def test_add_message(self):
        '''
        Test adding messages to the database.
        '''
        print '('+self.test_add_message.__name__+')', self.test_add_message.__doc__

        resp = self.client.post(resources.api.url_for(resources.Messages),
                                headers={'Content-Type': COLLECTIONJSON},
                                data=json.dumps(self.message_1_request)
                               )
        self.assertTrue(resp.status_code == 201)
        url = resp.headers.get('Location')
        self.assertIsNotNone(url)
        resp = self.client.get(url)
        self.assertTrue(resp.status_code == 200)

        resp = self.client.post(resources.api.url_for(resources.Messages),
                                headers={'Content-Type': COLLECTIONJSON},
                                data=json.dumps(self.message_2_request)
                               )
        self.assertTrue(resp.status_code == 201)
        url = resp.headers.get('Location')
        self.assertIsNotNone(url)
        resp = self.client.get(url)
        self.assertTrue(resp.status_code == 200)

        resp = self.client.post(resources.api.url_for(resources.Messages),
                                headers={'Content-Type': COLLECTIONJSON},
                                data=json.dumps(self.message_3_request)
                               )
        self.assertTrue(resp.status_code == 201)
        url = resp.headers.get('Location')
        self.assertIsNotNone(url)
        resp = self.client.get(url)
        self.assertTrue(resp.status_code == 200)

    def test_add_message_wrong_media(self):
        '''
        Test adding messages with a media different than json
        '''
        print '('+self.test_add_message_wrong_media.__name__+')', self.test_add_message_wrong_media.__doc__
        resp = self.client.post(resources.api.url_for(resources.Messages),
                                headers={'Content-Type': 'text'},
                                data=self.message_1_request.__str__()
                               )
        self.assertTrue(resp.status_code == 415)

    def test_add_message_incorrect_format(self):
        '''
        Test that add message response correctly when sending erroneous message
        format.
        '''
        print '('+self.test_add_message_incorrect_format.__name__+')', self.test_add_message_incorrect_format.__doc__
        resp = self.client.post(resources.api.url_for(resources.Messages),
                                headers={'Content-Type': COLLECTIONJSON},
                                data=json.dumps(self.message_4_wrong)
                               )
        self.assertTrue(resp.status_code == 400)

        resp = self.client.post(resources.api.url_for(resources.Messages),
                                headers={'Content-Type': COLLECTIONJSON},
                                data=json.dumps(self.message_5_wrong)
                               )
        self.assertTrue(resp.status_code == 400)

class MessageTestCase (ResourcesAPITestCase):

    #ATTENTION: json.loads return unicode
    message_req_1 = {
        "template": {
            "data": [
                {"name": "headline", "value": "Do not use IE"},
                {"name": "articleBody", "value": "Do not try to fix what others broke"},
                {"name": "author", "value": "HockeyFan"}
            ]
        }
    }

    message_resp_1 = {
        "articleBody": "Do not try to fix what others broke",
        "author": "HockeyFan",
        "headline": "Do not use IE",
        "editor": None,
        "_links": {
            "curies": [
                {
                    "href": FORUM_MESSAGE_PROFILE,
                    "name": "msg"
                },
                {
                    "href": "https://tools.ietf.org/html/rfc4685",
                    "name": "atom-thread"
                }
            ],
            "self": {
                "profile": FORUM_MESSAGE_PROFILE,
                "href": "/forum/api/messages/msg-21/"
            },
            "msg:author": {
                "profile": FORUM_USER_PROFILE,
                "href": "/forum/api/users/HockeyFan/",
                "type": "application/hal+json"
            },
            "atom-thread:in-reply-to": {
                "profile": FORUM_MESSAGE_PROFILE,
                "href": "/forum/api/messages/msg-1/",
                "type": "application/hal+json"
            },
            "collection": {
                "profile": FORUM_MESSAGE_PROFILE,
                "href": "/forum/api/messages/",
                "type": "application/vnd.collection+json"},
            "msg:reply": {
                "href": "/forum/api/messages/msg-1",
                "profile": "/profiles/message_profile",
            }
        },
        "template": {
            "data": [
                {"required": True, "prompt": "",
                 "name": "headline", "value": ""},
                {"required": True, "prompt": "",
                 "name": "articleBody", "value": ""},
                {"required": False, "prompt": "",
                 "name": "author", "value": ""},
                {"required": False, "prompt": "",
                 "name": "editor", "value": ""}
            ]
        }
    }

    message_mod_req_1 = {
        "template": {
            "data": [
                {"name": "headline", "value": "CSS: Margin problems with IE 6.0"},
                {"name": "articleBody", "value": "I am using a float layout on my website but I've run into some problems with Internet Explorer. I have set the left margin of a float to 100 pixels, but IE 6.0 uses a margin of 200px instead. Why is that? Is this one of the many bugs in IE 6.0? It does not happen with IE 7.0"},
                {"name": "author", "value": "AxelW"},
                {"name": "editor", "value": "AxelW"}
            ]
        }
    }

    message_wrong_req_1 = {
        "template": {
            "data": [
                {"name": "headline", "value": "CSS: Margin problems with IE 6.0"}
            ]
        }
    }

    message_wrong_req_2 = {
        "template": {
            "data": [
                {"name": "articleBody", "value": "Do not try to fix what others broke"},
            ]
        }
    }

    message_wrong_req_3 = {
        "headline": "Do not use IE",
        "articleBody": "Do not try to fix what others broke",
        "author": "HockeyFan"
    }

    def setUp(self):
        super(MessageTestCase, self).setUp()
        self.url = resources.api.url_for(resources.Message,
                                         messageid='msg-1',
                                         _external=False)
        self.url_wrong = resources.api.url_for(resources.Message,
                                               messageid='msg-290',
                                               _external=False)

    def test_url(self):
        '''
        Checks that the URL points to the right resource
        '''
        #NOTE: self.shortDescription() shuould work.
        _url = '/forum/api/messages/msg-1/'
        print '('+self.test_url.__name__+')', self.test_url.__doc__
        with resources.app.test_request_context(_url):
            rule = flask.request.url_rule
            view_point = resources.app.view_functions[rule.endpoint].view_class
            self.assertEquals(view_point, resources.Message)

    def test_wrong_url(self):
        '''
        Checks that GET Message return correct status code if given a
        wrong message
        '''
        resp = self.client.get(self.url_wrong)
        self.assertEquals(resp.status_code, 404)

    def test_get_message(self):
        '''
        Checks that GET Message return correct status code and data format
        '''
        print '('+self.test_get_message.__name__+')', self.test_get_message.__doc__
        with resources.app.test_client() as client:
            resp = client.get(self.url)
            self.assertEquals(resp.status_code, 200)
            data = json.loads(resp.data)

            #Check that the links is correct
            links = data['_links']
            self.assertEquals(6, len(links))
            for link_name in links:
                self.assertIn(link_name, ('curies', 'self',
                                          'atom-thread:in-reply-to',
                                          'msg:author', 'collection',
                                          'msg:reply'))
                link = links[link_name]
                if link_name != 'curies':
                    for link_attribute in link:
                        self.assertIn(link_attribute, ('href',
                                                       'profile',
                                                       'type'))
                if link_name == 'self':
                    self.assertEquals(link['href'], self.url)
                    self.assertEquals(link['profile'],
                                      FORUM_MESSAGE_PROFILE)
                elif link_name == "atom-thread:in-reply-to":
                    self.assertEquals(link['href'], None)
                    self.assertEquals(link['profile'],
                                      FORUM_MESSAGE_PROFILE)
                    self.assertEquals(link['type'], HAL)
                elif link_name == "msg:reply":
                    self.assertEquals(link['profile'],
                                      FORUM_MESSAGE_PROFILE)
                    self.assertEquals(link['href'],
                                      resources.api.url_for(resources.Message,
                                                            messageid='msg-1',
                                                            _external=False))
                    self.assertEquals(link['profile'], FORUM_MESSAGE_PROFILE)
                elif link_name == "collection":
                    self.assertEquals(link['href'],
                                      resources.api.url_for(resources.Messages))
                    self.assertEquals(link['profile'],
                                      FORUM_MESSAGE_PROFILE)
                    self.assertEquals(link['type'], COLLECTIONJSON)
                elif link_name == "msg:author":
                    self.assertEquals(link['profile'],
                                      FORUM_USER_PROFILE)
                    self.assertEquals(link['href'],
                                      resources.api.url_for(resources.User,
                                                            nickname='AxelW',
                                                            _external=False))
                    self.assertEquals(link['type'], HAL)

            #Check that the template is correct
            template_values = data['template']['data']
            self.assertEquals(4, len(template_values))
            for template_value in template_values:
                self.assertIn(template_value['name'], ('headline',
                                                       'articleBody',
                                                       'author',
                                                       'editor'))
            #Check rest attributes
            self.assertIn('articleBody', data)
            self.assertIn('author', data)
            self.assertIn('headline', data)
            self.assertIn('editor', data)

    def test_get_message_mimetype(self):
        '''
        Checks that GET Messages return correct status code and data format
        '''
        print '('+self.test_get_message_mimetype.__name__+')', self.test_get_message_mimetype.__doc__

        #Check that I receive status code 200
        resp = self.client.get(self.url)
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp.headers.get('Content-Type',None),
                          HAL+";"+FORUM_MESSAGE_PROFILE)

    def test_add_reply_unexisting_message(self):
        '''
        Try to add a reply to an unexisting message
        '''
        print '('+self.test_add_reply_unexisting_message.__name__+')', self.test_add_reply_unexisting_message.__doc__
        resp = self.client.post(self.url_wrong,
                                data=json.dumps(self.message_req_1),
                                headers={"Content-Type": COLLECTIONJSON})
        self.assertEquals(resp.status_code, 404)

    def test_add_reply_wrong_message(self):
        '''
        Try to add a reply to a message sending wrong data
        '''
        print '('+self.test_add_reply_wrong_message.__name__+')', self.test_add_reply_wrong_message.__doc__
        resp = self.client.post(self.url,
                                data=json.dumps(self.message_wrong_req_1),
                                headers={"Content-Type": COLLECTIONJSON})
        self.assertEquals(resp.status_code, 400)
        resp = self.client.post(self.url,
                                data=json.dumps(self.message_wrong_req_2),
                                headers={"Content-Type": COLLECTIONJSON})
        self.assertEquals(resp.status_code, 400)
        resp = self.client.post(self.url,
                                data=json.dumps(self.message_wrong_req_3),
                                headers={"Content-Type": COLLECTIONJSON})
        self.assertEquals(resp.status_code, 400)

    def test_add_reply_wrong_type(self):
        '''
        Checks that returns the correct status code if the Content-Type is wrong
        '''
        print '('+self.test_add_reply_wrong_type.__name__+')', self.test_add_reply_wrong_type.__doc__
        resp = self.client.post(self.url,
                                data=json.dumps(self.message_req_1),
                                headers={"Content-Type": "application/json"})
        self.assertEquals(resp.status_code, 415)

    def test_add_reply(self):
        '''
        Add a new message and check that I receive the same data
        '''
        print '('+self.test_add_reply.__name__+')', self.test_add_reply.__doc__
        resp = self.client.post(self.url,
                                data=json.dumps(self.message_req_1),
                                headers={"Content-Type": COLLECTIONJSON})
        self.assertEquals(resp.status_code, 201)
        self.assertIn('Location', resp.headers)
        message_url = resp.headers['Location']
        #Check that the message is stored
        resp2 = self.client.get(message_url)
        self.assertEquals(resp2.status_code, 200)
        #data = json.loads(resp2.data)
        #self.assertEquals(data, self.message_resp_1)

    def test_modify_message(self):
        '''
        Modify an exsiting message and check that the message has been modified correctly in the server
        '''
        print '('+self.test_modify_message.__name__+')', self.test_modify_message.__doc__
        resp = self.client.put(self.url,
                               data=json.dumps(self.message_mod_req_1),
                               headers={"Content-Type": COLLECTIONJSON})
        self.assertEquals(resp.status_code, 204)
        #Check that the message has been modified
        resp2 = self.client.get(self.url)
        self.assertEquals(resp2.status_code, 200)
        data = json.loads(resp2.data)
        #Check that the title and the body of the message has been modified with the new data
        self.assertEquals(data['headline'],
                          self.message_mod_req_1['template']['data'][0]['value']
                         )
        self.assertEquals(data['articleBody'],
                          self.message_mod_req_1['template']['data'][1]['value']
                         )

    def test_modify_unexisting_message(self):
        '''
        Try to modify a message that does not exist
        '''
        print '('+self.test_modify_unexisting_message.__name__+')', self.test_modify_unexisting_message.__doc__
        resp = self.client.put(self.url_wrong,
                                data=json.dumps(self.message_mod_req_1),
                                headers={"Content-Type":COLLECTIONJSON})
        self.assertEquals(resp.status_code, 404)

    def test_modify_wrong_message(self):
        '''
        Try to modify a message sending wrong data
        '''
        print '('+self.test_modify_wrong_message.__name__+')', self.test_modify_wrong_message.__doc__
        resp = self.client.put(self.url,
                               data=json.dumps(self.message_wrong_req_1),
                               headers={"Content-Type":COLLECTIONJSON})
        self.assertEquals(resp.status_code, 400)
        resp = self.client.put(self.url,
                               data=json.dumps(self.message_wrong_req_2),
                               headers={"Content-Type": COLLECTIONJSON})
        self.assertEquals(resp.status_code, 400)
        resp = self.client.put(self.url,
                               data=json.dumps(self.message_wrong_req_3),
                               headers={"Content-Type": COLLECTIONJSON})
        self.assertEquals(resp.status_code, 400)

    def test_delete_message(self):
        '''
        Checks that Delete Message return correct status code if corrected delete
        '''
        print '('+self.test_delete_message.__name__+')', self.test_delete_message.__doc__
        resp = self.client.delete(self.url)
        self.assertEquals(resp.status_code, 204)
        resp2 = self.client.get(self.url)
        self.assertEquals(resp2.status_code, 404)

    def test_delete_unexisting_message(self):
        '''
        Checks that Delete Message return correct status code if given a wrong address
        '''
        print '('+self.test_delete_unexisting_message.__name__+')', self.test_delete_unexisting_message.__doc__
        resp = self.client.delete(self.url_wrong)
        self.assertEquals(resp.status_code, 404)

class UsersTestCase (ResourcesAPITestCase):

    user_1_request = {"template": {
        "data": [
            {"name": "nickname", "value": "Rigors"},
            {"object": {"addressLocality":'Manchester', "addressCountry":"UK"},
             "name": "address"},
            {"name": "avatar", "value": "image3.jpg"},
            {"name": "birthday", "value": "2009-09-09"},
            {"name": "email", "value": "rigors@gmail.com"},
            {"name": "familyName", "value": "Rigors"},
            {"name": "gender", "value": "Male"},
            {"name": "givenName", "value": "Reagan"},
            {"name": "image", "value": "image2.jpg"},
            {"name": "signature", "value": "I am like Ronald McDonald"},
            {"name": "skype", "value": "rigors"},
            {"name": "telephone", "value": "0445555666"},
            {"name": "website", "value": "http://rigors.com"}
        ]}
    }

    user_2_request = {"template": {
        "data": [
            {"name": "nickname", "value": "Rango"},
            {"name": "avatar", "value": "image3.jpg"},
            {"name": "birthday", "value": "2009-09-09"},
            {"name": "email", "value": "rango@gmail.com"},
            {"name": "familyName", "value": "Rango"},
            {"name": "gender", "value": "Male"},
            {"name": "givenName", "value": "Rangero"},
            {"name": "signature", "value": "I am like Ronald McDonald"},
        ]}
    }

    #Existing nickname
    user_wrong_1_request =  {"template": {
        "data": [
            {"name": "nickname", "value": "AxelW"},
            {"name": "avatar", "value": "image3.jpg"},
            {"name": "birthday", "value": "2009-09-09"},
            {"name": "email", "value": "rango@gmail.com"},
            {"name": "familyName", "value": "Rango"},
            {"name": "gender", "value": "Male"},
            {"name": "givenName", "value": "Rangero"},
            {"name": "signature", "value": "I am like Ronald McDonald"},
        ]}
    }

    #Mssing nickname
    user_wrong_2_request =  {"template": {
        "data": [
            {"name": "avatar", "value": "image3.jpg"},
            {"name": "birthday", "value": "2009-09-09"},
            {"name": "email", "value": "rango@gmail.com"},
            {"name": "familyName", "value": "Rango"},
            {"name": "gender", "value": "Male"},
            {"name": "givenName", "value": "Rangero"},
            {"name": "signature", "value": "I am like Ronald McDonald"},
        ]}
    }

    #Missing mandatory
    user_wrong_3_request = {"template": {
        "data": [
            {"name": "nickname", "value": "Rango"},
            {"name": "email", "value": "rango@gmail.com"},
            {"name": "familyName", "value": "Rango"},
            {"name": "gender", "value": "Male"},
            {"name": "givenName", "value": "Rangero"},
            {"name": "signature", "value": "I am like Ronald McDonald"},
        ]}
    }

    #Wrong address
    user_wrong_4_request = {"template": {
        "data": [
            {"name": "nickname", "value": "Rango"},
            {"name": "avatar", "value": "image3.jpg"},
            {"name": "address", "value": "Indonesia, Spain"},
            {"name": "birthday", "value": "2009-09-09"},
            {"name": "email", "value": "rango@gmail.com"},
            {"name": "familyName", "value": "Rango"},
            {"name": "gender", "value": "Male"},
            {"name": "givenName", "value": "Rangero"},
            {"name": "signature", "value": "I am like Ronald McDonald"},
        ]}
    }

    def setUp(self):
        super(UsersTestCase, self).setUp()
        self.url = resources.api.url_for(resources.Users,
                                         _external=False)

    def test_url(self):
        '''
        Checks that the URL points to the right resource
        '''
        #NOTE: self.shortDescription() shuould work.
        _url = '/forum/api/users/'
        print '('+self.test_url.__name__+')', self.test_url.__doc__,
        with resources.app.test_request_context(_url):
            rule = flask.request.url_rule
            view_point = resources.app.view_functions[rule.endpoint].view_class
            self.assertEquals(view_point, resources.Users)

    def test_get_users(self):
        '''
        Checks that GET users return correct status code and data format
        '''
        print '('+self.test_get_users.__name__+')', self.test_get_users.__doc__
        #Check that I receive status code 200
        resp = self.client.get(flask.url_for('users'))
        self.assertEquals(resp.status_code, 200)

        # Check that I receive a collection and adequate href
        data = json.loads(resp.data)['collection']
        self.assertEquals(resources.api.url_for(resources.Users,
                                                _external=False),
                          data['href'])

        #Check that template is correct
        template_data = data['template']['data']
        self.assertEquals(len(template_data), 13)
        for t_data in template_data:
            self.assertIn(('required' and 'prompt' and 'name'),
                          t_data)
            self.assertTrue(any(k in t_data for k in ('value', 'object')))
            self.assertIn(t_data['name'], ('nickname', 'address',
                                           'avatar', 'birthday',
                                           'email', 'familyName',
                                           'gender', 'givenName',
                                           'image', 'signature',
                                           'skype', 'telephone',
                                           'website'))
        #Check that links are correct
        links = data['links']
        self.assertEquals(len(links), 1)  # Just one link
        self.assertIn('prompt', links[0])
        self.assertEquals(links[0]['rel'], 'messages-all')
        self.assertEquals(links[0]['href'],
                          flask.url_for('messages', _external=False))

        #Check that items are correct.
        items = data['items']
        self.assertEquals(len(items), initial_users)
        for item in items:
            self.assertIn(flask.url_for('users', _external=False),
                          item['href'])
            self.assertIn('links', item)
            self.assertEquals(2, len(item['data']))
            for attribute in item['data']:
                self.assertIn(attribute['name'], ('nickname', 'registrationdate'))

    def test_get_users_mimetype(self):
        '''
        Checks that GET Messages return correct status code and data format
        '''
        print '('+self.test_get_users_mimetype.__name__+')', self.test_get_users_mimetype.__doc__

        #Check that I receive status code 200
        resp = self.client.get(self.url)
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp.headers.get('Content-Type',None),
                          COLLECTIONJSON+";"+FORUM_USER_PROFILE)

    def test_add_user(self):
        '''
        Checks that the user is added correctly

        '''
        print '('+self.test_add_user.__name__+')', self.test_add_user.__doc__

        # With a complete request
        resp = self.client.post(resources.api.url_for(resources.Users),
                                headers={'Content-Type': COLLECTIONJSON},
                                data=json.dumps(self.user_1_request)
                               )
        self.assertEquals(resp.status_code, 201)
        self.assertIn('Location', resp.headers)
        url = resp.headers['Location']
        resp2 = self.client.get(url)
        self.assertEquals(resp2.status_code, 200)

        #With just mandaaory parameters
        resp = self.client.post(resources.api.url_for(resources.Users),
                                headers={'Content-Type': COLLECTIONJSON},
                                data=json.dumps(self.user_2_request)
                               )
        self.assertEquals(resp.status_code, 201)
        self.assertIn('Location', resp.headers)
        url = resp.headers['Location']
        resp2 = self.client.get(url)
        self.assertEquals(resp2.status_code, 200)

    def test_add_user_missing_mandatory(self):
        '''
        Test that it returns error when is missing a mandatory data
        '''
        print '('+self.test_add_user_missing_mandatory.__name__+')', self.test_add_user_missing_mandatory.__doc__

        # Removing nickname
        resp = self.client.post(resources.api.url_for(resources.Users),
                                headers={'Content-Type': COLLECTIONJSON},
                                data=json.dumps(self.user_wrong_2_request)
                               )
        self.assertEquals(resp.status_code, 400)

        #Removing avatar
        resp = self.client.post(resources.api.url_for(resources.Users),
                                headers={'Content-Type': COLLECTIONJSON},
                                data=json.dumps(self.user_wrong_3_request)
                               )
        self.assertEquals(resp.status_code, 400)

    def test_add_existing_user(self):
        '''
        Testign that trying to add an existing user will fail

        '''
        print '('+self.test_add_existing_user.__name__+')', self.test_add_existing_user.__doc__
        resp = self.client.post(resources.api.url_for(resources.Users),
                                headers={'Content-Type': COLLECTIONJSON},
                                data=json.dumps(self.user_wrong_1_request)
                               )
        self.assertEquals(resp.status_code, 409)

    def test_add_bad_formmatted(self):
        '''
        Test that it returns error when address is bad formatted
        '''
        print '('+self.test_add_bad_formmatted.__name__+')', self.test_add_bad_formmatted.__doc__

        # Removing nickname
        resp = self.client.post(resources.api.url_for(resources.Users),
                                headers={'Content-Type': COLLECTIONJSON},
                                data=json.dumps(self.user_wrong_4_request)
                               )
        self.assertEquals(resp.status_code, 400)

    def test_wrong_type(self):
        '''
        Test that return adequate error if sent incorrect mime type
        '''
        print '('+self.test_wrong_type.__name__+')', self.test_wrong_type.__doc__
        resp = self.client.post(resources.api.url_for(resources.Users),
                                headers={'Content-Type': "application/json"},
                                data=json.dumps(self.user_1_request)
                               )
        self.assertEquals(resp.status_code, 415)

class UserTestCase (ResourcesAPITestCase):

    def setUp(self):
        super(UserTestCase, self).setUp()
        user1_nickname = 'AxelW'
        user2_nickname = 'Jacobino'
        self.url1 = resources.api.url_for(resources.User,
                                          nickname=user1_nickname,
                                          _external=False)
        self.url_wrong = resources.api.url_for(resources.User,
                                               nickname=user2_nickname,
                                               _external=False)
    def test_url(self):
        '''
        Checks that the URL points to the right resource
        '''
        #NOTE: self.shortDescription() shuould work.
        print '('+self.test_url.__name__+')', self.test_url.__doc__
        url = "/forum/api/users/AxelW/"
        with resources.app.test_request_context(url):
            rule = flask.request.url_rule
            view_point = resources.app.view_functions[rule.endpoint].view_class
            self.assertEquals(view_point, resources.User)

    def test_wrong_url(self):
        '''
        Checks that GET Message return correct status code if asking for an
        unexisting user.
        '''
        print '('+self.test_wrong_url.__name__+')', self.test_wrong_url.__doc__
        resp = self.client.get(self.url_wrong)
        self.assertEquals(resp.status_code, 404)

    def test_right_url(self):
        '''
        Checks that GET Message return correct status code if asking for an
        existing user.
        '''
        print '('+self.test_right_url.__name__+')', self.test_right_url.__doc__
        resp = self.client.get(self.url1)
        self.assertEquals(resp.status_code, 200)

    def test_get_user_mimetype(self):
        '''
        Checks that GET Messages return correct status code and data format
        '''
        print '('+self.test_get_user_mimetype.__name__+')', self.test_get_user_mimetype.__doc__

        #Check that I receive status code 200
        resp = self.client.get(self.url1)
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp.headers.get('Content-Type',None),
                          HAL+";"+FORUM_USER_PROFILE)

    def test_get_format(self):
        '''
        Checks that the format of user is correct

        '''
        print '('+self.test_get_format.__name__+')', self.test_get_format.__doc__
        resp = self.client.get(self.url1)
        self.assertEquals(resp.status_code, 200)
        data = json.loads(resp.data)

        attributes = ('nickname', 'registrationdate', '_links')
        self.assertEquals(len(data), 3)
        for data_attribute in data:
            self.assertIn(data_attribute, attributes)

        links = data["_links"]
        links_attributes = ("user:messages", "user:public-data",
                            "user:restricted-data", "curies", "self",
                            "collection", "delete")

        for links_attribute in links:
            self.assertIn(links_attribute, links_attributes)

        link_attributes = ("href", "profile", "type")
        for link_name, link in links.items():
            if link_name == "curies":
                continue
            else:
                for link_attribute in link:
                    self.assertIn(link_attribute, link_attributes)
                    if link_name == 'self' or link_name == 'delete':
                        self.assertEquals(link['href'], self.url1)
                        self.assertEquals(link['profile'], FORUM_USER_PROFILE)
                    elif link_name == 'user:messages':
                        self.assertEquals(link['href'],
                                            resources.api.url_for(
                                                resources.History,
                                                nickname='AxelW',
                                                _external=False))
                        self.assertEquals(link['profile'], FORUM_MESSAGE_PROFILE)
                        self.assertEquals(link['type'], COLLECTIONJSON)
                    elif link_name == "user:public-data":
                        self.assertEquals(link['href'],
                                            resources.api.url_for(
                                                resources.User_public,
                                                nickname='AxelW',
                                                _external=False))
                        self.assertEquals(link['profile'], FORUM_USER_PROFILE)
                        self.assertEquals(link['type'], HAL)
                    elif link_name == "user:restricted-data":
                        self.assertEquals(link['href'],
                                            resources.api.url_for(
                                                resources.User_restricted,
                                                nickname='AxelW',
                                                _external=False))
                        self.assertEquals(link['profile'], FORUM_USER_PROFILE)
                        self.assertEquals(link['type'], HAL)
                    elif link_name == "collection":
                        self.assertEquals(link['href'],
                                          resources.api.url_for(resources.Users, _external=False))
                        self.assertEquals(link['profile'], FORUM_USER_PROFILE)
                        self.assertEquals(link['type'], COLLECTIONJSON)

    def test_delete_user(self):
        '''
        Checks that Delete user return correct status code if corrected delete
        '''
        print '('+self.test_delete_user.__name__+')', self.test_delete_user.__doc__
        resp = self.client.delete(self.url1)
        self.assertEquals(resp.status_code, 204)
        resp2 = self.client.get(self.url1)
        self.assertEquals(resp2.status_code, 404)

    def test_delete_unexisting_user(self):
        '''
        Checks that Delete user return correct status code if given a wrong address
        '''
        print '('+self.test_delete_unexisting_user.__name__+')', self.test_delete_unexisting_user.__doc__
        resp = self.client.delete(self.url_wrong)
        self.assertEquals(resp.status_code, 404)

class HistoryTestCase (ResourcesAPITestCase):


    def setUp(self):
        super(HistoryTestCase, self).setUp()
        self.url1= resources.api.url_for(resources.History, nickname='AxelW',
                                         _external=False)
        self.messages1_number = 2
        self.url2= resources.api.url_for(resources.History, nickname='Mystery',
                                         _external=False)
        self.messages2_number = 2
        self.url3 = self.url1+'?length=1'
        self.messages3_number = 1
        self.url4 = self.url1+'?after=1362317481'
        self.messages4_number = 1
        self.url5 = self.url1+'?before=1362317481'
        self.messages5_number = 1
        self.url6 = self.url1+'?before=1362317481&after=1362217481'
        self.url_wrong= resources.api.url_for(resources.History, nickname='WRONG',
                                         _external=False)


    def test_url(self):
        '''
        Checks that the URL points to the right resource
        '''
        #NOTE: self.shortDescription() shuould work.
        print '('+self.test_url.__name__+')', self.test_url.__doc__,
        url = '/forum/api/users/AxelW/history/'
        with resources.app.test_request_context(url):
            rule = flask.request.url_rule
            view_point = resources.app.view_functions[rule.endpoint].view_class
            self.assertEquals(view_point, resources.History)

    def test_get_history_mimetype(self):
        '''
        Checks that GET Messages return correct status code and data format
        '''
        print '('+self.test_get_history_mimetype.__name__+')', self.test_get_history_mimetype.__doc__

        #Check that I receive status code 200
        resp = self.client.get(self.url1)
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp.headers.get('Content-Type',None),
                          COLLECTIONJSON+";"+FORUM_MESSAGE_PROFILE)

    def test_get_history_number_values(self):
        '''
        Checks that GET history return correct status code and number of values
        '''
        print '('+self.test_get_history_number_values.__name__+')', self.test_get_history_number_values.__doc__
        #I use this because I need the app context to use the api.url_for
        with resources.app.test_client() as client:
            resp = client.get(self.url1)
            self.assertEquals(resp.status_code, 200)
            data = json.loads(resp.data)['collection']
            self.assertIn('items', data)
            messages = data['items']
            self.assertEquals(len(messages), self.messages1_number)

            resp = client.get(self.url2)
            self.assertEquals(resp.status_code, 200)
            data = json.loads(resp.data)['collection']
            self.assertIn('items', data)
            messages = data['items']
            self.assertEquals(len(messages), self.messages2_number)

            resp = client.get(self.url3)
            self.assertEquals(resp.status_code, 200)
            data = json.loads(resp.data)['collection']
            self.assertIn('items', data)
            messages = data['items']
            self.assertEquals(len(messages), self.messages3_number)


    def test_get_history_timestamp_values(self):
        '''
        Checks that GET history return correct status code and format
        '''
        print '('+self.test_get_history_timestamp_values.__name__+')', self.test_get_history_timestamp_values.__doc__
        #I use this because I need the app context to use the api.url_for
        with resources.app.test_client() as client:
            resp = client.get(self.url4)
            self.assertEquals(resp.status_code, 200)
            data = json.loads(resp.data)['collection']
            self.assertIn('items', data)
            messages = data['items']
            self.assertEquals(len(messages), self.messages4_number)

            resp = client.get(self.url5)
            data = json.loads(resp.data)['collection']
            self.assertIn('items', data)
            messages = data['items']
            self.assertEquals(len(messages), self.messages5_number)

            resp = client.get(self.url6)
            self.assertEquals(resp.status_code, 404)

    def test_get_history_unknown_user(self):
        '''
        Checks that the system returns 404 when tryign to find history for unknown
        user.
        '''
        print '('+self.test_get_history_unknown_user.__name__+')', self.test_get_history_unknown_user.__doc__
        resp = self.client.get(self.url_wrong)
        self.assertEquals(resp.status_code, 404)

    def test_get_history(self):
        '''
        Checks that GET history return correct status code and number of values
        '''
        print '('+self.test_get_history.__name__+')', self.test_get_history.__doc__
        #I use this because I need the app context to use the api.url_for
        with resources.app.test_client() as client:
            resp = client.get(self.url1)
            self.assertEquals(resp.status_code, 200)
            data = json.loads(resp.data)['collection']
            collection_attributes = ('href', 'items', 'version', 'links', 'queries')
            self.assertEquals(len(data), 5)
            for collection_attribute in data:
                self.assertIn(collection_attribute, collection_attributes)


if __name__ == '__main__':
    print 'Start running tests'
    unittest.main()
