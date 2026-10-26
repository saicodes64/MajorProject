"""Canonical MetroPT-3 signal -> industrial tag mapping.

Every meaning, unit and signal class below is taken directly from the official
dataset documentation ("Data Description_Metro.pdf", UCI MetroPT-3 dataset) and
the companion paper. Units are only set where the documentation states them;
digital/electrical signals have NO unit and are left as ``None``.

This single source of truth is shared by both the inspection and ingestion
scripts so the CSV columns and the database tags never drift apart.
"""
from __future__ import annotations

# The MetroPT-3 machine this dataset belongs to.
MACHINE = {
    "machine_code": "M001",
    "name": "MetroPT Air Compressor",
    "machine_type": "Air Production Unit",
    "location": "Metro Train",
    "description": (
        "Air Production Unit (APU) compressor instrumented on an operational "
        "metro train. Source: UCI MetroPT-3 dataset (INESC TEC / Univ. Porto), "
        "data logged Feb-Aug 2020."
    ),
}

# The first unnamed CSV column is the original 1Hz row index; it is NOT a signal.
INDEX_COLUMN = ""  # header is empty string in the raw file
TIMESTAMP_COLUMN = "timestamp"

# Ordered tag definitions. ``csv_column`` must match the CSV header exactly.
# ``data_type`` is the signal class used by downstream tooling: "analog" (real
# measurement) or "digital" (electrical on/off signal). ``unit`` is None when the
# documentation provides none.
TAG_DEFINITIONS = [
    # --- Analogue sensors (1-7) ---
    {
        "csv_column": "TP2",
        "tag_name": "TP2",
        "display_name": "Compressor Pressure",
        "data_type": "analog",
        "unit": "bar",
        "description": "Pressure on the compressor.",
    },
    {
        "csv_column": "TP3",
        "tag_name": "TP3",
        "display_name": "Pneumatic Panel Pressure",
        "data_type": "analog",
        "unit": "bar",
        "description": "Pressure generated at the pneumatic panel.",
    },
    {
        "csv_column": "H1",
        "tag_name": "H1",
        "display_name": "Cyclonic Separator Pressure",
        "data_type": "analog",
        "unit": "bar",
        "description": (
            "Pressure generated due to the pressure drop when the cyclonic "
            "separator filter discharges."
        ),
    },
    {
        "csv_column": "DV_pressure",
        "tag_name": "DV_pressure",
        "display_name": "Dryer Tower Discharge Pressure",
        "data_type": "analog",
        "unit": "bar",
        "description": (
            "Pressure drop generated when the towers discharge the air dryers; "
            "a zero reading indicates the compressor is operating under load."
        ),
    },
    {
        "csv_column": "Reservoirs",
        "tag_name": "Reservoirs",
        "display_name": "Reservoir Pressure",
        "data_type": "analog",
        "unit": "bar",
        "description": (
            "Downstream pressure of the reservoirs, which should be close to "
            "the pneumatic panel pressure (TP3)."
        ),
    },
    {
        "csv_column": "Oil_temperature",
        "tag_name": "Oil_temperature",
        "display_name": "Oil Temperature",
        "data_type": "analog",
        "unit": "degC",
        "description": "Oil temperature on the compressor.",
    },
    {
        "csv_column": "Motor_current",
        "tag_name": "Motor_current",
        "display_name": "Motor Current",
        "data_type": "analog",
        "unit": "A",
        "description": (
            "Current of one phase of the three-phase motor: ~0A off, ~4A "
            "offloaded, ~7A under load, ~9A when starting."
        ),
    },
    # --- Digital / electrical signals (8-15) ---
    {
        "csv_column": "COMP",
        "tag_name": "COMP",
        "display_name": "Air Intake Valve Signal (COMP)",
        "data_type": "digital",
        "unit": None,
        "description": (
            "Electrical signal of the air intake valve; active when there is no "
            "air intake (compressor off or operating offloaded)."
        ),
    },
    {
        "csv_column": "DV_eletric",
        "tag_name": "DV_eletric",
        "display_name": "Outlet Valve Control Signal (DV electric)",
        "data_type": "digital",
        "unit": None,
        "description": (
            "Electrical signal controlling the compressor outlet valve; active "
            "when the compressor is functioning under load."
        ),
    },
    {
        "csv_column": "Towers",
        "tag_name": "Towers",
        "display_name": "Drying Tower Selector (TOWERS)",
        "data_type": "digital",
        "unit": None,
        "description": (
            "Defines the active drying/draining tower; inactive = tower one "
            "operating, active = tower two operating."
        ),
    },
    {
        "csv_column": "MPG",
        "tag_name": "MPG",
        "display_name": "Load Start Signal (MPG)",
        "data_type": "digital",
        "unit": None,
        "description": (
            "Starts the compressor under load by activating the intake valve "
            "when APU pressure falls below 8.2 bar; it activates COMP."
        ),
    },
    {
        "csv_column": "LPS",
        "tag_name": "LPS",
        "display_name": "Low Pressure Signal (LPS)",
        "data_type": "digital",
        "unit": None,
        "description": "Activates when the pressure drops below 7 bar.",
    },
    {
        "csv_column": "Pressure_switch",
        "tag_name": "Pressure_switch",
        "display_name": "Pressure Switch",
        "data_type": "digital",
        "unit": None,
        "description": "Detects the discharge in the air-drying towers.",
    },
    {
        "csv_column": "Oil_level",
        "tag_name": "Oil_level",
        "display_name": "Oil Level Signal",
        "data_type": "digital",
        "unit": None,
        "description": (
            "Detects the oil level on the compressor; active when the oil is "
            "below the expected values."
        ),
    },
    {
        "csv_column": "Caudal_impulses",
        "tag_name": "Caudal_impulses",
        "display_name": "Air Flow Pulse Counter (Caudal Impulse)",
        "data_type": "digital",
        "unit": None,
        "description": (
            "Counts the pulse outputs generated by the absolute amount of air "
            "flowing from the APU to the reservoirs."
        ),
    },
]

# Convenience lookups
SIGNAL_COLUMNS = [t["csv_column"] for t in TAG_DEFINITIONS]
ANALOG_COLUMNS = [t["csv_column"] for t in TAG_DEFINITIONS if t["data_type"] == "analog"]
DIGITAL_COLUMNS = [t["csv_column"] for t in TAG_DEFINITIONS if t["data_type"] == "digital"]
