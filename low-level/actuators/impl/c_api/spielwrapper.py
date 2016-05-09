"""
 ****************************************************************************
 Filename:          spielwrapper.py
 Description:       C data structures for creating Mero Spiel objects 
                    (Derived from m0spiel tool)
 Creation Date:     5/05/2016
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from mero import *
from ctypes import *

from framework.utils.service_logging import logger


class Fid(Structure):
     """struct m0_fid"""
     _fields_ = [("f_container", c_uint64),
                 ("f_key", c_uint64)]

     def __str__(self):
         return "<" + hex(self.f_container)[:-1] + ":" + str(self.f_key) + ">"

class NetXprt(Structure):
     """struct m0_net_xprt"""
     _fields_ = [('nx_name', c_char_p),
                 ('nx_ops', c_void_p)]

class ReqhInitArgs(Structure):
     """struct m0_reqh_init_args"""
     _fields_ = [('rhia_dtm', c_void_p), ('rhia_db', c_void_p),
                 ('rhia_mdstore', c_void_p), ('rhia_pc', c_void_p),
                 ('rhia_fid', POINTER(Fid))]

class FsStats(Structure):
     _fields_ = [('fs_free', c_uint64),
                 ('fs_total', c_uint64)]


def require(**params):
    """It will be executed before annotated function. Helper takes a dictionary
        where key is parameter name and value is required parameter type. If all
        parameters pass type checking then the target function will be called,
        otherwise TypeError will be raised with error message containing information
        about invalid parameter.
 
        Example of usage:
        @require(fid=Fid)
        service_init(self, fid)
    """
    def check_types(func, params=params):
        def modified(*args, **kw):
            arg_names = func.func_code.co_varnames
            kw.update(zip(arg_names, args))
            for name, type in params.iteritems():
                param = kw[name]
                param_valid = param is None or isinstance(param, type)
                if not param_valid:
                    raise TypeError("Parameter '{0}' should be of type '{1}'"
                                    .format(name, type.__name__))
            return func(**kw)
        return modified
    return check_types

def call(func, *args):
    """call function func with *args"""
    try:
        rc = func(*args)
        if rc != 0:
            logger.exception("Mero function call failed: %d" % rc)
    except Exception as ae:
        logger.exception(ae)

class SpielWrapper:
    """Taken from mero's m0spiel tool and will probably be in flux"""
    def __init__(self, mero_path):
        self.mero = CDLL(mero_path)
        self.mero.malloc.restype = c_void_p

        self.spiel       = None
        self.ha_session  = None
        self.ha_conn     = None
        self.rpc_machine = None
        self.reqh        = None
        self.buffer_pool = None
        self.domain      = None
        self.m0          = None

    def spiel_init(self, ha_ep, client_ep):
        try:
            self.client_ep = c_char_p(client_ep)
            self.ha_ep = c_char_p(ha_ep)
            self.__m0_init()
            self.__net_domain_init()
            self.__net_buffer_pool_setup()
            self.__reqh_setup()
            self.__rpc_machine_init()
            self.__ha_session_init()
            self.__spiel_init()
        except Exception as ae:
            logger.exception(ae)

    def spiel_fini(self):
        """Clean up and free mem"""
        if self.spiel:
            self.mero.m0_spiel_fini(self.spiel)
            self.__free(self.spiel)
 
        if self.ha_session:
            self.mero.m0_ha_state_fini()
            self.mero.m0_rpc_session_destroy(self.ha_session, ~0L)
            self.__free(self.ha_session)
 
        if self.ha_conn:
            self.mero.m0_rpc_conn_destroy(self.ha_conn, ~0L)
            self.__free(self.ha_conn)
 
        if self.rpc_machine:
            self.mero.m0_rpc_machine_fini(self.rpc_machine)
            self.__free(self.rpc_machine)
 
        if self.reqh:
            self.mero.m0_reqh_services_terminate(self.reqh);
            self.mero.m0_reqh_fini(self.reqh)
            self.__free(self.reqh)
             
        if self.buffer_pool:
            self.mero.m0_rpc_net_buffer_pool_cleanup(self.buffer_pool)
            self.__free(self.buffer_pool)
 
        if self.domain:
            self.mero.m0_net_domain_fini(self.domain)
            self.__free(self.domain)
         
        if self.m0:
            self.mero.m0_fini(self.m0)
            self.__free(self.m0)
 
    def rconfc_start(self):
        return self.mero.m0_spiel_rconfc_start(self.spiel)
 
    def rconfc_stop(self):
        self.mero.m0_spiel_rconfc_stop(self.spiel)
 
    @require(profile=str)
    def cmd_profile_set(self, profile):
        return self.mero.m0_spiel_cmd_profile_set(self.spiel, profile)
 
    @require(fid=Fid, stats=FsStats)
    def filesystem_stats_fetch(self, fid, stats):
        return self.mero.m0_spiel_filesystem_stats_fetch(self.spiel,
                                                         byref(fid),
                                                         byref(stats))
    def __m0_init(self):
        logger.info("m0 size: %s" % m0__size())
        m0 = self.__malloc(m0__size())
        call(self.mero.m0_init, m0)
        self.m0 = m0
 
    def __net_domain_init(self):
        domain = self.__malloc(m0_net_domain__size())
        xprt = NetXprt.in_dll(self.mero, 'm0_net_lnet_xprt')
        call(self.mero.m0_net_domain_init, domain, pointer(xprt))
        self.domain = domain
 
    def __net_buffer_pool_setup(self):
        buffer_pool = self.__malloc(m0_net_buffer_pool__size())
        call(self.mero.m0_rpc_net_buffer_pool_setup, self.domain, buffer_pool,
            c_uint32(2), # nr bufs
            c_uint32(1)) # nr TMs
        self.buffer_pool = buffer_pool
 
    def __reqh_setup(self):
        reqh = self.__malloc(m0_reqh__size())
        reqh_args = ReqhInitArgs()
 
        reqh_args.rhia_fid = pointer(Fid(0x7200000000000001, 5)) # process-5
 
        reqh_args.rhia_dtm = 1
        reqh_args.rhia_mdstore = 1 # dummy value
 
        call(self.mero.m0_reqh_init, reqh, byref(reqh_args))
        self.__free(reqh_args)
        self.mero.m0_reqh_start(reqh)
        rms = self.__malloc(m0_reqh_service__size())
        rms_p = cast(rms, c_void_p)
        call(self.mero.m0_reqh_service_setup, rms_p, self.mero.m0_rms_type,
             reqh, None, byref(spiel_rms_fid))
        self.reqh = reqh
 
    def __rpc_machine_init(self):
        rpc_machine = self.__malloc(m0_rpc_machine__size())
        call(self.mero.m0_rpc_machine_init, rpc_machine, self.domain,
             self.client_ep, self.reqh, self.buffer_pool,
             c_uint(~0),      # M0_BUFFER_ANY_COLOUR
             c_uint(1 << 17), # M0_RPC_DEF_MAX_RPC_MSG_SIZE (128 KB)
             c_uint(2))       # M0_NET_TM_RECV_QUEUE_DEF_LEN
        self.rpc_machine = rpc_machine
 
    def __ha_session_init(self):
        self.ha_conn = self.__malloc(m0_rpc_conn__size())
        self.ha_session = self.__malloc(m0_rpc_session__size())
        call(self.mero.m0_rpc_client_connect, self.ha_conn, self.ha_session,
             self.rpc_machine, self.ha_ep, None,
             2) # max_rpcs_in_flight
        self.mero.m0_ha_state_init(self.ha_session)
 
    def __spiel_init(self):
        spiel = self.__malloc(m0_spiel__size())
        call(self.mero.m0_spiel_init, spiel, self.reqh)
        self.spiel = spiel
 
    def __malloc(self, size):
        ptr = self.mero.malloc(size) 
        memset(ptr, 0, size)
        return ptr
 
    def __free(self, ptr):
        self.mero.free(ptr)
