#!/usr/bin/env python
"""
_SetLocation_

MySQL implementation of Jobs.SetLocation
"""

__all__ = []
__revision__ = "$Id: SetLocation.py,v 1.1 2010/01/22 17:38:01 mnorman Exp $"
__version__ = "$Revision: 1.1 $"

from WMCore.Database.DBFormatter import DBFormatter

class SetLocation(DBFormatter):
    """
    _GetLocation_

    Retrieve all files that are associated with the given job from the
    database.
    """
    sql = """UPDATE wmbs_job SET location = (SELECT id FROM wmbs_location WHERE site_name = :location)
              WHERE id = :jobid"""

        
    def execute(self, jobid = None, location = None, bulkList = None, conn = None, transaction = False):
        """
        _execute_

        Execute the SQL for the given job ID and location
        """


        if bulkList:
            binds = bulkList
        else:
            binds = {'jobid': jobid, 'location': location}

        self.dbi.processData(self.sql, binds, conn = conn, transaction = transaction)
        return

