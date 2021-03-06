# -*- coding: utf-8 -*-
"""
Created on Tue May 05 08:16:08 2015
@author: Ferriss

Diffusion in 1 and 3 dimensions with and without path-integration
Uses lmfit library to set up and pass parameters

THIS MODULE ASSUMES THAT ALL CONCENCENTRATIONS ARE ALREADY NORMALIZED TO 1.

### 1-dimensional diffusion ###
Simplest function call is diffusion1D(length, diffusivity, time)
    Step 1. Create lmfit parameters with params = params_setup1D
            (Here is where you set what to vary when fitting)
    Step 2. Pass these parameters into diffusion1D_params(params)
    Step 3. Plot with plot_diffusion1D
With profiles in styles, use profile.plot_diffusion() and fitD()

### 3-dimensional diffusion without path integration: 3Dnpi ###
Simplest: diffusion3Dnpi(lengths, D's, time) to get a figure
    Step 1. Create parameters with params = params_setup3D
    Step 2. Pass parameters into diffusion3Dnpi_params(params) to get profiles
            Returns full 3D matrix v, sliceprofiles, then slice positions
    Step 3. Plot with styles.plot_3panels(slice positions, slice profiles)

### Whole-Block: 3-dimensional diffusion with path integration: 3Dwb ###
    Step 1. Create parameters with params = params_setup3D 
            Same as for non-path integrated 3D.
    Step 2. Pass parameters into diffusion3Dwb(params)

### pynams module Profile and WholeBlock classes have bound functions to 
plot and fit diffusivities using these functions: plot_diffusion,
fitDiffusivity, and fitD

### Arrhenius diagrams ###
class Diffusivities() groups together temperatures and diffusivities
for use in plotting directly onto Arrhenius diagrams


"""
import lmfit
import numpy as np
import scipy
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from mpl_toolkits.axes_grid1.parasite_axes import SubplotHost
import styles
from uncertainties import ufloat
import sys

GAS_CONSTANT = 0.00831 # kJ/mol K

#%% 1D Diffusion in a thin slab; Eq 4.18 in Crank, 1975
def diffusionThinSlab(log10D_m2s, thickness_microns, max_time_hours=2000, 
                      infinity=200, timesteps=300):
    """ Takes log10 of the diffusivity D in m2/s, thickness in microns,
    and maximum time in hours, and returns time array in hours and corresponding 
    curve of C/C0, the concentration divided by the initial concentration
    """
    t_hours = np.linspace(0., max_time_hours, timesteps)
    t_seconds = t_hours * 3600.
    L_meters = thickness_microns / 2.E6
    cc = np.zeros_like(t_seconds)
    D_m2s = 10.**log10D_m2s

    for idx in range(len(t_seconds)):
        infsum = 0.
        for n in range(infinity):
            exponent_top = D_m2s * (((2.*n)+1.)**2.) * (np.pi**2.) * t_seconds[idx] 
            exponent_bot = 4. * (L_meters**2)
            exponent = np.exp(-1. * exponent_top / exponent_bot)
            addme = 8. * (1. / ((((2.*n)+1)**2.) * (np.pi**2.))) * exponent
            infsum = infsum + addme
        cc[idx] = infsum
    
    return t_hours, cc
    

#%% 1D diffusion profiles
def params_setup1D(microns, log10D_m2s, time_seconds, init=1., fin=0.,
                   vD=True, vinit=False, vfin=False):
    """Takes required info for diffusion in 1D - length, diffusivity, time,
    and whether or not to vary them - vD, vinit, vfin. 
    Return appropriate lmfit params to pass into diffusion1D_params"""
    params = lmfit.Parameters()
    params.add('microns', microns, False, None, None, None)
    params.add('log10D_m2s', log10D_m2s, vD, None, None, None)
    params.add('time_seconds', time_seconds, False, None, None, None)
    params.add('initial_unit_value', init, vinit, None, None, None)
    params.add('final_unit_value', fin, vfin, None, None, None)
    return params

