<div align='center'>

# Two-Station Machining Cell Control System

### *A microcontroller-based electrical control system that sequences, interlocks, and protects a two-station machining and material-handling cell — designed and simulated entirely as a substitute for PLC hardware and software.*

A concept-stage industrial automation project focused on **PLC-style sequencing, safety interlocks, overload protection, and fault handling**, with the control architecture designed for **STM32 implementation** and **Proteus-based validation**.

Built as a bridge between **industrial electrical control design** and **embedded PLC-equivalent engineering**.

<br>

<img src='https://img.shields.io/badge/Status-Architecture%20Complete-4caf50?style=for-the-badge' />
<img src='https://img.shields.io/badge/Firmware-Source%20Code%20Ready-1976d2?style=for-the-badge' />
<img src='https://img.shields.io/badge/Python-UART%20Log%20Parser%20Ready-00897b?style=for-the-badge' />

<img src='https://img.shields.io/badge/STM32CubeIDE-Integration%20Pending-455a64?style=for-the-badge' />
<img src='https://img.shields.io/badge/Simulation-Proteus%20Pending-f57c00?style=for-the-badge' />
<img src='https://img.shields.io/badge/Controller-STM32F103C8T6-1565c0?style=for-the-badge' />

<img src='https://img.shields.io/badge/Safety-E--Stop%20Interlock-c62828?style=for-the-badge' />
<img src='https://img.shields.io/badge/Domain-Industrial%20Automation-546e7a?style=for-the-badge' />




</div>

---


## 1. Overview

This project reproduces the *electrical control logic* of a small industrial production cell: a part is loaded, confirmed present, sent through a machining cycle, checked pass/fail, and cycled back — all governed by strict sequencing, safety interlocks, and overload protection.

In real industry, this class of control is implemented on a PLC (Programmable Logic Controller) using ladder logic or Sequential Function Charts, wired into a control panel with protection and safety relays. This project implements the *same control philosophy* — a cyclic scan loop, interlocked state transitions, hardware-interrupt-driven safety response, and latched fault handling — on an **STM32 microcontroller**, programmed in bare-metal embedded C, with the entire system built and validated in **circuit simulation (Proteus)** rather than on physical hardware.

The goal is not to imitate a PLC superficially, but to demonstrate the underlying control discipline a PLC-programmed system actually relies on: deterministic scanning, explicit interlocking, and safe, auditable fault behavior.

---

## 2. Key Features

- **Two-station finite-state-machine sequencing** — Loading → Machining → Inspection result, with no station able to act on stale or invalid upstream state.
- **Hardware-interrupt-driven Emergency Stop** — response is not dependent on main-loop timing; the E-stop can force a safe state from anywhere in the program at any time.
- **Threshold-based overload-protection interlock** — a simplified stand-in for a motor overload relay, with debounce logic to avoid nuisance trips on momentary signal spikes.
- **Fault latching with verified reset** — once a fault occurs, the system will not clear it automatically; a manual reset is required, and that reset is only honored if the underlying fault condition has genuinely cleared.
- **Live status display** — a 16x4 character LCD shows the current station, cycle status, and fault reason in real time.
- **Full event logging** — every state transition is transmitted over UART with a timestamp, producing an objective, reviewable record of system behavior for each test run.
- **Fully simulation-based** — designed and validated entirely in Proteus, with no physical hardware, to keep the project reproducible at zero cost.

---

## 3. System Architecture

```
 ┌─────────────┐     ┌─────────────────────┐     ┌───────────────────┐
 │  Station 1  │ --> │      Station 2      │ --> │  Result Handling  │
 │  (Loading)  │     │  (Machining +       │     │ (Pass / Reject)   │
 │             │     │   Overload Monitor) │     │                   │
 └─────────────┘     └─────────────────────┘     └───────────────────┘
         │                     │                          │
         └─────────────────────┴──────────────────────────┘
                               │
                     ┌────────────────────┐
                     │   STM32 Control    │
                     │   Hub (FSM Engine) │
                     └────────────────────┘
                        │       │     │
                 ┌──────┘   ┌───┘     └──────┐
             LCD Status   UART Log     E-Stop / Reset
             Display      (PC Terminal) (Interrupt-driven)
```

The system is organized into five functional subsystems:

| Subsystem | Responsibility |
|---|---|
| **Sequencing** | Core finite-state machine — `IDLE → LOADED → MACHINING → DONE → IDLE`, with `FAULT` reachable from any state |
| **Safety** | Interrupt-driven E-stop handling, fault latching, and two-condition manual reset |
| **Protection** | Analog current-sense sampling, threshold comparison, and debounce logic |
| **Display** | Live station/fault status on a 16x4 character LCD |
| **Logging** | Timestamped UART transmission of every state transition |

