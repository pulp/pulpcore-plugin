# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Contains the manager class and exceptions for operations surrounding the creation,
update, and deletion on a Pulp user.
"""

import logging
import re

from pulp.server import config
from pulp.server.db.model.auth import User
from pulp.server.auth import cert_generator, principal, authorization
from pulp.server.auth.authorization import is_last_super_user, revoke_all_permissions_from_user
from pulp.server.exceptions import PulpDataException, DuplicateResource, InvalidValue, MissingResource
from pulp.server.managers import factory

import pulp.server.auth.password_util as password_util

# -- constants ----------------------------------------------------------------

_USER_LOGIN_REGEX = re.compile(r'^[\-_A-Za-z0-9]+$') # letters, numbers, underscore, hyphen

_LOG = logging.getLogger(__name__)

# -- classes ------------------------------------------------------------------

class UserManager(object):
    """
    Performs user related functions relating to CRUD operations.
    """

    def create_user(self, login, password=None, name=None, roles=None):
        """
        Creates a new Pulp user and adds it to specified to roles.

        @param login: login name / unique identifier for the user
        @type  login: str

        @param password: password for login credentials
        @type  password: str

        @param name: user's full name
        @type  name: str

        @param roles: list of roles user will belong to
        @type  notes: dict

        @raise DuplicateResource: if there is already a user with the requested login
        @raise InvalidValue: if any of the fields are unacceptable
        """

        existing_user = User.get_collection().find_one({'login' : login})
        if existing_user is not None:
            raise DuplicateResource(login)

        invalid_values = []

        if login is None or not is_user_login_valid(login):
            invalid_values.append('login')
        if name is not None and not isinstance(name, basestring):
            invalid_values.append('name')
        if roles is not None and not isinstance(roles, list):
            invalid_values.append('roles')

        if invalid_values:
            raise InvalidValue(invalid_values)

        # Use the login for user name if one was not specified
        name = name or login
        roles = roles or None

        # Encode plain-text password
        hashed_password = None
        if password:
            hashed_password = password_util.hash_password(password)

        # Creation
        create_me = User(login=login, password=hashed_password, name=name, roles=roles)
        User.get_collection().save(create_me, safe=True)

        # Retrieve the user to return the SON object
        created = User.get_collection().find_one({'login' : login})

        return created


    def delete_user(self, login):
        """
        Deletes the given user. Deletion of last superuser is not permitted.

        @param login: identifies the user being deleted
        @type  login: str

        @raise MissingResource: if the given user does not exist
        @raise InvalidValue: if login value is invalid
        """

        # Raise exception if login is invalid
        if login is None or not isinstance(login, basestring) or login == 'admin':
            raise InvalidValue(['login'])

        # Check whether user exists
        found = User.get_collection().find_one({'login' : login})
        if found is None:
            raise MissingResource(login)

        # Make sure user is not the last super user 
        if is_last_super_user(found): 
            raise PulpDataException(_("The last superuser [%s] cannot be deleted" % found['id']))
             
        # Revoke all permissions from the user
        revoke_all_permissions_from_user(login)
        
        User.get_collection().remove({'login' : login}, safe=True)



    def update_user(self, login, delta):
        """
        Updates the user. Following fields may be updated through this call:
        * password
        * name
        * roles

        Other fields found in delta will be ignored.

        @param login: identifies the user
        @type  login: str

        @param delta: list of attributes and their new values to change
        @type  delta: dict

        @raise MissingResource: if there is no user with login
        """

        user_coll = User.get_collection()

        user = user_coll.find_one({'login' : login})
        if user is None:
            raise MissingResource(login)

        # Check
        invalid_values = []
        if 'password' in delta:
            if not isinstance(delta['password'], basestring):
                invalid_values.append('password')
            else:
                user['password'] = password_util.hash_password(delta['password'])

        if 'name' in delta:
            if delta['name'] is not None and not isinstance(delta['name'], basestring):
                invalid_values.append('name')
            else:
                user['name'] = delta['name']

        if 'roles' in delta:
            if delta['roles'] is not None and not isinstance(delta['roles'], list):
                invalid_values.append('roles')
            else:
                user['roles'] = delta['roles']

        if invalid_values:
            raise InvalidValue(invalid_values)

        user_coll.save(user, safe=True)

        return user


    def find_all(self):
        """
        Returns serialized versions of all users in the database.

        @return: list of serialized users
        @rtype:  list of dict
        """
        all_users = list(User.get_collection().find())
        for user in all_users:
            user.pop('password')
        return all_users


    def find_by_login(self, login):
        """
        Returns a serialized version of the given user if it exists.
        If a user cannot be found with the given login, None is returned.

        @return: serialized data describing the user
        @rtype:  dict or None
        """
        user = User.get_collection().find_one({'login' : login})
        return user


    def find_by_id_list(self, login_list):
        """
        Returns serialized versions of all of the given users. Any
        login that does not refer to valid user are ignored and will not
        raise an error.

        @param login_list: list of logins
        @type  login_list: list of str

        @return: list of serialized users
        @rtype:  list of dict
        """
        users = list(User.get_collection().find({'id' : {'$in' : login_list}}))
        return users
    
    def ensure_admin(self):
        """
        This function ensures that there is at least one super user for the system.
        If no super users are found, the default admin user (from the pulp config)
        is looked up or created and added to the super users role.
        """
        super_users = authorization._get_users_belonging_to_role( 
                    authorization._get_role(authorization.super_user_role))
        if super_users:
            return
        default_login = config.config.get('server', 'default_login')
        user_manager = factory.user_manager()
        admin = user_manager.find_by_login(default_login)
        if admin is None:
            default_password = config.config.get('server', 'default_password')
            admin = user_manager.create_user(login=default_login, password=default_password)
        authorization.add_user_to_role(authorization.super_user_role, default_login)



    def generate_user_certificate(self):
        """
        Generates a user certificate for the currently logged in user.

        @return: certificate and private key, combined into a single string,
                 that can be used to identify the current user on subsequent calls
        @rtype:  str
        """

        # Get the currently logged in user
        user = principal.get_principal()
        key, certificate = cert_generator.make_admin_user_cert(user)
        return key + certificate


# -- functions ----------------------------------------------------------------

def is_user_login_valid(login):
    """
    @return: true if the login is valid; false otherwise
    @rtype:  bool
    """
    result = _USER_LOGIN_REGEX.match(login) is not None
    return result