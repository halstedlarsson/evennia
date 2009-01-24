"""
These commands typically are to do with building or modifying Objects.
"""
from src.objects.models import Object, Attribute
# We'll import this as the full path to avoid local variable clashes.
import src.flags
from src import ansi

def cmd_teleport(command):
    """
    Teleports an object somewhere.
    """
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("Teleport where/what?")
        return

    eq_args = command.command_argument.split('=', 1)
    
    # The quiet switch suppresses leaving and arrival messages.
    if "quiet" in command.command_switches:
        tel_quietly = True
    else:
        tel_quietly = False

    # If we have more than one entry in our '=' delimited argument list,
    # then we're doing a @tel <victim>=<location>. If not, we're doing
    # a direct teleport, @tel <destination>.
    if len(eq_args) > 1:
        # Equal sign teleport.
        victim = Object.objects.standard_objsearch(source_object, eq_args[0])
        # Use standard_objsearch to handle duplicate/nonexistant results.
        if not victim:
            return

        destination = Object.objects.standard_objsearch(source_object, eq_args[1])
        # Use standard_objsearch to handle duplicate/nonexistant results.
        if not destination:
            return

        if victim.is_room():
            source_object.emit_to("You can't teleport a room.")
            return

        if victim == destination:
            source_object.emit_to("You can't teleport an object inside of itself!")
            return
        source_object.emit_to("Teleported.")
        victim.move_to(destination, quiet=tel_quietly)
    else:
        # Direct teleport (no equal sign)
        target_obj = Object.objects.standard_objsearch(source_object, 
                                                    command.command_argument)
        # Use standard_objsearch to handle duplicate/nonexistant results.
        if not target_obj:
            return

        if target_obj == source_object:
            source_object.emit_to("You can't teleport inside yourself!")
            return
        source_object.emit_to("Teleported.")
            
        source_object.move_to(target_obj, quiet=tel_quietly)

def cmd_alias(command):
    """
    Assigns an alias to a player object for ease of paging, etc.
    """
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("Alias whom?")
        return
    
    eq_args = command.command_argument.split('=', 1)
    
    if len(eq_args) < 2:
        source_object.emit_to("Alias missing.")
        return
    
    target_string = eq_args[0]
    new_alias = eq_args[1]
    
    # An Object instance for the victim.
    target = Object.objects.standard_objsearch(source_object, target_string)
    # Use standard_objsearch to handle duplicate/nonexistant results.
    if not target:
        source_object.emit_to("I can't find that player.")
        return
  
    old_alias = target.get_attribute_value('ALIAS')
    duplicates = Object.objects.player_alias_search(source_object, new_alias)
    if not duplicates or old_alias.lower() == new_alias.lower():
        # Either no duplicates or just changing the case of existing alias.
        if source_object.controls_other(target):
            target.set_attribute('ALIAS', new_alias)
            source_object.emit_to("Alias '%s' set for %s." % (new_alias, 
                                                    target.get_name()))
        else:
            source_object.emit_to("You do not have access to set an alias for %s." % 
                                                   (target.get_name(),))
    else:
        # Duplicates were found.
        source_object.emit_to("Alias '%s' is already in use." % (new_alias,))
        return

def cmd_wipe(command):
    """
    Wipes an object's attributes, or optionally only those matching a search
    string.
    """
    source_object = command.source_object
    attr_search = False

    if not command.command_argument:    
        source_object.emit_to("Wipe what?")
        return

    # Look for a slash in the input, indicating an attribute wipe.
    attr_split = command.command_argument.split("/", 1)

    # If the splitting by the "/" character returns a list with more than 1
    # entry, it's an attribute match.
    if len(attr_split) > 1:
        attr_search = True
        # Strip the object search string from the input with the
        # object/attribute pair.
        searchstr = attr_split[1]
    else:
        searchstr = command.command_argument

    target_obj = Object.objects.standard_objsearch(source_object, attr_split[0])
    # Use standard_objsearch to handle duplicate/nonexistant results.
    if not target_obj:
        return

    if attr_search:
        # User has passed an attribute wild-card string. Search for name matches
        # and wipe.
        attr_matches = target_obj.attribute_namesearch(searchstr, 
                                                       exclude_noset=True)
        if attr_matches:
            for attr in attr_matches:
                target_obj.clear_attribute(attr.get_name())
            source_object.emit_to("%s - %d attributes wiped." % (
                                                        target_obj.get_name(), 
                                                        len(attr_matches)))
        else:
            source_object.emit_to("No matching attributes found.")
    else:
        # User didn't specify a wild-card string, wipe entire object.
        attr_matches = target_obj.attribute_namesearch("*", exclude_noset=True)
        for attr in attr_matches:
            target_obj.clear_attribute(attr.get_name())
        source_object.emit_to("%s - %d attributes wiped." % (target_obj.get_name(), 
                                                   len(attr_matches)))