def diffusion1D_params(params, data_x_microns=None, data_y_unit_areas=None, 
                 erf_or_sum='erf', need_to_center_x_data=True,
                 infinity=100, points=50):
    """Function set up to follow lmfit fitting requirements.
    Requires input as lmfit parameters value dictionary 
    passing in key information as 'length_microns',
    'time_seconds', 'log10D_m2s', and 'initial_unit_value'. 

    If data are None (default), returns 1D unit diffusion profile 
    x_microns and y as vectors of length points (default 50). 

    Optional keywords:    
     - erf_or_sum: whether to use python's error functions (default) 
       or infinite sums
     - whether to center x data
     - points sets how many points to calculate in profile. Default is 50.
     - what 'infinity' is if using infinite sum approximation
     
    If not including data, returns the x vector and model y values.
    With data, return the residual for use in fitting.

    Visualize results with plot_diffusion1D
    """
    # extract important values from parameter dictionary passed in
    p = params.valuesdict()
    L_meters = p['microns'] / 1e6
    t = p['time_seconds']
    D = 10.**p['log10D_m2s']
    initial_value = p['initial_unit_value']
    final_value = p['final_unit_value']

    if initial_value > final_value:
        going_out = True
        solubility = initial_value
        minimum_value = final_value
    else:
        going_out = False        
        solubility = final_value
        minimum_value = initial_value
    
    a_meters = L_meters / 2.
    twoA = L_meters

    if t < 0:
        print 'no negative time'
        return           

    # Fitting to data or not? Default is not
    fitting = False
    if (data_x_microns is not None) and (data_y_unit_areas is not None):
        if len(data_x_microns) == len(data_y_unit_areas):
            fitting = True
        else:
            print 'x and y data must be the same length'
            print 'x', len(data_x_microns)
            print 'y', len(data_y_unit_areas)
        
    # x is in meters and assumed centered around 0
    if fitting is True:
        # Change x to meters and center it
        x = np.array(data_x_microns) / 1e6
        if need_to_center_x_data is True:
            x = x - a_meters
    else:
        x = np.linspace(-a_meters, a_meters, points)
    
    if erf_or_sum == 'infsum':
        xsum = np.zeros_like(x)
        for n in range(infinity):
           # positive number that converges to 1
            xadd1 = ((-1.)**n) / ((2.*n)+1.)        
            # time conponent
            xadd2 = np.exp(
                            (-D * (((2.*n)+1.)**2.) * (np.pi**2.) * t) / 
                            (twoA**2.) 
                            )                        
            # There the position values come in to create the profile
            xadd3 = np.cos(
                            ((2.*n)+1.) * np.pi * x / twoA
                            )        
            xadd = xadd1 * xadd2 * xadd3
            xsum = xsum + xadd
            
        model = xsum * 4. / np.pi
    

    elif erf_or_sum == 'erf':
        sqrtDt = (D*t)**0.5
        model = ((scipy.special.erf((a_meters+x)/(2*sqrtDt))) + 
                   (scipy.special.erf((a_meters-x)/(2*sqrtDt))) - 1) 

    else:
        print ('erf_or_sum must be set to either "erf" for python built-in ' +
               'error function approximation (defaul) or "sum" for infinite ' +
               'sum approximation with infinity=whatever, defaulting to ' + 
               str(infinity))
        return False

    if going_out is False:
        model = np.ones_like(model) - model

    concentration_range = solubility - minimum_value
    model = (model * concentration_range) + minimum_value

    x_microns = x * 1e6

    # If not including data, just return the model values
    # With data, return the residual for use in fitting.
    if fitting is False:
        return x_microns, model
    return model-data_y_unit_areas

def plot_diffusion1D(x_microns, model, initial_value=None,
                     fighandle=None, axishandle=None, top=1.2,
                     style=None, fitting=False, show_km_scale=False,
                     show_initial=True):
    """Takes x and y diffusion data and plots 1D diffusion profile input"""
    a_microns = (max(x_microns) - min(x_microns)) / 2.
    a_meters = a_microns / 1e3
    
    if fighandle is None and axishandle is not None:
        print 'Remember to pass in handles for both figure and axis'
    if fighandle is None or axishandle is None:
        fig = plt.figure()          
        ax  = SubplotHost(fig, 1,1,1)
        ax.grid()
        ax.set_ylim(0, top)
    else:
        fig = fighandle
        ax = axishandle

    if style is None:
        if fitting is True:
            style = {'linestyle' : 'none', 'marker' : 'o'}
        else:
            style = styles.style_lightgreen

    if show_km_scale is True:
        ax.set_xlabel('Distance (km)')
        ax.set_xlim(0., 2.*a_meters/1e3)
        x_km = x_microns / 1e6
        ax.plot((x_km) + a_meters/1e3, model, **style)
    else:                
        ax.set_xlabel('position ($\mu$m)')
        ax.set_xlim(-a_microns, a_microns)
        ax.plot(x_microns, model, **style)

    if initial_value is not None and show_initial is True:
        ax.plot(ax.get_xlim(), [initial_value, initial_value], '--k')

    ax.set_ylabel('Unit concentration or final/initial')
    fig.add_subplot(ax)

    return fig, ax

