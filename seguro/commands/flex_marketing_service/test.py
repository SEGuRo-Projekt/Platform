# SPDX-FileCopyrightText: 2024-2025 Lukas Lenz, RWTH Aachen
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
from .pyvolt import network
from .pyvolt import nv_powerflow
from .pyvolt import nv_state_estimator
from .pyvolt import measurement

import numpy as np
import cimpy
import os

# Define input files
p = "net"
xml_path = Path(p)
print(xml_path)
xml_files = [os.path.join(xml_path, "seguro_split_net1.xml")]

# Read cim files and create new network.System object
print("Reading cim files...")
res = cimpy.cim_import(xml_files, "cgmes_v2_4_15")
print("Create network system...")
system = network.System()
base_apparent_power = 25  # MW
Vbase = 10  # line-line voltage
print("Loading cim data into system...")
system.load_cim_data(res["topology"], base_apparent_power)

# Check if voltage of Slack bus is 1+j0
for n in system.nodes:
    if n.type == network.BusType.SLACK:
        if n.voltage_pu == complex(0, 0):
            n.voltage_pu = complex(1.0, 0)
            n.voltage = complex(1.0 * Vbase, 0)


# print("system:")
# print(system)
# print("node_names:")
# print(system.print_nodes_names())
# print("node_types:")
# print(system.print_node_types())
# print("node_power:")
# print(system.print_power())

# print(str(len(system.nodes)) + " nodes:")
# for node in system.nodes:
#     print(node)

# print()

# print(str(len(system.branches)) + " branches:")
# for branch in system.branches:
#     print(branch)

# Execute power flow analysis
print("Starting power flow...")
results_pf, num_iter = nv_powerflow.solve(system)
print("Powerflow converged in " + str(num_iter) + " iterations.\n")

for node in results_pf.nodes:
    print(node)

print()

for branch in results_pf.branches:
    print(branch)

# Execute state estimation analysis
# --- State Estimation ---
""" Write here the percent uncertainties of the measurements"""
V_unc = 0
I_unc = 0
Sinj_unc = 0
S_unc = 0
Pmu_mag_unc = 1
Pmu_phase_unc = 0

# Create measurements data structures
"""use all node voltages as measures"""
measurements_set = measurement.MeasurementSet()
for node in results_pf.nodes:
    measurements_set.create_measurement(
        node.topology_node,
        measurement.ElemType.Node,
        measurement.MeasType.Vpmu_mag,
        np.absolute(node.voltage_pu),
        Pmu_mag_unc,
    )
for node in results_pf.nodes:
    measurements_set.create_measurement(
        node.topology_node,
        measurement.ElemType.Node,
        measurement.MeasType.Vpmu_phase,
        np.angle(node.voltage_pu),
        Pmu_phase_unc,
    )
measurements_set.meas_creation()

# Perform state estimation
state_estimation_results = nv_state_estimator.DsseCall(
    system, measurements_set
)

# Print node voltages
# print("state_estimation_results.voltages: ")
# for node in state_estimation_results.nodes:
#     print("{}={}".format(node.topology_node.name, node.voltage))


print("State estimation results:")
for node in state_estimation_results.nodes:
    print(node)
