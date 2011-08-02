'''
Created on Jul 28, 2011

@author: sdaubin
'''

import collections

AgentConfig = collections.namedtuple('AgentConfig', ['all_settings','server_settings','apdex_t','apdex_f','sampling_rate','transaction_tracer','transaction_name_limit'])
TransactionTracerConfig = collections.namedtuple('TransactionTracerConfig', ['enabled','transaction_threshold','record_sql','stack_trace_threshold'])

_config_defaults = {"apdex_t":0.5,"sampling_rate":0,
                    "transaction_tracer.enabled":True,                    
                    "transaction_tracer.transaction_threshold":"apdex_f",
                    "transaction_tracer.record_sql":"obfuscated",
                    "transaction_tracer.stack_trace_threshold":0.5,
                    "transaction_name.limit":500}

def create_configuration(config_dict={}):
    c = _config_defaults.copy() # clone the defaults
    c.update(config_dict) # merge in the user settings
    
    tt_settings = TransactionTracerConfig(enabled=c["transaction_tracer.enabled"],
                        transaction_threshold=_process_transaction_threshold(c,c["transaction_tracer.transaction_threshold"]),
                        record_sql=_process_record_sql(c["transaction_tracer.record_sql"]),
                        stack_trace_threshold=c["transaction_tracer.stack_trace_threshold"]) 
    
    
    return AgentConfig(server_settings=config_dict,all_settings=c,
                       apdex_t=c["apdex_t"],apdex_f=c["apdex_t"]*4,
                       sampling_rate=c["sampling_rate"],
                       transaction_tracer=tt_settings,
                       transaction_name_limit=c["transaction_name.limit"])

def _process_transaction_threshold(all_settings, threshold):
    if threshold is "apdex_f":
        return all_settings["apdex_t"]*4
    else:
        return threshold
    
def _process_record_sql(val):
#    from newrelic.config import _RECORD_SQL
#    return _RECORD_SQL[val]
    return val