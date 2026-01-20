import streamlit as st
from functools import wraps
import time
import hashlib

def measure_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        if 'performance_metrics' not in st.session_state:
            st.session_state.performance_metrics = {}
        st.session_state.performance_metrics[func.__name__] = end - start
        return result
    return wrapper

def cache_jira_data(ttl=300):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key_parts = [func.__name__, str(args), str(kwargs)]
            cache_key = hashlib.md5("|".join(key_parts).encode()).hexdigest()
            
            if 'jira_cache' not in st.session_state:
                st.session_state.jira_cache = {}
            
            current_time = time.time()
            
            if (cache_key in st.session_state.jira_cache and 
                current_time - st.session_state.jira_cache[cache_key]['timestamp'] < ttl):
                return st.session_state.jira_cache[cache_key]['data']
            
            result = func(*args, **kwargs)
            st.session_state.jira_cache[cache_key] = {
                'data': result,
                'timestamp': current_time
            }
            
            return result
        return wrapper
    return decorator

def show_performance_metrics():
    if hasattr(st.session_state, 'performance_metrics') and st.session_state.performance_metrics:
        st.sidebar.subheader(" Performance")
        for func_name, duration in st.session_state.performance_metrics.items():
            st.sidebar.metric(f"{func_name}", f"{duration:.2f}s")