def diffusion1D(length_microns, log10D_m2s, time_seconds, init=1., fin=0.,
                erf_or_sum='erf', show_plot=True, 
                fighandle=None, axishandle=None,
                style=None, need_to_center_x_data=True,
                infinity=100, points=100, top=1.2, show_km_scale=False):
    """Simplest implementation.
    Takes required inputs length, diffusivity, and time 
    and plots diffusion curve on new or specified figure. 
    Optional inputs are unit initial value and final values. 
    Defaults assume diffusion 
    out, so init=1. and fin=0. Reverse these for diffusion in.
    Returns figure, axis, x vector in microns, and model y data."""
    params = params_setup1D(length_microns, log10D_m2s, time_seconds, 
                            init, fin,
                            vD=None, vinit=None, vfin=None)
                            
    x_microns, model = diffusion1D_params(params, None, None, 
                                          erf_or_sum, need_to_center_x_data, 
                                          infinity, points)

    fig, ax = plot_diffusion1D(x_microns, model, initial_value=init, 
                               fighandle=fighandle, axishandle=axishandle,
                               style=style, fitting=False, 
                               show_km_scale=show_km_scale)
    
    return fig, ax, x_microns, model


#%% 3-dimensional diffusion parameter setup
def params_setup3D(microns3, log10D3, time_seconds, 
                   initial=1., final=0., isotropic=False, slowb=False,
                   vD=[True, True, True], vinit=False, vfin=False):
    """Takes required info for diffusion in 3D without path averaging and 
    return appropriate lmfit params.
    
    Returning full matrix and 
    slice profiles in one long list for use in fitting

    """
    params = lmfit.Parameters()
    params.add('microns3', microns3, False, None, None, None)
    params.add('log10Dx', log10D3[0], vD[0], None, None, None)
    params.add('time_seconds', time_seconds, False, None, None, None)
    params.add('initial_unit_value', initial, vinit, None, None, None)
    params.add('final_unit_value', final, vfin, None, None, None)

    if isotropic is True:
        params.add('log10Dy', log10D3[1], vD[1], None, None, 'log10Dx')
        params.add('log10Dz', log10D3[2], vD[2], None, None, 'log10Dx')
    elif slowb is True:
        params.add('log10Dy', log10D3[1], vD[1], None, None, 'log10Dx - 1.')
        params.add('log10Dz', log10D3[2], vD[2], None, None, 'log10Dx')
    else:            
        params.add('log10Dy', log10D3[1], vD[1], None, None, None)
        params.add('log10Dz', log10D3[2], vD[2], None, None, None)

    return params

def diffusion3Dnpi_params(params, data_x_microns=None, data_y_unit_areas=None, 
                 erf_or_sum='erf', centered=True, 
                 infinity=100, points=50):
    """ Diffusion in 3 dimensions in a rectangular parallelipiped.
    Takes params - Setup parameters with params_setup3D.
    General setup and options similar to diffusion1D_params.
    
    Returns complete 3D concentration
    matrix v, slice profiles, and 
    positions of slice profiles.
    
    ### NOT COMPLETELY SET UP FOR FITTING JUST YET ###
    """   
    fitting = False
    if (data_x_microns is not None) and (data_y_unit_areas is not None):
        x_data = np.array(data_x_microns)
        y_data = np.array(data_y_unit_areas)
        if np.shape(x_data) == np.shape(y_data):
            fitting = True
            print 'fitting to data'
        else:
            print 'x and y data must be the same shape'
            print 'x', np.shape(x_data)
            print 'y', np.shape(y_data)

    p = params.valuesdict()
    L3_microns = np.array(p['microns3'])
    t = p['time_seconds']
    init = p['initial_unit_value']
    vary_init = [params['initial_unit_value'].vary]
    fin = p['final_unit_value']
    vary_fin = [params['final_unit_value'].vary]
    log10D3 = [p['log10Dx'], p['log10Dy'], p['log10Dz']]
    vary_D = [params['log10Dx'].vary, 
              params['log10Dy'].vary, 
              params['log10Dz'].vary]

    # If initial values > 1, scale down to 1 to avoid blow-ups later
    going_out = True
    scale = 1.
    if init > 1.0:
        scale = init
        init = 1.
    if init < fin:
        going_out = False
    
    if init > fin:
        minimum_value = fin
    else:
        minimum_value = init
    
    if going_out is False:        
        # I'm having trouble getting diffusion in to work simply, so this
        # is a workaround. The main effort happens as diffusion going in, then
        # I subtract it all from 1.
        init, fin = fin, init
        
    # First create 3 1D profiles, 1 in each direction
    xprofiles = []    
    yprofiles = []
    kwdict = {'points' : points}
    
    for k in range(3):
        p1D = lmfit.Parameters()
        p1D.add('microns', L3_microns[k], False)
        p1D.add('time_seconds', t, params['time_seconds'].vary)
        p1D.add('log10D_m2s', log10D3[k], vary_D[k])
        p1D.add('initial_unit_value', init, vary_init)
        p1D.add('final_unit_value', fin, vary_fin)
        
        x, y = diffusion1D_params(p1D, **kwdict)

        xprofiles.append(x)
        yprofiles.append(y)
                                      
    # Then multiply them together to get a 3D matrix
    # I should figure out how to do this without the for-loops
    v = np.ones((points, points, points))
    for d in range(0, points):
        for e in range(0, points):
            for f in range(0, points):
                v[d][e][f] = yprofiles[0][d]*yprofiles[1][e]*yprofiles[2][f]

    v = v * scale

    if going_out is False:
        v = np.ones((points, points, points)) - v
        v = v + np.ones_like(v)*minimum_value

    mid = int(points/2.)
    
    aslice = v[:, mid][:, mid]
    bslice = v[mid][:, mid]
    cslice = v[mid][mid]
    sliceprofiles = [aslice, bslice, cslice]

    slice_positions_microns = []
    for k in range(3):
        a = L3_microns[k] / 2.
        if centered is False:            
            x = np.linspace(0, a*2., points)
        else:
            x = np.linspace(-a, a, points)
        slice_positions_microns.append(x)
          
    # Returning full matrix and 
    # slice profiles in one long list for use in fitting
    sliceprofiles = [aslice, bslice, cslice]
    
    if fitting is False:
        return v, sliceprofiles, slice_positions_microns
    else:
        ### Still need to set up residuals! ###
        residuals = np.zeros_like(sliceprofiles)
        return residuals

