# -*- coding: utf-8 -*-

""" This file is part of B{Domogik} project (U{http://www.domogik.org}).

License
=======

B{Domogik} is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

B{Domogik} is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Domogik. If not, see U{http://www.gnu.org/licenses}.

Plugin purpose
==============

Exceptions.

Implements
==========

- DomogikBaseError
- XplMessageError

@author:Frédéric Mantegazza <frederic.mantegazza@gbiloba.org>
@copyright: (C) 2012 Domogik project
@license: GPL(v3)
@organization: Domogik
"""


class DomogikBaseError(Exception):
    """ Base error class for all Domogik errors.
    """


class XplMessageError(DomogikBaseError):
    """ Invalid xPL message.
    """
