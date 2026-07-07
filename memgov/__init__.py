"""memgov — cross-agent memory governance.

Govern what an agent's persistent memory is allowed to assert before the
agent relies on it. A transplant of the RCGov axiom
(InjectContext_t => ContextReady_t) onto agent memory:
memory is a point-in-time snapshot, not live state, so status-bearing
claims must pass a readiness gate before injection or reliance.
"""

__version__ = "0.1.0"