def diffusion3Dnpi(lengths_microns, log10Ds_m2s, time_seconds, points=50,
                    initial=1, final=0., top=1.2, plot3=True, centered=True,
                    styles3=[None]*3, figaxis3=None):
        """
        Required input:
        list of 3 lengths, list of 3 diffusivities, and time 
        
        Optional input:
        initial concentration (1), final concentration (0), 
        whether to plot output (plot3=True), maximum y limit on plot (top=1.2),
        and number of points to use during calculation (points=50)
        
        If plot3=True (default), plots results and returns:
        1. f, figure of plot of 3D non-path-averaged diffusion profiles.
        2. ax, 3 axes of figure
        3. v, 3D matrix of diffusion
        4. x, list of 3 sets of x values plotted
        5. y, list of 3 sets of y values plotted
        
        If plot3=False, returns only v, x, y
        """
        params = params_setup3D(lengths_microns, log10Ds_m2s, time_seconds,
                                initial=initial, final=final)
                                                                
        v, y, x = diffusion3Dnpi_params(params, points=points, centered=False)

        if centered is True:
            for idx in xrange(3):
                x[idx] = x[idx] - (lengths_microns[idx] / 2.)

        if plot3 is True:
            try:
                if figaxis3 is None:
                    f, ax = styles.plot_3panels(x, y, figaxis3=figaxis3, 
                                                top=top, centered=centered,
                                                styles3=styles3, 
                                                lengths=lengths_microns)
                    return f, ax, v, x, y
                else:
                    styles.plot_3panels(x, y, top=top, centered=centered, 
                                        styles3=styles3, figaxis3=figaxis3,
                                        lengths=lengths_microns)
                    return v, x, y
            except(TypeError):
                print
                print 'TypeError: problem in plot_3panels()'
                
        else:
            return v, x, y
            
