/**
 * @fileOverview Forum administration dashboard. It utilizes the Forum API to 
                 handle user information (retrieve user list, edit user profile, 
                 as well as add and remove new users form the system). It also 
                 permits to list and remove user's messages.
 * @author &lt;a href="mailto:ivan@ee.oulu.fi">Ivan Sanchez Milara&lt;/a>
 * @version 1.0
 * 
 * NOTE: The documentation utilizes jQuery syntax to refer to classes and ids in
         the HTML code: # is utilized to refer to HTML elements ids while . is
         utilized to refer to HTML elements classes.
**/


/**** START CONSTANTS****/

/** 
 * Set this to true to activate the debugging messages. 
 * @constant {boolean}
 * @default 
 */
var DEBUG = true,

/** 
 * Collection+JSON mime-type 
 * @constant {string}
 * @default 
 */
COLLECTIONJSON = "application/vnd.collection+json",

/** 
 * HAL mime type
 * @constant {string}
 * @default 
 */
HAL = "application/hal+json",

/** 
 * Link to Users_profile
 * @constant {string}
 * @default 
 */
FORUM_USER_PROFILE = "/profiles/users",

/** 
 * Link to Messages_profile
 * @constant {string}
 * @default 
 */
FORUM_MESSAGE_PROFILE = "/profiles/messages",

/** 
 * Default datatype to be used when processing data coming from the server.
 * Due to JQuery limitations we should use json in order to process Collection+JSON
 * and HAL responses
 * @constant {string}
 * @default 
 */
DEFAULT_DATATYPE = "json",

/** 
 * Entry point of the application
 * @constant {string}
 * @default 
 */
ENTRYPOINT = "/forum/api/users/"; //Entrypoint: Resource Users

/**** END CONSTANTS****/


/**** START RESTFUL CLIENT****/

/**** Description of the functions that call Forum API by means of jQuery.ajax()
      calls. We have implemented one function per link relation in both profiles.
      Since we are not interesting in the whole API functionality, some of the
      functions does not do anything. Hence, those link relations are ignored
****/ 


/**
 * This function is the entrypoint to the Forum API.
 *
 * Associated rel attribute: Users Collection+JSON and users-all
 * 
 * Sends an AJAX GET request to retrive the list of all the users of the application
 * 
 * ONSUCCESS=> Show users in the #user_list. 
 *             After processing the response it utilizes the method {@link #appendUserToList}
 *             to append the user to the list.  
 *             Each user is an anchor pointing to the respective user url.
 * ONERROR => Show an alert to the user.
 *
 * @param {string} [apiurl = ENTRYPOINT] - The url of the Users instance.
**/
function getUsers(apiurl) {
    apiurl = apiurl || ENTRYPOINT;
    $("#mainContent").hide();
    return $.ajax({
        url: apiurl,
        dataType:DEFAULT_DATATYPE
    }).always(function(){
        //Remove old list of users
        //clear the form data hide the content information(no selected)
        $("#user_list").empty();
        $("#mainContent").hide();

    }).done(function (data, textStatus, jqXHR){
        if (DEBUG) {
            console.log ("RECEIVED RESPONSE: data:",data,"; textStatus:",textStatus);
        }
        //Extract the users
        users = data.collection.items;
        for (var i=0; i &lt; users.length; i++){
            var user = users[i];
            //Extract the nickname by getting the data values. Once obtained
            // the nickname use the method appendUserToList to show the user
            // information in the UI.
            //Data format example:
            //  [ { "name" : "nickname", "value" : "Mystery" },
            //    { "name" : "registrationdate", "value" : "2014-10-12" } ]
            var user_data = user.data;
            for (var j=0; j&lt;user_data.length;j++){
                if (user_data[j].name=="nickname"){
                    appendUserToList(user.href, user_data[j].value);
                }
            }
        }

        //Prepare the new_user_form to create a new user
        createFormFromTemplate(data.collection.href,data.collection.template,
                             "new_user_form",
                             {'createUser':users_collection_add_item});

    }).fail(function (jqXHR, textStatus, errorThrown){
        if (DEBUG) {
            console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown);
        }
        //Inform user about the error using an alert message.
        alert ("Could not fetch the list of users.  Please, try again");
    });
}

/*** FUNCTIONS FOR USER PROFILE ***/

/**
 * Sends an AJAX GET request to retrieve information related to user history.
 *
 * Associated rel attribute: messages 
 *
 * ONSUCCESS =>
 *   a.1) Check the number of messages received (data.collection.items) 
 *   a.2) Add the previous value to the #messageNumber input element (located in 
 *        #userHeader section).
 *   b.1) Iterate through all messages. 
 *   b.2) For each message in the history, access the message information by
 *        calling the corresponding Message instance (call {@link history_collection_get_item})
 *        The url of the message is obtained from the href attribute of the
 *        message item. 
 * ONERROR =>
 *    a)Show an *alert* informing the user that the target user history could not be retrieved
 *    b)Deselect current user calling {@link #deselectUser}.
 * @param {string} apiurl - The url of the History instance.
**/
    //TODO 3: Send the AJAX to retrieve the history information. 
    //        Do not implement the handlers yet, just show some DEBUG text in the console.
    //TODO 4: Implement the handlers for done() and fail() responses 
    