def cmd_set(command):
    """
    Sets flags or attributes on objects.
    """
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("Set what?")
        return
  
    # Break into target and value by the equal sign.
    eq_args = command.command_argument.split('=', 1)
    if len(eq_args) < 2:
        # Equal signs are not optional for @set.
        source_object.emit_to("Set what?")
        return
    
    victim = Object.objects.standard_objsearch(source_object, eq_args[0])
    # Use standard_objsearch to handle duplicate/nonexistant results.
    if not victim:
        return

    if not source_object.controls_other(victim):
        source_object.emit_to(defines_global.NOCONTROL_MSG)
        return

    attrib_args = eq_args[1].split(':', 1)
    if len(attrib_args) > 1:
        # We're dealing with an attribute/value pair.
        attrib_name = attrib_args[0].upper()
        splicenum = eq_args[1].find(':') + 1
        attrib_value = eq_args[1][splicenum:]
        
        # In global_defines.py, see NOSET_ATTRIBS for protected attribute names.
        if not Attribute.objects.is_modifiable_attrib(attrib_name) and not source_object.is_superuser():
            source_object.emit_to("You can't modify that attribute.")
            return
        
        if attrib_value:
            # An attribute value was specified, create or set the attribute.
            verb = 'set'
            victim.set_attribute(attrib_name, attrib_value)
        else:
            # No value was given, this means we delete the attribute.
            verb = 'cleared'
            victim.clear_attribute(attrib_name)
        source_object.emit_to("%s - %s %s." % (victim.get_name(), attrib_name, verb))
    else:
        # Flag manipulation form.
        flag_list = eq_args[1].split()
        
        for flag in flag_list:
            flag = flag.upper()
            if flag[0] == '!':
                # We're un-setting the flag.
                flag = flag[1:]
                if not src.flags.is_modifiable_flag(flag):
                    source_object.emit_to("You can't set/unset the flag - %s." % (flag,))
                else:
                    source_object.emit_to('%s - %s cleared.' % (victim.get_name(), 
                                                                flag.upper(),))
                    victim.set_flag(flag, False)
            else:
                # We're setting the flag.
                if not src.flags.is_modifiable_flag(flag):
                    source_object.emit_to("You can't set/unset the flag - %s." % (flag,))
                else:
                    source_object.emit_to('%s - %s set.' % (victim.get_name(), 
                                                            flag.upper(),))
                    victim.set_flag(flag, True)

def cmd_find(command):
    """
    Searches for an object of a particular name.
    """
    source_object = command.source_object
    can_find = source_object.has_perm("genperms.builder")

    if not command.command_argument:
        source_object.emit_to("No search pattern given.")
        return
    
    searchstring = command.command_argument
    results = Object.objects.global_object_name_search(searchstring)

    if len(results) > 0:
        source_object.emit_to("Name matches for: %s" % (searchstring,))
        for result in results:
            source_object.emit_to(" %s" % (result.get_name(fullname=True),))
        source_object.emit_to("%d matches returned." % (len(results),))
    else:
        source_object.emit_to("No name matches found for: %s" % (searchstring,))

def cmd_create(command):
    """
    Creates a new object of type 'THING'.
    """
    source_object = command.source_object
    
    if not command.command_argument:
        source_object.emit_to("You must supply a name!")
    else:
        # Create and set the object up.
        # TODO: This dictionary stuff is silly. Feex.
        odat = {"name": command.command_argument, 
                "type": 3, 
                "location": source_object, 
                "owner": source_object}
        new_object = Object.objects.create_object(odat)
        
        source_object.emit_to("You create a new thing: %s" % (new_object,))
    