#%% 3D whole-block: 3-dimensional diffusion with path integration
def diffusion3Dwb_params(params, data_x_microns=None, data_y_unit_areas=None, 
                          raypaths=None, erf_or_sum='erf', show_plot=True, 
                          fig_ax=None, style=None, need_to_center_x_data=True,
                          infinity=100, points=50, show_1Dplots=False):
    """ Diffusion in 3 dimensions with path integration.
    Requires setup with params_setup3Dwb
    """
    if raypaths is None:
        print 'raypaths must be in the form of a list of three abc directions'
        return

    # v is the model 3D array of internal concentrations
    ### Need to add in all the keywords ###
    v, sliceprofiles, slicepositions = diffusion3Dnpi_params(params, 
                    points=points, erf_or_sum=erf_or_sum,
#                    need_to_center_x_data=need_to_center_x_data
                    )

    
    # Fitting to data or not? Default is not
    # Add appropriate x and y data to fit
    fitting = False
    if (data_x_microns is not None) and (data_y_unit_areas is not None):
        x_array = np.array(data_x_microns)
        y_array = np.array(data_y_unit_areas)
        if np.shape(x_array) == np.shape(y_array):
            print 'fitting to data'
            fitting = True
        else:
            print 'x and y data must be the same shape'
            print 'x', np.shape(x_array)
            print 'y', np.shape(y_array)
            
    # Whole-block measurements can be obtained through any of the three 
    # planes of the whole-block, so profiles can come from one of two ray path
    # directions. These are the planes.
    raypathA = v.mean(axis=0)
    raypathB = v.mean(axis=1)
    raypathC = v.mean(axis=2)

    # Specify whole-block profiles in model
    mid = points/2
    if raypaths[0] == 'b':
        wbA = raypathB[:, mid]
    elif raypaths[0] == 'c':
        wbA = raypathC[:, mid]       
    else:
        print 'raypaths[0] for profile || a must be "b" or "c"'
        return
        
    if raypaths[1] == 'a':
        wbB = raypathA[:, mid]
    elif raypaths[1] == 'c':
        wbB = raypathC[mid]       
    else:
        print 'raypaths[1] for profile || b must be "a" or "c"'
        return

    if raypaths[2] == 'a':
        wbC = raypathA[mid]
    elif raypaths[2] == 'b':
        wbC = raypathB[mid]       
    else:
        print 'raypaths[2] for profile || c must be "a" or "b"'
        return

    p = params.valuesdict()
    L3 = p['microns3']
    
    wb_profiles = [wbA, wbB, wbC]
    wb_positions = []
    for k in range(3):
        a = L3[k] / 2.
        x_microns = np.linspace(0., 2.*a, points)
        wb_positions.append(x_microns)
        
    if show_plot is True:
        if style is None:
            style = [None, None, None]
            for k in range(3):
                style[k] = styles.style_lightgreen

        if fig_ax is None:
            f, fig_ax = styles.plot_3panels(wb_positions, wb_profiles, L3, style)
        else:
            styles.plot_3panels(wb_positions, wb_profiles, L3, style, 
                         figaxis3=fig_ax)                         

    if fitting is False:        
        return wb_positions, wb_profiles
    
    if fitting is True:
        # Return residuals 
        y_model = []
        y_data = []
        residuals = []
        for k in range(3):
            for pos in range(len(x_array[k])):
                # wb_positions are centered, data are not
                microns = x_array[k][pos]
                # Find the index of the full model whole-block value 
                # closest to the data positions
                idx = (np.abs(wb_positions[k]-microns).argmin())
                
                model = wb_profiles[k][idx]
                data = y_array[k][pos]
                res = model - data
                
                y_model.append(model)
                y_data.append(data)
                residuals.append(res)                
        return residuals

def diffusion3Dwb(lengths_microns, log10Ds_m2s, time_seconds, raypaths,
                   initial=1., final=0., top=1.2, points=50., show_plot=True,
                   figax=None, isotropic=False):
        """Takes list of 3 lengths, list of 3 diffusivities, and time.
        Returns plot of 3D path-averaged (whole-block) diffusion profiles"""
        params = params_setup3D(lengths_microns, log10Ds_m2s, time_seconds,
                                initial=initial, final=final)

        return params
        
        x, y = diffusion3Dwb_params(params, raypaths=raypaths, show_plot=False,
                                    points=points)

        if show_plot is True:
            if figax is None:
                f, ax = styles.plot_3panels(x, y, top=top)
                return f, ax, x, y
            else: 
                styles.plot_3panels(x, y, top=top, figaxis3=figax)
        return x, y

        
#%% Arrhenius diagram
def Arrhenius_outline(low=6., high=11., bottom=-18., top=-8.,
                      celsius_labels = np.arange(0, 2000, 100),
                      figsize_inches = (6, 4), shrinker_for_legend = 0.3,
                      generic_legend=True, sunk=-2., ncol=2):
    """Make Arrhenius diagram outline. Returns figure, axis, legend handle"""
    fig = plt.figure(figsize=figsize_inches)
    ax = SubplotHost(fig, 1,1,1)
    ax_celsius = ax.twin()
    parasite_tick_locations = 1e4/(celsius_labels + 273.15)
    ax_celsius.set_xticks(parasite_tick_locations)
    ax_celsius.set_xticklabels(celsius_labels)
    fig.add_subplot(ax)
    ax.axis["bottom"].set_label("10$^4$/Temperature (K$^{-1}$)")
    ax.axis["left"].set_label("log$_{10}$diffusivity (m$^{2}$/s)")
    ax_celsius.axis["top"].set_label("Temperature ($\degree$C)")
    ax_celsius.axis["top"].label.set_visible(True)
    ax_celsius.axis["right"].major_ticklabels.set_visible(False)
    ax.set_xlim(low, high)
    ax.set_ylim(bottom, top)
    ax.grid()
    
    # main legend below
    legend_handles_main = []
    box = ax.get_position()
    ax.set_position([box.x0, box.y0 + box.height*shrinker_for_legend, 
                     box.width, box.height*(1.0-shrinker_for_legend)])
    main_legend = plt.legend(handles=legend_handles_main, numpoints=1, 
                             ncol=ncol, 
                             bbox_to_anchor=(low, bottom, high-low, sunk),
                             bbox_transform=ax.transData, mode='expand')
    plt.gca().add_artist(main_legend)
    return fig, ax, legend_handles_main