function user_messages(apiurl){
    return $.ajax({
        url: apiurl,
        dataType:DEFAULT_DATATYPE
    }).done(function (data, textStatus, jqXHR){
        if (DEBUG) {
            console.log ("RECEIVED RESPONSE: data:",data,"; textStatus:",textStatus);
        }
        //Fill number of messages
        var messages = data.collection.items;
        $("#messagesNumber").val(messages.length.toString());

        //Add message
        for (var i=0; i &lt; messages.length; i++) {
            var messageurl = messages[i].href;
            history_collection_get_item(messageurl);
        }

    }).fail(function (jqXHR, textStatus, errorThrown){
        if (DEBUG) {
            console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown);
        }
        if (jqXHR.status == 404) {
            //There is no messages for this user
            $("#messagesNumber").val("0");
            return;
        }
        //Inform the user that could not retrieve the history because an error different to status code
        alert ("Cannot retrieve the messages for the user");
        deselectUser();
    });
}

/**
 * This client does not support listing forum messages.
 * 
 * Associated rel attribute: messages-all
 * 
 * @param {string} apiurl - The url of the Messages instance.
**/
function user_messages_all(apiurl) {
    return; //THE CLIENT DOES NOT KNOW HOW TO HANDLE LIST OF MESSAGES
}

/**
 * This client does not support handling public user information
 *
 * Associated rel attribute: public-data
 * 
 * @param {string} apiurl - The url of the Public profile instance.
**/
function user_public_data(apiurl){
    return; // THE CLIENT DOES NOT SHOW USER PUBLIC DATA SUCH AVATAR OR IMAGE

}

/**
 * Sends an AJAX request to retrieve the restricted profile information:
 * {@link http://docs.pwpforumappcomplete.apiary.io/#reference/users/users-private-profile/get-user's-restricted-profile | User Restricted Profile}
 * 
 * Associated rel attribute: restricted-data
 * 
 * ONSUCCESS =>
 *  a) Extract all the links relations and its corresponding URLs (href)
 *  b) Create a form and fill it with attribute data (semantic descriptors) coming
 *     from the request body. The generated form should be embedded into #user_restricted_form.
 *     All those tasks are performed by the method {@link #fillFormWithHALData}
 *     b.1) If "user:edit" relation exists add its href to the form action attribute. 
 *          In addition make the fields editables and use template to add missing
 *          fields. 
 *  c) Add buttons to the previous generated form.
 *      c.1) If "user:delete" relation exists show the #deleteUserRestricted button
 *      c.2) If "user:edit" relation exists show the #editUserRestricted button
 *
 * ONERROR =>
 *   a)Show an alert informing the restricted profile could not be retrieved and
 *     that the data shown in the screen is not complete.
 *   b)Unselect current user and go to initial state by calling {@link #deselectUser}
 * 
 * @param {string} apiurl - The url of the Restricted Profile instance.
**/
function user_restricted_data(apiurl){
    return $.ajax({
            url: apiurl,
            dataType:DEFAULT_DATATYPE,
        }).done(function (data, textStatus, jqXHR){
            if (DEBUG) {
            console.log ("RECEIVED RESPONSE: data:",data,"; textStatus:",textStatus);
            }
            //Extract links
            var user_links = data._links;
            var template, resource_url = null;
            if ("user:delete" in user_links){
                resource_url = user_links["user:delete"].href; // User delete link
            }
            if ("user:edit" in user_links){
                resource_url = user_links["user:edit"].href;
                //Extract the template value
                template = data.template;
            }
            $form = fillFormWithHALData(resource_url, data, "user_restricted_form", template, ['nickname', 'template']);
            
            //Show the buttons()
            if ("user:delete" in user_links)
                $("#deleteUserRestricted").show();
            if ("user:edit" in user_links)
                $("#editUserRestricted").show();
        }).fail(function (jqXHR, textStatus, errorThrown){
            if (DEBUG) {
                console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown);
            }
            //Show an alert informing that I cannot get info from the user.
            alert ("Cannot extract all the information about this user from the server");
            deselectUser();
        });
}

/**
 * This client does not support this functionality.
 *
 * Associated rel attribute: parent
 *
 * @param {string} apiurl - The url of the Public profile instance.
**/
function user_parent(apiurl){
    return; //We do not process this information. 
}

/**
 * Sends an AJAX request to modify the restricted profile of a user, using PUT
 *
 * Associated rel attribute: edit
 *
 * ONSUCCESS =>
 *     a)Show an alert informing the user that the user information has been modified
 * ONERROR =>
 *     a)Show an alert informing the user that the new information was not stored in the databse
 * 
 * @param {string} apiurl - The url of the intance to edit. 
 * @param {object} body - An associative array containing a Collection+JSON template with
 * the new data of the target user
 * @see {@link https://github.com/collection-json/spec#23-template}
**/
function user_edit(apiurl, body){
    //TODO 3: Send an AJAX request to modify the restricted profile of a user
        // Do not implement the handlers yet, just show some DEBUG text in the console. 
        // Check users_collection_add_item for some hints.
        // Do not forget that:
        //   * To modify a User_restricted resource you must use the PUT method.
        //   * The contentType is CollectionJSON
        //   * You should not processData (processData:false)
        //   * The data you want to send in the entity body is obtained by 
        //     appliying the method JSON.stringify() to the given body
    //TODO 4: Implement the handlers successful and failures responses accordding to the function documentation.
    $.ajax({
        url: apiurl,
        type: "PUT",
        data:JSON.stringify(body),
        processData:false,
        contentType: COLLECTIONJSON
    }).done(function (data, textStatus, jqXHR){
        if (DEBUG) {
            console.log ("RECEIVED RESPONSE: data:",data,"; textStatus:",textStatus);
        }
        alert ("User information have been modified successfully");

    }).fail(function (jqXHR, textStatus, errorThrown){
        if (DEBUG) {
            console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown);
        }
        var error_message = $.parseJSON(jqXHR.responseText).message;
        alert ("Could not modify user information;\r\n"+error_message);
    });
}

