#!/usr/bin/env python
"""
Poll request manager for new work
"""
__all__ = []
__revision__ = "$Id: WorkQueueManagerReqMgrPoller.py,v 1.17 2010/07/20 13:42:34 swakef Exp $"
__version__ = "$Revision: 1.17 $"

import re
import os
import os.path
import time

from WMCore.WorkerThreads.BaseWorkerThread import BaseWorkerThread
from WMCore.WMSpec.WMWorkload import WMWorkloadHelper

class WorkQueueManagerReqMgrPoller(BaseWorkerThread):
    """
    Polls for requests
    """
    def __init__(self, reqMgr, queue, config):
        """
        Initialise class members
        """
        BaseWorkerThread.__init__(self)
        self.reqMgr = reqMgr
        self.wq = queue
        self.config = config

    def algorithm(self, parameters):
        """
        retrive workload (workspec) from RequestManager
	    """
        self.wq.logger.info("Contacting Request manager for more work")
        work = 0
        try:
            workLoads = self.retrieveWorkLoadFromReqMgr()
        except Exception, ex:
            workLoads = {}
            msg = "Error contacting RequestManager: %s" % str(ex)
            self.wq.logger.warning(msg)
        if workLoads:
            self.wq.logger.debug(workLoads)
            #TODO: Same functionality as WorkQueue.pullWork() - combine
            for reqName, workLoadUrl in workLoads.items():
                try:
                    self.wq.logger.info("Processing request %s" % reqName)
                    wmspec = WMWorkloadHelper()
                    wmspec.load(workLoadUrl)
                    units = self.wq._splitWork(wmspec)

                    # Process each request in a transaction - isolate bad req's
                    with self.wq.transactionContext():
                        for unit in units:
                            self.wq._insertWorkQueueElement(unit, requestName = reqName)
                        try:
                            self.reqMgr.putWorkQueue(reqName, 
                                            self.config.get('monitorURL', 'NoMonitor'))
                        except Exception, ex:
                            self.wq.logger.error("Unable to update ReqMgr state: %s" % str(ex))
                            self.wq.logger.error('Request "%s" not queued' % reqName)
                            raise

                    work += len(units)
                except Exception, ex:
                    self.wq.logger.exception("Error processing request %s" % reqName)

        self.logger.info("%s element(s) obtained from RequestManager" % work)

        try:
            self.reportToReqMgr()
        except:
            pass # error message already logged
        return


    def retrieveCondition(self):
        """
        _retrieveCondition_
        set true or false for given retrieve condion
        i.e. thredshod on workqueue 
        """
        return True

    def retrieveWorkLoadFromReqMgr(self):
        """
        retrieveWorkLoad
        retrieve list of url for workloads.
        """
        #requestName = "TestRequest"
        #requestName = 'rpw_100122_145356'
        #wmAgentUrl = "ralleymonkey.com"
        result = self.reqMgr.getAssignment(self.config.get('teamName', ''))
        return result

    # Reuse this when bulk updates supported
#    def sendConfirmationToReqMgr(self, requestNames):
#        """
#        """
#        #TODO: allow bulk post
#        for requestName in requestNames:
#            result = self.reqMgr.postAssignment(requestName)

    def reportToReqMgr(self):
        """Report request status to ReqMgr"""
        now = int(time.time())
        updated = []

        elements = self.wq.status(reqMgrUpdateNeeded = True)
        if not elements:
            return

        for ele in elements:
            try:
                status = self.reqMgrStatus(ele)
                if status:
                    self.reqMgr.reportRequestStatus(ele['RequestName'],
                                                    status)
                if ele['PercentComplete'] or ele['PercentSuccess']:
                    args = {'percent_complete' : ele['PercentComplete'],
                            'percent_success' : ele['PercentSuccess']}
                    self.reqMgr.reportRequestProgress(ele['RequestName'],
                                                      **args)

                updated.append(ele['Id'])

            except RuntimeError, ex:
                msg = "Error updating ReqMgr about element %s: %s"
                self.wq.logger.warning(msg % (ele['Id'], str(ex)))
        try:
            self.wq.setReqMgrUpdate(now, updated)
        except StandardError:
            msg = "Error saving reqMgr status update to db"
            self.wq.logger.exception(msg)

    def reqMgrStatus(self, ele):
        """Map WorkQueue Status to that reported to ReqMgr"""
        status = None
        if ele.isComplete():
            status = 'completed'
        elif ele.isFailed():
            status = 'failed'
        elif ele.isRunning():
            status = 'running'
        return status