def cmd_cpattr(command):
    """
    Copies a given attribute to another object.

    @cpattr <obj>/<attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
    @cpattr <obj>/<attr> = <obj1> [,<obj2>,<obj3>,...]
    @cpattr <attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
    @cpattr <attr> = <obj1>[,<obj2>,<obj3>,...]
    """
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("What do you want to copy?")
        return

    # Split up source and target[s] via the equals sign.
    eq_args = command.command_argument.split('=', 1)

    if len(eq_args) < 2:
        # There must be both a source and a target pair for cpattr
        source_object.emit_to("You have not supplied both a source and a target(s).")
        return

    # Check that the source object and attribute exists, by splitting the eq_args 'source' entry with '/'
    source = eq_args[0].split('/', 1)
    source_string = source[0].strip()
    source_attr_string = source[1].strip().upper()

    # Check whether src_obj exists
    src_obj = Object.objects.standard_objsearch(source_object, source_string)
    
    if not src_obj:
        source_object.emit_to("Source object does not exist.")
        return
        
    # Check whether src_obj has src_attr
    src_attr = src_obj.attribute_namesearch(source_attr_string)
    
    if not src_attr:
        source_object.emit_to("Source object does not have attribute: %s" + source_attr_string)
        return
    
    # For each target object, check it exists
    # Remove leading '' from the targets list.
    targets = eq_args[1].strip().split(',')

    for target in targets:
        tar = target.split('/', 1)
        tar_string = tar[0].strip()
        tar_attr_string = tar[1].strip().upper()

        tar_obj = Object.objects.standard_objsearch(source_object, tar_string)

        # Does target exist?
        if not tar_obj:
            source_object.emit_to("Target object does not exist: " + tar_string)
            # Continue if target does not exist, but give error on this item
            continue

        # If target attribute is not given, use source_attr_string for name
        if tar_attr_string == '':
            tar_attr_string = source_attr_string

        # Set or update the new attribute on the target object
        src_attr_contents = src_obj.get_attribute_value(source_attr_string)
        tar_obj.set_attribute(tar_attr_string, src_attr_contents)
        source_object.emit_to("%s - %s set." % (tar_obj.get_name(), 
                                                tar_attr_string))

def cmd_nextfree(command):
    """
    Returns the next free object number.
    """   
    nextfree = Object.objects.get_nextfree_dbnum()
    command.source_object.emit_to("Next free object number: #%s" % (nextfree,))
    
def cmd_open(command):
    """
    Handle the opening of exits.
    
    Forms:
    @open <Name>
    @open <Name>=<Dbref>
    @open <Name>=<Dbref>,<Name>
    """
    source_object = command.source_object
    
    if not command.command_argument:
        source_object.emit_to("Open an exit to where?")
        return
        
    eq_args = command.command_argument.split('=', 1)
    exit_name = eq_args[0]
    
    if len(exit_name) == 0:
        source_object.emit_to("You must supply an exit name.")
        return
        
    # If we have more than one entry in our '=' delimited argument list,
    # then we're doing a @open <Name>=<Dbref>[,<Name>]. If not, we're doing
    # an un-linked exit, @open <Name>.
    if len(eq_args) > 1:
        # Opening an exit to another location via @open <Name>=<Dbref>[,<Name>].
        comma_split = eq_args[1].split(',', 1)
        destination = Object.objects.standard_objsearch(source_object, 
                                                            comma_split[0])
        # Use standard_objsearch to handle duplicate/nonexistant results.
        if not destination:
            return

        if destination.is_exit():
            source_object.emit_to("You can't open an exit to an exit!")
            return

        odat = {"name": exit_name, 
                "type": 4, 
                "location": source_object.get_location(), 
                "owner": source_object, 
                "home": destination}
        new_object = Object.objects.create_object(odat)

        source_object.emit_to("You open the an exit - %s to %s" % (
                                                        new_object.get_name(),
                                                        destination.get_name()))
        if len(comma_split) > 1:
            second_exit_name = ','.join(comma_split[1:])
            odat = {"name": second_exit_name, 
                    "type": 4, 
                    "location": destination, 
                    "owner": source_object, 
                    "home": source_object.get_location()}
            new_object = Object.objects.create_object(odat)
            source_object.emit_to("You open the an exit - %s to %s" % (
                                            new_object.get_name(),
                                            source_object.get_location().get_name()))

    else:
        # Create an un-linked exit.
        odat = {"name": exit_name, 
                "type": 4, 
                "location": source_object.get_location(), 
                "owner": source_object, 
                "home": None}
        new_object = Object.objects.create_object(odat)

        source_object.emit_to("You open an unlinked exit - %s" % (new_object,))
        