/**
 * Sends an AJAX request to delete an user from the system. Utilizes the DELETE method.
 *
 * Associated rel attribute: delete
 *
 *ONSUCCESS =>
 *    a)Show an alert informing the user that the user has been deleted
 *    b)Reload the list of users: {@link #getUsers}
 *
 * ONERROR =>
 *     a)Show an alert informing the user that the new information was not stored in the databse
 *
 * @param {string} apiurl - The url of the intance to delete. 

**/
function user_delete(apiurl){
    $.ajax({
        url: apiurl,
        type: "DELETE",
    }).done(function (data, textStatus, jqXHR){
        if (DEBUG) {
            console.log ("RECEIVED RESPONSE: data:",data,"; textStatus:",textStatus);
        }
        alert ("The user information has been deleted from the database");
        //Update the list of users from the server.
        getUsers();

    }).fail(function (jqXHR, textStatus, errorThrown){
        if (DEBUG) {
            console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown);
        }
        alert ("The user information could not be deleted from the database");
    });
}


/*** FUNCTIONS FOR MESSAGE PROFILE ***/

/*** Note, the client is mainly utilized to manage users, not to manage
messages ***/

/**
 * @see {@link #getUsers}
**/
function message_users_all(apiurl){
    return getUsers(apiurl);
}

/**
 * This client does not support this functionality.
 *
 * Associated rel attribute: messages-all
 *
 * @param {string} apiurl - The url of the Messages list.
**/
function message_messages_all(apiurl){
    return; //THE CLIENT DOES NOT KNOW HOW TO HANDLE LIST OF MESSAGES
}

/**
 * This client does not support this functionality.
 *
 * Associated rel attribute: reply
 *
 * @param {string} apiurl - The url of the parent message.
 * @param {object} body - An associative array containing a Collection+JSON template with
 * information of the new message
 * @see {@link https://github.com/collection-json/spec#23-template}
**/
function message_reply(apiurl,body){
    return; //THE CLIENT DOES NOT KNOW HOW TO ADD A NEW MESSAGE
}

/**
 * This client does not support this functionality.
 *
 * Associated rel attribute: author
 *
 * @param {string} apiurl - The url of the User instance.
**/
function message_author(apiurl){
    return; //THE CLIEND DOES NOT KNOW TO HANDLE THIS RELATION.
}

/**
 * This client does not support this functionality.
 *
 * Associated rel attribute: messages-all
 *
 * @param {string} apiurl - The url of the Messages list.
**/
function message_collection(apiurl){
    return; //THE CLIENT DOES NOT KNOW HOW TO HANDLE A LIST OF MESSAGES
}

/**
 * This client does not support this functionality.
 *
 * Associated rel attribute: in-reply-to
 *
 * @param {string} apiurl - The url of the Message
**/
function message_in_reply_to(apiurl){
    return; //THE CLIENT DOES NOT KNOW HOW TO REPRESENT A HIERARHCY OF MESSAGEs

}

/*** FUNCTIONS FOR MESSAGES COLLECTION ***/

/*** NOTE: messages collection not utilized by the client. Does not know
     how to handle/render them ***/

/**
 * This client does not support this functionality.
 *
 * Associated action: Collection+JSON add item
 *
 * @param {string} apiurl - The url of the Message
 * @param {object} template - An associative array containing a Collection+JSON template with
 * the new information of the message
 * @see {@link https://github.com/collection-json/spec#23-template}
**/
function messages_collection_edit_item(apiurl, template){
    return; //THE CLIENT DOES NOT KNOW HOW TO HANDLE COLLECTION OF MESSAGES
}

/**
 * This client does not support this functionality.
 *
 * Associated action: Collection+JSON delete item
 *
 * @param {string} apiurl - The url of the Message
 * @see {@link https://github.com/collection-json/}
**/
function messages_collection_delete_item(apiurl){
    return; //THE CLIENT DOES NOT KNOW HOW TO HANDLE COLLECTION OF MESSAGES
}

/**
 * This client does not support this functionality.
 *
 * Associated action: Collection+JSON get item
 *
 * @param {string} apiurl - The url of the Message
 * @see {@link https://github.com/collection-json/}
**/
function messages_collection_get_item(apiurl){
    return; //THE CLIENT DOES NOT KNOW HOW TO HANDLE COLLECTION OF MESSAGES
}

