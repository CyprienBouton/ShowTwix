############################
# Import necessary libraries
############################

import numpy as np
from scipy.stats import mode
from scipy.optimize import differential_evolution

############################
# Useful functions
############################

def compute_E1(duration, T1):
    return np.exp(-duration / T1)

def compute_relaxation(Mz, duration, T1):
    E1 = compute_E1(duration, T1)
    return Mz * E1 + (1 - E1)

def get_min_delta_triggers(readout_times, trigger_times, SPPRESS_duration=0.01750): # SPPRESS duration is around 17.5 ms
    min_delta_trigger_seq = 0
    i = 0
    last_trigger_time = None
    for t in trigger_times:
        while i < len(readout_times) and readout_times[i] < t:
            i += 1        
        if i>0 and last_trigger_time is not None:
            min_delta_trigger = readout_times[i-1] - last_trigger_time + SPPRESS_duration
            if min_delta_trigger > min_delta_trigger_seq:
                min_delta_trigger_seq = min_delta_trigger
        last_trigger_time = t
    return min_delta_trigger_seq

def get_TR(trigger_times, readout_times):
    TR = 0
    i = 0
    for t in trigger_times:
        while i < len(readout_times) and readout_times[i] < t:
            i += 1        
        if i>0:
            TR = (readout_times[i-1] - readout_times[0]) / (i-1) # TR is the average time between readouts
            break
    return TR

def get_segments(trigger_times, readout_times):
    i = 0
    for t in trigger_times:
        while i < len(readout_times) and readout_times[i] < t:
            i += 1        
        if i>0:
            return i-1
    raise ValueError("Trigger times are not compatible with readout times. Please check the input data.")

def find_corrupted_shot(delta_triggers, tolerance=0.15, precision=5e-2):
    delta_triggers_rounded = np.round((delta_triggers / precision)) * precision

    # Calculate mode using scipy.stats.mode
    delta_trigger_base = mode(delta_triggers_rounded, axis=None).mode
    # ignore the first shot (dummy) and other depends on the previous shot trigger duration
    corrupted_shots = np.concatenate([ 
        np.array([False]), 
        (abs(delta_triggers[:-1]-delta_trigger_base) > tolerance*delta_trigger_base) 
    ])
    return corrupted_shots

def compute_Mzeq_with_SPRESS(TI, T1, delta_trigger, TR, Nseg):
    """Compute the longitudinal equilibirum after a SPPRESS module

    Args:
        TI (float): inversion time in seconds.
        T1 (float): T1 relaxation time in seconds.
        delta_trigger (float): delta between two triggers in seconds.
        TR (float): repetition time (sometimes called echo spacing) in seconds.
        Nseg (int): number of segments.

    Returns:
        float: equilibrium magnetization
    """
    SPPRESS_duration = 17.25e-3 # duration in seconds
    RD = delta_trigger - TI - Nseg * TR - SPPRESS_duration
    E1_rec = compute_E1(RD, T1)
    return 1-E1_rec


############################
# Main functions
############################


def find_1_optimal_pulse(
            trigger_times, 
            readout_times, 
            TI,
            T1s=1e-3*np.arange(250, 1500, 100), 
            TR=None, 
            Nseg=None, 
            maxiter=1000,
            precision=5e-2,
            tolerance=0.15,
        ):
        """Useful method to compute the optimal duration and angle of the optimized pulse to restore magnetization

        Args:
                delta_trigger_corrupted (float): delta time between the two last triggers before the corrupted shot in seconds.
                T1s (float, optional): range of T1 relaxation times considered for the optimization. Defaults to 1e-3*torch.arange(250, 1500, 100).
            TR (float, optional): repetition time (sometimes called echo spacing) in seconds. Defaults to None.
            Nseg (int, optional): Number of segments in one shot. Defaults to None.
            maxiter (int, optional) maximum number of repetition performed during the optimization process.

        Returns:
            tuple(duration, angle): duration in seconds and angle in radian of the optimized repetition.
        """
        if Nseg is None:
            Nseg = get_segments(trigger_times, readout_times)
        if TR is None:
            TR = get_TR(trigger_times, readout_times)
        
        delta_triggers = np.diff(trigger_times)
        corrupted_shots = find_corrupted_shot(delta_triggers, tolerance=0.15, precision=5e-2)
        
        delta_triggers_rounded = np.round((delta_triggers / precision)) * precision
        delta_trigger_base = mode(delta_triggers_rounded, axis=None).mode
        
        all_t_a_opt = []
        all_alpha_b_opt = []
        delta_triggers_corrupted = delta_triggers[np.where(corrupted_shots)[0]-1] # get the delta_trigger of shot before the corrupted shots
        
        for i, delta_trigger_corrupted in enumerate(delta_triggers_corrupted):
            # Objective function to minimize
            def objective(params):
                t_a, alpha_b = params
                total_error = 0

                cos_b = np.cos(alpha_b)
                for T1 in T1s:
                    Mzeq = compute_Mzeq_with_SPRESS(TI, T1, delta_trigger_base, TR, Nseg)
                    M_corruped = compute_relaxation(Mzeq, delta_trigger_corrupted-delta_trigger_base, T1)
                
                    M = compute_relaxation(-M_corruped, TI-t_a, T1)
                    M *= cos_b  # apply reduced FA
                    M = compute_relaxation( M, t_a, T1)
                
                    S_corrected = M
                    S_eq = compute_relaxation(-Mzeq, TI, T1)
                    
                    total_error += (S_corrected-S_eq)**2
                
                return total_error
            # Bounds: t_a and t_c must be positive; alpha_b in [0, pi]
            bounds = [(0, TI), (0, np.pi)]

            result = differential_evolution(objective, bounds=bounds, maxiter=maxiter)
            t_a_opt, alpha_b_opt = result.x
            print(f"A pulse of {t_a_opt*1e3:.2f} ms with a flip angle of {np.rad2deg(alpha_b_opt):.2f}° is used to restore magnetization of shot {i}.")
            all_t_a_opt.append(t_a_opt)
            all_alpha_b_opt.append(np.rad2deg(alpha_b_opt))

        return all_t_a_opt, all_alpha_b_opt
        
        
        
