"""
HART-MCP Plugins Package
Revolutionary AI consciousness and agent systems
"""

# Import key classes for easy access
from .tools import *
from .agent_core import SpecialistAgent
from .orchestrator_core import OrchestratorAgent

# Advanced consciousness systems
try:
    from .meta_consciousness import MetaConsciousnessEngine, QuantumThought, ConsciousnessLevel
    from .quantum_agent_evolution import QuantumGeneticAlgorithm, EvolutionaryAgent
    from .neural_fusion_engine import DistributedNeuralFusionEngine
    from .godlike_meta_agent import GodlikeMetaAgent, create_godlike_meta_agent
    
    __all__ = [
        'MetaConsciousnessEngine', 'QuantumThought', 'ConsciousnessLevel',
        'QuantumGeneticAlgorithm', 'EvolutionaryAgent', 
        'DistributedNeuralFusionEngine',
        'GodlikeMetaAgent', 'create_godlike_meta_agent',
        'SpecialistAgent', 'OrchestratorAgent'
    ]
except ImportError as e:
    # Graceful degradation if advanced systems aren't available
    __all__ = ['SpecialistAgent', 'OrchestratorAgent']
    import logging
    logging.warning(f"Some advanced consciousness systems not available: {e}")

__version__ = "1.0.0"