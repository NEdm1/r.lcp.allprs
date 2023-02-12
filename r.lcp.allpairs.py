#!/usr/bin/env python

############################################################################
#
# MODULE:    r.lcp.allpairs
# AUTHOR(S): Nagy Edmond
# PURPOSE:	 Script for generating least-cost vector paths between
#                each pair of input vector points via r.cost or r.walk,
#                and r.drain.
# COPYRIGHT: (C) 2017 by Nagy Edmond, and the GRASS Development Team
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
############################################################################

#%module
#% description: Creates least-cost vector paths with r.cost/r.walk and r.drain.
#% keyword: vector
#% keyword: r.cost
#% keyword: r.walk
#% keyword: r.drain
#%end

#%option G_OPT_V_INPUT
#% description: Input vector points
#% required: yes
#%end

#%option G_OPT_R_INPUT
#% key: frict
#% description: Input friction raster
#% required: yes
#%END

#%option G_OPT_V_OUTPUT
#% description: Output vector lines
#% required: yes
#%end

#%flag
#% key: k
#% description: Slower but more accurate outputs (with flag -k)
#%end

#%flag
#% key: w
#% description: Run module using r.walk (with flag -w) (r.cost by default)
#%end

#%option
#% key: m
#% type: integer
#% description: Maximum cumulative cost
#%answer: 0
#%end

#%option
#% key: memory
#% type: integer
#% description: Amount of memory to use (in MB)
#%answer: 500
#%end

#%option G_OPT_R_INPUT
#% key: elev
#% description: Input DEM (r.walk only, and is mandatory)
#% required: no
#%END

#%option
#% key: a
#% type: double
#% description: Coefficient for walking energy formula parameter A (r.walk only)
#%answer: 0.72
#%end

#%option
#% key: b
#% type: double
#% description: Coefficient for walking energy formula parameter B (r.walk only)
#%answer: 6.0
#%end

#%option
#% key: c
#% type: double
#% description: Coefficient for walking energy formula parameter C (r.walk only)
#%answer: 1.9998
#%end

#%option
#% key: d
#% type: double
#% description: Coefficient for walking energy formula parameter D (r.walk only)
#%answer: -1.9998
#%end

#%option
#% key: l
#% type: double
#% description: Lambda coefficient (r.walk only)
#%answer: 1.0
#%end

#%option
#% key: s
#% type: double
#% description: Slope factor coefficient (r.walk only)
#%answer: -0.2125
#%end


import sys
import grass.script as grass


def main():

    # get the options and set parameter variables
    options, flags = grass.parser()

    vInput      = options["input"]
    vOutput     = options["output"]
    friction    = options["frict"]
    elevation   = options["elev"]
    maxCost     = options["m"]
    memory      = options["memory"]
    lambd       = options["l"]
    slopeF      = options["s"]
    
    walkCo      = ""
    for option in ("a", "b", "c", "d"):
        parameter = options[option]
        walkCo = walkCo + str(parameter) + ","
    walkCo = walkCo[:-1] # the coefficients used in r.walk
    
    count = 0         # for naming temporary outputs
    VleastcpList = [] # to store the individual lcp vectors
    
    # see if the input is valid
    pointnb = grass.vector_info_topo(map=vInput)['points']
    
    if int(pointnb) < 2:
        grass.error(_("There are too few or no point features in the input. There have to be at least two."))

    else:
        if (flags["w"] == True) and (options["elev"] == ""):
            grass.warning(_("No elevation raster map (DEM) detected. Using r.cost then."))
        
        # run operation based on user choice
        vInputCoordsInfo = grass.read_command("v.out.ascii", flags="r", input=vInput, type="point",
                                              format="point", separator=",").strip()
        coordList = []
        for line in vInputCoordsInfo.splitlines():
            if line:
                coordsInfo = line.strip().split(",")
                coordList.append(coordsInfo[0] + "," + coordsInfo[1])
        
        grass.message(_("Creating individual least-cost paths."))
        
        # start the loop
        for pos in coordList:
            count += 1

            if (flags["w"] == True) and (options["elev"] != ""):
                # reading the r.walk command - because flag is ticked
                if flags["k"]:
                    grass.read_command("r.walk", flags="k", elevation=elevation, quiet=True,
                                       friction=friction, output="costCumul", outdir="movmDir",
                                       start_coordinates=pos, stop_coordinates=coordList,
                                       max_cost=maxCost, slope_factor=slopeF, walk_coeff=walkCo,
                                       lambd=lambd, memory=memory, overwrite=True)
                else:
                    grass.read_command("r.walk", elevation=elevation, quiet=True, friction=friction,
                                       output="costCumul", outdir="movmDir", lambd=lambd, memory=memory,
                                       start_coordinates=pos, stop_coordinates=coordList,
                                       max_cost=maxCost, slope_factor=slopeF, walk_coeff=walkCo,
                                       overwrite=True)
            else:
                # reading the r.cost command by default
                if flags["k"]:
                    grass.read_command("r.cost", flags="k", input=friction, output="costCumul",
                                       outdir="movmDir", start_coordinates=pos,
                                       stop_coordinates=coordList, max_cost=maxCost, quiet=True,
                                       memory=memory, overwrite=True)
                else:
                    grass.read_command("r.cost", input=friction, output="costCumul", quiet=True,
                                       outdir="movmDir", start_coordinates=pos,
                                       stop_coordinates=coordList, max_cost=maxCost, memory=memory,
                                       overwrite=True)
                
            # run the r.drain command
            grass.run_command("r.drain", flags="d", input="costCumul", direction="movmDir",
                              output="rdrainRast", drain="rdrainVect" + str(count), quiet=True,
                              overwrite=True, start_coordinates=coordList)
                
            if int(pointnb) == 2:
                # finish the final output - clean it and remove the "rdrainVect" leftover
                grass.run_command("v.clean", input="rdrainVect" + str(count), type="line",
                                  output=vOutput, tool="rmline,rmdupl", quiet=True)
                grass.run_command("g.remove", quiet=True, flags="f", type="vector",
                                  name="rdrainVect" + str(count))
                
            else:
                # create the network by appending "rdrainVect, but also remove it after that
                if count == 1:
                    VleastcpList.append("rdrainVect" + str(count))
                elif count == 2:
                    VleastcpList.append("rdrainVect" + str(count))
                    grass.run_command("v.patch", quiet=True, output="network",
                                      input=(",").join(VleastcpList))
                    grass.run_command("g.remove", quiet=True, flags="f", type="vector",
                                      name=(",").join(VleastcpList))
                else:
                    grass.run_command("v.patch", flags="a", quiet=True, overwrite=True,
                                      input="rdrainVect" + str(count), output="network")
                    grass.run_command("g.remove", quiet=True, flags="f", type="vector",
                                      name="rdrainVect" + str(count))
        
        # finish the final network output
        if int(pointnb) > 2:
            grass.message(_("Finishing the final vector output."))
            grass.run_command("v.clean", input="network", type="line", output=vOutput,
                              tool="rmline,rmdupl", quiet=True)
            grass.run_command("g.remove", quiet=True, flags="f", type="vector", name="network")

        # add tables to the final output and remove the other leftovers
        grass.run_command("v.db.addtable", map=vOutput, quiet=True)
        grass.run_command("g.remove", quiet=True, flags="f", type="raster",
                          name="costCumul,movmDir,rdrainRast")
    
    return

if __name__ == "__main__":
    sys.exit(main())