def cmd_chown(command):
    """
    Changes the ownership of an object. The new owner specified must be a
    player object.

    Forms:
    @chown <Object>=<NewOwner>
    """
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("Change the ownership of what?")
        return

    eq_args = command.command_argument.split('=', 1)
    target_name = eq_args[0]
    owner_name = eq_args[1]    

    if len(target_name) == 0:
        source_object.emit_to("Change the ownership of what?")
        return

    if len(eq_args) > 1:
        target_obj = Object.objects.standard_objsearch(source_object, target_name)
        # Use standard_objsearch to handle duplicate/nonexistant results.
        if not target_obj:
            return

        if not source_object.controls_other(target_obj):
            source_object.emit_to(defines_global.NOCONTROL_MSG)
            return

        owner_obj = Object.objects.standard_objsearch(source_object, owner_name)
        # Use standard_objsearch to handle duplicate/nonexistant results.
        if not owner_obj:
            return
        if not owner_obj.is_player():
            source_object.emit_to("Only players may own objects.")
            return
        if target_obj.is_player():
            source_object.emit_to("You may not change the ownership of player objects.")
            return

        target_obj.set_owner(owner_obj)
        source_object.emit_to("%s now owns %s." % (owner_obj, target_obj))
    else:
        # We haven't provided a target.
        source_object.emit_to("Who should be the new owner of the object?")
        return
    
def cmd_chzone(command):
    """
    Changes an object's zone. The specified zone may be of any object type, but
    will typically be a THING.

    Forms:
    @chzone <Object>=<NewZone>
    """
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("Change the zone of what?")
        return

    eq_args = command.command_argument.split('=', 1)
    target_name = eq_args[0]
    zone_name = eq_args[1]    

    if len(target_name) == 0:
        source_object.emit_to("Change the zone of what?")
        return

    if len(eq_args) > 1:
        target_obj = Object.objects.standard_objsearch(source_object, target_name)
        # Use standard_objsearch to handle duplicate/nonexistant results.
        if not target_obj:
            return

        if not source_object.controls_other(target_obj):
            source_object.emit_to(defines_global.NOCONTROL_MSG)
            return

        # Allow the clearing of a zone
        if zone_name.lower() == "none":
            target_obj.set_zone(None)
            source_object.emit_to("%s is no longer zoned." % (target_obj))
            return
        
        zone_obj = Object.objects.standard_objsearch(source_object, zone_name)
        # Use standard_objsearch to handle duplicate/nonexistant results.
        if not zone_obj:
            return

        target_obj.set_zone(zone_obj)
        source_object.emit_to("%s is now in zone %s." % (target_obj, zone_obj))

    else:
        # We haven't provided a target zone.
        source_object.emit_to("What should the object's zone be set to?")
        return

def cmd_link(command):
    """
    Sets an object's home or an exit's destination.

    Forms:
    @link <Object>=<Target>
    """
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("Link what?")
        return

    eq_args = command.command_argument.split('=', 1)
    target_name = eq_args[0]
    dest_name = eq_args[1]    

    if len(target_name) == 0:
        source_object.emit_to("What do you want to link?")
        return

    if len(eq_args) > 1:
        target_obj = Object.objects.standard_objsearch(source_object, target_name)
        # Use standard_objsearch to handle duplicate/nonexistant results.
        if not target_obj:
            return

        if not source_object.controls_other(target_obj):
            source_object.emit_to(defines_global.NOCONTROL_MSG)
            return

        # If we do something like "@link blah=", we unlink the object.
        if len(dest_name) == 0:
            target_obj.set_home(None)
            source_object.emit_to("You have unlinked %s." % (target_obj,))
            return

        destination = Object.objects.standard_objsearch(source_object, dest_name)
        # Use standard_objsearch to handle duplicate/nonexistant results.
        if not destination:
            return

        target_obj.set_home(destination)
        source_object.emit_to("You link %s to %s." % (target_obj, destination))

    else:
        # We haven't provided a target.
        source_object.emit_to("You must provide a destination to link to.")
        return