/**
 * This client does not support this functionality.
 *
 * Associated action: Collection+JSON add item
 *
 * @param {string} apiurl - The url of the parent Messages collection
 * @see {@link https://github.com/collection-json/}
**/
function messages_collection_add_item(apiurl,template){
    return; //THE CLIENT DOES NOT KNOW HOW TO HANDLE COLLECTION OF MESSAGES
}

/*** FUNCTIONS FOR USERS COLLECTION ***/

/**
 * Edit existing user information. 
 * 
 * @see {@link #user_edit}
**/
function users_collection_edit_item(apiurl, template){
    return user_edit(apiurl, template);
}

/**
 * Delete existing user. 
 * 
 * @see {@link #user_delete}
**/    
function users_collection_delete_item(apiurl){
    return user_delete(apiurl);

}

/**
 * Sends an AJAX request to retrieve information related to a User {@link http://docs.pwpforumappcomplete.apiary.io/#reference/users/user}
 *
 * Associated action: Collection+JSON getitem
 *
 *  ONSUCCESS =>
 *              a) Fill basic user information: nickname and registrationdate.
 *                  Extract the information from the attribute input
 *              b) Extract associated link relations from the response
 *                    b.1) If user:delete: Show the #deleteUser button. Add the href
 *                        to the #user_form action attribute.
 *                    b.2) If user:edit: Show the #editUser button. Add the href
 *                        to the #user_form action attribute.
 *                    b.3) If user:restricted data: Call the function {@link #user_restricted_data} to 
 *                        extract the information of the restricted profile
 *                    b.4) If user:messages: Call the function {@link #user_messages} to extract
 *                        the messages history of the current user.  *
 *
 * ONERROR =>   a) Alert the user
 *              b) Unselect the user from the list and go back to initial state 
 *                (Call {@link deleselectUser})
 * 
 * @param {string} apiurl - The url of the User instance. 
**/
function users_collection_get_item(apiurl) {
    return $.ajax({
        url: apiurl,
        dataType:DEFAULT_DATATYPE,
        processData:false,
    }).done(function (data, textStatus, jqXHR){
        if (DEBUG) {
            console.log ("RECEIVED RESPONSE: data:",data,"; textStatus:",textStatus);
        }


        //Fill basic information from the user_basic_form 
        $("#nickname").val(data.nickname || "??");
        delete(data.nickname);
        $("#registrationdate").val(getDate(data.registrationdate || 0));
        delete(data.registrationdate);
        $("#messagesNumber").val("??");

        //Extract user information
        var user_links = data._links;
        //Extracts urls from links. I need to get if the different links in the
        //response.
        if ("user:restricted-data" in user_links) {
           var private_profile_url = user_links["user:restricted-data"].href; //Restricted profile
        }
        if ("user:messages" in user_links){
            var messages_url = user_links["user:messages"].href; // History
        }
        if ("user:delete" in user_links)
            var delete_link = user_links["user:delete"].href; // User delete linke
        if ("user:edit" in user_links)
            var edit_link = user_links["user:edit"].href;

         if (delete_link){
            $("#user_form").attr("action", delete_link);
            $("#deleteUser").show();
        }
        if (edit_link){
            $("#user_form").attr("action", edit_link);
            $("#editUser").show();
        }

        //Fill the user profile with restricted user profile. This method
        // Will call also to the list of messages.
        if (private_profile_url){
            user_restricted_data(private_profile_url);
        }
        //Get the history link and ask for history.
        if (messages_url){
            user_messages(messages_url);
        }
       

    }).fail(function (jqXHR, textStatus, errorThrown){
        if (DEBUG) {
            console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown);
        }
        //Show an alert informing that I cannot get info from the user.
        alert ("Cannot extract information about this user from the forum service.");
        //Deselect the user from the list.
        deselectUser();
    });
}

/**
 * Sends an AJAX request to create a new user {@link http://docs.pwpforumappcomplete.apiary.io/#reference/users/user}
 *
 * Associated action: Collection+JSON create item
 *
 *  ONSUCCESS =>
 *       a) Show an alert informing the user that the user information has been modified
 *       b) Append the user to the list of users by calling {@link #appendUserToList}
 *          * The url of the resource is in the Location header
 *          * {@link #appendUserToList} returns the li element that has been added.
 *       c) Make a click() on the added li element. To show the created user's information.
 *     
 * ONERROR =>
 *      a) Show an alert informing that the new information was not stored in the databse
 * 
 * @param {string} apiurl - The url of the User instance. 
 * @param {object} template - An associative array containing a Collection+JSON template with
 * the new user's information
 * @see {@link https://github.com/collection-json/spec#23-template}
**/   
function users_collection_add_item(apiurl,template){
    var userData = JSON.stringify(template);
    return $.ajax({
        url: apiurl,
        type: "POST",
        //dataType:DEFAULT_DATATYPE,
        data:userData,
        processData:false,
        contentType: COLLECTIONJSON,
    }).done(function (data, textStatus, jqXHR){
        if (DEBUG) {
            console.log ("RECEIVED RESPONSE: data:",data,"; textStatus:",textStatus);
        }
        alert ("User successfully added");
        //Add the user to the list and load it.
        $user = appendUserToList(jqXHR.getResponseHeader("Location"),nickname);
        $user.children("a").click();

    }).fail(function (jqXHR, textStatus, errorThrown){
        if (DEBUG) {
            console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown);
        }
        alert ("Could not create new user:"+jqXHR.responseJSON.message);
    });
}

