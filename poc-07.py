#!/usr/bin/python3
#
# https://github.com/OfflineIMAP/imapfw/wiki/sync-07
#
# HINT 01: the output of the run is wrong. Read it carefully.


from functools import total_ordering
from collections import UserList

@total_ordering
class Message(object):
    def __init__(self, uid=None, body=None, flags=['unread']):
        self.uid = uid
        self.body = body
        self.flags = flags

    def __repr__(self):
        return "<Message %s [%s] '%s'>"% (self.uid,
            ','.join(self.flags), self.body)

    def __eq__(self, other):
        return self.uid == other

    def __hash__(self):
        return hash(self.uid)

    def __lt__(self, other):
        return self.uid < other

    def identical(self, mess):
        return (mess.uid == self.uid and mess.body == self.body and
            mess.flags == self.flags)

class Messages(UserList):
    """Enable collections of messages the easy way."""
    pass


class Driver(object):
    def __init__(self, list_messages):
        self.messages = Messages(list_messages) # Fake the real data.

    def search(self):
        return self.messages


# Not a driver but APIs interesting here are similar.
class StateBackend(Driver):
    """Would run in a worker."""
    def __init__(self):
        self.messages = Messages() # Fake the real data.

class StateController(object):
    """State controller for a driver."""
    def __init__(self, driver):
        self.driver = driver
        self.state = StateBackend() # Would be an emitter.

    def search(self):
        changedMessages = Messages() # Collection of new, deleted and updated messages.
        print("search(): creating empty collection of messages: %s"% changedMessages)
        messages = self.driver.search() # Would be async.
        stateMessages = self.state.search() # Would be async.

        for message in messages:
            if message not in stateMessages:
                # Missing in the other side.
                changedMessages.append(message)
            else:
                pass # TODO: compare: did message change?
        return changedMessages


class Engine(object):
    """The engine."""
    def __init__(self, left, right):
        # Add the state controller to the chain of controllers of the drivers.
        # Driver will need to provide API to work on chained controllers.
        self.left = StateController(left)
        self.right = StateController(right)

    def run(self):
        leftMessages = self.left.search() # Would be async.
        rightMessages = self.right.search() # Would be async.

        print("New, deleted and updated messages")
        print("left: %s"% leftMessages)
        print("rght: %s"% rightMessages)


if __name__ == '__main__':

    # Messages
    m1r = Message(1, "1 body")
    m1l = Message(1, "1 body") # Same as m1r

    m2r = Message(2, "2 body")
    m2l = Message(2, "2 body", ['read']) # Same as m2r but read.

    m3r = Message(3, "3 body") # Not at left.

    m4l = Message(None, "4 body") # Not at right.

    leftMessages = Messages([m1l, m2l, m4l])
    rghtMessages = Messages([m1r, m2r, m3r])

    # Fill both sides with pre-existing data.
    left = Driver(leftMessages) # Fake those data.
    right = Driver(rghtMessages) # Fake those data.

    # Start engine.
    engine = Engine(left, right)
    print("Initial content of both sides:")
    print("rght:       %s"% engine.right.driver.messages)
    print("state rght: %s"% engine.right.state.messages)
    print("left:       %s"% engine.left.driver.messages)
    print("state left: %s"% engine.left.state.messages)

    print("\n# PASS 1")
    engine.run()