def Arrhenius_add_line(fig_ax, Ea, D0, low=6.0, high=10.0, 
                       style={'color' : 'k', 'linestyle' : '-'}):
    """Takes figure axis from above, Ea activation energy in kJ/mol, D0 in m2/s
    Plots Arrhenius line from 1E4/T = low to high"""
    T = 1E4 / np.linspace(low, high) 
    log10D = np.log10(D0) - (Ea/(2.303 * GAS_CONSTANT * T))
    fig_ax.plot(1E4 / T, log10D, **style)

def solve_Ea_D0(log10D_list, celsius_list):
    """Takes list of diffusivities as log10 in m2/s and associated 
    temperatures in celsius. 
    Returns activation energy Ea in kJ/mol K and D0 in m2/s.
    The errors on the individual diffusivities are not included.
    """
    T = np.array(celsius_list) + 273.15
    x = 1.E4 / T
    y = np.array(log10D_list)

    if (len(x) < 2) or (len(y) < 2):
        print 'Warning: fitting to only one point'
        return None, None
    
    # If I don't add in a very low weighted extra number, the covariance
    # matrix, and hence the error, comes out as infinity. The actual
    # fitting results don't change.
    x_extra = np.concatenate((x, x[-1:]), axis=0)
    y_extra = np.concatenate((y, y[-1:]), axis=0)    
    weights = list(np.ones(len(x))) + [sys.float_info.epsilon]

    fit_extra, cov_extra = np.polyfit(x_extra, y_extra, 1, w=weights, cov=True)

    if cov_extra[0][0] > 0:
        Ea_error = cov_extra[0][0]
    else:
        Ea_error = 0.

    if cov_extra[1][1] > 0:
        D0_error = cov_extra[1][1]
    else:
        D0_error = 0.

    Ea_extra = -ufloat(fit_extra[0], Ea_error) * 2.303 * GAS_CONSTANT * 1.E4
    D0_extra = 10.**ufloat(fit_extra[1], D0_error)
    return Ea_extra, D0_extra

def whatIsD(Ea, D0, celsius, printout=True):
    """ Takes activation energy in kJ/mol, D0 in m2/s and 
    temperature in celsius. Returns log10 diffusivity in m2/s"""
    T = celsius + 273.15
    D = D0 * np.exp(-Ea / (GAS_CONSTANT * T))
    if printout is True:
        print 'log10 D at ', celsius, 'C: ', '{:.1f}'.format(np.log10(D)), ' in m2/s'
    return np.log10(D)

#%%
def get_iorient(orient):
    """Converts x, y, z, u to 0, 1, 2, 3"""
    if orient == 'x':
        iorient = 0
    elif orient == 'y':
        iorient = 1
    elif orient == 'z':
        iorient = 2
    elif orient == 'u':
        iorient = 3
    else:
        iorient = orient
    return iorient
        
