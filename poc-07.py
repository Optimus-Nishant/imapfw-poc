#!/usr/bin/python3
#
# https://github.com/OfflineIMAP/imapfw/wiki/sync-07


from functools import total_ordering
from collections import UserList

@total_ordering
class Message(object):
    """Fake the real Message class."""
    def __init__(self, uid=None, body=None, flags=None):
        self.uid = uid
        self.body = body
        self.flags = {'read': False, 'important': False}

    def __repr__(self):
        return "<Message %s [%s] '%s'>"% (self.uid, self.flags, self.body)

    def __eq__(self, other):
        return self.uid == other

    def __hash__(self):
        return hash(self.uid)

    def __lt__(self, other):
        return self.uid < other

    def identical(self, mess):
        if mess.uid != self.uid:
            return False
        if mess.body != self.body:
            return False
        if mess.flags != self.flags:
            return False

        return True # Identical

    def markImportant(self):
        self.flags['important'] = True

    def markRead(self):
        self.flags['read'] = True

    def unmarkImportant(self):
        self.flags['important'] = False

    def unmarkRead(self):
        self.flags['read'] = False


class Messages(UserList):
    """Enable collections of messages the easy way."""
    pass #TODO: implement collection comparison.


#TODO: fake writes on disk.
class Driver(object):
    """Fake a driver."""
    def __init__(self, list_messages):
        self.messages = Messages(list_messages) # Fake the real data.

    def search(self):
        return self.messages

    def update(self, messages):
        """Update the storage.
        messages: is the collection of messages we have to create, update
        or remove."""

        """
        Bug: If we provide try to update leftside first it will be updated as per right side changes provided by Engine. 
             For Example: m2l is marked read and m2r is unread. Now when we are first trying to update left side 
             with changes. We are making it unread on both the side.
             Where as if we first update right side we will have m2l as well as m2r as read.
             same goes for removal. Lets say there is m4l but m4r is missing . So what should we do should we remove m4l
             or what.
        """
        for message in messages:
            if message not in self.messages:
                self.messages.append(message)  #Adding new message to the sel.messages storage
            else: 
                for s_message  in self.messages:            
                    if message.uid == s_message.uid and message.identical(s_message):
                        break   
                        """
                        Message found in self.messages and is identical. 
                        No need to search for message in self.messages and hence get out of loop
                        """
                    elif message.uid == s_message.uid and not message.identical(s_message):
                        """
                        Updating the message.
                        """
                        s_message.body = message.body
                        s_message.flags = message.flags
                        break     
        
# Not a driver but APIs interesting here are similar.
#TODO: fake reads and writes on disk.
class StateBackend(Driver):
    """Would run in a worker."""
    def __init__(self):
        self.messages = Messages() # Fake the real data.

    def update(self,mess):
        self.messages = mess

    """
        StateBackend Must Contain MetaData for last synced messages rather than messages.
        For now we are putting messages. WE HAVE TO LATER THINK OF ITS IMPLEMENTATION.
    """

class StateController(object):
    """State controller for a driver.

    Notice each state controller owns a driver and is the stranger of the other
    side.

    The state controller is supposed to communicate with:
        - our driver;
        - the engine;
        - our state backend;
        - their state backend (read-only).
        #Comment Nishant : I think State Controller is supposed to communicate with thier state backend 
        (write - Only)
    """

    def __init__(self, driver):
        self.driver = driver # The driver we own.
        self.state = StateBackend() # Would be an emitter.

    def update(self, theirMessages, theirstate):
        """Update this side with the messages from the other side."""
        self.driver.update(theirMessages)
        theirstate.update(self.driver.messages)

    def search(self):
        """Explore our messages. Only return changes since previous sync."""

        changedMessages = Messages() # Collection of new, deleted and updated messages.
        messages = self.driver.search() # Would be async.
        stateMessages = self.state.search() # Would be async.

        for message in messages:
            if message not in stateMessages:
                # Missing in the other side.
                changedMessages.append(message)
            else:
                for stateMessage in stateMessages:
                    if message.uid == stateMessage.uid:
                        if not message.identical(stateMessage):
                            changedMessages.append(message)
                            break #There is no point of iterating further.

        for stateMessage in stateMessages:
            if stateMessage not in messages:
                # TODO: mark message as destroyed from real repository.
                changedMessages.append(message)

        return changedMessages


class Engine(object):
    """The engine."""
    def __init__(self, left, right):
        # Add the state controller to the chain of controllers of the drivers.
        # Driver will need to provide API to work on chained controllers.
        self.left = StateController(left)
        self.right = StateController(right)

    def debug(self, title):
        print('\n')
        print(title)
        print("rght:       %s"% self.right.driver.messages)
        print("state rght: %s"% self.right.state.messages)
        print("left:       %s"% self.left.driver.messages)
        print("state left: %s"% self.left.state.messages)

    def run(self):
        leftMessages = self.left.search() # Would be async.
        rightMessages = self.right.search() # Would be async.

        print("New, deleted and updated messages")
        print("left: %s"% leftMessages)
        print("rght: %s"% rightMessages)

        self.left.update(rightMessages,self.right.state)
        self.right.update(leftMessages,self.left.state)


if __name__ == '__main__':

    # Messages
    m1r = Message(1, "1 body")
    m1l = Message(1, "1 body") # Same as m1r

    m2r = Message(2, "2 body")
    m2l = Message(2, "2 body")
    m2l.markRead()              # Same as m2r but read.

    m3r = Message(3, "3 body") # Not at left.

    m4l = Message(None, "4 body") # Not at right.

    leftMessages = Messages([m1l, m2l, m4l])
    rghtMessages = Messages([m1r, m2r, m3r])

    # Fill both sides with pre-existing data.
    left = Driver(leftMessages) # Fake those data.
    right = Driver(rghtMessages) # Fake those data.

    # Start engine.
    engine = Engine(left, right)
    engine.debug("Initial content of both sides:")

    print("\n# PASS 1")
    engine.run()
    engine.debug("Run of PASS 1: done.")

    print("\n# PASS 2")
    engine.run()
    engine.debug("Run of PASS 2: done.")

    #TODO: PASS 3 with changed messages.
