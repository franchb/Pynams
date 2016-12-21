# -*- coding: utf-8 -*-
"""
Created on Tue May 05 08:16:08 2015
@author: Ferriss

Provides basic plotting and functions for creating Arrhenius diagrams and 
handling groups of diffusivities that get plotted on them, including 
determining activation energies and pre-exponential terms and calculating
the expected diffusivity at a given temperature.

class Diffusivities() groups together temperatures and diffusivities
for use in plotting directly onto Arrhenius diagrams and solving 
for activation energies and pre-exponential components

"""
from pynams import styles
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from mpl_toolkits.axes_grid1.parasite_axes import SubplotHost
from pynams.uncertainties import ufloat
import sys

GAS_CONSTANT = 0.00831 # kJ/mol K

def solve_Ea_D0(log10D_list, celsius_list):
    """Takes lists of diffusivities as log10 in m2/s and associated 
    temperatures in celsius. Returns activation energy Ea in kJ/mol K and D0 
    in m2/s. The errors on the individual diffusivities are not included.
    """
    T = np.array(celsius_list) + 273.15
    x = 1.E4 / T
    y = np.array(log10D_list)

    if (len(x) < 2) or (len(y) < 2):
        print 'Warning: fitting to only one point'
        return None, None
    
    # If I don't add in a very low weighted extra number, the covariance
    # matrix, and hence the error, comes out as infinity. The actual
    # fitting results don't change. The very low number in this case I'm 
    # getting from sys.float_info.
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

def get_iorient(orient):
    """Converts x, y, z, u to 0, 1, 2, 3. This is a helper function for 
    bound methods in class diffusivitiy later on"""
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
    def __init__(self, description=None, 
                 celsius_x=[], celsius_y=[], celsius_z=[], celsius_u=[], 
                 logDx=[], logDy=[], logDz=[], logDu=[], 
                 logDx_error=[], logDy_error=[], logDz_error=[], 
                 logDu_error=[],                  
                 celsius_all=None, logD_all=[], logD_all_error = [], 
                 activation_energy_kJmol = [None, None, None, None], 
                 logD0 = [None, None, None, None], 
                 sample=None, basestyle = styles.style_points, 
                 ):
        """
        Groups together temperatures and diffusivities for measurements
        for use in easy plotting directly onto Arrhenius diagrams
        
        You can include lists of temperatures in celsius in 3 directions
        (abc=xyz=[100], [010], [001] here) and unoriented (u), and of their 
        associated diffusivities, input as log base 10 and in m2/s, and the
        errors in those diffusivities. 
        
        You can also ignore directions and just input temperatures and/or
        diffusivities for all measurements.
        
        The activations energies and pre-exponential factors are input as lists
        ordered as [a, b, c, unoriented]. They can also be determined by the 
        code for you [need to clarify by which functions]. 
        
        It can be convenient to link to compositional information here
        by specifying the sample.
        
        The basestyle and marker information are just to change how the 
        points show up when plotted on an Arrhenius diagram.
        
        """
        self.description = description
        self.celsius_all = celsius_all
        self.basestyle = basestyle.copy()
        self.sample = sample
        
        if celsius_all is not None:
            celsius_x = celsius_all
            celsius_y = celsius_all
            celsius_z = celsius_all
            celsius_u = celsius_all
            
        if len(logD_all) > 0:
            logDx = logD_all
            logDy = logD_all
            logDz = logD_all
            logDu = logD_all
            
        if len(logD_all_error) > 0:
            logDx_error = logD_all_error
            logDy_error = logD_all_error
            logDz_error = logD_all_error
            logDu_error = logD_all_error
            
        self.celsius = [celsius_x, celsius_y, celsius_z, celsius_u]
        self.logD = [logDx, logDy, logDz, logDu]
        self.logD_error = [logDx_error, logDy_error, logDz_error, logDu_error]
        self.activation_energy_kJmol = activation_energy_kJmol
        self.logD0 = logD0

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
                                     celsius, printout=printout)
                        D.append(xD)
                else:
                    D.append(None)
        else:
            Ea_and_D0 = self.solve_Ea_D0(orient=orient)
            if Ea_and_D0 is None:
                print 'Problem with self.solve_Ea_D0()'
                return None
            D = whatIsD(Ea_and_D0[0].n, Ea_and_D0[1].n, celsius, 
                        printout=printout)
            
        return D
        
#    def get_from_wholeblock(self, peak_idx=None, print_diffusivities=False,
#                            wholeblock=True, heights_instead=False):
#        """Grab diffusivities from whole-block"""
#        self.celsius_all = []
#        D = [[], [], []]
#        error = [[], [], []]
#
#        for wb in self.wholeblocks:
#            if wb.temperature_celsius is None:
#                print wb.name, 'needs temperature_celsius attribute'
#                return
#
#            wb.get_diffusivities()
#            
#            if print_diffusivities is True:
#                wb.print_diffusivities()
#            
#            self.celsius_all.append(wb.temperature_celsius)
#
#            if wholeblock is True:
#                if peak_idx is None:
#                    for k in range(3):
#                        D[k].append(wb.profiles[k].D_area_wb)
#                        error[k].append(wb.profiles[k].D_area_wb_error)
#                else:
#                    if heights_instead is False:
#                        for k in range(3):
#                            D[k].append(wb.profiles[k].D_peakarea_wb[peak_idx])
#                            error[k].append(wb.profiles[k].D_peakarea_wb_error[peak_idx])
#                    else:
#                        for k in range(3):
#                            D[k].append(wb.profiles[k].D_height_wb[peak_idx])
#                            error[k].append(wb.profiles[k].D_height_wb_error[peak_idx])
#            else:
#                print 'Sorry, only working with wholeblock data so far'
#                return
#                
#        self.logDx = D[0]
#        self.logDy = D[1]
#        self.logDz = D[2]
#        self.logDx_error = error[0]
#        self.logDy_error = error[1]
#        self.logDz_error = error[2]

    def plotD(self, fig_axis, orient='ALL', plotdata=True,
              offset_celsius=0, plotline=True, extrapolate_line=False,
              show_error=True, legend_add=False, legendlabel=None, 
              legend_handle=None, style=None, ecolor=None, 
              style_line=None, label=None, oriented_shading=True):
        """Takes axis label for Arrhenius diagram created by 
        Arrhenius_outline() below and plots data (plotdata=True) and 
        best-fit line (plotline=True) for specified orientations, 
        default: orient='ALL'. If extrapolate_line=True, the line will
        be extended all the way to the edges of the plot. You can also 
        add it to the legend or not."""
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