class Diffusivities():

    def __init__(self, description=None, celsius_all=None, logD_all=[],
                 celsius_unoriented = [], 
                 celsius_x = [], celsius_y = [], celsius_z = [], 
                 logDx = [], logDy = [], logDz = [], logD_unoriented = [], 
                 logD_all_error = [],   
                 logDx_error = [], logDy_error = [], logDz_error = [], 
                 logDu_error = [], basestyle = styles.style_points_tiny, 
                 activation_energy_kJmol = [None, None, None, None], 
                 logD0 = [None, None, None, None], 
                 Fe2=None, Fe3=None, Mg=None, Al=None, Ti=None,
                 color=None,
                 marker=None, markersize=None, mew=1., alpha=1., error=[]):

        """All logarithms of diffusivities, logD, are base 10 and m2/s.
        Order is || x, || y, ||z, not oriented or isotropic"""
        self.description = description
        self.celsius_all = celsius_all
        self.basestyle = basestyle.copy()
        
        if celsius_all is not None:
            celsius_x = celsius_all
            celsius_y = celsius_all
            celsius_z = celsius_all
            celsius_unoriented = celsius_all
            
        if len(logD_all) > 0:
            logDx = logD_all
            logDy = logD_all
            logDz = logD_all
            logD_unoriented = logD_all
            
        if len(logD_all_error) > 0:
            logDx_error = logD_all_error
            logDy_error = logD_all_error
            logDz_error = logD_all_error
            logDu_error = logD_all_error
            
        self.celsius = [celsius_x, celsius_y, celsius_z, celsius_unoriented]
        self.logD = [logDx, logDy, logDz, logD_unoriented]
        self.logD_error = [logDx_error, logDy_error, logDz_error, logDu_error]
        self.activation_energy_kJmol = activation_energy_kJmol
        self.logD0 = logD0

        if color is not None:
            self.basestyle['color'] = color
        if marker is not None:
            self.basestyle['marker'] = marker
        if markersize is not None:
            self.basestyle['markersize'] = markersize
        if mew is not None:
            self.basestyle['mew'] = mew
        if alpha is not None:
            self.basestyle['alpha'] = alpha                                       

        self.Fe2 = Fe2
        self.Fe3 = Fe3
        self.Mg = Mg
        self.Al = Al
        self.Ti = Ti
        if (Fe2 is not None) and (Fe3 is not None):
            self.Fe = Fe2 + Fe3

    def get_MgNumber(self):
        try:
            MgNum = 100. * self.Mg / (self.Fe + self.Mg)
        except TypeError:
            print self.description
            print 'Check Mg and Fe are not None'
        else:
            return MgNum
            
    def picker_DCelsius(self, orient=None):
        """Returns lists of log10D in m2/s and temperatures in Celsius
        of Diffusivities object for specified orientation"""
        iorient = get_iorient(orient)
        try:
            logD_of_interest = self.logD[iorient]
            celsius_of_interest = self.celsius[iorient]
        except TypeError:
            print ''.join(("orient must be an integer 0-3 or", 
                           "'x' (=0), 'y' (=1), 'z' (=2), or 'u' (=3) for unoriented"))
        except IndexError:
            print ''.join(("orient must be an integer 0-3 or", 
                           "'x'=0, 'y'=1, 'z'=2, or 'u'=3 for unoriented"))
        else:
            return logD_of_interest, celsius_of_interest
        
    def solve_Ea_D0(self, orient=None):
        """Returns activation energy in kJ/mol and D0 in m2/s for 
        diffusivity estimates""" 
        
        logD_and_Celsius = self.picker_DCelsius(orient=orient)        

        if logD_and_Celsius is None:
            print 'Problem with self.picker_DCelsius()'
            return None            
        else:
            logD = logD_and_Celsius[0]
            celsius = logD_and_Celsius[1]

        if (len(logD) < 2) or (len(celsius) < 2):
            print
            print 'Only one point for orientation', orient
            print 'logD:', logD
            print 'celsius:', celsius
            print
            return None

        Ea, D0 = solve_Ea_D0(logD, celsius)
        return Ea, D0

    def whatIsD(self, celsius, orient='ALL', printout=True):
        """ Takes temperature in celsius. Returns log10 diffusivity in m2/s.
        """
        D = []  
        if orient == 'ALL':
            for idx, direction in enumerate(['x', 'y', 'z', 'u']):
                if len(self.logD[idx]) > 0:
                    Ea_and_D0 = self.solve_Ea_D0(orient=direction)
                    if Ea_and_D0 is not None:
                        xD = whatIsD(Ea_and_D0[0].n, Ea_and_D0[1].n, 
                                     celsius, printout=False)
                        D.append(xD)
                else:
                    D.append(None)
#                        D = D.append(whatIsD(Ea_and_D0[0].n, Ea_and_D0[1].n, 
#                                             celsius, printout=False))
#                print D
                    
        else:
            Ea_and_D0 = self.solve_Ea_D0(orient=orient)
            if Ea_and_D0 is None:
                print 'Problem with self.solve_Ea_D0()'
                return None
            D = whatIsD(Ea_and_D0[0].n, Ea_and_D0[1].n, celsius, 
                        printout=printout)
            
        return D
        
    def get_from_wholeblock(self, peak_idx=None, print_diffusivities=False,
                            wholeblock=True, heights_instead=False):
        """Grab diffusivities from whole-block"""
        self.celsius_all = []
        D = [[], [], []]
        error = [[], [], []]

        for wb in self.wholeblocks:
            if wb.temperature_celsius is None:
                print wb.name, 'needs temperature_celsius attribute'
                return

            wb.get_diffusivities()
            
            if print_diffusivities is True:
                wb.print_diffusivities()
            
            self.celsius_all.append(wb.temperature_celsius)

            if wholeblock is True:
                if peak_idx is None:
                    for k in range(3):
                        D[k].append(wb.profiles[k].D_area_wb)
                        error[k].append(wb.profiles[k].D_area_wb_error)
                else:
                    if heights_instead is False:
                        for k in range(3):
                            D[k].append(wb.profiles[k].D_peakarea_wb[peak_idx])
                            error[k].append(wb.profiles[k].D_peakarea_wb_error[peak_idx])
                    else:
                        for k in range(3):
                            D[k].append(wb.profiles[k].D_height_wb[peak_idx])
                            error[k].append(wb.profiles[k].D_height_wb_error[peak_idx])
            else:
                print 'Sorry, only working with wholeblock data so far'
                return
                
        self.logDx = D[0]
        self.logDy = D[1]
        self.logDz = D[2]
        self.logDx_error = error[0]
        self.logDy_error = error[1]
        self.logDz_error = error[2]

    def make_styles(self, orient):
        """Marker and line styles for plotting and adding to the legend"""
        iorient = get_iorient(orient)
        style = self.basestyle.copy()
        style['linestyle'] = 'None'

#        if orient is None:
        style['fillstyle'] = 'full'