/*** FUNCTIONS FOR HISTORY COLLECTION ***/

/**
 * This client does not support this functionality.
 *
 * Associated action: Collection+JSON edit item
 *
 * @param {string} apiurl - The url of the message to edit
 * @param {object} template - An associative array containing a Collection+JSON template with
 * the new information of the message
 * @see {@link https://github.com/collection-json/}
**/
function history_collection_edit_item(apiurl, template){
    return; //NOT SUPPORTED BY THE CLIENT. WE DO NOT WANT TO EDIT THE MESSAGES.
}

/**
 * Sends an AJAX request to remove an user from the system. Utilizes the DELETE method.
 *
 * Associated action: Collection+JSON delete item
 * ONSUCCESS=>
 *          a) Inform the user with an alert.
 *          b) Go to the initial state by calling the function {@link #reloadUserData} *
 *
 * ONERROR => Show an alert to the user
 *
 * @param {string} apiurl - The url of the Message
 * @see {@link https://github.com/collection-json/}
**/
    
function history_collection_delete_item(apiurl){
    //TODO 3: Send an AJAX request to remove the current message
        // Do not implement the handlers yet, just show some DEBUG text in the console.
        // You just need to send a $.ajax request of type "DELETE". No extra parameters
        //are required.
    //TODO 4
       //Implemente the handlers following the instructions from the function documentation.
    $.ajax({
        url: apiurl,
        type: "DELETE",
        dataType:DEFAULT_DATATYPE
    }).done(function (data, textStatus, jqXHR){
        if (DEBUG) {
            console.log ("RECEIVED RESPONSE: data:",data,"; textStatus:",textStatus);
        }
        alert("The message was deleted successfully");
        //Reload the user information, so messages are reloaded.
        reloadUserData();

    }).fail(function (jqXHR, textStatus, errorThrown){
        if (DEBUG) {
            console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown);
        }
        alert("Could not delete a message");
    });
}

/**
 * Sends an AJAX request to retrieve message information Utilizes the GET method.
 *
 * Associated action: Collection+JSON get item
 *
 * ONSUCCESS=>
 *          a) Extract message information from the response body. The response
 *             utilizes a HAL format.
 *          b) Show the message headline and articleBody in the UI. Call the helper
 *             method {@link appendMessageToList}
 *
 * ONERROR => Show an alert to the user
 *
 * @param {string} apiurl - The url of the Message
 * @see {@link https://github.com/collection-json/}
**/

function history_collection_get_item(apiurl){
    $.ajax({
        url: apiurl,
        dataType:DEFAULT_DATATYPE
    }).done(function (data, textStatus, jqXHR){
        if (DEBUG) {
            console.log ("RECEIVED RESPONSE: data:",data,"; textStatus:",textStatus);
        }
        var message_url = data._links.self.href;
        var headline = data.headline;
        var articleBody =  data.articleBody;
        appendMessageToList(message_url, headline, articleBody);

    }).fail(function (jqXHR, textStatus, errorThrown){
        if (DEBUG) {
            console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown);
        }
        alert("Cannot get information from message: "+ apiurl);
    });
}

/**** END RESTFUL CLIENT****/

/**** UI HELPERS ****/

/**** This functions are utilized by rest of the functions to interact with the
      UI ****/

/**
 * Append a new user to the #user_list. It appends a new &lt;li> element in the #user_list 
 * using the information received in the arguments.  
 *
 * @param {string} url - The url of the User to be added to the list
 * @param {string} nickname - The nickname of the User to be added to the list
 * @returns {Object} The jQuery representation of the generated &lt;li> elements.
**/
function appendUserToList(url, nickname) {
    var $user = $('&lt;li>').html('&lt;a class= "user_link" href="'+url+'">'+nickname+'&lt;/a>');
    //Add to the user list
    $("#user_list").append($user);
    return $user;
}

/**
 * Populate a form with the &lt;input> elements contained in the &lt;i>template&lt;/i> input parameter.
 * The action attribute is filled in with the &lt;i>url&lt;/i> parameter. Values are filled
 * with the default values contained in the template. It supports Collection+JSON
 * required extension to mark inputs with required property. 
 *
 * @param {string} url - The url of to be added in the action attribute
 * @param {Object} template - a Collection+JSON template ({@link https://github.com/collection-json/spec#23-template}) 
 * which is utlized to append &lt;input> elements in the form
 * @param {string} id - The id of the form is gonna be populated
**/
function createFormFromTemplate(url,template,id){
    $form=$('#'+ id);
    $form.attr("action",url);
    //Clean the forms
    $form_content=$(".form_content",$form);
    $form_content.empty();
    $("input[type='button']",$form).hide();
    if (template.data) {
        for (var i =0; i&lt;template.data.length; i++){
            var name = template.data[i].name;
            var input_id = "new_"+name+"_id";
            var value = template.data[i].value;
            var prompt = template.data[i].prompt;
            var required = template.data[i].required;
            $input = $('&lt;input type="text">&lt;/input>');
            $input.addClass("editable");
            $input.attr('name',name);
            $input.attr('id',input_id);
            $label_for = $('&lt;label>&lt;/label>');
            $label_for.attr("for",input_id);
            $label_for.text(name);
            $form_content.append($label_for);
            $form_content.append($input);
            if(value){
                $input.attr('value', value);
            }
            if(prompt){
                $input.attr('placeholder', prompt);
            }
            if(required){
                $input.prop('required',true);
                $label = $("label[for='"+$input.attr('id')+"']");
                $label.append(document.createTextNode("*"));
            }
            
        }
    }
}