def cmd_unlink(command):
    """
    Unlinks an object.
    
    @unlink <Object>
    """
    source_object = command.source_object
    
    if not command.command_argument:    
        source_object.emit_to("Unlink what?")
        return
    else:
        target_obj = Object.objects.standard_objsearch(source_object,
                                                      command.command_argument)
        # Use standard_objsearch to handle duplicate/nonexistant results.
        if not target_obj:
            return

        if not source_object.controls_other(target_obj):
            source_object.emit_to(defines_global.NOCONTROL_MSG)
            return

        target_obj.set_home(None)
        source_object.emit_to("You have unlinked %s." % (target_obj.get_name(),))

def cmd_dig(command):
    """
    Creates a new object of type 'ROOM'.
    
    @dig <Name>
    """
    source_object = command.source_object
    roomname = command.command_argument
    
    if not roomname:
        source_object.emit_to("You must supply a name!")
    else:
        # Create and set the object up.
        odat = {"name": roomname, 
                "type": 2, 
                "location": None, 
                "owner": source_object}
        new_object = Object.objects.create_object(odat)
        
        source_object.emit_to("You create a new room: %s" % (new_object,))

def cmd_name(command):
    """
    Handle naming an object.
    
    @name <Object>=<Value>
    """
    source_object = command.source_object
    
    if not command.command_argument:    
        source_object.emit_to("What do you want to name?")
        return
    
    eq_args = command.command_argument.split('=', 1)
    
    if len(eq_args) < 2:
        source_object.emit_to("Name it what?")
        return
    
    # Only strip spaces from right side in case they want to be silly and
    # have a left-padded object name.
    new_name = eq_args[1].rstrip()
    
    if len(eq_args) < 2 or eq_args[1] == '':
        source_object.emit_to("What would you like to name that object?")
    else:
        target_obj = Object.objects.standard_objsearch(source_object, eq_args[0])
        # Use standard_objsearch to handle duplicate/nonexistant results.
        if not target_obj:
            return
        
        ansi_name = ansi.parse_ansi(new_name, strip_formatting=True)
        source_object.emit_to("You have renamed %s to %s." % (target_obj, 
                                                              ansi_name))
        target_obj.set_name(new_name)

def cmd_description(command):
    """
    Set an object's description.
    """
    source_object = command.source_object
    
    if not command.command_argument:    
        source_object.emit_to("What do you want to describe?")
        return
    
    eq_args = command.command_argument.split('=', 1)
    
    if len(eq_args) < 2:
        source_object.emit_to("How would you like to describe that object?")
        return

    target_obj = Object.objects.standard_objsearch(source_object, eq_args[0])
    # Use standard_objsearch to handle duplicate/nonexistant results.
    if not target_obj:
        return

    if not source_object.controls_other(target_obj):
        source_object.emit_to(defines_global.NOCONTROL_MSG)
        return

    new_desc = eq_args[1]
    if new_desc == '':
        source_object.emit_to("%s - DESCRIPTION cleared." % target_obj)
        target_obj.set_description(None)
    else:
        source_object.emit_to("%s - DESCRIPTION set." % target_obj)
        target_obj.set_description(new_desc)

def cmd_destroy(command):
    """
    Destroy an object.
    """
    source_object = command.source_object
    switch_override = False
       
    if not command.command_argument:    
        source_object.emit_to("Destroy what?")
        return
    
    # Safety feature. Switch required to delete players and SAFE objects.
    if "override" in command.command_switches:
        switch_override = True
        
    target_obj = Object.objects.standard_objsearch(source_object,
                                                   command.command_argument)
    # Use standard_objsearch to handle duplicate/nonexistant results.
    if not target_obj:
        return
    
    if target_obj.is_player():
        if source_object.id == target_obj.id:
            source_object.emit_to("You can't destroy yourself.")
            return
        if not switch_override:
            source_object.emit_to("You must use @destroy/override on players.")
            return
        if target_obj.is_superuser():
            source_object.emit_to("You can't destroy a superuser.")
            return
    elif target_obj.is_going() or target_obj.is_garbage():
        source_object.emit_to("That object is already destroyed.")
        return
    
    source_object.emit_to("You destroy %s." % target_obj.get_name())
    target_obj.destroy()