#            style_line = styles.style_orient_lines[3].copy()
#            style_line['linestyle'] = '-'
#            
#        else:
#        style['fillstyle'] = styles.style_orient[iorient]['fillstyle']
        style_line = styles.style_orient_lines[iorient].copy()

        style_line['color'] = style['color']
        
        return style, style_line

    def plotD(self, fig_axis, orient='ALL', plotdata=True,
              offset_celsius=0, plotline=True, extrapolate_line=False,
              show_error=True, legend_add=False, legendlabel=None, 
              legend_handle=None, style=None, ecolor=None, 
              style_line=None, label=None, oriented_shading=True):
        """Takes axis label for Arrhenius diagram created by 
        Arrhenius_outline() and plots data (plotdata=True) and 
        best-fit line (plotline=True) for specified orientations, 
        default: orient='ALL'. """
        if orient == 'ALL':
            orient_list = range(4)
        else:
            iorient = get_iorient(orient)    
            orient_list = [iorient]
                  
        for iorient in orient_list:
            celsius = self.celsius[iorient]
            logD = self.logD[iorient]
            Derror = self.logD_error[iorient]

            if orient == 'ALL':
                label = None
#                style = None
#                style_line = None
                
            if label is None:
                if iorient == 0:
                    label = '|| [100]'
                elif iorient == 1:
                    label = '|| [010]'
                elif iorient == 2:
                    label = '|| [001]'
                elif iorient == 3:
                    label = 'not oriented'                   

            if style is None:
                style, _ = self.make_styles(iorient)
#    
            if (style_line is None) and (plotline is True):
                _, style_line = self.make_styles(iorient)
#                
            if legend_add is True and legend_handle is None:
                print self.description
                print 'Need legend_handle for legend'
                return
               
            if (len(celsius) == 0) and (self.celsius_all is not None):
                celsius = self.celsius_all

            if (len(celsius) == 0):
                continue
    
            if logD is None:
                continue
    
            if len(celsius) != len(logD):
                print '\n', self.description
                print 'temp and logD not the same length'
                continue
    
            # change temperature scale                   
            x = []
            for k in range(len(celsius)):
                x.append(1.0e4 / (celsius[k] + offset_celsius + 273.15))

            if show_error is True:
                if len(Derror) > 0:
                    if ecolor is None:
                        ecolor = style['color']
                    fig_axis.errorbar(x, logD, yerr=Derror, ecolor=ecolor,
                                      fmt=None)

            if plotline is True:
                if 'markerfacecolor' in self.basestyle:
                    style_line['color'] = self.basestyle['markerfacecolor']
                elif 'color' in self.basestyle:
                    style_line['color'] = self.basestyle['color']
                else:
                    style_line['color'] = 'k'
    
                Tmin = min(x)
                Tmax = max(x)
                T = [Tmin, Tmax]
                p = np.polyfit(x, logD, 1)
                
                if extrapolate_line is True:
                    extrap = fig_axis.get_xlim()
                    fig_axis.plot(extrap,np.polyval(p, extrap), **style_line)
                else:
                    fig_axis.plot(T,np.polyval(p, T), **style_line)
                   
            fig_axis.plot(x, logD, label=legendlabel, **style)
            
            if legend_add is True:
                self.add_to_legend(fig_axis, legend_handle, style=style,
                                   style_line=style_line, plotline=plotline,
                                   oriented_shading=oriented_shading)
    
            
    def add_to_legend(self, fig_axis, legend_handle_list, sunk=-2.0,
                      orient=None, plotline=False,
                      ncol=2, oriented_shading=False, 
                      style=None, style_line=None, label=None):
        """Take a figure axis and its list of legend handles 
        and adds information to it"""
        if label is None:
            if self.description is None:
                print 'Need label or self.description to make legend'
                return
            else:
               descript = self.description
        else:
            descript = label

        if style is None:
            style, _ = self.make_styles(orient)

        if plotline is True:
            if style_line is None:
                _, style_line = self.make_styles(orient)
            style['linestyle'] = style_line['linestyle']
        
        add_marker = mlines.Line2D([], [], label=descript, **style) 
        
        legend_handle_list.append(add_marker)
        
        low = fig_axis.get_xlim()[0]
        high = fig_axis.get_xlim()[1]
        bottom = fig_axis.get_ylim()[0]
        main_legend = plt.legend(handles=legend_handle_list, 
                                 numpoints=1, ncol=ncol, 
                                 bbox_to_anchor=(low, bottom, high-low, sunk),
                                 bbox_transform=fig_axis.transData, 
                                 mode='expand')
        plt.gca().add_artist(main_legend)
        return legend_handle_list

generic = Diffusivities()
generic.basestyle = {'marker' : 's', 'color' : 'black', 'alpha' : 0.5,
                     'markersize' : 8, 'linestyle': 'none'}