/**
 * Populate a form with the &lt;input> elements contained in the &lt;i>data&lt;/i> parameter. 
 * The data.parameter name is the &lt;input> name attribute while the data.parameter 
 * value represents the &lt;input> value. All parameters are by default assigned as 
 * &lt;i>readonly&lt;/i>.
 * The action attribute is filled in with the &lt;i>url&lt;/i> parameter. 
 * If a template is provided, the &lt;input> parameters contained in the template
 * are set editable. Required &lt;input> fields are marked with the &lt;i>required&lt;/i> property.
 * If a template property does not have its &lt;input> counterpart it will create a new 
 * &lt;input> for that property.
 * 
 * NOTE: All buttons in the form are hidden. After executing this method adequate
 *       buttons should be shown using $(#button_name).show()
 *
 * @param {string} url - The url of to be added in the action attribute
 * @param {Object} data - An associative array formatted using HAL format ({@link https://tools.ietf.org/html/draft-kelly-json-hal-07})
 * Each element in the dictionary will create an &lt;input> element in the form. 
 * @param {string} id - The id of the form is gonna be populated
 * @param {Object} [template] - a Collection+JSON template ({@link https://github.com/collection-json/spec#23-template}) 
 * which is utlized to set the properties of the &lt;input> elements in the form, or
 * append missing ones. 
 * @param {Array} [exclude] - A list of attributes names from the &lt;i>data&lt;/i> parametsr
 * that are not converted in &lt;input> elements.
**/
function fillFormWithHALData(url,data,id,template,exclude){
    $form=$('#'+ id);
    $form.attr("action",url);
    //Clean the forms
    $form_content=$(".form_content",$form);
    $form_content.empty();
    $("input[type='button']",$form).hide();

    for (var attribute_name in data){
        if ($.inArray(attribute_name, exclude) != -1 || attribute_name == "_links")
            continue;
        var $input = $('&lt;input type="text">&lt;/input>');
        $input.attr('name',attribute_name);
        $input.attr('value', data[attribute_name]);
        $input.attr('id', attribute_name+"_id");
        $input.attr('readonly','readonly');
        $label_for = $('&lt;label>&lt;/label>');
        $label_for.attr("for", attribute_name+"_id");
        $label_for.text(attribute_name);
        $form_content.append($label_for);
        $form_content.append($input);
    }
    
    if (template &amp;&amp; template.data){
        for (var i =0; i&lt;template.data.length; i++){
            var t_attribute_name = template.data[i].name;
            var input_id = t_attribute_name + "_id";
            var prompt = template.data[i].prompt;
            var required = template.data[i].required;
            var value = template.data[i].value;
            var $template_input = null;
            //If the input already exists
            if ($("#" + input_id, $form).length !== 0) {
                $template_input = $("#" +input_id, $form);
            }
            //Otherwise create it.
            else {
                $template_input = $('&lt;input type="text">&lt;/input>');
                $template_input.attr('name',t_attribute_name);
                if(value){
                    $template_input.attr('value', value);
                }
                $template_input.attr('id',input_id);
                $template_label_for = $('&lt;label>&lt;/label>');
                $template_label_for.attr("for", t_attribute_name+"_id");
                $template_label_for.text(t_attribute_name);
                $form_content.append($template_label_for);
                $form_content.append($template_input);
            }
            $template_input.addClass("editable");
            if(prompt){
                $template_input.attr('placeholder', prompt);
            }
            if(required){
                $template_input.prop('required',true);
                var $label = $("label[for='"+$template_input.attr('id')+"']");
                $label.append(document.createTextNode("*"));
            }
            $template_input.removeAttr("readonly");
        }
    }
}

/**
 * Serialize the input values from a given form (jQuer instance) into a
 * Collection+JSON template.
 * 
 * @param {Object} $form - a jQuery instance of the form to be serailized
 * @returs {Object} An associative array in which each form &lt;input> is converted
 * into an element in the dictionary. It is encapsulate in a Collection+JSON template.
 * @see {@link https://github.com/collection-json/spec#23-template}
**/
function serializeFormTemplate($form){
    var envelope={'template':{
                                'data':[]
    }};
    // get all the inputs into an array.
    var $inputs = $form.find(".form_content input");
    $inputs.each(function(){
        var _data = {};
        _data.name = this.name;
        if (_data.name === "address"){
            _data.object = getAddress($(this).val());
        }
        else
            _data.value = $(this).val();
        envelope.template.data.push(_data);
    });
    return envelope;
}

