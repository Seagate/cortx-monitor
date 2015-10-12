#!/usr/bin/python
"""
    Fake LDAP server
"""
import tempfile
import sys
from twisted.application import service, internet
from twisted.internet import reactor
from twisted.internet.protocol import ServerFactory
from twisted.python.components import registerAdapter

from ldaptor.interfaces import IConnectedLDAPEntry
from ldaptor.protocols.ldap.ldapserver import LDAPServer
from ldaptor.ldiftree import LDIFTreeEntry
from twisted.python import log
from threading import Thread
from schema import COM, ORG, PEOPLE, USERS1, USERS2


class Tree:
    def __init__(self, path='/tmp'):
        dirname = tempfile.mkdtemp('.ldap', 'test-server', '/tmp')
        self.db = LDIFTreeEntry(dirname)
        self.init_db()

    def init_db(self):
        """
            Add subtrees to the top entry
        """
        com = self.db.addChild(COM[0], COM[1])
        org = com.addChild(ORG[0], ORG[1])
        people1 = org.addChild(PEOPLE[0], PEOPLE[1])
        people2 = org.addChild(PEOPLE[2], PEOPLE[3])
        people3 = org.addChild(PEOPLE[4], PEOPLE[5])
        for user in USERS1:
                people2.addChild(user[0], user[1])
        for user in USERS2:
                people3.addChild(user[0], user[1])


class LDAPServerFactory(ServerFactory):
    """
        Store ldap tree using Factory
    """
    protocol = LDAPServer

    def __init__(self, root):
        self.root = root

if __name__ == '__main__':
    log.startLogging(sys.stdout)
    # Initialize LDAP tree
    tree = Tree()
    # Register LDAP Factory
    registerAdapter(lambda x: x.root,
                    LDAPServerFactory,
                    IConnectedLDAPEntry)

    # Start LDAP Server
    log.msg('Starting LDAP Server')
    factory = LDAPServerFactory(tree.db)
    application = service.Application("ldaptor-server")
    myService = service.IServiceCollection(application)
    reactor.listenTCP(389, factory)
    Thread(target=reactor.run, args=(False,)).start()
