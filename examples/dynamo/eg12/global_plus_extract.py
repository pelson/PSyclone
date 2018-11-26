# -----------------------------------------------------------------------------
# BSD 3-Clause License
#
# Copyright (c) 2017-2018, Science and Technology Facilities Council
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# -----------------------------------------------------------------------------
# Authors: R. Ford and A. R. Porter, STFC Daresbury Laboratory
# Modified: I. Kavcic, Met Office


''' File containing a PSyclone transformation script for the Dynamo0p3
API to apply colouring and OpenMP generically. This can be applied via
the -s option in the generator.py script. '''
from __future__ import print_function
from psyclone.transformations import Dynamo0p3ColourTrans, \
    DynamoOMPParallelLoopTrans, ExtractRegionTrans
from psyclone.psyGen import Loop, Kern, Node
from psyclone.dynamo0p3 import DISCONTINUOUS_FUNCTION_SPACES
from psyclone.extractor import Extractor

invoke_extract_name = "1"
invoke_name = "invoke_" + invoke_extract_name.lower()
kernel_name = "matrix_vector_code"

def trans(psy):
    ''' PSyclone transformation script for the dynamo0p3 api to apply
    colouring and OpenMP generically.'''
    ctrans = Dynamo0p3ColourTrans()
    otrans = DynamoOMPParallelLoopTrans()

    # Loop over all of the Invokes in the PSy object
    for invoke in psy.invokes.invoke_list:

        print("Transforming invoke '"+invoke.name+"'...")
        schedule = invoke.schedule

        # Colour all of the loops over cells unless they are on
        # discontinuous spaces (W3, WTHETA and W2V)
        cschedule = schedule
        for child in schedule.children:
            if isinstance(child, Loop) \
               and child.field_space.orig_name \
               not in DISCONTINUOUS_FUNCTION_SPACES \
               and child.iteration_space == "cells":
                cschedule, _ = ctrans.apply(child)
        # Then apply OpenMP to each of the colour loops
        schedule = cschedule
        for child in schedule.children:
            if isinstance(child, Loop):
                if child.loop_type == "colours":
                    schedule, _ = otrans.apply(child.children[0])
                else:
                    schedule, _ = otrans.apply(child)

        if invoke.name == invoke_name:
            #eobj = Extractor()
            #schedule = extract(schedule, kernel_name, invoke_name)
            schedule = Extractor.extract_kernel(schedule, kernel_name)
            #print(type(eobj))
            #print(type(eobj.extract_kernel))
            #schedule = eobj.extract_kernel(schedule, kernel_name)

        #schedule.view()
        invoke.schedule = schedule

    return psy


#def extract(schedule, kernel_name, invoke_name):
    #''' Extract function for a specific kernel and invoke '''
    ## Find the kernel and invoke to extract

    #etrans = ExtractRegionTrans()

    #for kernel in schedule.walk(schedule.children, Kern):
        #if kernel.name == kernel_name:
            #extract_parent = kernel.root_at_depth(1)

    #modified_schedule, _ = etrans.apply(extract_parent)

    #return modified_schedule