/**
 * Add a new .message HTML element in the to the #messages_list &lt;div> element.
 * The format of the generated HTML is the following:
 * @example
 *  //&lt;div class='message'>
 *  //        &lt;form action='#'>
 *  //            &lt;div class="commands">
 *  //                &lt;input type="button" class="editButton editMessage" value="Edit"/>
 *  //                &lt;input type="button" class="deleteButton deleteMessage" value="Delete"/>
 *  //             &lt;/div>
 *  //             &lt;div class="form_content">
 *  //                &lt;input type=text class="headline">
 *  //                &lt;input type="textarea" class="articlebody">
 *  //             &lt;/div>  
 *  //        &lt;/form>
 *  //&lt;/div>
 *
 * @param {string} url - The url of the created message
 * @param {string} headline - The title of the new message
 * @param {string} articlebody - The body of the crated message. 
**/
function appendMessageToList(url, headline, articlebody) {
        
    var $message = $("&lt;div>").addClass('message').html(""+
                        "&lt;form action='"+url+"'>"+
                        "   &lt;div class='form_content'>"+
                        "       &lt;input type=text class='headline' value='"+headline+"' readonly='readonly'/>"+
                        "       &lt;div class='articlebody'>"+articlebody+"&lt;/div>"+
                        "   &lt;/div>"+
                        "   &lt;div class='commands'>"+
                        "        &lt;input type='button' class='deleteButton deleteMessage' value='Delete'/>"+
                        "   &lt;/div>" +
                        "&lt;/form>"
                    );
    //Append to list
    $("#messages_list").append($message);
}

/**
 * Helper method to be called before showing new user data information
 * It purges old user's data and hide all buttons in the user's forms (all forms
 * elements inside teh #userData)
 *
**/
function prepareUserDataVisualization() {
    
    //Remove all children from form_content
    $("#userData .form_content").empty();
    //Hide buttons
    $("#userData .commands input[type='button'").hide();
    //Reset all input in userData
    $("#userData input[type='text']").val("??");
    //Remove old messages
    $("#messages_list").empty();
    //Be sure that the newUser form is hidden
    $("#newUser").hide();
    //Be sure that user information is shown
    $("#userData").show();
    //Be sure that mainContent is shown
    $("#mainContent").show();
}

/**
 * Helper method to visualize the form to create a new user (#new_user_form)
 * It hides current user information and purge old data still in the form. It 
 * also shows the #createUser button.
**/
function showNewUserForm () {
    //Remove selected users in the sidebar
    deselectUser();

    //Hide the user data, show the newUser div and reset the form
    $("#userData").hide();
    var form =  $("#new_user_form")[0];
    form.reset();
    // Show butons
    $("input[type='button']",form).show();
    
    $("#newUser").show();
    //Be sure that #mainContent is visible.
    $("#mainContent").show();
}

/**
 * Helper method that unselects any user from the #user_list and go back to the
 * initial state by hiding the "#mainContent".
**/
function deselectUser() {
    $("#user_list li.selected").removeClass("selected");
    $("#mainContent").hide();
}

/**
 * Helper method to reload current user's data by making a new API call
 * Internally it makes click on the href of the selected user.
**/
function reloadUserData() {
    var selected = $("#user_list li.selected a");
    selected.click();
}

/**
 * Transform a date given in a UNIX timestamp into a more user friendly string
 * 
 * @param {number} timestamp - UNIX timestamp
 * @returns {string} A string representation of the UNIX timestamp with the 
 * format: 'dd.mm.yyyy at hh:mm:ss'
**/
function getDate(timestamp){
    // create a new javascript Date object based on the timestamp
    // multiplied by 1000 so that the argument is in milliseconds, not seconds
    var date = new Date(timestamp*1000);
    // hours part from the timestamp
    var hours = date.getHours();
    // minutes part from the timestamp
    var minutes = date.getMinutes();
    // seconds part from the timestamp
    var seconds = date.getSeconds();

    var day = date.getDate();

    var month = date.getMonth()+1;

    var year = date.getFullYear();

    // will display time in 10:30:23 format
    return day+"."+month+"."+year+ " at "+ hours + ':' + minutes + ':' + seconds;
}

/** 
 * Transforms an address with the format 'city, country' into a dictionary.
 * @param {string} input - The address to be converted into a dictionary with the
 * format 'city, country'
 * @returns {Object} a dictionary with the following format: 
 * {'object':{'addressLocality':locality, 'addressCountry':country}}
**/
function getAddress(address){
    var _address = address.split(",",2);
    return {'addressLocality':_address[0], 'addressCountry':_address[1]||"??"};

}
/**** END UI HELPERS ****/

/**** BUTTON HANDLERS ****/

/**
 * Shows in #mainContent the #new_user_form. Internally it calls to {@link #showNewUserForm}
 *
 * TRIGGER: #addUserButton
**/
function handleShowUserForm(event){
    if (DEBUG) {
        console.log ("Triggered handleShowUserForm");
    }
    //Show the form. Note that the form was updated when I apply the user collection
    showNewUserForm();
    return false;
}

/**
 * Uses the API to delete the currently selected user.
 *
 * TRIGGER: #deleteUser 
**/
function handleDeleteUser(event){
    //Extract the url of the resource from the form action attribute.
    if (DEBUG) {
        console.log ("Triggered handleDeleteUser");
    }

    var userurl = $(this).closest("form").attr("action");
    users_collection_delete_item(userurl);
}

/**
 * Uses the API to update the user's with the form attributes in the present form.
 *
 * TRIGGER: #editUser 
**/
function handleEditUser(event){
    if (DEBUG) {
        console.log ("Triggered handleEditUser");
    }
    var $form = $(this).closest("form");
    var body = serializeFormTemplate($form);
    var url = $form.attr("action");
    users_collection_edit_item(url, body);
    return false; //Avoid executing the default submit
}