def series_Mz_1FA_SPPRESS(
    TI, 
    T1, 
    FA, 
    readout_times, 
    trigger_times, 
    corrupted_shots=[], 
    t_a=0, 
    alpha_b=0, 
    time_step=1e-3, 
    do_SPPRESS=True, 
    reordering='Centric'
):
    """Generate a series of longitudinal magnetization.

    Args:
        TI (float): inversion time in seconds.
        T1 (float): T1 relaxation time in seconds.
        FA (float): flip angle in degrees.
        readout_times (list): list of readout times in seconds.
        trigger_times (list): list of trigger times in seconds.
        corrupted_shots (list, optional): list of corrupted shot indices. Defaults to []. 
            0 is before the first trigger, 1 is the first shot after the first trigger, etc.
        t_a (float, optional): delay of the optimized block pre readout in seconds. Defaults to 0.
        alpha_b (float, optional): alpha_b pulse angle in degrees. Defaults to 0.
        time_step (float, optional): time step in seconds. Defaults to 1e-3.
        do_SPPRESS (bool, optional): whether to do SPPRESS. Defaults to True.
        reordering (str, optional): reordering scheme. Defaults to 'Centric'.

    Raises:
        ValueError: if the reordering scheme is invalid.

    Returns:
        tuple: (all_times, all_Mz, all_times_center, all_Mz_center) 
        where all_times and all_Mz are the time points and corresponding magnetization values for the whole series, 
        and all_times_center and all_Mz_center are the time points and magnetization values for the center shot.
    """
    all_times = []
    all_Mz = []
    all_times_center = []
    all_Mz_center = []
    t = 0
    all_Mz.append(1.)
    all_times.append(0.)
    readout_times_iter = iter(readout_times)
    current_readout_time = next(readout_times_iter)
    trigger_times = np.concatenate([ trigger_times, [readout_times.max()+time_step] ]) # add a trigger time after the last readout time to end the simulation after the last readout
    min_delta_trigger = get_min_delta_triggers(readout_times, trigger_times)
    nb_segments = get_segments(trigger_times, readout_times)
    if reordering=='Centric':
        center_shot = 0
    elif reordering=='Linear':
        center_shot = nb_segments//2
    else:
        raise ValueError("Invalid reordering scheme. Choose 'Centric' or 'Linear'.")
    if t_a is not None:
        if isinstance(t_a, (float, int)):
            t_a = [t_a]*len(corrupted_shots)
        t_a_iter = iter(t_a)
        current_t_a = next(t_a_iter)
    if alpha_b is not None:
        if isinstance(alpha_b, (float, int)):
            alpha_b = [alpha_b]*len(corrupted_shots)
        alpha_b_iter = iter(alpha_b)
        current_alpha_b = next(alpha_b_iter)
    
    Mz = 1 # M0
    
    for i, next_trigger_time in enumerate(trigger_times):
        SPPRESS_not_executed = True
        t_last_RF = t
        Mz = -Mz # inversion pulse
        all_Mz.append(Mz)
        all_times.append(t)
        # relaxation during TI
        if t_a is not None and alpha_b is not None and i-1 in corrupted_shots: # the first shot is after the first trigger
            while t-t_last_RF<TI-current_t_a:
                Mz = compute_relaxation(Mz, time_step, T1)
                all_Mz.append(Mz)
                all_times.append(t)
                t+=time_step
            Mz = Mz*np.cos(np.deg2rad(current_alpha_b)) # alpha_b pulse at the end of the segment
            while t-t_last_RF<TI:
                Mz = compute_relaxation(Mz, time_step, T1)
                all_Mz.append(Mz)
                all_times.append(t)
                t+=time_step
            current_t_a = next(t_a_iter, current_t_a)
            current_alpha_b = next(alpha_b_iter, current_alpha_b)
    
        else:
            while t-t_last_RF<TI:
                Mz = compute_relaxation(Mz, time_step, T1)
                all_Mz.append(Mz)
                all_times.append(t)
                t+=time_step
        # readout
        seg_number = 0
        while t < next_trigger_time:
            if t>= current_readout_time:
                Mz = compute_relaxation(Mz, current_readout_time-(t-time_step), T1)*np.cos(np.deg2rad(FA)) # readout at current_readout_time
                Mz = compute_relaxation(Mz, t-current_readout_time, T1) # relaxation after the readout
                current_readout_time = next(readout_times_iter, float('inf')) # get the next readout time
                if seg_number==center_shot:
                    all_Mz_center.append(Mz)
                    all_times_center.append(t)
                seg_number+=1
            elif t - t_last_RF > min_delta_trigger and do_SPPRESS and SPPRESS_not_executed and i>0:
                Mz = compute_relaxation(0, t-t_last_RF- min_delta_trigger, T1) # relaxation after SPPRESS
                SPPRESS_not_executed = False
            else:
                Mz = compute_relaxation(Mz, time_step, T1) # relaxation without readout
            all_Mz.append(Mz)
            all_times.append(t) 
            t+=time_step
            
    return all_times, all_Mz, all_times_center, all_Mz_center