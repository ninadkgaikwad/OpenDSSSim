# P1 — MPC-Inspired Branching Dueling Double DQN

**Status:** DAY-2 RL MATHEMATICS RATIFIED  
**Implementation status:** custom PyTorch/SB3-primitive-compatible implementation required

Stable-Baselines3 2.8.0 DQN supports a single `Discrete` action space and does not provide
the branching Dueling Double DQN architecture required here. The P1 implementation will
therefore implement BDQ directly in PyTorch while reusing generic SB3-style utilities
where useful (for example replay-buffer/schedule/logging/evaluation conventions).

## State/information

`state_RL = [o_t, forecast_t]`.

The current observation contains voltages, regulator states, capacitor states, PV
active/reactive operating points, and authorized current load/PV information.

The forecast tensor is the same authorized load/PV tensor supplied to MPC.

Forecast use does not make the method model-based; the policy has no transition model and
all transitions come from `env.step(...)`.

## Action branches

For arbitrary device cardinalities:

`N_A = |R| + |C| + |P|`.

Each regulator branch has actions `{-1,0,+1}`.
Each capacitor branch has actions `{0,1}`.
Each PV branch has normalized actions `{-1,-0.5,0,+0.5,+1}`.

PV physical request:
`q_p^{PV,req} = alpha_p Qmax_p`.

Every branch acts each timestep; the branch outputs are concatenated into one simultaneous
requested action vector.

## Branching dueling Q-network

A shared encoder maps the normalized policy input to a common latent representation.
A common state-value head and one advantage head per action dimension form:

`Q_d(s,a_d) = V(s) + A_d(s,a_d) - mean_{a'_d} A_d(s,a'_d)`.

Greedy action for branch `d`:
`a_d* = argmax_{a_d} Q_d(s,a_d)`.

The complete action concatenates all branchwise choices.

## Reward

`r_t = -ell_t`,

where `ell_t` is the same common physical stage cost used by MPC.

## Double-DQN target

The online network chooses the greedy next action in each branch and the target network
evaluates it. A shared target is formed from the mean target value over branches:

`y_t = r_t + gamma(1-delta_t) (1/N_A) sum_d Q_d^-(s_{t+1}, argmax_a Q_d(s_{t+1},a))`.

The training loss is the mean branch squared TD error:

`L = E[(1/N_A) sum_d (y_t - Q_d(s_t,a_{d,t}))^2]`.

Uniform replay, target-network updates, and epsilon-greedy exploration are used. Exact
numerical training hyperparameters are configuration/training-protocol items and are not
hard-coded into the controller science.