/**
 * Uses the API to delete the restricted profile of the selected user.
 *
 * TRIGGER: #deleteRestrictedUser
**/
function handleDeleteUserRestricted(event){
    //Extract the url of the resource from the form action attribute.
    if (DEBUG) {
        console.log ("Triggered handleDeleteUserRestricted");
    }

    var user_restricted_url = $(this).closest("form").attr("action");
    user_delete(user_restricted_url);
}

/**
 * Uses the API to update the user's restricted profile with the form attributes in the present form.
 *
 * TRIGGER: #editRestrictedUser 
**/
function handleEditUserRestricted(event){
    //Extract the url of the resource from the form action attribute.
    if (DEBUG) {
        console.log ("Triggered handleDeleteUserRestricted");
    }
    var $form = $(this).closest("form");
    var body = serializeFormTemplate($form);
    var user_restricted_url = $(this).closest("form").attr("action");
    user_edit(user_restricted_url, body);
}

/**
 * Uses the API to create a new user with the form attributes in the present form.
 *
 * TRIGGER: #createUser 
**/
function handleCreateUser(event){
    if (DEBUG) {
        console.log ("Triggered handleCreateUser");
    }
    var $form = $(this).closest("form");
    var template = serializeFormTemplate($form);
    var url = $form.attr("action");
    users_collection_add_item(url, template);
    return false; //Avoid executing the default submit
}
/**
 * Uses the API to retrieve user's information from the clicked user. In addition, 
 * this function modifies the selected user in the #user_list (removes the .selected
 * class from the old user and add it to the current user)
 *
 * TRIGGER: click on #user_list li a 
**/
function handleGetUser(event) {
    if (DEBUG) {
        console.log ("Triggered handleGetUser");
    }
    //TODO 2
    // This event is triggered by an #user_list li a element. Hence, $(this)
    // is the &lt;a> that the user has pressed. $(this).parent() is the li element
    // containing such anchor.
    //
    // Use the method event.preventDefault() in order to avoid default action
    // for anchor links.
    //
    // Remove the class "selected" from the previous #user_list li element and
    // add it to the current #user_list li element. Remember, the current
    // #user_list li element is $(this).parent()
    //
    // Purge the forms by calling the function prepareUserDataVisualization()
    // 
    // Finally extract the href attribute from the current anchor ($(this))
    // and call the function users_collection_get_item(url) to make the corresponding 
    // HTTP call to the RESTful API. You can extract an HTML attribute using the
    // attr("attribute_name") method from JQuery.
    
    event.preventDefault();
    $("#user_list .selected").removeClass("selected");
    $(this).parent().addClass("selected");
    //Clean the forms.
    //Purge and show the existingUserData div.
    prepareUserDataVisualization();
    var url = $(this).attr("href");
    users_collection_get_item(url);
    return false; //IMPORTANT TO AVOID &lt;A> BUBLING
}


/**
 * Uses the API to delete the associated message
 *
 * TRIGGER: .deleteMessage
**/
function handleDeleteMessage(event){
    if (DEBUG) {
        console.log ("Triggered handleDeleteMessage");
    }
    //TODO 2:
    //  Extract the url of the resource to be deleted from the form action attribute.
    //  Call the method history_collection_delete_item(messageurl).
    //  Check handleDeleteUser for more hints.
    var messageurl = $(this).closest("form").attr("action");
    history_collection_delete_item(messageurl);
}

/**** END BUTTON HANDLERS ****/

/*** START ON LOAD ***/
//This method is executed when the webpage is loaded.
$(function(){

    //TODO 1: Add corresponding click handler to all HTML buttons
    // The handlers are:
    // #addUserButton -> handleShowUserForm
    // #deleteUser -> handleDeleteUser
    // #editUser -> handleEditUser
    // #deleteUserRestricted -> handleDeleteUserRestricted
    // #editUserRestricted -> handleEditUserRestricted
    // #createUser -> handleCreateUser
    alert("YOLO");
    // Check http://api.jquery.com/on/ for more help.
    $("#addUserButton").on("click",  handleShowUserForm);
    $("#deleteUser").on("click", handleDeleteUser);
    $("#editUser").on("click", handleEditUser);
    $("#deleteUserRestricted").on("click", handleDeleteUserRestricted);
    $("#editUserRestricted").on("click", handleEditUserRestricted);
    $("#createUser").on("click", handleCreateUser);
    alert("YOLO");
    
    //TODO 1: Add corresponding click handlers for .deleteMessage button and
    // #user_list li a anchors. Since these elements are generated dynamically
    // (they are not in the initial HTML code), you must use delegated events.
    // Recommend delegated elements are #messages_list for .deleteMessage buttons and
    // #user_list for "#user_list li a" anchors.
    // The handlers are:
    // .deleteMessage => handleDeleteMessage
    // #user_list li a => handleGetUser
    // More information for direct and delegated events from http://api.jquery.com/on/
    $("#user_list").on("click","li a",handleGetUser);
    $("#messages_list").on("click", ".deleteMessage", handleDeleteMessage);
    //Retrieve list of users from the server
    getUsers(ENTRYPOINT);
});
/*** END ON LOAD**/
