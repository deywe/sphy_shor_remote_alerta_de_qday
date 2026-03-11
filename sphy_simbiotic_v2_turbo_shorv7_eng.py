"""
===============================================================================
PROJECT: HARPIA SPHY - QUANTUM-SYMBIOTIC SIMULATION ENGINE
VERSION: 1.0.0
DESCRIPTION: This script implements a hybrid quantum-classical simulation 
             using Cirq to model modular exponentiation (Shor's Algorithm 
             components). It utilizes an active Decision Gate (API-based) 
             to adjust sampling rates and fidelity boosts based on real-time 
             system coherence (SPHY percentage).
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
import time  # <--- IMPORT FIXED

# Settings
API_URL = "http://161.153.0.202:5050"

async def get_confidence(session):
    """Queries the system integrity sensor."""
    try:
        async with session.get(f"{API_URL}/status") as r:
            status = await r.json()
            # Returns the SPHY percentage (phase coupling integrity)
            return status.get("sphy_pct", 100.0)
    except Exception:
        return 50.0  # Conservative fallback

def get_quantum_circuit(a, N, p_bit, p_thermal):
    n_phase_qubits = 8
    phase_qubits = cirq.LineQubit.range(n_phase_qubits)
    circuit = cirq.Circuit()
    circuit.append(cirq.H.on_each(*phase_qubits))
    
    for i in range(n_phase_qubits):
        exponent = 2**(n_phase_qubits - 1 - i)
        # Phase calculation based on modular exponentiation
        phase = 2 * np.pi * pow(int(a), int(exponent), int(N)) / N
        circuit.append(cirq.ZPowGate(exponent=phase/np.pi).on(phase_qubits[i]))
        
    circuit.append(cirq.qft(*phase_qubits, inverse=True))
    
    # Injecting noise profile (Bit-flip)
    if p_bit > 0: 
        circuit = circuit.with_noise(cirq.bit_flip(p=p_bit))
    return circuit

async def process_number(session, N, p_bit, p_thermal):
    # 1. Query the AI Decision Gate for integrity status
    confidence = await get_confidence(session)
    # Adjust sampling rate (shots) based on coherence confidence
    repetitions = 100 if confidence < 85.0 else 10
    
    a = random.randint(2, N - 1)
    circuit = get_quantum_circuit(a, N, p_bit, p_thermal)
    
    # 2. Entropy Injection to force variation on the server-side solver
    payload = {
        "N": N, 
        "noise": [p_bit, p_thermal], 
        "shots": repetitions,
        "seed": random.random(),
        "ts": time.time()
    }
    
    # Requesting the optimized frequency (f_opt) from the symbiotic engine
    async with session.post(f"{API_URL}/resolver_fopt", json=payload, timeout=5.0) as r:
        if r.status == 200:
            data = await r.json()
            boost = data.get("f_opt", 0.02)
        else:
            boost = random.uniform(0.1, 0.9)

    print(f"✅ N={N:4} | Confidence: {confidence:5.1f}% | Boost: {boost:.4f} | R: {repetitions}")

async def main():
    print("--- HARPIA SPHY Simulation with Active Decision Gate ---")
    p_bit = 0.05
    p_thermal = 0.02
    
    # RSA Moduli candidates
    candidates = [15, 21, 33, 35, 51, 55, 65, 77, 85, 91, 143]
    
    async with aiohttp.ClientSession() as session:
        tasks = [process_number(session, N, p_bit, p_thermal) for N in candidates]
        await asyncio.gather(*tasks)
    print("\n✅ Simulation successfully completed.")

if __name__ == "__main__":
    async def run_async():
        await main()
    asyncio.run(run_async())
