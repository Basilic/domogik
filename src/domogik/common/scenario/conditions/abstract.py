#!/usr/bin/python
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

@author: Maxence Dunnewind <maxence@dunnewind.net>
@copyright: (C) 2007-2009 Domogik project
@license: GPL(v3)
@organization: Domogik
"""

import json
from exceptions import ValueError


class AbstractCondition:
    """ This class provides base methods for the scenario conditions
    It must not be instanciated directly but need to be extended.
    A condition is a boolean expression composed of tests.
    Some useful methods to create and evaluate the condition are provided here.
    This class will be only extended by another one at the beginning. This structure of
    abstract class has been chosen to keep it coherent with tests and parameters,
    but usually nobody should need to create a new condition
    The condition is a JSON expression like :
    { "AND" : {
            "OR" : {
                "one-uuid" : {
                    "param_name_1" : {
                        "token1" : "value",
                        "token2" : "othervalue"
                    },
                    "param_name_2" : {
                        "token3" : "foo"
                    }
                },
                "another-uuid" : {
                    "param_name_1" : {
                        "token4" : "bar"
                    }
                }
            },
            "yet-another-uuid" : {
                "param_name_1" : {
                    "url" : "http://google.fr",
                    "interval" : "5"
                }
            }
        }
    }
    The UUID will be obtained by a query of the API in ordrer to keep a list of tests used.
    The worflow is :
        * The UI make a call to get the list of available tests and parameters. RINOR sends this list with,
        for each tests, the list of needed parameters.
        * The UI allows the user to create any boolean expression. When a user wants to create
        a new instance of some test, the UI call RINOR to say "I want a new instance of $TEST$",
        with $TEST$ the name of the test created. RINOR sends an answer with a generated UUID, at same time
        RINOR keeps a mapping of uuid and test's name. It is not needed to create the instance of the test at this time.
        * The UI lets user fill the parameters for each test
        * When the scenario is ready, the UI generates JSON and send it to RINOR
        * RINOR create all the instances of tests and map them to uuid
        * RINOR create a new Condition with the JSON and the list of uuids/tests, which are parsed by the condition itself
    """

    def __init__(self, log, name=None, condition=None, mapping=None, on_true=None):
        """ Create the instance
        @param log : A logger instance
        @param condition : A JSON expression
        @param mapping : a dictionnary of uuid => test instances
        @param on_true : what trigger to call if the condition evaluates to true
        """
        self._log = log
        self._name = name
        self._condition = condition
        self._mapping = mapping
        self._parsed_condition = None
        self._on_true = on_true
        self._set_condition_for_tests()

    def destroy(self):
        ret = []
        print(self._mapping)
        for (uid, test) in list(self._mapping.items()):
            if type(test) not in [str, unicode]: 
                test.destroy()
            ret.append(uid)
        return ret

    def set_condition(self, condition):
        """ Set the condition to  some JSON expression
        @param condition : A JSON expression
        """
        self._condition = condition

    def set_mapping(self, mapping):
        """ Set the mapping to some JSON expression
        @param mapping : A dictionnary of uuid: pointer to a test instance
        """
        self._mapping = mapping
        self._set_condition_for_tests()

    def get_mapping(self):
        """ Get the mapping for this condition
        @return : A dictionnary of uuid: pointer to a test instance
        """
        return self._mapping

    def _set_condition_for_tests(self):
        for (uid, test) in list(self._mapping.items()):
            test.set_condition(self)

    def __parse_boolean(self, json):
        """ Recursive method which returns a string which represent the boolean expression defined by a json
        @param json : a json expression which represents some boolean expression
            if json is a dict => just proceed
            if json is a tuple => it will be a key, dict => create a new dict from this
        """
        if type(json) == tuple:
            json = {json[0]: json[1]}
        if type(json) == dict:
            for k in list(json.keys()):
                v = json[k]
                if k in ["AND", "OR"]:
                    return "( {0} {1} {2} )".format(self.__parse_boolean(list(v.items())[0]), k.lower(), self.__parse_boolean(list(v.items())[1]))
                elif k == "NOT":
                    return "not {0}".format(self.__parse_boolean(v))
                elif type(v) == dict:
                    #declaration of tests
                    test = self._mapping[k]
                    test.fill_parameters(v)
                    return "self._mapping['{0}'].evaluate()".format(k)

    def get_parsed_condition(self):
        """Returns the parsed condition
        @return None if parse_condition as never called with a valid condition else the parsed condition
        """
        if self._parsed_condition is None:
            self._log.debug("get_parsed_condition called but parsed_condition is empty, try to parse condition first")
            self.parse_condition()
        return self._parsed_condition

    def parse_condition(self):
        """ Parse the JSON to create the list of tests, parametrize them, and create a boolean condition
        @return True if the parsing has been done correctly and everything is successfully initialized
        @raise ValueError if the JSON can't be correctly parsed
        """
        try:
            _j = json.loads(self._condition)
        except ValueError as e:
            self._log.warning("Can't load json : {0}".format(self._condition))
            raise e
        self._parsed_condition = self.__parse_boolean(_j)
        return True

    def eval_condition(self):
        """ Evaluate the condition.
        @raise ValueError if no parsed condition is avaiable
        @return a boolean representing result of evaluation
        """
        if self._parsed_condition is None:
            return None
        res = eval(self._parsed_condition)
        self._log.info("Evaluating condition {0} result = {1}".format(self._name, res))
        self._log.debug("_parsed condition is : {0}, eval is {1}".format(self._parsed_condition, eval(self._parsed_condition)))
        if res:
            # call the callback
            self._on_true(self._name)
            return True
        else:
            return False
