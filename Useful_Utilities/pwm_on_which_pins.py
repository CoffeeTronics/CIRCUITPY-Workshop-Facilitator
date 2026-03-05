# To use this program, paste its contents into D:\code.py
# It will identify all PWM capable pins and the timers that use them.
# All PWM pins that use THE SAME TIMER cannot be used together at the same time.
# Conversely, PWM pins that use different timers can be used at the same time.
# SPDX-License-Identifier: MIT
"""CircuitPython PWM pin scanner - groups pins by shared hardware timer."""
import board
import pwmio

# --- Pass 1: Find all PWM-capable pins (both clean successes and timer conflicts) ---
pwm_capable = []
for pin_name in dir(board):
    pin = getattr(board, pin_name)
    try:
        p = pwmio.PWMOut(pin)
        p.deinit()
        pwm_capable.append(pin_name)
    except RuntimeError:
        pwm_capable.append(pin_name)  # Timer conflict = still PWM capable
    except (ValueError, TypeError):
        pass  # Not a PWM pin or not a pin at all

# --- Pass 2: Group by shared timer ---
# Hold pin A open, then probe all unassigned pins.
# A RuntimeError on pin B means it shares pin A's timer.
groups = []
assigned = set()

for pin_a_name in pwm_capable:
    if pin_a_name in assigned:
        continue
    try:
        p_a = pwmio.PWMOut(getattr(board, pin_a_name))
    except (RuntimeError, ValueError):
        continue  # Couldn't claim it this pass, skip

    group = [pin_a_name]
    assigned.add(pin_a_name)

    for pin_b_name in pwm_capable:
        if pin_b_name in assigned:
            continue
        try:
            p_b = pwmio.PWMOut(getattr(board, pin_b_name))
            p_b.deinit()  # Succeeded - different timer, leave it for its own group
        except RuntimeError:
            group.append(pin_b_name)  # Conflict = same timer as pin A
            assigned.add(pin_b_name)
        except (ValueError, TypeError):
            pass

    p_a.deinit()
    groups.append(group)

# --- Print results ---
print(f"Found {len(pwm_capable)} PWM-capable pins across {len(groups)} timer groups:\n")
for i, group in enumerate(groups, 1):
    if len(group) == 1:
        print(f"  Timer {i} (exclusive): {group[0]}")
    else:
        print(f"  Timer {i} (shared):    {', '.join(group)}")