---

## 4. Hardware (Simulated)

All components below are simulated in Proteus — no physical hardware is used.

| Component | Role in the system |
|---|---|
| STM32F103C8T6 (Blue Pill class) | Central controller — runs the FSM, evaluates interlocks, drives all outputs |
| 4x Push-buttons | Stand-ins for: part-present sensor, PASS/FAIL inspection input, manual reset, emergency stop |
| Potentiometer (current-sense) | Variable analog signal representing motor current, feeding the overload-protection logic |
| Potentiometer (LCD contrast) | Standard contrast-bias input required by the HD44780-type display |
| 4x LEDs | Station-1 active, Station-2 active, Fault/alarm, Trip-relay indicators |
| Relay module | Represents the contactor coil that would be de-energized on a real overload trip |
| 16x4 Character LCD (HD44780-compatible) | Live operator-facing status display |

---

## 5. Software & Tools

| Tool | Purpose |
|---|---|
| **Proteus 8 Professional** | Schematic capture and mixed-mode circuit simulation, including simulation of the compiled STM32 firmware against a virtual chip |
| **STM32CubeIDE + CubeMX** | Peripheral configuration and embedded C firmware development (HAL-based) |
| **Python** *(optional)* | Parses captured UART logs into a timeline/visual plot |
| **GitHub** | Version control and documentation hosting |

---

## 6. Control Logic

### 6.1 State Machine

| State | Description |
|---|---|
| `IDLE` | Awaiting a part; all outputs off |
| `LOADED` | Part confirmed present at Station 1 |
| `MACHINING` | Timed machining cycle in progress; overload current continuously monitored |
| `DONE` | Cycle complete; PASS/FAIL result logged; automatically returns to `IDLE` |
| `FAULT` | Entered from any state, via E-stop or overload trip; latched until manually and validly reset |

### 6.2 Interlocks

- Station 2 (`MACHINING`) can only be entered from a genuinely completed `LOADED` state — there is no direct path that skips a station.
- No station output can remain active while a fault is latched.
- The overload trip requires the current-sense signal to remain above threshold continuously for a minimum duration (debounced), preventing momentary-spike nuisance trips.
- A fault can only be cleared if the reset input is pressed **and** the underlying condition (current below threshold, E-stop released) is verified clear at that moment — a reset action alone is not sufficient.

### 6.3 Emergency Stop

The E-stop is configured as a hardware interrupt (EXTI), not a polled input, so that a safety-relevant stop function is not subject to the timing of the main control loop.

---

## 7. Evidence / Validation Approach

Every state transition is transmitted over UART as a timestamped log line, e.g.:

```
[00:03.214] IDLE -> LOADED
[00:06.214] LOADED -> MACHINING
[00:12.487] MACHINING -> FAULT (reason: OVERLOAD_TRIP)
```

This log is the project's primary evidence artifact. Three scenarios are used to validate correct behavior:
1. A normal, complete cycle with no faults.
2. An E-stop triggered mid-cycle.
3. An overload condition triggered mid-cycle.

Captured logs for each scenario are stored in [`/logs`](./logs).

---

## 8. Repository Structure

```
├── /schematics       # Proteus schematic files and exported images
├── /firmware          # STM32CubeIDE project (source, headers, build config)
├── /logs              # Captured UART logs from validation runs
├── /docs              # Extended documentation (I/O list, architecture notes, pin map)
├── README.md
```

---

## 9. Design Scope & Limitations

This project intentionally uses simplified stand-ins where full industrial fidelity was not achievable within a simulation-only, zero-budget build:

- The overload trip uses a fixed current threshold rather than a full IEC 60947-style thermal (I²t) accumulation model.
- Sensor and quality-inspection inputs are represented by push-buttons, not real proximity or vision-inspection hardware.
- The Emergency Stop circuit is single-channel; a certified industrial safety circuit would typically use dual-channel, self-monitoring logic.
- No real motor, current sensor, or physical panel exists — every component is a Proteus simulation model.

These are documented as deliberate scope decisions, not oversights, and are tracked as future extensions in [`/docs`](./docs).

---

## 10. Future Work

- Full IEC 60947-4-1-style I²t thermal-trip model, validated against standard trip-class curves.
- A dedicated third inspection station with a more elaborate PASS/FAIL handshake.
- Python-based UART log visualization (timeline/Gantt-style plot).
- Documented digital handshake interface for future robot-controller integration.

---

## License

`[Add a license of your choice, e.g., MIT, if you intend this repository to be publicly reusable.]`
