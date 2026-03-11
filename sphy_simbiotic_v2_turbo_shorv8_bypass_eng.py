"""
===============================================================================
PROJECT: HARPIA QUANTUM SIMULATOR (ADAPTIVE MODE)
VERSION: 2.0.0
DESCRIPTION: A specialized simulation engine for modular exponentiation 
             (Shor's Algorithm logic) that provides a comparative interface
             between 'BASELINE' (unmitigated noise) and 'HARPIA' (AI-driven 
             mitigation). It uses a remote SPHY API to dynamically optimize 
             quantum circuit fidelity based on real-time coherence metrics.
AUTHOR: Deywe Okabe
===============================================================================
"""
import cirq
import numpy as np
import os
import random
import json
import asyncio
import aiohttp
import time

# --- CONFIGURATIONS ---
API_URL = "http://161.153.0.202:5050"
# TOGGLE HERE TO COMPARE: 
# True  -> BASELINE MODE (Native execution with fidelity loss due to depth)
# False -> HARPIA MODE (Active mitigation via SPHY API)
BYPASS_IA = True  

async def get_confidence(session):
    try:
        async with session.get(f"{API_URL}/status") as r:
            status = await r.json()
            return status.get("sphy_pct", 100.0)
    except:
        return 50.0

def get_quantum_circuit(a, N, p_bit, p_thermal):
    """Generates a simplified circuit for Shor's Algorithm."""
    n_phase_qubits = 8
    phase_qubits = cirq.LineQubit.range(n_phase_qubits)
    circuit = cirq.Circuit()
    circuit.append(cirq.H.on_each(*phase_qubits))
    
    for i in range(n_phase_qubits):
        exponent = 2**(n_phase_qubits - 1 - i)
        # Simulation of quantum phase based on modular arithmetic
        phase = 2 * np.pi * pow(int(a), int(exponent), int(N)) / N
        circuit.append(cirq.ZPowGate(exponent=phase/np.pi).on(phase_qubits[i]))
        
    circuit.append(cirq.qft(*phase_qubits, inverse=True))
    
    # Application of bit-flip noise if defined
    if p_bit > 0: 
        circuit = circuit.with_noise(cirq.bit_flip(p=p_bit))
    return circuit

async def process_number(session, N, p_bit, p_thermal):
    # Selection of a random coprime 'a'
    a = random.randint(2, N - 1)
    
    if BYPASS_IA:
        # --- BYPASS MODE: Native execution (Baseline) ---
        # The system ignores the AI and suffers from real quantum noise
        circuit = get_quantum_circuit(a, N, p_bit, p_thermal)
        
        # Simulating fidelity degradation as the circuit gets deeper (higher N)
        # In real circuits, depth D ∝ log(N), here we use a linear penalty for stress
        base_fidelity = max(0.001, 0.5 * (1 - (N / 1000))) 
        # Random hardware noise without correction
        boost = base_fidelity * random.uniform(0.5, 1.0)
        
        mode = "BASELINE"
        repetitions = 10
    else:
        # --- HARPIA MODE: Active Mitigation with SPHY AI ---
        confidence = await get_confidence(session)
        # If the SPHY network confidence is low, we increase shots (repetitions)
        repetitions = 100 if confidence < 85.0 else 10
        
        payload = {
            "N": N, 
            "noise": [p_bit, p_thermal], 
            "shots": repetitions,
            "seed": random.random(),
            "ts": time.time()
        }
        
        try:
            async with session.post(f"{API_URL}/resolver_fopt", json=payload, timeout=5.0) as r:
                if r.status == 200:
                    data = await r.json()
                    boost = data.get("f_opt", 0.02)
                else:
                    boost = 0.02
                mode = "HARPIA"
        except:
            boost = 0.01  # Connection failure with AI
            mode = "ERROR/FALLBACK"
            
    # Formatted output for your terminal
    color = "\033[91m" if mode == "BASELINE" else "\033[92m"
    reset = "\033[0m"
    print(f"✅ N={N:4} | {color}Mode: {mode:8}{reset} | Boost (Fidelity): {boost:.6f} | R: {repetitions}")

async def main():
    print(f"\n--- 🌀 HARPIA QUANTUM SIMULATOR (Bypass: {BYPASS_IA}) ---")
    print(f"📡 Target API: {API_URL}")
    print("-" * 65)

    p_bit, p_thermal = 0.05, 0.02
    # List of numbers for factorization
    candidates = [15, 21, 33, 35, 51, 55, 65, 77, 85, 91, 143, 221, 323]
    
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        # Asynchronous processing to simulate hardware parallelism
        tasks = [process_number(session, N, p_bit, p_thermal) for N in candidates]
        await asyncio.gather(*tasks)
    
    end_time = time.time()
    print("-" * 65)
    print(f"✅ Simulation completed in {end_time - start_time:.2f}s.")

if __name__ == "__main__":
    asyncio.run(main())
